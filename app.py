"""
Engordando Holando — by Sofía Stieglitz
Entry point: page config, CSS, nav, routing only.
All page logic lives in modules/pages/.
All economic logic lives in modules/economics/.
"""
from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

from modules.sidebar import render_sidebar
from modules.version import get_version_string
from modules.economics.comparador import Comparador
from modules.pages import (
    page_inicio,
    page_parametros,
    page_modelo_productivo,
    page_ingresos,
    page_costos,
    page_margenes,
    page_sensibilidad,
    page_reportes,
)

st.set_page_config(
    page_title="Engordando Holando — by Sofía Stieglitz",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
_CSS = """
<style>

/* ═══════════════════════════════════════════════════
   SIDEBAR — dark theme
═══════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(170deg, #0c1a2e 0%, #091525 100%);
    border-right: 1px solid #16304f;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stMarkdown  { color: #7fa8cc !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4           { color: #c5dff0 !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #4a7a9b !important; }
[data-testid="stSidebar"] hr           { border-color: #16304f !important; margin: 8px 0 !important; }
[data-testid="stSidebar"] details {
    border: 1px solid #16304f !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,0.03) !important;
    margin-bottom: 4px !important;
}
[data-testid="stSidebar"] details summary { color: #7fa8cc !important; padding: 8px 12px !important; }
[data-testid="stSidebar"] details[open] summary { color: #a8cfea !important; }

/* ═══════════════════════════════════════════════════
   NATIVE st.metric — tabs pages
═══════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #f8fafd;
    border: 1px solid #dce8f5;
    border-radius: 12px;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(13,27,66,0.05);
}
[data-testid="stMetricValue"] {
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    color: #0d1b42 !important;
    line-height: 1.2 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    color: #5d7a95 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* ═══════════════════════════════════════════════════
   MAIN CONTENT AREA
═══════════════════════════════════════════════════ */
.main .block-container {
    padding-top: 1.6rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

/* ── Page typography ─────────────────────────────── */
.ap-page-title {
    font-size: 1.5rem; font-weight: 800; color: #0c1a2e;
    margin: 0 0 3px 0; letter-spacing: -0.025em; line-height: 1.15;
}
.ap-page-sub {
    font-size: 0.86rem; color: #64748b; margin: 0 0 1.2rem 0;
}
.ap-section {
    font-size: 0.78rem; font-weight: 700; color: #7a8fa6;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 1.6rem 0 0.8rem 0;
}

/* ═══════════════════════════════════════════════════
   KPI CARDS — custom HTML
═══════════════════════════════════════════════════ */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e4eaf4;
    border-radius: 16px;
    padding: 20px 22px 18px;
    box-shadow: 0 2px 10px rgba(13,27,66,0.07), 0 0 0 1px rgba(13,27,66,0.02);
    position: relative;
    overflow: hidden;
    height: 100%;
    box-sizing: border-box;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.ac-blue::after   { background: linear-gradient(90deg,#1565c0,#42a5f5); }
.ac-green::after  { background: linear-gradient(90deg,#1a6b3c,#4caf50); }
.ac-amber::after  { background: linear-gradient(90deg,#b45309,#f5a623); }
.ac-purple::after { background: linear-gradient(90deg,#5c35c4,#9c27b0); }
.ac-cyan::after   { background: linear-gradient(90deg,#0891b2,#22d3ee); }
.ac-rose::after   { background: linear-gradient(90deg,#be123c,#f43f5e); }
.ac-teal::after   { background: linear-gradient(90deg,#0d9488,#2dd4bf); }

.kpi-badge {
    display: inline-block;
    font-size: 0.66rem; font-weight: 700;
    padding: 2px 9px; border-radius: 20px;
    margin-bottom: 10px;
    letter-spacing: 0.05em; text-transform: uppercase;
}
.bd-amber { background:#fff7ed; color:#b45309; border:1px solid #fde68a; }
.bd-blue  { background:#eff6ff; color:#1565c0; border:1px solid #bfdbfe; }
.bd-green { background:#f0fdf4; color:#1a6b3c; border:1px solid #bbf7d0; }

.kpi-icon { font-size:1.55rem; margin-bottom:8px; display:block; }

.kpi-value {
    font-size: 2rem; font-weight: 800; color: #0c1a2e;
    letter-spacing: -0.04em; line-height: 1.05; margin-bottom: 5px;
}
.kpi-value-md {
    font-size: 1.45rem; font-weight: 800; color: #0c1a2e;
    letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 5px;
}
.kpi-label {
    font-size: 0.69rem; font-weight: 700; color: #7a8fa6;
    text-transform: uppercase; letter-spacing: 0.07em;
}

.kpi-delta-pos { font-size:0.77rem; color:#16a34a; font-weight:600; margin-top:6px; }
.kpi-delta-neg { font-size:0.77rem; color:#dc2626; font-weight:600; margin-top:6px; }
.kpi-delta-off { font-size:0.77rem; color:#64748b; font-weight:500; margin-top:6px; }

.kpi-hr { border:none; border-top:1px solid #f0f4fa; margin:12px 0 10px; }
.kpi-sub { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.kpi-sub-v { font-size: 0.92rem; font-weight: 700; color: #1e3a5f; line-height: 1.2; }
.kpi-sub-l {
    font-size: 0.64rem; font-weight: 700; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1px;
}

/* ═══════════════════════════════════════════════════
   FLUJO FINANCIERO — horizontal strip
═══════════════════════════════════════════════════ */
.flujo-wrap { display: flex; align-items: stretch; gap: 6px; margin: 4px 0; }
.flujo-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #e4eaf4;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 1px 6px rgba(13,27,66,0.05);
}
.flujo-icon { font-size: 1.3rem; margin-bottom: 6px; }
.flujo-v    { font-size: 1.05rem; font-weight: 800; color: #0c1a2e; letter-spacing: -0.02em; line-height: 1.15; }
.flujo-l    { font-size: 0.62rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 3px; }
.flujo-pos  { color: #16a34a !important; }
.flujo-neg  { color: #dc2626 !important; }
.flujo-neu  { color: #1565c0 !important; }
.flujo-arrow { display: flex; align-items: center; justify-content: center; color: #c8d8ea; font-size: 1.4rem; flex-shrink: 0; }

/* ═══════════════════════════════════════════════════
   BEST-SCENARIO BANNER
═══════════════════════════════════════════════════ */
.ap-banner {
    border-radius: 12px; padding: 14px 22px; margin-bottom: 20px;
    font-size: 0.92rem; line-height: 1.75;
}

/* ═══════════════════════════════════════════════════
   PLACEHOLDER
═══════════════════════════════════════════════════ */
.ap-ph {
    border: 2px dashed #c5d8ed; border-radius: 16px;
    padding: 64px 40px; text-align: center;
    background: #f5f9fd; margin-top: 16px;
}
.ap-ph-icon  { font-size: 3rem; margin-bottom: 12px; }
.ap-ph-title { font-size: 1.2rem; font-weight: 700; color: #1e3a5f; margin-bottom: 6px; }
.ap-ph-text  { font-size: 0.9rem; color: #5d7a95; }

</style>
"""

# ── Nav ───────────────────────────────────────────────────────────────────────
_NAV_ITEMS: list[tuple[str, str]] = [
    ("Inicio",                  "house-fill"),
    ("Parámetros",              "sliders"),
    ("Modelo Productivo",       "layers-fill"),
    ("Costos",                  "cash-stack"),
    ("Ingresos",                "graph-up-arrow"),
    ("Margen Bruto",            "bar-chart-fill"),
    ("Sensibilidad y Riesgo",   "diagram-3-fill"),
    ("Reportes",                "file-earmark-text-fill"),
]

_NAV_STYLES: dict = {
    "container": {"padding": "2px 0 !important", "background-color": "transparent"},
    "icon": {"color": "#4da6ff", "font-size": "14px"},
    "nav-link": {
        "font-size": "0.86rem", "text-align": "left",
        "margin": "1px 8px", "padding": "7px 12px", "border-radius": "7px",
        "color": "#7fa8cc", "--hover-color": "rgba(77,166,255,0.12)",
    },
    "nav-link-selected": {
        "background-color": "rgba(21,101,192,0.32)",
        "color": "#e0f0ff", "font-weight": "600",
    },
    "menu-title": {"display": "none"},
}

_PAGES: dict = {
    "Inicio":                   page_inicio.render,
    "Parámetros":               page_parametros.render,
    "Modelo Productivo":        page_modelo_productivo.render,
    "Costos":                   page_costos.render,
    "Ingresos":                 page_ingresos.render,
    "Margen Bruto":             page_margenes.render,
    "Sensibilidad y Riesgo":    page_sensibilidad.render,
    "Reportes":                 page_reportes.render,
}


def _branding() -> None:
    st.markdown(
        """<div style="padding:1.3rem 1rem 1.1rem;border-bottom:1px solid #16304f;margin-bottom:2px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <div style="width:44px;height:44px;border-radius:11px;flex-shrink:0;
                    background:linear-gradient(135deg,#1565c0,#0d47a1);
                    box-shadow:0 3px 10px rgba(21,101,192,0.45);
                    display:flex;align-items:center;justify-content:center;font-size:24px;">🐄</div>
                <div>
                    <div style="font-size:1.06rem;font-weight:700;color:#ddeeff;
                                letter-spacing:-0.01em;line-height:1.2;">Engordando Holando</div>
                    <div style="font-size:0.67rem;font-weight:600;color:#4da6ff;
                                letter-spacing:0.05em;margin-top:2px;font-style:italic;">
                        by Sofía Stieglitz</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _version_footer() -> None:
    st.markdown(
        f"""<div style="padding:10px 14px 14px;margin-top:auto;
                        font-size:0.66rem;color:#4a7a9b;
                        letter-spacing:0.03em;line-height:1.4;">
            <span style="color:#3d6885;">build</span>
            <span style="color:#7fa8cc;font-family:monospace;">{get_version_string()}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # Sidebar: branding + nav
    with st.sidebar:
        _branding()
        labels = [i[0] for i in _NAV_ITEMS]
        icons  = [i[1] for i in _NAV_ITEMS]
        selected: str = option_menu(
            menu_title=None,
            options=labels,
            icons=icons,
            default_index=0,
            styles=_NAV_STYLES,
            key="main_nav",
        )
        st.divider()
        _version_footer()

    # Read params from session_state (widgets live in page_parametros)
    params = render_sidebar()
    comp = Comparador(params)

    # Route to page module
    render_fn = _PAGES.get(selected)
    if render_fn:
        render_fn(params, comp)


if __name__ == "__main__":
    main()
