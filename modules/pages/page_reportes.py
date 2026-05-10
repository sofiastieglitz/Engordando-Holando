"""
Reportes — One Pager ejecutivo (formato A4).

Snapshot de la simulación activa: contexto + margen total + cards por etapa
activa + tabla de detalle productivo y económico + bloque de riesgo. Refleja
dinámicamente la selección de etapas hecha en Parámetros.
"""
from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING

import streamlit as st

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.state import stages as S
from modules.pages.ui import page_header
from modules.pages import page_costos as cp
from modules.pages import page_margenes as pm
from modules.pages import page_sensibilidad as ps

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Metadatos por etapa (mismos colores que las otras slides) ────────────────

_STAGE_META: dict[str, dict] = {
    "cria":    {"title": "Cría",    "icon": "🌱", "color": "#16a34a",
                "bg": "#f0fdf4", "border": "#bbf7d0"},
    "recria":  {"title": "Recría",  "icon": "🔵", "color": "#1565c0",
                "bg": "#eff6ff", "border": "#bfdbfe"},
    "eng_int": {"title": "Engorde", "icon": "🟢", "color": "#0d9488",
                "bg": "#f0fdfa", "border": "#99f6e4"},
}


# ── Session state keys ──────────────────────────────────────────────────────

_K_EMPRESA     = "report_empresa"
_K_RESPONSABLE = "report_responsable"
_K_FECHA       = "report_fecha"
_K_LOGO        = "report_include_logo"


def _ensure_state() -> None:
    """Inicializa las claves de session_state si no existen.
    Idempotente: respeta valores ya editados por el usuario."""
    if _K_EMPRESA not in st.session_state:
        st.session_state[_K_EMPRESA] = "Mi Empresa Ganadera"
    if _K_RESPONSABLE not in st.session_state:
        st.session_state[_K_RESPONSABLE] = ""
    if _K_FECHA not in st.session_state:
        st.session_state[_K_FECHA] = date.today()
    if _K_LOGO not in st.session_state:
        st.session_state[_K_LOGO] = True


# ── 1. Editor de inputs (toolbar superior) ──────────────────────────────────

def _render_editor() -> None:
    st.markdown(
        '<p style="font-size:0.66rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:0 0 8px 0;">⚙️ Configuración del reporte</p>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns([2.2, 2.2, 1.3, 1.2])
    with c1:
        st.text_input(
            "Empresa", key=_K_EMPRESA,
            placeholder="Nombre de la empresa",
        )
    with c2:
        st.text_input(
            "Responsable", key=_K_RESPONSABLE,
            placeholder="Nombre del responsable",
        )
    with c3:
        st.date_input("Fecha", key=_K_FECHA, format="DD/MM/YYYY")
    with c4:
        # Empuja el checkbox para alinearlo con los inputs (que tienen label)
        st.markdown("<div style='height:28px'></div>",
                    unsafe_allow_html=True)
        st.checkbox("Incluir logo", key=_K_LOGO)

    st.markdown(
        '<div style="height:6px;border-bottom:1px dashed #e4eaf4;'
        'margin:10px 0 22px 0;"></div>',
        unsafe_allow_html=True,
    )


# ── 2. Logo de Engordando Holando ───────────────────────────────────────────

def _logo_block_html() -> str:
    """HTML del logo cuando está activado (réplica del branding del sidebar)."""
    return (
        '<div style="display:flex;align-items:center;gap:14px;">'
        '<div style="width:64px;height:64px;border-radius:14px;'
        'background:linear-gradient(135deg,#1565c0,#0d47a1);'
        'box-shadow:0 4px 14px rgba(21,101,192,0.35);'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:34px;color:white;flex-shrink:0;">🐄</div>'
        '<div>'
        '<div style="font-size:1.10rem;font-weight:800;color:#0c1a2e;'
        'letter-spacing:-0.01em;line-height:1.15;">Engordando Holando</div>'
        '<div style="font-size:0.66rem;font-weight:600;color:#1565c0;'
        'letter-spacing:0.04em;margin-top:3px;font-style:italic;">'
        'by Sofía Stieglitz</div>'
        '</div></div>'
    )


# ── 3. Header ejecutivo (dentro del A4) ─────────────────────────────────────

def _format_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value) if value else "—"


def _info_field_html(label: str, value: str) -> str:
    val = (value or "").strip() or "—"
    return (
        f'<div style="margin-top:5px;">'
        f'<div style="font-size:0.60rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.07em;">{label}</div>'
        f'<div style="font-size:0.92rem;color:#0c1a2e;font-weight:700;'
        f'line-height:1.25;">{val}</div></div>'
    )


def _header_html() -> str:
    show_logo   = bool(st.session_state.get(_K_LOGO, True))
    empresa     = st.session_state.get(_K_EMPRESA, "")
    responsable = st.session_state.get(_K_RESPONSABLE, "")
    fecha_str   = _format_date(st.session_state.get(_K_FECHA, date.today()))

    logo_html = _logo_block_html() if show_logo else '<div></div>'

    info_html = (
        '<div style="text-align:right;">'
        + _info_field_html("Empresa", empresa)
        + _info_field_html("Responsable", responsable)
        + _info_field_html("Fecha", fecha_str)
        + '</div>'
    )

    return (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:24px;padding-bottom:18px;'
        'border-bottom:2px solid #e4eaf4;">'
        f'{logo_html}{info_html}'
        '</div>'
    )


# ── 4. Título principal ─────────────────────────────────────────────────────

def _title_html() -> str:
    return (
        '<div style="text-align:center;margin:28px 0 22px 0;">'
        '<div style="font-size:0.66rem;font-weight:800;color:#1565c0;'
        'letter-spacing:0.18em;text-transform:uppercase;margin-bottom:10px;">'
        '📑 Reporte ejecutivo</div>'
        '<div style="font-size:2rem;font-weight:800;color:#0c1a2e;'
        'letter-spacing:-0.03em;line-height:1.15;margin-bottom:8px;">'
        'Reporte Estratégico Ganadero</div>'
        '<div style="font-size:0.94rem;color:#64748b;font-weight:500;'
        'line-height:1.45;max-width:560px;margin:0 auto;">'
        'Resumen ejecutivo de simulación productiva y económica</div>'
        '</div>'
    )


# ── 5. Helpers de color (riesgo / robustez) ─────────────────────────────────

def _risk_color(score: float) -> str:
    """Mayor riesgo = peor (rojo); menor = verde."""
    if score >= 70: return "#dc2626"
    if score >= 40: return "#d97706"
    return "#16a34a"


def _robust_color(score: float) -> str:
    """Mayor robustez = mejor (verde)."""
    if score >= 70: return "#16a34a"
    if score >= 40: return "#d97706"
    return "#dc2626"


def _hero_margen_html(margen_total: float, active_keys: list[str],
                       n_terneros: int, dias_total: int) -> str:
    """Hero principal: MARGEN TOTAL DEL SISTEMA en grande."""
    color_tot = "#16a34a" if margen_total >= 0 else "#dc2626"
    sign = "+" if margen_total >= 0 else "−"
    accent = "#1565c0"

    pretty = " · ".join(
        f'<span style="color:{_STAGE_META[k]["color"]};">'
        f'{_STAGE_META[k]["icon"]} {_STAGE_META[k]["title"]}</span>'
        for k in active_keys
    ) or "—"

    return (
        f'<div style="background:linear-gradient(135deg,{accent}10,{accent}03);'
        f'border:2px solid {accent}40;border-radius:14px;'
        f'padding:26px 30px;margin-top:18px;text-align:center;">'
        f'<div style="font-size:0.66rem;color:{accent};font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.18em;margin-bottom:8px;">'
        f'Margen total del sistema</div>'
        f'<div style="font-size:3.0rem;font-weight:800;color:{color_tot};'
        f'line-height:1;letter-spacing:-0.04em;'
        f'font-variant-numeric:tabular-nums;margin:6px 0 8px;">'
        f'{sign}USD {abs(margen_total):,.0f}</div>'
        f'<div style="font-size:0.85rem;color:#475569;line-height:1.4;'
        f'margin-top:4px;">{pretty}</div>'
        f'<div style="font-size:0.72rem;color:#94a3b8;line-height:1.4;'
        f'margin-top:3px;">{n_terneros:,} cab · {dias_total} días totales</div>'
        f'</div>'
    )


def _simulation_context_html(active_keys: list[str], n_terneros: int) -> str:
    """Franja con contexto identificatorio de la simulación."""
    empresa     = (st.session_state.get(_K_EMPRESA, "") or "—").strip() or "—"
    responsable = (st.session_state.get(_K_RESPONSABLE, "") or "—").strip() or "—"
    fecha_str   = _format_date(st.session_state.get(_K_FECHA, date.today()))

    if not active_keys:
        etapas_str = "—"
    else:
        etapas_str = " + ".join(_STAGE_META[k]["title"] for k in active_keys)

    items = [
        ("Empresa",      empresa),
        ("Responsable",  responsable),
        ("Fecha",        fecha_str),
        ("Etapas",       etapas_str),
        ("Cabezas",      f"{n_terneros:,}"),
    ]
    cells = "".join(
        f'<div style="flex:1;min-width:0;padding:0 10px;'
        f'border-right:1px solid #e4eaf4;">'
        f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.08em;'
        f'margin-bottom:3px;">{lbl}</div>'
        f'<div style="font-size:0.84rem;color:#0c1a2e;font-weight:700;'
        f'line-height:1.2;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{val}</div></div>'
        for lbl, val in items
    )
    # remove the last border-right
    cells = cells.replace(
        'border-right:1px solid #e4eaf4;', 'border-right:1px solid #e4eaf4;', 4
    )
    return (
        f'<div style="background:#f8fafd;border:1px solid #e4eaf4;'
        f'border-radius:10px;padding:11px 6px;margin-top:14px;'
        f'display:flex;align-items:stretch;">'
        f'{cells}</div>'
        f'<style>'
        f'</style>'
    )


def _stage_cards_html(active_keys: list[str], marg: dict,
                       risk_by_key: dict) -> str:
    """Cards por etapa activa con: margen/cab, ingreso/cab, costo/cab,
    riesgo, robustez."""
    if not active_keys:
        return ""

    n = len(active_keys)
    grid = "1fr" if n == 1 else ("1fr 1fr" if n == 2 else "1fr 1fr 1fr")

    cards_html = ""
    for k in active_keys:
        meta = _STAGE_META[k]
        m = marg[k]
        r = risk_by_key.get(k, {})
        margen_cab  = m["margen_bruto_cab"]
        ingreso_cab = m["ingreso_cab"]
        costo_cab   = m["costo_cab"]
        riesgo      = r.get("risk_composite", 0.0)
        robustez    = r.get("robustness", 0.0)

        m_color = "#16a34a" if margen_cab >= 0 else "#dc2626"
        m_sign  = "+" if margen_cab >= 0 else "−"
        ri_col  = _risk_color(riesgo)
        ro_col  = _robust_color(robustez)

        cards_html += (
            f'<div style="background:white;border:1px solid {meta["border"]};'
            f'border-top:3px solid {meta["color"]};border-radius:12px;'
            f'padding:14px 16px;box-shadow:0 1px 6px rgba(13,27,66,0.05);">'
            # Header
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'margin-bottom:10px;">'
            f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
            f'<span style="font-size:0.78rem;font-weight:800;color:{meta["color"]};'
            f'text-transform:uppercase;letter-spacing:0.07em;">'
            f'{meta["title"]}</span>'
            f'</div>'
            # Margen — destacado
            f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.07em;">Margen / cab</div>'
            f'<div style="font-size:1.45rem;font-weight:800;color:{m_color};'
            f'line-height:1.1;letter-spacing:-0.02em;'
            f'margin:1px 0 10px;font-variant-numeric:tabular-nums;">'
            f'{m_sign}USD {abs(margen_cab):,.0f}</div>'
            # Ingreso/Costo
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;'
            f'border-top:1px solid #f0f4fa;padding-top:8px;">'
            f'<div><div style="font-size:0.85rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.1;font-variant-numeric:tabular-nums;">'
            f'USD {ingreso_cab:,.0f}</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.07em;'
            f'margin-top:2px;">Ingreso</div></div>'
            f'<div><div style="font-size:0.85rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.1;font-variant-numeric:tabular-nums;">'
            f'USD {costo_cab:,.0f}</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.07em;'
            f'margin-top:2px;">Costo</div></div>'
            f'</div>'
            # Riesgo / Robustez
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;'
            f'margin-top:8px;padding-top:8px;border-top:1px solid #f0f4fa;">'
            f'<div><div style="font-size:0.85rem;font-weight:700;color:{ri_col};'
            f'line-height:1.1;font-variant-numeric:tabular-nums;">'
            f'{riesgo:.0f}/100</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.07em;'
            f'margin-top:2px;">Riesgo</div></div>'
            f'<div><div style="font-size:0.85rem;font-weight:700;color:{ro_col};'
            f'line-height:1.1;font-variant-numeric:tabular-nums;">'
            f'{robustez:.0f}/100</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.07em;'
            f'margin-top:2px;">Robustez</div></div>'
            f'</div>'
            f'</div>'
        )

    return (
        f'<div style="display:grid;grid-template-columns:{grid};'
        f'gap:10px;margin-top:14px;">{cards_html}</div>'
    )


def _stage_detail_html(active_keys: list[str], marg: dict,
                        costos: dict) -> str:
    """Tabla compacta con detalle productivo + económico por etapa activa."""
    if not active_keys:
        return ""

    th_style = ('font-size:0.56rem;color:#7a8fa6;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.06em;'
                'padding:6px 7px;text-align:right;border-bottom:1px solid #e4eaf4;')
    th_first = th_style + 'text-align:left;'
    td_style = ('font-size:0.78rem;color:#0c1a2e;font-weight:600;'
                'padding:7px 7px;text-align:right;'
                'border-bottom:1px solid #f0f4fa;'
                'font-variant-numeric:tabular-nums;')
    td_first = td_style.replace("text-align:right", "text-align:left")

    headers = ["Etapa", "Cab", "Días", "kg in", "kg out", "GDP", "CA",
               "USD/kg", "USD/cab/día", "Margen/cab"]

    head_html = "<tr>" + "".join(
        f'<th style="{th_first if i == 0 else th_style}">{h}</th>'
        for i, h in enumerate(headers)
    ) + "</tr>"

    rows_html = ""
    for k in active_keys:
        meta = _STAGE_META[k]
        m = marg[k]
        c = costos[k]
        kg_in   = m["kg_in"]
        kg_out  = m["kg_out"]
        dias    = m["dias"]
        gdp     = (kg_out - kg_in) / dias if dias > 0 else 0.0
        ca_val  = ps._g({
            "cria": K.A_CA, "recria": K.B_CA, "eng_int": K.C_CA,
        }[k], DEFAULTS[{"cria": "a_ca", "recria": "r_ca", "eng_int": "t_ca"}[k]])
        usd_kg  = c.get("usd_kg", 0.0)
        ucd     = m["usd_cab_dia"]
        margen  = m["margen_bruto_cab"]
        m_color = "#16a34a" if margen >= 0 else "#dc2626"
        m_sign  = "+" if margen >= 0 else "−"

        cells = [
            f'<span style="color:{meta["color"]};font-weight:800;">{meta["icon"]} '
            f'{meta["title"]}</span>',
            f'{m["cab_in"]:,}',
            f'{dias}',
            f'{kg_in:.0f}',
            f'{kg_out:.0f}',
            f'{gdp:.3f}',
            f'{ca_val:.1f}',
            f'{usd_kg:.2f}',
            f'{ucd:.2f}',
            f'<span style="color:{m_color};font-weight:800;">'
            f'{m_sign}{abs(margen):,.0f}</span>',
        ]
        rows_html += "<tr>" + "".join(
            f'<td style="{td_first if i == 0 else td_style}">{v}</td>'
            for i, v in enumerate(cells)
        ) + "</tr>"

    return (
        f'<div style="margin-top:18px;background:white;border:1px solid #e4eaf4;'
        f'border-radius:10px;padding:6px 10px;'
        f'box-shadow:0 1px 4px rgba(13,27,66,0.04);">'
        f'<div style="font-size:0.62rem;font-weight:800;color:#1565c0;'
        f'text-transform:uppercase;letter-spacing:0.09em;'
        f'padding:7px 4px 5px;">Detalle por etapa</div>'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead>{head_html}</thead><tbody>{rows_html}</tbody></table>'
        f'</div>'
    )


def _clean_var_label(raw: str) -> str:
    """Quita iconos y deltas del label de tornado: '💲 Precio venta (±20%)' → 'Precio venta'."""
    s = raw
    if "(" in s:
        s = s.split("(")[0]
    parts = s.strip().split()
    if parts and not parts[0][:1].isalpha():
        parts = parts[1:]
    return " ".join(parts).strip()


def _risk_summary_html(active_keys: list[str], sens: dict,
                        risk_by_key: dict) -> str:
    """Bloque de riesgo: variable más sensible + robustez sistema + alertas."""
    if not active_keys:
        return ""

    # Variable más sensible: la de mayor swing entre todas las etapas activas
    top_var, top_swing, top_stage = "—", 0.0, None
    for k in active_keys:
        rows, _ = ps._tornado_data(sens[k], "margen_cab")
        if not rows:
            continue
        biggest = max(rows, key=lambda r: r["swing"])
        if biggest["swing"] > top_swing:
            top_swing = biggest["swing"]
            top_var = _clean_var_label(biggest["var_label"])
            top_stage = k

    if top_stage is None:
        crit_html = "—"
    else:
        meta = _STAGE_META[top_stage]
        crit_html = (
            f'<b>{top_var}</b> en '
            f'<span style="color:{meta["color"]};font-weight:800;">'
            f'{meta["icon"]} {meta["title"]}</span> · '
            f'swing USD {top_swing:,.0f}/cab'
        )

    # Robustez del sistema = promedio entre etapas activas
    rob_vals = [risk_by_key[k]["robustness"] for k in active_keys
                if k in risk_by_key]
    rob_sys = sum(rob_vals) / len(rob_vals) if rob_vals else 0.0
    rob_col = _robust_color(rob_sys)

    # Alertas: tomamos las primeras 2 alertas relevantes (warning/critical)
    rows_rr = ps._build_risk_return(sens)
    alerts = ps._generate_alerts(rows_rr, sens) if rows_rr else []
    relevant = [a for a in alerts if a.get("level") in ("critical", "warning")][:2]
    if not relevant:
        alerts_html = (
            '<div style="font-size:0.74rem;color:#0c1a2e;line-height:1.4;">'
            'Sin alertas relevantes.</div>'
        )
    else:
        alerts_html = "".join(
            f'<div style="font-size:0.74rem;color:#0c1a2e;line-height:1.4;'
            f'margin-bottom:4px;">'
            f'<span style="font-weight:700;">{a["icon"]}</span> {a["msg"]}</div>'
            for a in relevant
        )

    return (
        f'<div style="display:grid;grid-template-columns:1.1fr 0.9fr;'
        f'gap:10px;margin-top:14px;">'
        # Card 1: Variable + Robustez
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-top:3px solid #7c3aed;border-radius:10px;'
        f'padding:13px 14px;box-shadow:0 1px 4px rgba(13,27,66,0.05);">'
        f'<div style="font-size:0.62rem;font-weight:800;color:#7c3aed;'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">'
        f'🌪 Riesgo y robustez</div>'
        f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.07em;">Variable más sensible</div>'
        f'<div style="font-size:0.82rem;color:#0c1a2e;line-height:1.35;'
        f'margin:2px 0 10px;">{crit_html}</div>'
        f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.07em;">Robustez del sistema</div>'
        f'<div style="font-size:1.20rem;font-weight:800;color:{rob_col};'
        f'line-height:1.1;font-variant-numeric:tabular-nums;'
        f'margin-top:2px;">{rob_sys:.0f}/100</div>'
        f'</div>'
        # Card 2: Alertas
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-top:3px solid #d97706;border-radius:10px;'
        f'padding:13px 14px;box-shadow:0 1px 4px rgba(13,27,66,0.05);">'
        f'<div style="font-size:0.62rem;font-weight:800;color:#d97706;'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">'
        f'⚠ Alertas relevantes</div>'
        f'{alerts_html}'
        f'</div>'
        f'</div>'
    )


# ── 6. A4 page (contenedor centrado, blanco, sombra suave) ──────────────────

def _render_a4_page() -> None:
    """Compone el A4: header → título → hero margen → contexto → cards por
    etapa activa → tabla detalle → bloque de riesgo."""
    active_keys = S.active_stages()
    n_terneros  = int(st.session_state.get(K.ANIMAL_CANTIDAD,
                                            DEFAULTS["n_terneros"]))

    marg   = pm._build_margenes()
    costos = cp._build_costos()
    sens   = ps._build_sensibilidad()
    risk_rows = ps._build_risk_return(sens) if active_keys else []
    risk_by_key = {r["key"]: r for r in risk_rows}

    # Margen total y días sólo de etapas activas
    margen_total = sum(marg[k]["margen_bruto_total"] for k in active_keys)
    dias_total   = sum(marg[k]["dias"]                for k in active_keys)

    if active_keys:
        body = (
            f'{_hero_margen_html(margen_total, active_keys, n_terneros, dias_total)}'
            f'{_simulation_context_html(active_keys, n_terneros)}'
            f'{_stage_cards_html(active_keys, marg, risk_by_key)}'
            f'{_stage_detail_html(active_keys, marg, costos)}'
            f'{_risk_summary_html(active_keys, sens, risk_by_key)}'
        )
    else:
        body = (
            '<div style="margin-top:24px;padding:24px;text-align:center;'
            'background:#fef3c7;border:1px solid #fde68a;border-radius:10px;'
            'color:#92400e;font-weight:600;">'
            'No hay etapas activas. Activá al menos una etapa en Parámetros '
            'para generar el reporte.</div>'
        )

    st.markdown(
        f'<div style="max-width:880px;margin:0 auto;background:white;'
        f'border:1px solid #e4eaf4;border-radius:14px;'
        f'box-shadow:0 4px 24px rgba(13,27,66,0.08);'
        f'padding:36px 44px 44px;min-height:600px;'
        f'font-family:Inter,Arial,sans-serif;">'
        f'{_header_html()}'
        f'{_title_html()}'
        f'{body}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Entry point ─────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Reportes",
        "One Pager ejecutivo — estructura visual inicial del reporte "
        "estratégico (sin generación de PDF todavía).",
    )

    _ensure_state()
    _render_editor()
    _render_a4_page()
