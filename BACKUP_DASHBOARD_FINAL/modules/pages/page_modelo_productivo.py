"""
Modelo Productivo — Visualización del flujo biológico y operativo del animal
a lo largo del ciclo productivo:

    Nacimiento → Cría → Destete → Recría → Engorde interno → Engorde exportación

La página tiene dos bloques:
  1. Curva de crecimiento continua con hitos biológicos.
  2. Cards por etapa productiva (animales + alimentos).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.pages.ui import page_header, section

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Stage metadata ────────────────────────────────────────────────────────────

_SEG = {
    "cria":    ("Cría",                "🌱", "#16a34a"),
    "recria":  ("Recría",              "🔵", "#1565c0"),
    "eng_int": ("Engorde interno",     "🟢", "#0d9488"),
    "eng_exp": ("Engorde exportación", "🌐", "#7c3aed"),
}

_FILLS = {
    "cria":    ("rgba(22,163,74,0.08)",   "#f0fdf4", "#bbf7d0"),
    "recria":  ("rgba(21,101,192,0.08)",  "#eff6ff", "#bfdbfe"),
    "eng_int": ("rgba(13,148,136,0.08)",  "#f0fdfa", "#99f6e4"),
    "eng_exp": ("rgba(124,58,237,0.08)",  "#faf5ff", "#ddd6fe"),
}

_FEED_EDITOR_KEYS = {
    "cria":    "feed_table_cria_de",
    "recria":  "feed_table_recria_de",
    "eng_int": "feed_table_eng_int_de",
    "eng_exp": "feed_table_eng_exp_de",
}


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convierte '#RRGGBB' a 'rgba(r,g,b,alpha)' para propiedades Plotly
    que NO aceptan el formato hex de 8 caracteres (#RRGGBBAA)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Stage data reader ─────────────────────────────────────────────────────────

def _read_stages() -> dict:
    ss = st.session_state
    kg_cria_out = float(ss.get(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"]))
    kg_recria_out = float(ss.get(K.B_PESO_SALIDA, DEFAULTS["r_peso_salida"]))
    return {
        "cria": {
            "kg_in":   float(ss.get(K.A_KG_ENTRADA,   DEFAULTS["a_kg_entrada"])),
            "kg_out":  kg_cria_out,
            "dias":    int(ss.get(K.A_DIAS,           DEFAULTS["d_dias"])),
            "mort":    float(ss.get(K.A_MORTALIDAD,   DEFAULTS["d_mortalidad"])),
            "rac_dia": float(ss.get(K.A_RAC_DIARIA,   DEFAULTS["a_rac_diaria"])),
        },
        "recria": {
            "kg_in":   kg_cria_out,
            "kg_out":  kg_recria_out,
            "dias":    int(ss.get(K.B_DIAS,           DEFAULTS["b_dias"])),
            "mort":    float(ss.get(K.B_MORTALIDAD,   DEFAULTS["r_mortalidad"])),
            "rac_dia": float(ss.get(K.B_RAC_DIARIA,   DEFAULTS["b_rac_diaria"])),
        },
        "eng_int": {
            "kg_in":   kg_recria_out,
            "kg_out":  float(ss.get(K.C_PESO_FINAL,   DEFAULTS["t_peso_final"])),
            "dias":    int(ss.get(K.C_DIAS,           DEFAULTS["c_dias"])),
            "mort":    float(ss.get(K.C_MORTALIDAD,   DEFAULTS["t_mortalidad"])),
            "rac_dia": float(ss.get(K.C_RAC_DIARIA,   DEFAULTS["c_rac_diaria"])),
        },
        "eng_exp": {
            "kg_in":   float(ss.get(K.E_KG_ENTRADA,   DEFAULTS["e_kg_entrada"])),
            "kg_out":  float(ss.get(K.E_KG_SALIDA,    DEFAULTS["e_kg_salida"])),
            "dias":    int(ss.get(K.E_DIAS,           DEFAULTS["e_dias"])),
            "mort":    float(ss.get(K.E_MORTALIDAD,   DEFAULTS["e_mortalidad"])),
            "rac_dia": float(ss.get(K.E_RAC_DIARIA,   DEFAULTS["e_rac_diaria"])),
        },
    }


# ── Feed table helpers ────────────────────────────────────────────────────────

def _empty_feed_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Ingrediente": [""] * 10,
        "%":           [0.0] * 10,
        "USD/kg MS":   [0.0] * 10,
    })


def _read_feed_df(editor_key: str) -> pd.DataFrame:
    """
    Reconstruye el DataFrame de la tabla de alimentación desde session_state.

    st.data_editor con key guarda en ss[key] un dict-delta:
        {"edited_rows": {idx: {col: val}}, "added_rows": [...], "deleted_rows": [...]}
    En num_rows="fixed" sólo aparecen edited_rows. Si la versión guarda DataFrame
    directo, lo aceptamos también.
    """
    base = _empty_feed_df()
    ss = st.session_state
    if editor_key not in ss:
        return base

    val = ss[editor_key]
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


def _active_ingredients(df: pd.DataFrame) -> pd.DataFrame:
    name = df["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(df["%"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(df["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)
    return pd.DataFrame({
        "Ingrediente": name[mask].values,
        "%":           pct[mask].values,
        "USD/kg MS":   usd[mask].values,
    })


# ── Growth chart — flujo biológico continuo ──────────────────────────────────

def _build_chart(d: dict) -> go.Figure:
    """
    Curva continua del peso vivo a lo largo de las 4 etapas SECUENCIALES.

    Las etapas se concatenan en la línea de tiempo y los pesos se encadenan
    visualmente para representar la evolución de un mismo animal:
        Nacimiento → Cría → Destete → Recría → Engorde interno → Engorde exportación
    """
    t_a = d["cria"]["dias"]
    t_b = t_a + d["recria"]["dias"]
    t_c = t_b + d["eng_int"]["dias"]
    t_e = t_c + d["eng_exp"]["dias"]

    # Pesos encadenados (continuidad biológica visual)
    kg_birth       = d["cria"]["kg_in"]
    kg_destete     = d["cria"]["kg_out"]
    kg_recria_out  = d["recria"]["kg_out"]
    kg_eng_int_out = d["eng_int"]["kg_out"]
    kg_eng_exp_out = d["eng_exp"]["kg_out"]

    fig = go.Figure()

    # ── 1. Bandas de fondo por etapa ───────────────────────────────────────
    bands = [
        (0,    t_a, _FILLS["cria"][0]),
        (t_a,  t_b, _FILLS["recria"][0]),
        (t_b,  t_c, _FILLS["eng_int"][0]),
        (t_c,  t_e, _FILLS["eng_exp"][0]),
    ]
    for x0, x1, fill in bands:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=fill,
                      layer="below", line_width=0)

    # ── 2. Divisores verticales suaves entre etapas ────────────────────────
    for xd in [t_a, t_b, t_c]:
        fig.add_vline(x=xd, line_dash="dot",
                      line_color="rgba(100,116,139,0.30)", line_width=1.5)

    # ── 3. Curva de crecimiento (halo + línea principal con spline) ────────
    xs = [0, t_a, t_b, t_c, t_e]
    ys = [kg_birth, kg_destete, kg_recria_out, kg_eng_int_out, kg_eng_exp_out]

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color="rgba(21,101,192,0.18)", width=14,
                  shape="spline", smoothing=0.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines+markers",
        line=dict(color="#1565c0", width=3.5,
                  shape="spline", smoothing=0.5),
        marker=dict(size=12, color="#1565c0", symbol="circle",
                    line=dict(color="white", width=3)),
        showlegend=False,
        hovertemplate="<b>Día %{x}</b><br>Peso: %{y:.0f} kg<extra></extra>",
    ))

    # ── 4. Hitos biológicos (con flecha hacia el punto de la curva) ────────
    milestones = [
        (0,   kg_birth,       "🐣 Nacimiento",         "#16a34a"),
        (t_a, kg_destete,     "🥛 Destete",            "#1565c0"),
        (t_b, kg_recria_out,  "🟢 Inicio Engorde",     "#0d9488"),
        (t_c, kg_eng_int_out, "🌐 Inicio Exportación", "#7c3aed"),
        (t_e, kg_eng_exp_out, "💰 Venta final",        "#b91c1c"),
    ]
    for x, y, label, color in milestones:
        fig.add_annotation(
            x=x, y=y,
            text=(f"<b>{label}</b>"
                  f"<br><span style='color:#475569;font-size:9px;'>"
                  f"{y:.0f} kg · día {x}</span>"),
            showarrow=True,
            arrowhead=0, arrowwidth=1, arrowcolor=_hex_to_rgba(color, 0.6),
            ax=0, ay=-50,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor=color,
            borderwidth=1,
            borderpad=5,
        )

    # ── 5. Labels de etapa BAJO el eje X (nombre + duración) ───────────────
    stage_labels = [
        (t_a / 2,           "🌱 Cría",              d["cria"]["dias"],    "#16a34a"),
        ((t_a + t_b) / 2,   "🔵 Recría",            d["recria"]["dias"],  "#1565c0"),
        ((t_b + t_c) / 2,   "🟢 Eng. interno",      d["eng_int"]["dias"], "#0d9488"),
        ((t_c + t_e) / 2,   "🌐 Eng. exportación",  d["eng_exp"]["dias"], "#7c3aed"),
    ]
    for xc, name, dur, color in stage_labels:
        fig.add_annotation(
            x=xc, y=-0.18, xref="x", yref="paper",
            text=(f"<b style='color:{color};'>{name}</b>"
                  f"<br><span style='color:#94a3b8;font-size:9px;'>{dur} días</span>"),
            showarrow=False,
            font=dict(size=11),
            align="center",
        )

    fig.update_layout(
        height=560,
        margin=dict(t=80, b=110, l=70, r=40),
        xaxis=dict(
            title=None,
            range=[-15, t_e + 25],
            gridcolor="#eef2f7",
            zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            ticksuffix=" d",
        ),
        yaxis=dict(
            title=dict(text="Peso vivo (kg/animal)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7",
            zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            ticksuffix=" kg",
        ),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter, Arial, sans-serif"),
        hovermode="x unified",
    )
    return fig


# ── Sección Animales (grid moderno de 8 métricas) ────────────────────────────

def _animals_section_html(
    cabezas: int, dias: int, kg_in: float, kg_out: float,
    gdp: float, mort: float, conv: float, consumo: float,
    color: str,
) -> str:
    metrics = [
        ("🐄", "Cabezas",       f"{cabezas:,}",   "cab"),
        ("📅", "Días",          f"{dias}",        "días"),
        ("⚖️", "Peso entrada",  f"{kg_in:.0f}",   "kg"),
        ("⚖️", "Peso salida",   f"{kg_out:.0f}",  "kg"),
        ("📈", "GDP",           f"{gdp:.3f}",     "kg/día"),
        ("⚠️", "Mortandad",     f"{mort:.1f}",    "%"),
        ("🔄", "Conversión",    f"{conv:.2f}",    "kg/kg"),
        ("🌾", "Consumo MS",    f"{consumo:.0f}", "kg/cab"),
    ]
    items = ""
    for icon, label, value, unit in metrics:
        items += (
            f'<div style="background:white;border:1px solid {color}28;'
            f'border-radius:8px;padding:9px 11px;">'
            f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;'
            f'display:flex;align-items:center;gap:4px;">'
            f'<span style="font-size:0.78rem;">{icon}</span>{label}</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:#0c1a2e;'
            f'line-height:1.1;white-space:nowrap;">{value}'
            f'<span style="font-size:0.65rem;color:#94a3b8;font-weight:600;'
            f'margin-left:3px;">{unit}</span></div>'
            f'</div>'
        )
    return (
        f'<div>'
        f'<div style="font-size:0.66rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:6px;">'
        f'<span style="height:3px;width:14px;background:{color};border-radius:2px;"></span>'
        f'🐂 Animales</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">'
        f'{items}</div></div>'
    )


# ── Sección Alimentos (tabla 6 columnas) ─────────────────────────────────────

def _feed_section_html(
    editor_key: str, rac_dia: float, dias: int, color: str,
) -> str:
    df = _active_ingredients(_read_feed_df(editor_key))

    header = (
        f'<div style="font-size:0.66rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:6px;">'
        f'<span style="height:3px;width:14px;background:{color};border-radius:2px;"></span>'
        f'🌾 Alimentos</div>'
    )

    if df.empty:
        return (
            f'<div style="margin-top:16px;">{header}'
            f'<div style="border:1.5px dashed {color}33;border-radius:8px;'
            f'padding:14px 12px;text-align:center;color:#94a3b8;'
            f'font-size:0.74rem;line-height:1.4;">'
            f'Sin ingredientes cargados<br>'
            f'<span style="font-size:0.66rem;">Definí en Parámetros → Alimentación</span>'
            f'</div></div>'
        )

    rows_html = ""
    for i, (_, r) in enumerate(df.iterrows()):
        name = str(r["Ingrediente"]).strip()
        pct = float(r["%"])
        usd_kg = float(r["USD/kg MS"])

        kg_ms_dia   = rac_dia * (pct / 100.0)
        kg_ms_etapa = kg_ms_dia * dias
        usd_dia     = kg_ms_dia * usd_kg
        usd_etapa   = kg_ms_etapa * usd_kg

        bg = "rgba(255,255,255,0.6)" if i % 2 == 0 else "transparent"
        cell = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                'color:#374151;white-space:nowrap;')
        cell_l = ('padding:5px 6px;font-size:0.74rem;text-align:left;'
                  'color:#0c1a2e;font-weight:600;white-space:nowrap;'
                  'overflow:hidden;text-overflow:ellipsis;max-width:90px;')
        cell_strong = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                       'color:#0c1a2e;font-weight:700;white-space:nowrap;')

        rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="{cell_l}" title="{name}">{name}</td>'
            f'<td style="{cell}">{pct:.1f}%</td>'
            f'<td style="{cell}">{kg_ms_dia:.2f}</td>'
            f'<td style="{cell}">{kg_ms_etapa:.0f}</td>'
            f'<td style="{cell}">{usd_dia:.3f}</td>'
            f'<td style="{cell_strong}">{usd_etapa:.2f}</td>'
            f'</tr>'
        )

    th_base = (f'padding:5px 6px;font-size:0.60rem;font-weight:700;'
               f'color:{color};white-space:nowrap;text-transform:uppercase;'
               f'letter-spacing:0.04em;')
    th_l = th_base + 'text-align:left;'
    th_r = th_base + 'text-align:right;'

    return (
        f'<div style="margin-top:16px;">{header}'
        f'<div style="overflow-x:auto;border-radius:8px;">'
        f'<table style="width:100%;min-width:380px;border-collapse:collapse;">'
        f'<thead><tr style="background:{color}18;'
        f'border-bottom:1.5px solid {color}33;">'
        f'<th style="{th_l}">Ingrediente</th>'
        f'<th style="{th_r}">%</th>'
        f'<th style="{th_r}">kg MS/día</th>'
        f'<th style="{th_r}">kg MS/etapa</th>'
        f'<th style="{th_r}">USD/día</th>'
        f'<th style="{th_r}">USD/etapa</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div></div>'
    )


# ── Cards por etapa productiva ───────────────────────────────────────────────

def _segment_cards(d: dict) -> None:
    ss = st.session_state
    n_t = int(ss.get(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))

    # Cabezas en cascada (etapa previa × (1 - mortandad))
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100)), 0)

    cab = {"cria": n_t}
    cab["recria"]  = surv(cab["cria"],   d["cria"]["mort"])
    cab["eng_int"] = surv(cab["recria"], d["recria"]["mort"])
    cab["eng_exp"] = surv(cab["eng_int"], d["eng_int"]["mort"])

    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["cria", "recria", "eng_int", "eng_exp"]):
        title, icon, color = _SEG[key]
        _, bg, border = _FILLS[key]
        s = d[key]

        kg_in   = s["kg_in"]
        kg_out  = s["kg_out"]
        kg_prod = max(kg_out - kg_in, 0.0)
        dias    = s["dias"]
        gdp     = kg_prod / dias if dias > 0 else 0.0
        consumo = s["rac_dia"] * dias
        conv    = consumo / kg_prod if kg_prod > 0 else 0.0

        animals_html = _animals_section_html(
            cabezas=cab[key], dias=dias, kg_in=kg_in, kg_out=kg_out,
            gdp=gdp, mort=s["mort"], conv=conv, consumo=consumo,
            color=color,
        )
        feed_html = _feed_section_html(
            editor_key=_FEED_EDITOR_KEYS[key],
            rac_dia=s["rac_dia"],
            dias=dias,
            color=color,
        )

        with col:
            st.markdown(
                f"""<div style="background:{bg};border:1px solid {border};
                            border-radius:14px;padding:0;overflow:hidden;
                            box-shadow:0 1px 6px rgba(13,27,66,0.05);
                            height:100%;">
                    <div style="background:linear-gradient(135deg,{color},{color}dd);
                                padding:13px 16px;color:white;">
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center;gap:8px;">
                            <div style="display:flex;align-items:center;gap:8px;
                                        min-width:0;">
                                <span style="font-size:1.15rem;flex-shrink:0;">{icon}</span>
                                <span style="font-size:0.95rem;font-weight:700;
                                             white-space:nowrap;overflow:hidden;
                                             text-overflow:ellipsis;">{title}</span>
                            </div>
                            <div style="background:rgba(255,255,255,0.22);
                                        border-radius:14px;padding:3px 10px;
                                        font-size:0.70rem;font-weight:700;
                                        white-space:nowrap;flex-shrink:0;">
                                {dias} días
                            </div>
                        </div>
                    </div>
                    <div style="padding:14px 14px 16px;">
                        {animals_html}
                        {feed_html}
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


# ── Entry point ───────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Modelo Productivo",
        "Evolución biológica del animal: nacimiento → cría → destete → recría → "
        "engorde interno → engorde exportación.",
    )

    d = _read_stages()

    section("Curva de crecimiento — del nacimiento a la venta")
    st.plotly_chart(_build_chart(d), use_container_width=True)

    st.divider()

    section("Etapas productivas")
    _segment_cards(d)
