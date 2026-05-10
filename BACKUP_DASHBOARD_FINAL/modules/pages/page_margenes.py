"""
Margen Bruto — Visualización de la creación de valor económico
por las 4 etapas productivas (Cría · Recría · Engorde interno · Engorde
exportación).

Foco exclusivo: margen bruto y comparación entre estrategias.
NO incluye sensibilidad, riesgo, break-even ni cashflow.

Lee parámetros directamente desde session_state. Replica las mismas
fórmulas internas de costos e ingresos para mantener coherencia con
page_costos.py y page_ingresos.py. Mantiene la firma render(params, comp)
por compatibilidad con el router de app.py.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.pages.ui import page_header, section

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Etapas y paletas ─────────────────────────────────────────────────────────

_SEG = {
    "cria":    {"title": "Cría",                "icon": "🌱",
                "color": "#16a34a", "bg": "#f0fdf4", "border": "#bbf7d0"},
    "recria":  {"title": "Recría",              "icon": "🔵",
                "color": "#1565c0", "bg": "#eff6ff", "border": "#bfdbfe"},
    "eng_int": {"title": "Engorde interno",     "icon": "🟢",
                "color": "#0d9488", "bg": "#f0fdfa", "border": "#99f6e4"},
    "eng_exp": {"title": "Engorde exportación", "icon": "🌐",
                "color": "#7c3aed", "bg": "#faf5ff", "border": "#ddd6fe"},
}

_FEED_KEYS = {
    "cria":    "feed_table_cria_de",
    "recria":  "feed_table_recria_de",
    "eng_int": "feed_table_eng_int_de",
    "eng_exp": "feed_table_eng_exp_de",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _g(key: str, default: float) -> float:
    return float(st.session_state.get(key, default))


def _read_feed_df(editor_key: str) -> pd.DataFrame:
    """Misma lógica que page_costos / page_modelo_productivo."""
    base = pd.DataFrame({
        "Ingrediente": [""] * 10,
        "%":           [0.0] * 10,
        "USD/kg MS":   [0.0] * 10,
    })
    if editor_key not in st.session_state:
        return base
    val = st.session_state[editor_key]
    if isinstance(val, pd.DataFrame):
        return val
    if isinstance(val, dict):
        df = base.copy()
        for idx_str, changes in val.get("edited_rows", {}).items():
            try:
                idx = int(idx_str)
            except (ValueError, TypeError):
                continue
            if 0 <= idx < len(df):
                for col, v in changes.items():
                    if col in df.columns:
                        df.at[idx, col] = v
        return df
    return base


def _alim_usd_cab(rac_dia: float, dias: int, feed_key: str,
                  fallback_usd_dia: float) -> float:
    df = _read_feed_df(feed_key)
    name = df["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(df["%"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(df["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)
    if not mask.any():
        return float(fallback_usd_dia) * float(dias)
    total = 0.0
    for p, u in zip(pct[mask].values, usd[mask].values):
        total += rac_dia * (p / 100.0) * dias * u
    return float(total)


# ── Modelo de margen bruto ───────────────────────────────────────────────────

def _build_margenes() -> dict:
    """
    Calcula margen bruto por etapa siguiendo las mismas fórmulas que
    page_costos.py (costos) y page_ingresos.py (ingresos) para mantener
    consistencia entre páginas.

    Por etapa devuelve:
        kg_in, kg_out, dias, mort_pct
        cab_in, cab_vend                          (cabezas)
        ingreso_cab, ingreso_total                (USD)
        costo_cab, costo_total                    (USD)
        margen_bruto_cab, margen_bruto_total      (USD)
        margen_kg                                 (USD/kg producido)
        usd_cab_dia                               (USD/cab/día)
        roi_operativo                             (decimal)
        retorno_incremental                       (USD/cab vs etapa previa)
        kg_prod_total                             (kg producidos)
    """
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

    # ── Lecturas ──────────────────────────────────────────────────────────
    a_kg_in   = _g(K.A_KG_ENTRADA,        DEFAULTS["a_kg_entrada"])
    a_kg_out  = _g(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"])
    a_dias    = int(_g(K.A_DIAS,          DEFAULTS["d_dias"]))
    a_mort    = _g(K.A_MORTALIDAD,        DEFAULTS["d_mortalidad"])
    a_san     = _g(K.A_SANIDAD,           DEFAULTS["d_sanidad"])
    a_mo_dia  = _g(K.A_MO_DIA,            DEFAULTS["d_mo_dia"])
    a_alim_d  = _g(K.A_ALIM_COSTO_DIA,    DEFAULTS["d_costo_alim_dia"])
    a_rac     = _g(K.A_RAC_DIARIA,        DEFAULTS["a_rac_diaria"])
    a_com_pct = _g(K.A_COMISION_PCT,      DEFAULTS["a_comision_pct"])
    a_pv      = _g(K.A_PRECIO_VENTA,      DEFAULTS["d_precio_venta"])
    a_fe      = _g(K.A_FLETE_ENTRADA,     DEFAULTS["a_fe"])
    a_fs      = _g(K.A_FLETE_SALIDA,      DEFAULTS["d_flete"])

    b_kg_in   = a_kg_out
    b_kg_out  = _g(K.B_PESO_SALIDA,       DEFAULTS["r_peso_salida"])
    b_dias    = int(_g(K.B_DIAS,          DEFAULTS["b_dias"]))
    b_mort    = _g(K.B_MORTALIDAD,        DEFAULTS["r_mortalidad"])
    b_san     = _g(K.B_SANIDAD,           DEFAULTS["r_sanidad"])
    b_mo_dia  = _g(K.B_MO_DIA,            DEFAULTS["r_mo_dia"])
    b_alim_d  = _g(K.B_ALIM_DIA,          DEFAULTS["b_alim_dia"])
    b_rac     = _g(K.B_RAC_DIARIA,        DEFAULTS["b_rac_diaria"])
    b_com_pct = _g(K.B_COMISION_PCT,      DEFAULTS["b_comision_pct"])
    b_pc      = _g(K.B_PRECIO_COMPRA,     DEFAULTS["b_pc"])
    b_pv      = _g(K.B_PRECIO_VENTA,      DEFAULTS["r_precio_venta"])
    b_fe      = _g(K.B_FLETE_ENTRADA,     DEFAULTS["r_flete_entrada"])
    b_fs      = _g(K.B_FLETE_SALIDA,      DEFAULTS["r_flete_salida"])

    c_kg_in   = b_kg_out
    c_kg_out  = _g(K.C_PESO_FINAL,        DEFAULTS["t_peso_final"])
    c_dias    = int(_g(K.C_DIAS,          DEFAULTS["c_dias"]))
    c_mort    = _g(K.C_MORTALIDAD,        DEFAULTS["t_mortalidad"])
    c_san     = _g(K.C_SANIDAD,           DEFAULTS["t_sanidad"])
    c_mo_dia  = _g(K.C_MO_DIA,            DEFAULTS["t_mo_dia"])
    c_alim_d  = _g(K.C_ALIM_DIA,          DEFAULTS["c_alim_dia"])
    c_rac     = _g(K.C_RAC_DIARIA,        DEFAULTS["c_rac_diaria"])
    c_com_pct = _g(K.C_COMISION_PCT,      DEFAULTS["c_comision_pct"])
    c_pc      = _g(K.C_PRECIO_COMPRA,     DEFAULTS["c_pc"])
    c_pv      = _g(K.C_PRECIO_VENTA,      DEFAULTS["t_precio_venta"])
    c_fe      = _g(K.C_FLETE_ENTRADA,     DEFAULTS["t_flete_entrada"])
    c_fs      = _g(K.C_FLETE_SALIDA,      DEFAULTS["t_flete_salida"])

    e_kg_in   = _g(K.E_KG_ENTRADA,        DEFAULTS["e_kg_entrada"])
    e_kg_out  = _g(K.E_KG_SALIDA,         DEFAULTS["e_kg_salida"])
    e_dias    = int(_g(K.E_DIAS,          DEFAULTS["e_dias"]))
    e_mort    = _g(K.E_MORTALIDAD,        DEFAULTS["e_mortalidad"])
    e_san     = _g(K.E_SANIDAD,           DEFAULTS["e_sanidad"])
    e_mo_dia  = _g(K.E_MO_DIA,            DEFAULTS["e_mo_dia"])
    e_alim_d  = _g(K.E_ALIM_DIA,          DEFAULTS["e_alim_dia"])
    e_rac     = _g(K.E_RAC_DIARIA,        DEFAULTS["e_rac_diaria"])
    e_com_pct = _g(K.E_COMISION_PCT,      DEFAULTS["e_comision_pct"])
    e_pc      = _g(K.E_PRECIO_COMPRA,     DEFAULTS["e_pc"])
    e_pv      = _g(K.E_PRECIO_VENTA,      DEFAULTS["e_pv"])
    e_fe      = _g(K.E_FLETE_ENTRADA,     DEFAULTS["e_fe"])
    e_fs      = _g(K.E_FLETE_SALIDA,      DEFAULTS["e_fs"])

    # ── Cabezas en cascada ────────────────────────────────────────────────
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    cab_in_cria    = n_t
    cab_in_recria  = surv(cab_in_cria,    a_mort)
    cab_in_eng_int = surv(cab_in_recria,  b_mort)
    cab_in_eng_exp = surv(cab_in_eng_int, c_mort)

    def block(
        kg_in: float, kg_out: float, dias: int, mort_pct: float,
        cab_in: int, precio_venta: float,
        compra: float, alim: float, sanidad: float, mo: float, com: float,
    ) -> dict:
        cab_vend = surv(cab_in, mort_pct)

        # Costos (alineado con page_costos.py)
        acumulado = compra + alim + sanidad + mo + com
        mortandad = acumulado * mort_pct / 100.0
        costo_cab = acumulado + mortandad
        costo_total = costo_cab * cab_in    # se incurre sobre cab_in

        # Ingresos (alineado con page_ingresos.py)
        ingreso_cab = kg_out * precio_venta
        ingreso_total = ingreso_cab * cab_vend

        # Margen bruto
        margen_bruto_cab = ingreso_cab - costo_cab
        margen_bruto_total = ingreso_total - costo_total

        # kg producidos (sólo cabezas vivas a venta producen kg vendibles)
        kg_prod_total = max(kg_out - kg_in, 0.0) * cab_vend

        margen_kg = (margen_bruto_total / kg_prod_total
                     if kg_prod_total > 0 else 0.0)
        usd_cab_dia = margen_bruto_cab / dias if dias > 0 else 0.0
        roi_operativo = (margen_bruto_total / costo_total
                         if costo_total > 0 else 0.0)

        return {
            "kg_in": kg_in, "kg_out": kg_out, "dias": dias,
            "mort_pct": mort_pct,
            "cab_in": cab_in, "cab_vend": cab_vend,
            "precio_venta": precio_venta,
            "ingreso_cab": ingreso_cab, "ingreso_total": ingreso_total,
            "costo_cab": costo_cab, "costo_total": costo_total,
            "margen_bruto_cab": margen_bruto_cab,
            "margen_bruto_total": margen_bruto_total,
            "margen_kg": margen_kg,
            "usd_cab_dia": usd_cab_dia,
            "roi_operativo": roi_operativo,
            "kg_prod_total": kg_prod_total,
        }

    data = {
        "cria": block(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            cab_in=cab_in_cria, precio_venta=a_pv,
            compra  = pc_global * a_kg_in,
            alim    = _alim_usd_cab(a_rac, a_dias, _FEED_KEYS["cria"], a_alim_d),
            sanidad = a_san,
            mo      = a_mo_dia * a_dias,
            com     = (a_com_pct / 100.0) * a_pv * a_kg_out + a_fe + a_fs,
        ),
        "recria": block(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            cab_in=cab_in_recria, precio_venta=b_pv,
            compra  = b_pc * b_kg_in,
            alim    = _alim_usd_cab(b_rac, b_dias, _FEED_KEYS["recria"], b_alim_d),
            sanidad = b_san,
            mo      = b_mo_dia * b_dias,
            com     = (b_com_pct / 100.0) * b_pv * b_kg_out + b_fe + b_fs,
        ),
        "eng_int": block(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            cab_in=cab_in_eng_int, precio_venta=c_pv,
            compra  = c_pc * c_kg_in,
            alim    = _alim_usd_cab(c_rac, c_dias, _FEED_KEYS["eng_int"], c_alim_d),
            sanidad = c_san,
            mo      = c_mo_dia * c_dias,
            com     = (c_com_pct / 100.0) * c_pv * c_kg_out + c_fe + c_fs,
        ),
        "eng_exp": block(
            kg_in=e_kg_in, kg_out=e_kg_out, dias=e_dias, mort_pct=e_mort,
            cab_in=cab_in_eng_exp, precio_venta=e_pv,
            compra  = e_pc * e_kg_in,
            alim    = _alim_usd_cab(e_rac, e_dias, _FEED_KEYS["eng_exp"], e_alim_d),
            sanidad = e_san,
            mo      = e_mo_dia * e_dias,
            com     = (e_com_pct / 100.0) * e_pv * e_kg_out + e_fe + e_fs,
        ),
    }

    # ── Retorno incremental: margen actual − margen previo (USD/cab) ──────
    order = ["cria", "recria", "eng_int", "eng_exp"]
    prev = None
    for key in order:
        actual = data[key]["margen_bruto_cab"]
        data[key]["retorno_incremental"] = (actual - prev
                                            if prev is not None else 0.0)
        prev = actual

    return data


# ── 1. Resumen superior — KPIs comparativas ──────────────────────────────────

def _summary_kpis(data: dict) -> None:
    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["cria", "recria", "eng_int", "eng_exp"]):
        meta = _SEG[key]
        s = data[key]

        sign = "+" if s["margen_bruto_cab"] >= 0 else "−"
        margin_color = "#16a34a" if s["margen_bruto_cab"] >= 0 else "#dc2626"
        ret_inc = s["retorno_incremental"]
        if key == "cria":
            ret_html = (
                '<span style="color:#94a3b8;font-size:0.65rem;'
                'font-weight:600;">Etapa base</span>'
            )
        else:
            ret_color = "#16a34a" if ret_inc >= 0 else "#dc2626"
            ret_sign = "▲" if ret_inc >= 0 else "▼"
            ret_html = (
                f'<span style="color:{ret_color};font-size:0.70rem;'
                f'font-weight:700;">{ret_sign} USD {abs(ret_inc):,.1f}/cab</span>'
            )

        col.markdown(
            f"""<div style="background:#ffffff;border:1px solid {meta['border']};
                        border-radius:14px;padding:0;overflow:hidden;
                        box-shadow:0 1px 6px rgba(13,27,66,0.06);height:100%;">
                <div style="background:linear-gradient(135deg,{meta['color']},{meta['color']}dd);
                            padding:10px 16px;color:white;
                            display:flex;align-items:center;gap:8px;">
                    <span style="font-size:1.05rem;">{meta['icon']}</span>
                    <span style="font-size:0.86rem;font-weight:700;">{meta['title']}</span>
                </div>
                <div style="padding:14px 16px 12px;">
                    <div style="font-size:0.62rem;font-weight:700;color:#7a8fa6;
                                text-transform:uppercase;letter-spacing:0.07em;">
                        Margen bruto / cab
                    </div>
                    <div style="font-size:1.55rem;font-weight:800;color:{margin_color};
                                line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">
                        {sign}USD&nbsp;{abs(s['margen_bruto_cab']):,.1f}
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;
                                gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['margen_bruto_total']:,.0f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Margen Total</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['margen_kg']:.2f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Margen / kg</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['usd_cab_dia']:.2f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">USD/cab/día</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">{s['roi_operativo']*100:.1f}%</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">ROI operativo</div>
                        </div>
                    </div>
                    <div style="margin-top:10px;padding-top:8px;
                                border-top:1px solid #f0f4fa;text-align:center;">
                        <span style="font-size:0.62rem;color:#94a3b8;font-weight:700;
                                     text-transform:uppercase;letter-spacing:0.06em;">
                            Retorno incremental
                        </span><br>
                        {ret_html}
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )


# ── Gráfico comparativo: margen / cab y margen total ─────────────────────────

def _bars_two_panels(data: dict) -> go.Figure:
    stages = ["cria", "recria", "eng_int", "eng_exp"]
    x_labels = [f"{_SEG[k]['icon']}<br>{_SEG[k]['title']}" for k in stages]

    margen_cab   = [data[k]["margen_bruto_cab"]   for k in stages]
    margen_total = [data[k]["margen_bruto_total"] for k in stages]

    def colors_for(values: list[float]) -> list[str]:
        return [_SEG[stages[i]]["color"] if v >= 0 else "#dc2626"
                for i, v in enumerate(values)]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Margen bruto por cabeza (USD)",
                        "Margen bruto total (USD)"),
        horizontal_spacing=0.14,
    )

    fig.add_trace(go.Bar(
        x=x_labels, y=margen_cab,
        marker=dict(color=colors_for(margen_cab),
                    line=dict(color="white", width=1.2)),
        text=[f"USD {v:,.0f}" for v in margen_cab],
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        hovertemplate="<b>%{x}</b><br>USD %{y:,.2f} / cab<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=x_labels, y=margen_total,
        marker=dict(color=colors_for(margen_total),
                    line=dict(color="white", width=1.2)),
        text=[f"USD {v:,.0f}" for v in margen_total],
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        hovertemplate="<b>%{x}</b><br>USD %{y:,.0f}<extra></extra>",
        showlegend=False,
    ), row=1, col=2)

    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=12, color="#475569", family="Inter, Arial")

    fig.update_layout(
        height=420,
        margin=dict(t=60, b=40, l=50, r=30),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        bargap=0.40,
        hoverlabel=dict(bgcolor="white", bordercolor="#e4eaf4",
                        font=dict(size=12, color="#0c1a2e")),
    )
    fig.update_xaxes(tickfont=dict(size=11, color="#0c1a2e"),
                     gridcolor="rgba(0,0,0,0)", zeroline=False)
    fig.update_yaxes(gridcolor="#eef2f7", tickformat=",.0f",
                     ticksuffix=" ", zeroline=True,
                     zerolinecolor="#cbd5e1", zerolinewidth=1.2,
                     tickfont=dict(size=10, color="#64748b"))
    return fig


# ── Hero — gráfico principal comparativo ingresos · costos · margen ──────────

def _hero_comparative_chart(data: dict) -> go.Figure:
    """
    Gráfico principal: barras agrupadas comparando ingresos, costos y margen
    bruto para las 4 etapas (USD totales del sistema).

    Diseño SaaS/agtech: paleta suave, etiquetas USD destacadas, margen en
    color de la etapa cuando es positivo y rojo cuando es negativo.
    Anotación con ROI operativo bajo cada grupo para lectura rápida.
    """
    stages = ["cria", "recria", "eng_int", "eng_exp"]
    x_labels = [f"{_SEG[k]['icon']}  {_SEG[k]['title']}" for k in stages]

    ingresos = [data[k]["ingreso_total"]      for k in stages]
    costos   = [data[k]["costo_total"]        for k in stages]
    margenes = [data[k]["margen_bruto_total"] for k in stages]

    fig = go.Figure()

    # Ingresos — emerald suave
    fig.add_trace(go.Bar(
        name="Ingresos",
        x=x_labels, y=ingresos,
        marker=dict(color="#34d399",
                    line=dict(color="white", width=1.4)),
        text=[f"USD {v:,.0f}" for v in ingresos],
        textposition="outside",
        textfont=dict(size=10, color="#047857"),
        hovertemplate="<b>Ingresos</b><br>%{x}<br>"
                      "USD %{y:,.0f}<extra></extra>",
        offsetgroup="ing",
    ))

    # Costos — coral suave
    fig.add_trace(go.Bar(
        name="Costos",
        x=x_labels, y=costos,
        marker=dict(color="#fb7185",
                    line=dict(color="white", width=1.4)),
        text=[f"USD {v:,.0f}" for v in costos],
        textposition="outside",
        textfont=dict(size=10, color="#be123c"),
        hovertemplate="<b>Costos</b><br>%{x}<br>"
                      "USD %{y:,.0f}<extra></extra>",
        offsetgroup="cos",
    ))

    # Margen bruto — color etapa, resaltado
    margen_colors = [_SEG[k]["color"] if m >= 0 else "#dc2626"
                     for k, m in zip(stages, margenes)]
    fig.add_trace(go.Bar(
        name="Margen bruto",
        x=x_labels, y=margenes,
        marker=dict(color=margen_colors,
                    line=dict(color="white", width=2)),
        text=[f"<b>USD {v:,.0f}</b>" for v in margenes],
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        hovertemplate="<b>Margen bruto</b><br>%{x}<br>"
                      "USD %{y:,.0f}<extra></extra>",
        offsetgroup="mar",
    ))

    # Anotaciones bajo el eje X: ROI operativo por etapa
    for i, k in enumerate(stages):
        roi = data[k]["roi_operativo"] * 100.0
        roi_color = "#16a34a" if roi >= 0 else "#dc2626"
        fig.add_annotation(
            x=x_labels[i], y=-0.16, xref="x", yref="paper",
            text=(f"<span style='color:#94a3b8;font-size:9px;'>ROI op</span>"
                  f"<br><b style='color:{roi_color};font-size:11px;'>"
                  f"{roi:.1f}%</b>"),
            showarrow=False, align="center",
        )

    fig.update_layout(
        barmode="group",
        height=480,
        margin=dict(t=40, b=110, l=70, r=20),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        bargap=0.32,
        bargroupgap=0.08,
        legend=dict(
            orientation="h",
            yanchor="top", y=1.10,
            xanchor="center", x=0.5,
            font=dict(size=12, color="#475569"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="white", bordercolor="#e4eaf4",
                        font=dict(size=12, color="#0c1a2e")),
        xaxis=dict(
            tickfont=dict(size=12, color="#0c1a2e", family="Inter"),
            gridcolor="rgba(0,0,0,0)", zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="USD totales (sistema)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7", tickformat=",.0f", ticksuffix=" ",
            zeroline=True, zerolinecolor="#cbd5e1", zerolinewidth=1.2,
            tickfont=dict(size=10, color="#64748b"),
        ),
    )
    return fig


# ── Valor agregado entre etapas: transiciones consecutivas ──────────────────

_TRANSITIONS = [
    ("cria",    "recria",  "🌱 → 🔵", "Cría → Recría"),
    ("recria",  "eng_int", "🔵 → 🟢", "Recría → Engorde interno"),
    ("eng_int", "eng_exp", "🟢 → 🌐", "Engorde interno → Exportación"),
]


def _value_added_transitions(data: dict) -> list[dict]:
    """Calcula valor agregado por transición consecutiva."""
    rows: list[dict] = []
    for prev_key, next_key, arrow, label in _TRANSITIONS:
        prev = data[prev_key]
        nxt  = data[next_key]

        delta_margen_cab   = nxt["margen_bruto_cab"]   - prev["margen_bruto_cab"]
        delta_margen_total = nxt["margen_bruto_total"] - prev["margen_bruto_total"]
        delta_kg     = nxt["kg_out"] - prev["kg_out"]   # kilos extra al final
        delta_dias   = nxt["dias"]                       # días extra invertidos
        usd_per_kg   = delta_margen_cab / delta_kg   if delta_kg   > 0 else 0.0
        usd_per_day  = delta_margen_cab / delta_dias if delta_dias > 0 else 0.0

        # Veredicto: ¿vale la pena seguir agregando kilos?
        if delta_margen_cab > 0 and usd_per_kg >= 0.50 and usd_per_day >= 0.30:
            verdict = "✅ Vale la pena"
            v_color, v_bg = "#16a34a", "#f0fdf4"
        elif delta_margen_cab > 0:
            verdict = "⚠️ Marginal — evaluar"
            v_color, v_bg = "#b45309", "#fffbeb"
        else:
            verdict = "❌ No conviene"
            v_color, v_bg = "#dc2626", "#fef2f2"

        rows.append({
            "from_key": prev_key, "to_key": next_key,
            "arrow": arrow, "label": label,
            "delta_margen_cab": delta_margen_cab,
            "delta_margen_total": delta_margen_total,
            "delta_kg": delta_kg,
            "delta_dias": delta_dias,
            "usd_per_kg": usd_per_kg,
            "usd_per_day": usd_per_day,
            "from_margen": prev["margen_bruto_cab"],
            "to_margen":   nxt["margen_bruto_cab"],
            "verdict": verdict,
            "verdict_color": v_color,
            "verdict_bg": v_bg,
        })
    return rows


def _waterfall_value_chart(data: dict, transitions: list[dict]) -> go.Figure:
    """
    Waterfall del margen bruto/cab a lo largo del ciclo:
        Cría (base) → +Δ Recría → +Δ Eng. interno → +Δ Exportación → TOTAL.
    """
    margen_cria  = data["cria"]["margen_bruto_cab"]
    margen_final = data["eng_exp"]["margen_bruto_cab"]

    x_labels = ["🌱 Cría<br><span style='color:#94a3b8;font-size:9px;'>"
                "base</span>"]
    measure  = ["absolute"]
    y_vals   = [margen_cria]
    text     = [f"<b>USD {margen_cria:,.1f}</b>"]

    for t in transitions:
        x_labels.append(
            f"{t['arrow']}<br>"
            f"<span style='color:#94a3b8;font-size:9px;'>"
            f"+{t['delta_dias']} d · +{t['delta_kg']:.0f} kg</span>"
        )
        measure.append("relative")
        y_vals.append(t["delta_margen_cab"])
        sign = "+" if t["delta_margen_cab"] >= 0 else "−"
        text.append(f"<b>{sign}USD {abs(t['delta_margen_cab']):,.1f}</b>")

    x_labels.append("🏁 TOTAL<br><span style='color:#94a3b8;font-size:9px;'>"
                    "ciclo completo</span>")
    measure.append("total")
    y_vals.append(margen_final)
    text.append(f"<b>USD {margen_final:,.1f}</b>")

    fig = go.Figure(go.Waterfall(
        name="Valor agregado",
        orientation="v",
        measure=measure,
        x=x_labels,
        y=y_vals,
        text=text,
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        connector={"line": {"color": "#cbd5e1", "width": 1.5,
                            "dash": "dot"}},
        increasing={"marker": {"color": "#34d399",
                                "line": {"color": "white", "width": 1.5}}},
        decreasing={"marker": {"color": "#fb7185",
                                "line": {"color": "white", "width": 1.5}}},
        totals={"marker": {"color": "#7c3aed",
                            "line": {"color": "white", "width": 1.5}}},
        hovertemplate="<b>%{x}</b><br>Margen: %{text}<extra></extra>",
    ))

    fig.update_layout(
        height=440,
        margin=dict(t=50, b=60, l=80, r=30),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        showlegend=False,
        xaxis=dict(
            tickfont=dict(size=11, color="#0c1a2e"),
            gridcolor="rgba(0,0,0,0)", zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Margen bruto / cab (USD)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7", tickformat=",.0f",
            tickprefix="USD ",
            zeroline=True, zerolinecolor="#cbd5e1", zerolinewidth=1.2,
            tickfont=dict(size=10, color="#64748b"),
        ),
        hoverlabel=dict(bgcolor="white", bordercolor="#e4eaf4",
                        font=dict(size=12, color="#0c1a2e")),
    )
    return fig


def _transition_card_html(t: dict) -> str:
    delta = t["delta_margen_cab"]
    sign  = "+" if delta >= 0 else "−"
    delta_color = "#16a34a" if delta >= 0 else "#dc2626"
    delta_bg    = "#f0fdf4" if delta >= 0 else "#fef2f2"

    hero = (
        f'<div style="background:{delta_bg};'
        f'border:1.5px solid {delta_color}33;border-radius:10px;'
        f'padding:14px 16px;margin-bottom:10px;">'
        f'<div style="font-size:0.62rem;color:{delta_color};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">'
        f'📊 Δ Margen bruto / cab</div>'
        f'<div style="font-size:1.65rem;font-weight:800;color:{delta_color};'
        f'line-height:1;letter-spacing:-0.02em;">'
        f'{sign}USD {abs(delta):,.1f}</div>'
        f'<div style="font-size:0.70rem;color:#64748b;margin-top:6px;">'
        f'De USD {t["from_margen"]:,.1f} → USD {t["to_margen"]:,.1f}'
        f'</div></div>'
    )

    metrics = [
        ("⚖️", "Kilos agregados",     f"+{t['delta_kg']:.0f} kg"),
        ("💲", "USD / kg agregado",
         f"USD {t['usd_per_kg']:.2f}"),
        ("📅", "Días extra",           f"{t['delta_dias']:,} d"),
        ("⚡", "USD / cab / día",
         f"USD {t['usd_per_day']:.2f}"),
    ]
    tiles = ""
    for icon, lbl, val in metrics:
        tiles += (
            f'<div style="background:white;border:1px solid #e4eaf4;'
            f'border-radius:8px;padding:10px 12px;">'
            f'<div style="font-size:0.62rem;color:#7a8fa6;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;'
            f'display:flex;align-items:center;gap:4px;">'
            f'<span style="font-size:0.78rem;">{icon}</span>{lbl}</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:#0c1a2e;'
            f'line-height:1.15;white-space:nowrap;">{val}</div>'
            f'</div>'
        )

    delta_total_str = (
        f'+USD {t["delta_margen_total"]:,.0f}'
        if t["delta_margen_total"] >= 0
        else f'−USD {abs(t["delta_margen_total"]):,.0f}'
    )
    extra = (
        f'<div style="margin-top:10px;background:white;border:1px solid '
        f'#e4eaf4;border-radius:8px;padding:10px 12px;text-align:center;">'
        f'<span style="font-size:0.62rem;color:#7a8fa6;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;">'
        f'Δ Margen total (sistema)</span><br>'
        f'<span style="font-size:1.05rem;font-weight:800;color:{delta_color};'
        f'">{delta_total_str}</span>'
        f'</div>'
    )

    verdict = (
        f'<div style="background:{t["verdict_bg"]};'
        f'border:1px solid {t["verdict_color"]}55;border-radius:8px;'
        f'padding:10px 12px;margin-top:10px;text-align:center;">'
        f'<span style="font-size:0.92rem;font-weight:800;'
        f'color:{t["verdict_color"]};">{t["verdict"]}</span>'
        f'</div>'
    )

    return (
        f'<div style="background:#f8fafd;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;">'
        f'<div style="background:linear-gradient(135deg,#0c1a2e,#1e3a5f);'
        f'padding:14px 16px;color:white;text-align:center;">'
        f'<div style="font-size:1.45rem;letter-spacing:0.12em;'
        f'margin-bottom:3px;">{t["arrow"]}</div>'
        f'<div style="font-size:0.84rem;font-weight:700;'
        f'letter-spacing:0.02em;">{t["label"]}</div>'
        f'</div>'
        f'<div style="padding:14px;">'
        f'{hero}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
        f'{tiles}</div>'
        f'{extra}'
        f'{verdict}'
        f'</div></div>'
    )


def _value_added_section(data: dict) -> None:
    transitions = _value_added_transitions(data)

    st.plotly_chart(
        _waterfall_value_chart(data, transitions),
        width="stretch",
        key="margen_value_waterfall",
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    cols = st.columns(3, gap="small")
    for col, t in zip(cols, transitions):
        with col:
            st.markdown(_transition_card_html(t), unsafe_allow_html=True)


# ── Matriz estratégica comparativa ───────────────────────────────────────────

_MATRIX_TITLES = {
    "cria":    "Cría",
    "recria":  "Recría",
    "eng_int": "Feedlot (Eng. interno)",
    "eng_exp": "Exportación",
}

# Paleta de calificaciones (4 niveles)
_RATING_PALETTE = {
    "muy_bueno":  ("#16a34a", "#f0fdf4"),   # verde fuerte
    "bueno":      ("#65a30d", "#f7fee7"),   # lime
    "regular":    ("#d97706", "#fffbeb"),   # ámbar
    "malo":       ("#dc2626", "#fef2f2"),   # rojo
}


def _rank_to_rating(rank: int, n: int, *, lower_is_better: bool,
                    labels: tuple[str, str, str, str]) -> tuple[str, str, str]:
    """
    Mapea ranking (0 = menor valor, n-1 = mayor valor) a (label, color, bg)
    según si menor es mejor o no.

    labels = (mejor, segundo, tercero, peor)
    """
    pos = rank if lower_is_better else (n - 1 - rank)
    if pos == 0:
        key = "muy_bueno"
        label = labels[0]
    elif pos == 1:
        key = "bueno"
        label = labels[1]
    elif pos == n - 1:
        key = "malo"
        label = labels[3]
    else:
        key = "regular"
        label = labels[2]
    color, bg = _RATING_PALETTE[key]
    return label, color, bg


def _strategic_matrix_data(data: dict) -> list[dict]:
    """
    Deriva la matriz Modelo × {Margen, Riesgo, Capital, Liquidez}
    automáticamente desde los datos ya calculados.

    Métricas brutas:
        margen_score    = margen_bruto_cab                  (mayor = mejor)
        riesgo_score    = días × (1 + mort_pct/100)         (menor = mejor)
        capital_score   = costo_total (capital comprometido) (menor = mejor)
        liquidez_score  = 365 / días (ciclos por año)        (mayor = mejor)
    """
    stages = ["cria", "recria", "eng_int", "eng_exp"]

    raw = []
    for k in stages:
        s = data[k]
        margen_score   = s["margen_bruto_cab"]
        riesgo_score   = s["dias"] * (1 + s["mort_pct"] / 100.0)
        capital_score  = s["costo_total"]
        liquidez_score = (365.0 / s["dias"]) if s["dias"] > 0 else 0.0
        raw.append({
            "key": k, "title": _MATRIX_TITLES[k],
            "margen_cab":   s["margen_bruto_cab"],
            "margen_total": s["margen_bruto_total"],
            "dias":         s["dias"],
            "mort_pct":     s["mort_pct"],
            "capital":      s["costo_total"],
            "ciclos_anio":  liquidez_score,
            "_margen_score":   margen_score,
            "_riesgo_score":   riesgo_score,
            "_capital_score":  capital_score,
            "_liquidez_score": liquidez_score,
        })

    n = len(raw)

    # Rankings: índice de cada modelo en el orden ascendente del score
    def rank_of(values: list[float]) -> dict[int, int]:
        sorted_idx = sorted(range(n), key=lambda i: values[i])
        return {idx: rank for rank, idx in enumerate(sorted_idx)}

    rank_m = rank_of([r["_margen_score"]   for r in raw])
    rank_r = rank_of([r["_riesgo_score"]   for r in raw])
    rank_c = rank_of([r["_capital_score"]  for r in raw])
    rank_l = rank_of([r["_liquidez_score"] for r in raw])

    rows = []
    for i, r in enumerate(raw):
        # Margen — mayor = mejor (lower_is_better=False)
        if r["margen_cab"] < 0:
            m_label, m_color, m_bg = "Negativo", *_RATING_PALETTE["malo"]
        else:
            m_label, m_color, m_bg = _rank_to_rating(
                rank_m[i], n, lower_is_better=False,
                labels=("Muy alto", "Alto", "Medio", "Bajo"),
            )
        # Riesgo — menor = mejor
        ri_label, ri_color, ri_bg = _rank_to_rating(
            rank_r[i], n, lower_is_better=True,
            labels=("Bajo", "Medio-Bajo", "Medio-Alto", "Alto"),
        )
        # Capital — menor = mejor
        c_label, c_color, c_bg = _rank_to_rating(
            rank_c[i], n, lower_is_better=True,
            labels=("Bajo", "Medio-Bajo", "Medio-Alto", "Alto"),
        )
        # Liquidez — mayor = mejor
        l_label, l_color, l_bg = _rank_to_rating(
            rank_l[i], n, lower_is_better=False,
            labels=("Alta", "Media-Alta", "Media-Baja", "Baja"),
        )

        rows.append({
            **r,
            "margen_rating":   (m_label, m_color, m_bg),
            "riesgo_rating":   (ri_label, ri_color, ri_bg),
            "capital_rating":  (c_label, c_color, c_bg),
            "liquidez_rating": (l_label, l_color, l_bg),
        })
    return rows


def _matrix_pill(label: str, color: str, bg: str, subtext: str) -> str:
    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'gap:3px;">'
        f'<span style="background:{bg};border:1px solid {color}55;'
        f'color:{color};font-size:0.74rem;font-weight:800;'
        f'padding:4px 11px;border-radius:14px;letter-spacing:0.02em;'
        f'white-space:nowrap;">● {label}</span>'
        f'<span style="font-size:0.66rem;color:#64748b;font-weight:600;'
        f'white-space:nowrap;">{subtext}</span>'
        f'</div>'
    )


def _strategic_matrix_html(rows: list[dict]) -> str:
    """Tabla matriz estilo ejecutivo en HTML."""
    th_base = ('padding:11px 14px;font-size:0.66rem;font-weight:700;'
               'color:#7a8fa6;text-transform:uppercase;letter-spacing:0.08em;'
               'background:#f8fafd;border-bottom:1.5px solid #e4eaf4;')
    th_l = th_base + 'text-align:left;'
    th_c = th_base + 'text-align:center;'

    body = ""
    for i, r in enumerate(rows):
        meta = _SEG[r["key"]]
        bg_row = "#ffffff" if i % 2 == 0 else "#fbfcfe"

        margen_sub = (f"USD {r['margen_cab']:,.0f}/cab · "
                      f"USD {r['margen_total']:,.0f} tot")
        riesgo_sub = f"{r['dias']} d · {r['mort_pct']:.1f}% mort"
        capital_sub = f"USD {r['capital']:,.0f}"
        liquidez_sub = f"{r['ciclos_anio']:.1f} ciclos/año"

        # Modelo (col 1)
        modelo_cell = (
            f'<td style="padding:14px 16px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div style="width:34px;height:34px;border-radius:8px;'
            f'background:{meta["color"]}1f;display:flex;align-items:center;'
            f'justify-content:center;font-size:1.05rem;flex-shrink:0;">'
            f'{meta["icon"]}</div>'
            f'<div>'
            f'<div style="font-size:0.88rem;font-weight:800;color:#0c1a2e;'
            f'line-height:1.15;">{r["title"]}</div>'
            f'<div style="font-size:0.66rem;color:#94a3b8;font-weight:600;'
            f'margin-top:2px;">'
            f'{r["dias"]} días · {r["ciclos_anio"]:.1f} ciclos/año</div>'
            f'</div></div></td>'
        )

        cell_style = (f'padding:14px 14px;background:{bg_row};'
                      f'border-bottom:1px solid #f0f4fa;text-align:center;'
                      f'vertical-align:middle;')
        margen_cell  = (f'<td style="{cell_style}">'
                        + _matrix_pill(*r["margen_rating"],   margen_sub)  + '</td>')
        riesgo_cell  = (f'<td style="{cell_style}">'
                        + _matrix_pill(*r["riesgo_rating"],   riesgo_sub)  + '</td>')
        capital_cell = (f'<td style="{cell_style}">'
                        + _matrix_pill(*r["capital_rating"],  capital_sub) + '</td>')
        liquidez_cell= (f'<td style="{cell_style}">'
                        + _matrix_pill(*r["liquidez_rating"], liquidez_sub)+ '</td>')

        body += f'<tr>{modelo_cell}{margen_cell}{riesgo_cell}{capital_cell}{liquidez_cell}</tr>'

    return (
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 2px 10px rgba(13,27,66,0.06);">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:Inter,Arial,sans-serif;">'
        f'<thead><tr>'
        f'<th style="{th_l}">Modelo</th>'
        f'<th style="{th_c}">Margen</th>'
        f'<th style="{th_c}">Riesgo</th>'
        f'<th style="{th_c}">Capital</th>'
        f'<th style="{th_c}">Liquidez</th>'
        f'</tr></thead>'
        f'<tbody>{body}</tbody>'
        f'</table>'
        f'</div>'
        # Leyenda
        f'<div style="display:flex;justify-content:center;gap:18px;'
        f'flex-wrap:wrap;margin-top:10px;font-size:0.70rem;color:#64748b;">'
        f'<span><span style="color:#16a34a;font-weight:800;">●</span> '
        f'Mejor de la matriz</span>'
        f'<span><span style="color:#65a30d;font-weight:800;">●</span> '
        f'Bueno</span>'
        f'<span><span style="color:#d97706;font-weight:800;">●</span> '
        f'Regular</span>'
        f'<span><span style="color:#dc2626;font-weight:800;">●</span> '
        f'Peor de la matriz</span>'
        f'</div>'
    )


def _strategic_matrix_section(data: dict) -> None:
    rows = _strategic_matrix_data(data)
    st.markdown(_strategic_matrix_html(rows), unsafe_allow_html=True)


# ── Detalle por etapa: cards ─────────────────────────────────────────────────

def _metric_tile(label: str, value: str, color: str, icon: str = "",
                 value_color: str = "#0c1a2e") -> str:
    icon_html = (f'<span style="font-size:0.78rem;">{icon}</span>'
                 if icon else "")
    return (
        f'<div style="background:white;border:1px solid {color}28;'
        f'border-radius:8px;padding:10px 12px;">'
        f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;'
        f'display:flex;align-items:center;gap:4px;">'
        f'{icon_html}{label}</div>'
        f'<div style="font-size:0.95rem;font-weight:700;color:{value_color};'
        f'line-height:1.15;white-space:nowrap;">{value}</div>'
        f'</div>'
    )


def _stage_card_html(key: str, s: dict) -> str:
    meta = _SEG[key]
    color, bg, border = meta["color"], meta["bg"], meta["border"]

    margen_color = "#16a34a" if s["margen_bruto_cab"] >= 0 else "#dc2626"
    margen_bg    = "#f0fdf4" if s["margen_bruto_cab"] >= 0 else "#fef2f2"
    sign         = "+" if s["margen_bruto_cab"] >= 0 else "−"

    # ── Hero: margen bruto/cab destacado ──────────────────────────────────
    hero = (
        f'<div style="background:{margen_bg};'
        f'border:1.5px solid {margen_color}33;border-radius:10px;'
        f'padding:14px 16px;margin-bottom:10px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;gap:8px;">'
        f'<div>'
        f'<div style="font-size:0.62rem;color:{margen_color};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">'
        f'📊 Margen bruto / cab</div>'
        f'<div style="font-size:1.65rem;font-weight:800;color:{margen_color};'
        f'line-height:1;letter-spacing:-0.02em;">'
        f'{sign}USD {abs(s["margen_bruto_cab"]):,.1f}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.60rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;">Margen Total</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:{margen_color};'
        f'line-height:1.1;">USD {s["margen_bruto_total"]:,.0f}</div>'
        f'</div>'
        f'</div></div>'
    )

    # ── 6 tiles en grid 2×3 ───────────────────────────────────────────────
    tiles_data = [
        ("💵", "Ingreso/cab",         f"USD {s['ingreso_cab']:,.1f}",  "#0c1a2e"),
        ("💸", "Costo/cab",           f"USD {s['costo_cab']:,.1f}",    "#0c1a2e"),
        ("⚖️", "USD/kg producido",    f"USD {s['margen_kg']:.2f}",     "#0c1a2e"),
        ("📅", "USD/cab/día",         f"USD {s['usd_cab_dia']:.2f}",   "#0c1a2e"),
        ("📈", "ROI operativo",       f"{s['roi_operativo']*100:.1f}%", "#0c1a2e"),
        ("🧾", "Margen total (sist.)", f"USD {s['margen_bruto_total']:,.0f}",
         margen_color),
    ]
    tiles = "".join(_metric_tile(lbl, val, color, icon, vc)
                    for icon, lbl, val, vc in tiles_data)

    chip = (
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{s["cab_vend"]:,} cab · {s["dias"]} d</span>'
    )

    return (
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;">'
        f'<div style="background:linear-gradient(135deg,{color},{color}dd);'
        f'padding:13px 16px;color:white;display:flex;'
        f'justify-content:space-between;align-items:center;gap:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.15rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.95rem;font-weight:700;">{meta["title"]}</span>'
        f'</div>{chip}</div>'
        f'<div style="padding:14px 14px 16px;">'
        f'{hero}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
        f'{tiles}</div>'
        f'</div></div>'
    )


def _stage_grid(data: dict) -> None:
    cols = st.columns(2, gap="small")
    keys = ["cria", "recria", "eng_int", "eng_exp"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            st.markdown(
                _stage_card_html(key, data[key]),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:14px'></div>",
                        unsafe_allow_html=True)


# ── Entry point ──────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Margen Bruto",
        "Creación de valor económico por etapa productiva: ingresos − costos. "
        "Comparación entre estrategias y retorno incremental del ciclo.",
    )

    data = _build_margenes()

    # ── Resumen superior ──────────────────────────────────────────────────
    section("Comparativa por etapa")
    _summary_kpis(data)

    # ── Gráfico principal: ingresos · costos · margen ─────────────────────
    st.markdown(
        '<p style="font-size:0.78rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:1.6rem 0 0.2rem 0;">Ingresos · Costos · Margen bruto</p>'
        '<p style="font-size:0.78rem;color:#94a3b8;margin:0 0 0.6rem 0;">'
        'Comparación económica por etapa en USD totales del sistema. '
        'El ROI operativo de cada etapa figura debajo del grupo.'
        '</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _hero_comparative_chart(data),
        width="stretch",
        key="margen_hero_compare",
    )

    # ── Vista por cabeza vs total ─────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.78rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:1.6rem 0 0.2rem 0;">Margen por cabeza vs margen total</p>'
        '<p style="font-size:0.78rem;color:#94a3b8;margin:0 0 0.6rem 0;">'
        'Doble lectura: rendimiento unitario y tamaño absoluto del negocio.'
        '</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _bars_two_panels(data),
        width="stretch",
        key="margen_bars_compare",
    )

    st.divider()

    # ── Valor agregado entre etapas ───────────────────────────────────────
    section("Valor agregado entre etapas")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 12px 0;">'
        '<b>¿Vale la pena seguir agregando kilos?</b> '
        'Margen incremental, kilos adicionales, USD por kg agregado y días '
        'invertidos en cada transición del ciclo.'
        '</p>',
        unsafe_allow_html=True,
    )
    _value_added_section(data)

    st.divider()

    # ── Detalle por etapa ─────────────────────────────────────────────────
    section("Detalle por etapa")
    _stage_grid(data)

    st.divider()

    # ── Matriz estratégica ───────────────────────────────────────────────
    section("Matriz estratégica")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 14px 0;">'
        'Comparación ejecutiva de los 4 modelos productivos por '
        '<b>margen, riesgo, capital y liquidez</b>. Calificaciones derivadas '
        'automáticamente del ranking entre estrategias.'
        '</p>',
        unsafe_allow_html=True,
    )
    _strategic_matrix_section(data)
