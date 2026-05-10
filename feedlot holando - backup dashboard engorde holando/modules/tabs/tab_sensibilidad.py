from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from modules.config import COLORES_ESCENARIO
from modules.economics.scenarios import calcular_destete, calcular_recria, calcular_terminado

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador

# ── Variables para curvas de sensibilidad (sección 3) ────────────────────────
_VARIABLES = [
    "Precios de venta (todos)",
    "N° de terneros",
    "GDP / velocidad de crecimiento",
    "Mortalidad",
    "Conversión alimenticia (CA)",
    "Precio de alimento",
]


# ── Helpers para modificar params con inmutabilidad superficial ───────────────

def _mod_an(params: dict, **sub_updates) -> dict:
    """Return new params with animal_params sub-dicts updated."""
    an = dict(params["animal_params"])
    for sub, kv in sub_updates.items():
        if isinstance(kv, dict):
            an[sub] = {**an[sub], **kv}
        else:
            an[sub] = kv  # top-level key (e.g. n_terneros)
    return {**params, "animal_params": an}


def _mod_co(params: dict, **sub_updates) -> dict:
    co = dict(params["commercial_params"])
    for sub, kv in sub_updates.items():
        if isinstance(kv, dict):
            co[sub] = {**co[sub], **kv}
        else:
            co[sub] = kv
    return {**params, "commercial_params": co}


def _mod_fe(params: dict, **sub_updates) -> dict:
    fe = dict(params["feed_params"])
    for sub, kv in sub_updates.items():
        if isinstance(kv, dict):
            fe[sub] = {**fe[sub], **kv}
        else:
            fe[sub] = kv
    return {**params, "feed_params": fe}


def _params_modificados(params: dict, variable: str, mult: float) -> dict:
    an = params["animal_params"]
    co = params["commercial_params"]
    fe = params["feed_params"]

    if variable == "Precios de venta (todos)":
        return _mod_co(params,
            A={"precio_venta": co["A"]["precio_venta"] * mult},
            B={"precio_venta": co["B"]["precio_venta"] * mult},
            C={"precio_venta": co["C"]["precio_venta"] * mult},
        )
    elif variable == "N° de terneros":
        return _mod_an(params, n_terneros=max(1, int(an["n_terneros"] * mult)))
    elif variable == "GDP / velocidad de crecimiento":
        return _mod_an(params,
            B={"gdp": max(0.01, an["B"]["gdp"] * mult)},
            C={"gdp": max(0.01, an["C"]["gdp"] * mult)},
        )
    elif variable == "Mortalidad":
        return _mod_an(params,
            A={"mortalidad": max(0.0, min(0.99, an["A"]["mortalidad"] * mult))},
            B={"mortalidad": max(0.0, min(0.99, an["B"]["mortalidad"] * mult))},
            C={"mortalidad": max(0.0, min(0.99, an["C"]["mortalidad"] * mult))},
        )
    elif variable == "Conversión alimenticia (CA)":
        return _mod_an(params,
            B={"ca": max(1.0, an["B"]["ca"] * mult)},
            C={"ca": max(1.0, an["C"]["ca"] * mult)},
        )
    elif variable == "Precio de alimento":
        return _mod_fe(params,
            B={"precio_alimento": max(0.01, fe["B"]["precio_alimento"] * mult)},
            C={"precio_alimento": max(0.01, fe["C"]["precio_alimento"] * mult)},
        )
    return params


# ── Variables fijas para el tornado ──────────────────────────────────────────
# Cada entrada: getter(params) → float, setter(params, val) → params, clamp

_TORNADO_VARS: dict[str, dict] = {
    "Precio maíz (alim.)": {
        "getter": lambda p: p["feed_params"]["C"]["precio_alimento"],
        "setter": lambda p, v: _mod_fe(p,
            B={"precio_alimento": v},
            C={"precio_alimento": v},
        ),
        "clamp": lambda v: max(0.01, v),
    },
    "Precio novillo": {
        "getter": lambda p: p["commercial_params"]["C"]["precio_venta"],
        "setter": lambda p, v: _mod_co(p, C={"precio_venta": v}),
        "clamp": lambda v: max(0.01, v),
    },
    "Mortalidad feedlot": {
        "getter": lambda p: p["animal_params"]["C"]["mortalidad"],
        "setter": lambda p, v: _mod_an(p, C={"mortalidad": v}),
        "clamp": lambda v: max(0.0, min(0.99, v)),
    },
    "CA feedlot": {
        "getter": lambda p: p["animal_params"]["C"]["ca"],
        "setter": lambda p, v: _mod_an(p, C={"ca": v}),
        "clamp": lambda v: max(1.0, v),
    },
}


def _tornado_data(params: dict, pct: int) -> pd.DataFrame:
    """
    Calcula el impacto de variar ±pct% cada variable del tornado sobre el
    Escenario C.  Retorna DataFrame pivoteado, ordenado por rango de MB ascendente.
    """
    base = calcular_terminado(params)
    rows = []
    for label, spec in _TORNADO_VARS.items():
        for sign, case in [(-1, "low"), (1, "high")]:
            base_val = spec["getter"](params)
            new_val  = spec["clamp"](base_val * (1 + sign * pct / 100))
            p_var    = spec["setter"](params, new_val)
            t = calcular_terminado(p_var)
            rows.append({
                "Variable": label,
                "case": case,
                "mb_delta":  t.margen_bruto - base.margen_bruto,
                "roi_delta": t.roi_anual    - base.roi_anual,
            })

    df = pd.DataFrame(rows)
    pivot = df.pivot(index="Variable", columns="case", values=["mb_delta", "roi_delta"])
    pivot.columns = [f"{m}_{c}" for m, c in pivot.columns]
    pivot = pivot.reset_index()
    pivot["mb_range"] = (pivot["mb_delta_high"] - pivot["mb_delta_low"]).abs()
    return pivot.sort_values("mb_range", ascending=True)


def _chart_tornado(df: pd.DataFrame, pct: int, metric: str) -> go.Figure:
    if metric == "mb":
        col_low, col_high = "mb_delta_low", "mb_delta_high"
        xtitle    = "Δ Margen bruto — Esc. C (USD)"
        lows_txt  = [f"${v:+,.0f}" for v in df[col_low]]
        highs_txt = [f"${v:+,.0f}" for v in df[col_high]]
    else:
        col_low, col_high = "roi_delta_low", "roi_delta_high"
        xtitle    = "Δ ROI anual — Esc. C (pp)"
        lows_txt  = [f"{v:+.2f}pp" for v in df[col_low]]
        highs_txt = [f"{v:+.2f}pp" for v in df[col_high]]

    vars_list = df["Variable"].tolist()
    lows  = df[col_low].tolist()
    highs = df[col_high].tolist()
    c_low  = ["#27ae60" if v >= 0 else "#e74c3c" for v in lows]
    c_high = ["#27ae60" if v >= 0 else "#e74c3c" for v in highs]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=vars_list, x=lows, orientation="h", name=f"−{pct}%",
        marker_color=c_low, marker_line_width=0,
        text=lows_txt, textposition="outside", textfont=dict(size=10), opacity=0.88,
    ))
    fig.add_trace(go.Bar(
        y=vars_list, x=highs, orientation="h", name=f"+{pct}%",
        marker_color=c_high, marker_line_width=0,
        text=highs_txt, textposition="outside", textfont=dict(size=10), opacity=0.88,
    ))
    fig.add_vline(x=0, line_color="#5d6d7e", line_width=1.5, line_dash="dash")
    fig.update_layout(
        barmode="overlay", height=290, margin=dict(t=20, b=35, l=10, r=90),
        xaxis_title=xtitle,
        plot_bgcolor="rgba(248,249,250,1)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor="#e5e5e5"),
        yaxis=dict(showgrid=False),
        bargap=0.35,
    )
    if metric == "mb":
        fig.update_xaxes(tickprefix="$")
    else:
        fig.update_xaxes(ticksuffix=" pp")
    return fig


# ── Render principal ──────────────────────────────────────────────────────────

def render_tab_sensibilidad(params: dict, comp: "Comparador") -> None:
    an = params["animal_params"]
    co = params["commercial_params"]
    fe = params["feed_params"]

    esc_todos = [comp.destete, comp.recria, comp.terminado]

    # ════════════════════════════════════════════════════════════════════════════
    # Sección 1 — Ajuste directo de parámetros clave
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("#### Parámetros clave — ajuste directo (feedlot)")

    c1, c2, c3, c4 = st.columns(4)

    base_alim  = fe["C"]["precio_alimento"]
    base_pv    = co["C"]["precio_venta"]
    base_mort  = an["C"]["mortalidad"]
    base_ca    = an["C"]["ca"]

    with c1:
        st.markdown("**Precio maíz (USD/kg MS)**")
        if "sens_maiz" not in st.session_state:
            st.session_state["sens_maiz"] = float(max(0.05, min(0.80, base_alim)))
        precio_maiz = st.slider(
            "_maiz", 0.05, 0.80, step=0.01, format="%.2f",
            label_visibility="collapsed", key="sens_maiz",
        )
        st.caption(
            f"Base: **{base_alim:.2f}** &nbsp;·&nbsp; "
            f"Δ {precio_maiz - base_alim:+.2f}"
        )

    with c2:
        st.markdown("**Precio novillo (USD/kg)**")
        if "sens_novillo" not in st.session_state:
            st.session_state["sens_novillo"] = float(max(0.50, min(10.0, base_pv)))
        precio_novillo = st.slider(
            "_novillo", 0.50, 10.0, step=0.10, format="%.2f",
            label_visibility="collapsed", key="sens_novillo",
        )
        st.caption(
            f"Base: **{base_pv:.2f}** &nbsp;·&nbsp; "
            f"Δ {precio_novillo - base_pv:+.2f}"
        )

    with c3:
        st.markdown("**Mortalidad feedlot (%)**")
        if "sens_mort" not in st.session_state:
            st.session_state["sens_mort"] = float(max(0.0, min(20.0, base_mort * 100)))
        mort_pct = st.slider(
            "_mort", 0.0, 20.0, step=0.5, format="%.1f%%",
            label_visibility="collapsed", key="sens_mort",
        )
        st.caption(
            f"Base: **{base_mort * 100:.1f}%** &nbsp;·&nbsp; "
            f"Δ {mort_pct - base_mort * 100:+.1f} pp"
        )

    with c4:
        st.markdown("**CA feedlot (kg MS/kg PV)**")
        if "sens_ca" not in st.session_state:
            st.session_state["sens_ca"] = float(max(3.0, min(12.0, base_ca)))
        ca_feed = st.slider(
            "_ca", 3.0, 12.0, step=0.5, format="%.1f",
            label_visibility="collapsed", key="sens_ca",
        )
        st.caption(
            f"Base: **{base_ca:.1f}** &nbsp;·&nbsp; "
            f"Δ {ca_feed - base_ca:+.1f}"
        )

    # Construir params modificados con estructura grupada
    p_mod = _mod_fe(params,
        B={"precio_alimento": precio_maiz},
        C={"precio_alimento": precio_maiz},
    )
    p_mod = _mod_co(p_mod, C={"precio_venta": precio_novillo})
    p_mod = _mod_an(p_mod, C={"mortalidad": mort_pct / 100, "ca": ca_feed})

    d_mod = calcular_destete(p_mod)
    r_mod = calcular_recria(p_mod)
    t_mod = calcular_terminado(p_mod)
    e_mod_list = [d_mod, r_mod, t_mod]

    st.markdown("##### Impacto vs. caso base — Margen bruto (USD)")
    mb_cols = st.columns(3)
    for col, e_base, e_mod in zip(mb_cols, esc_todos, e_mod_list):
        delta = e_mod.margen_bruto - e_base.margen_bruto
        col.metric(
            e_base.nombre.split("—")[0].strip(),
            f"USD {e_mod.margen_bruto:,.0f}",
            delta=f"USD {delta:+,.0f}",
        )

    st.markdown("##### Impacto vs. caso base — ROI anual (%)")
    roi_cols = st.columns(3)
    for col, e_base, e_mod in zip(roi_cols, esc_todos, e_mod_list):
        delta = e_mod.roi_anual - e_base.roi_anual
        col.metric(
            e_base.nombre.split("—")[0].strip(),
            f"{e_mod.roi_anual:.1f}%",
            delta=f"{delta:+.1f} pp",
        )

    st.divider()

    # ════════════════════════════════════════════════════════════════════════════
    # Sección 2 — Tornado chart
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("#### Tornado — Sensibilidad por variable (Escenario C)")

    tor_ctrl, _ = st.columns([1, 3])
    with tor_ctrl:
        tornado_pct = st.slider("Rango ±(%)", 5, 50, 20, 5, key="tornado_pct")
    st.caption(
        f"Cada barra muestra cuánto cambia el resultado si esa variable varía ±{tornado_pct}% "
        "respecto al caso base del sidebar, manteniendo el resto fijo. "
        "Verde = impacto positivo · Rojo = impacto negativo."
    )

    df_tor = _tornado_data(params, tornado_pct)

    tor_mb_col, tor_roi_col = st.columns(2)
    with tor_mb_col:
        st.markdown("**Δ Margen bruto (USD)**")
        st.plotly_chart(_chart_tornado(df_tor, tornado_pct, "mb"), use_container_width=True)
    with tor_roi_col:
        st.markdown("**Δ ROI anual (%)**")
        st.plotly_chart(_chart_tornado(df_tor, tornado_pct, "roi"), use_container_width=True)

    with st.expander("Ver tabla de impacto por variable"):
        df_tabla_tor = df_tor[[
            "Variable",
            "mb_delta_low", "mb_delta_high",
            "roi_delta_low", "roi_delta_high",
        ]].copy()
        df_tabla_tor.columns = [
            "Variable",
            f"Δ MB −{tornado_pct}% (USD)", f"Δ MB +{tornado_pct}% (USD)",
            f"Δ ROI −{tornado_pct}% (pp)", f"Δ ROI +{tornado_pct}% (pp)",
        ]
        st.dataframe(
            df_tabla_tor.style.format({
                f"Δ MB −{tornado_pct}% (USD)": "${:+,.0f}",
                f"Δ MB +{tornado_pct}% (USD)": "${:+,.0f}",
                f"Δ ROI −{tornado_pct}% (pp)": "{:+.2f}",
                f"Δ ROI +{tornado_pct}% (pp)": "{:+.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ════════════════════════════════════════════════════════════════════════════
    # Sección 3 — Curvas de sensibilidad por variable
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown("#### Curvas de sensibilidad por variable")

    col_ctrl, col_g = st.columns([1, 2])

    with col_ctrl:
        st.markdown("##### Variable de análisis")
        variable = st.selectbox(
            "Variable", _VARIABLES,
            label_visibility="collapsed", key="sens_var",
        )
        variacion_pct = st.slider("Rango de variación (±%)", 5, 50, 25, 5, key="sens_rango")

        st.divider()
        st.markdown("##### Valores base")
        base_vals = {
            "Precios de venta (todos)": (
                f"A: USD {co['A']['precio_venta']:.2f} | "
                f"B: USD {co['B']['precio_venta']:.2f} | "
                f"C: USD {co['C']['precio_venta']:.2f}"
            ),
            "N° de terneros": f"{an['n_terneros']:,} cab.",
            "GDP / velocidad de crecimiento": (
                f"B: {an['B']['gdp']:.3f} | C: {an['C']['gdp']:.3f} kg/día"
            ),
            "Mortalidad": (
                f"A: {an['A']['mortalidad']*100:.1f}% | "
                f"B: {an['B']['mortalidad']*100:.1f}% | "
                f"C: {an['C']['mortalidad']*100:.1f}%"
            ),
            "Conversión alimenticia (CA)": (
                f"B: {an['B']['ca']:.1f} | C: {an['C']['ca']:.1f} kg MS/kg PV"
            ),
            "Precio de alimento": (
                f"B: USD {fe['B']['precio_alimento']:.3f} | "
                f"C: USD {fe['C']['precio_alimento']:.3f}/kg MS"
            ),
        }
        st.info(base_vals[variable])

        st.divider()
        st.markdown("##### Margen neto base (USD)")
        df_base = pd.DataFrame({
            "Escenario": [e.nombre for e in esc_todos],
            "Margen neto (USD)": [round(e.margen_neto, 0) for e in esc_todos],
            "ROI anual (%)":     [round(e.roi_anual, 1)   for e in esc_todos],
        })
        st.dataframe(
            df_base.style.format({
                "Margen neto (USD)": "${:,.0f}",
                "ROI anual (%)":     "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "La variación aplica el multiplicador `(1 + pct/100)` sobre el valor "
            "base de cada escenario."
        )

    with col_g:
        variaciones = list(range(-variacion_pct, variacion_pct + 1, 5))

        # ── Margen neto ───────────────────────────────────────────────────────
        rows_mn = []
        for v in variaciones:
            mult = 1 + v / 100
            p_v = _params_modificados(params, variable, mult)
            d = calcular_destete(p_v)
            r = calcular_recria(p_v)
            t = calcular_terminado(p_v)
            rows_mn.append({
                "Variación (%)":       v,
                comp.destete.nombre:   round(d.margen_neto, 0),
                comp.recria.nombre:    round(r.margen_neto, 0),
                comp.terminado.nombre: round(t.margen_neto, 0),
            })

        df_sens = pd.DataFrame(rows_mn)
        df_m = df_sens.melt(
            id_vars="Variación (%)", var_name="Escenario", value_name="Margen neto (USD)",
        )

        st.markdown(f"###### Margen neto vs. variación en: *{variable}*")
        fig = px.line(
            df_m, x="Variación (%)", y="Margen neto (USD)",
            color="Escenario", markers=True, color_discrete_map=COLORES_ESCENARIO,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#e74c3c",
                      annotation_text="Equilibrio", annotation_position="bottom right")
        fig.add_vline(x=0, line_dash="dot", line_color="#7f8c8d",
                      annotation_text="Base", annotation_position="top right")
        fig.update_layout(
            height=380, margin=dict(t=20, b=20),
            yaxis_title="Margen neto (USD)",
            xaxis_title=f"Variación en {variable} (%)",
            legend=dict(orientation="h", y=-0.28),
            plot_bgcolor="rgba(248,249,250,1)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ── ROI anual ─────────────────────────────────────────────────────────
        rows_roi = []
        for v in variaciones:
            mult = 1 + v / 100
            p_v = _params_modificados(params, variable, mult)
            d = calcular_destete(p_v)
            r = calcular_recria(p_v)
            t = calcular_terminado(p_v)
            rows_roi.append({
                "Variación (%)":       v,
                comp.destete.nombre:   round(d.roi_anual, 1),
                comp.recria.nombre:    round(r.roi_anual, 1),
                comp.terminado.nombre: round(t.roi_anual, 1),
            })

        df_roi_df = pd.DataFrame(rows_roi)
        df_roi_m = df_roi_df.melt(
            id_vars="Variación (%)", var_name="Escenario", value_name="ROI anual (%)",
        )

        st.markdown("###### ROI anual (%) por variación")
        fig2 = px.line(
            df_roi_m, x="Variación (%)", y="ROI anual (%)",
            color="Escenario", markers=True,
            color_discrete_map=COLORES_ESCENARIO, line_dash="Escenario",
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="#e74c3c")
        fig2.add_vline(x=0, line_dash="dot", line_color="#7f8c8d")
        fig2.update_layout(
            height=300, margin=dict(t=10, b=20),
            yaxis_title="ROI anual (%)", xaxis_title="Variación (%)",
            legend=dict(orientation="h", y=-0.38),
            plot_bgcolor="rgba(248,249,250,1)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.markdown("###### Tabla de margen neto (USD)")
        fmt_cols = {c: "${:,.0f}" for c in df_sens.columns if c != "Variación (%)"}
        fmt_cols["Variación (%)"] = "{:+d}%"
        st.dataframe(
            df_sens.style.format(fmt_cols),
            use_container_width=True,
            hide_index=True,
        )
