"""
Reportes — One Pager ejecutivo (estructura visual inicial).

Esta página construye el shell visual de un reporte ejecutivo estilo A4
dentro del dashboard. Por ahora expone:
  - inputs editables (empresa, responsable, fecha) persistidos en session_state,
  - checkbox para incluir/ocultar el logo,
  - header ejecutivo (logo izquierda · datos derecha),
  - título + subtítulo del reporte,
  - placeholder del cuerpo del reporte.

NO genera PDF ni habilita descargas (etapa posterior).
"""
from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING

import streamlit as st

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.pages.ui import page_header
from modules.pages import page_modelo_productivo as mp
from modules.pages import page_costos as cp
from modules.pages import page_ingresos as ip
from modules.pages import page_margenes as pm
from modules.pages import page_sensibilidad as ps

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


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


# ── 5. Resumen ejecutivo (estrategia recomendada + 5 KPIs) ──────────────────

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


def _kpi_card_html(icon: str, label: str, value: str,
                    value_color: str = "#0c1a2e",
                    subtext: str = "") -> str:
    sub_html = (
        f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-top:3px;'
        f'line-height:1;">{subtext}</div>'
        if subtext else ''
    )
    return (
        f'<div style="flex:1;background:white;border:1px solid #e4eaf4;'
        f'border-radius:10px;padding:13px 12px;text-align:center;'
        f'box-shadow:0 1px 4px rgba(13,27,66,0.05);min-width:0;">'
        f'<div style="font-size:1.05rem;line-height:1;margin-bottom:4px;">'
        f'{icon}</div>'
        f'<div style="font-size:0.56rem;color:#7a8fa6;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;'
        f'margin-bottom:5px;line-height:1.1;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{label}</div>'
        f'<div style="font-size:1.02rem;font-weight:800;color:{value_color};'
        f'line-height:1.1;font-variant-numeric:tabular-nums;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def _executive_summary_html() -> str:
    """Resumen ejecutivo del sistema productivo integrado.

    Agrega margen, USD/cab/día, riesgo y robustez a nivel sistema
    promediando entre las etapas (cría · recría · engorde) y muestra
    el margen total como headline del hero."""
    marg = pm._build_margenes()
    sens = ps._build_sensibilidad()
    risk_rows = ps._build_risk_return(sens)
    risk_by_key = {r["key"]: r for r in risk_rows}

    margen_total = sum(marg[k]["margen_bruto_total"] for k in _STAGES_KEYS)
    n = len(_STAGES_KEYS)
    usd_cab_dia_avg = sum(marg[k]["usd_cab_dia"] for k in _STAGES_KEYS) / n
    riesgo_avg = sum(risk_by_key[k]["risk_composite"]
                     for k in _STAGES_KEYS) / n
    robustez_avg = sum(risk_by_key[k]["robustness"]
                       for k in _STAGES_KEYS) / n

    color = "#1565c0"
    margen_color = "#16a34a" if margen_total >= 0 else "#dc2626"
    margen_sign = "+" if margen_total >= 0 else "−"

    title_html = (
        '<span style="color:#16a34a;">🌱 Cría</span>'
        ' <span style="color:#94a3b8;font-weight:600;font-size:0.85em;">+</span> '
        '<span style="color:#1565c0;">🔵 Recría</span>'
        ' <span style="color:#94a3b8;font-weight:600;font-size:0.85em;">+</span> '
        '<span style="color:#0d9488;">🟢 Engorde</span>'
    )

    hero = (
        f'<div style="background:linear-gradient(135deg,{color}1a,{color}05);'
        f'border:2px solid {color}55;border-radius:12px;'
        f'padding:18px 22px;margin-top:18px;'
        f'display:flex;align-items:center;justify-content:space-between;'
        f'gap:16px;flex-wrap:wrap;">'
        f'<div style="min-width:0;">'
        f'<div style="font-size:0.62rem;color:{color};font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:5px;">'
        f'Sistema productivo integrado</div>'
        f'<div style="font-size:1.40rem;font-weight:800;color:#0c1a2e;'
        f'line-height:1.15;letter-spacing:-0.01em;">{title_html}</div>'
        f'</div>'
        f'<div style="text-align:right;flex-shrink:0;">'
        f'<div style="font-size:0.60rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;">Margen total</div>'
        f'<div style="font-size:1.85rem;font-weight:800;color:{margen_color};'
        f'line-height:1;letter-spacing:-0.02em;">'
        f'{margen_sign}USD {abs(margen_total):,.0f}</div>'
        f'</div></div>'
    )

    cards = (
        _kpi_card_html(
            "💵", "Margen sistema",
            f"{margen_sign}USD {abs(margen_total):,.0f}",
            margen_color, "USD totales",
        )
        + _kpi_card_html(
            "⚡", "USD / cab / día",
            f"USD {usd_cab_dia_avg:.2f}",
            subtext="promedio etapas",
        )
        + _kpi_card_html(
            "⚠", "Riesgo",
            f"{riesgo_avg:.0f}/100",
            _risk_color(riesgo_avg),
            subtext="promedio etapas",
        )
        + _kpi_card_html(
            "🛡", "Robustez",
            f"{robustez_avg:.0f}/100",
            _robust_color(robustez_avg),
            subtext="promedio etapas",
        )
    )

    cards_block = (
        f'<div style="display:flex;gap:8px;margin-top:14px;'
        f'flex-wrap:nowrap;">{cards}</div>'
    )

    return hero + cards_block


# ── Helpers SVG (gráficos inline dentro del A4) ─────────────────────────────

def _svg_sparkline(xs: list[float], ys: list[float],
                    width: int = 240, height: int = 56,
                    color: str = "#1565c0",
                    show_dots: bool = True) -> str:
    """Genera una sparkline SVG con relleno suave bajo la línea."""
    if not xs or not ys or len(xs) != len(ys):
        return ""
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_max == x_min: x_max = x_min + 1
    if y_max == y_min: y_max = y_min + 1
    pad = 5

    def sx(x: float) -> float:
        return pad + (x - x_min) / (x_max - x_min) * (width - 2 * pad)

    def sy(y: float) -> float:
        return height - pad - (y - y_min) / (y_max - y_min) * (height - 2 * pad)

    pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
    area_pts = (
        pts +
        f" {sx(xs[-1]):.1f},{height - pad:.1f}"
        f" {sx(xs[0]):.1f},{height - pad:.1f}"
    )
    dots = ""
    if show_dots:
        for x, y in zip(xs, ys):
            dots += (
                f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.5" '
                f'fill="white" stroke="{color}" stroke-width="1.5" />'
            )
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{area_pts}" fill="{color}" fill-opacity="0.16" />'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
        f'{dots}'
        f'</svg>'
    )


def _hbars_html(items: list[tuple[str, float]],
                color: str = "#fb7185",
                top_n: int = 4) -> str:
    """Mini barras horizontales: lista (label, valor)."""
    if not items:
        return ""
    items_sorted = sorted(items, key=lambda x: -x[1])[:top_n]
    max_val = max(v for _, v in items_sorted) or 1.0
    rows = ""
    for label, val in items_sorted:
        pct = max(0.0, val / max_val * 100)
        rows += (
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'margin-bottom:4px;font-size:0.66rem;line-height:1;">'
            f'<span style="flex:0 0 78px;color:#475569;font-weight:600;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f'{label}</span>'
            f'<div style="flex:1;background:#eef2f7;height:6px;'
            f'border-radius:3px;overflow:hidden;">'
            f'<div style="background:{color};height:100%;'
            f'width:{pct:.1f}%;border-radius:3px;"></div></div>'
            f'<span style="flex:0 0 58px;color:#0c1a2e;font-weight:700;'
            f'text-align:right;font-variant-numeric:tabular-nums;">'
            f'{val:,.0f}</span></div>'
        )
    return rows


def _mini_block_html(accent_color: str, icon: str, title: str,
                      bullets: list[str], chart_html: str) -> str:
    """Card compacta: header de color + bullets + mini chart."""
    bullets_html = "".join(
        f'<li style="font-size:0.74rem;color:#0c1a2e;'
        f'margin-bottom:4px;line-height:1.35;list-style:none;'
        f'padding-left:11px;position:relative;">'
        f'<span style="position:absolute;left:0;top:0;color:{accent_color};'
        f'font-weight:800;font-size:0.85rem;line-height:1.1;">•</span>'
        f'{b}</li>'
        for b in bullets
    )
    return (
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-top:3px solid {accent_color};border-radius:10px;'
        f'padding:13px 14px;box-shadow:0 1px 4px rgba(13,27,66,0.05);'
        f'display:flex;flex-direction:column;height:100%;">'
        f'<div style="font-size:0.62rem;font-weight:800;color:{accent_color};'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:5px;">{icon} {title}</div>'
        f'<ul style="padding:0;margin:0 0 8px 0;">{bullets_html}</ul>'
        f'<div style="margin-top:auto;">{chart_html}</div>'
        f'</div>'
    )


# ── Mini-bloque: Modelo Productivo ──────────────────────────────────────────

def _modelo_productivo_mini_html() -> str:
    ms = mp._read_stages()
    t_a = ms["cria"]["dias"]
    t_b = t_a + ms["recria"]["dias"]
    t_c = t_b + ms["eng_int"]["dias"]

    kg_birth = ms["cria"]["kg_in"]
    kg_final = ms["eng_int"]["kg_out"]

    dias_totales = t_c
    gdp_avg = ((kg_final - kg_birth) / dias_totales
               if dias_totales > 0 else 0.0)

    bullets = [
        f"<b>{dias_totales}</b> días totales del ciclo",
        f"<b>{kg_final:.0f} kg</b> peso final",
        f"GDP promedio <b>{gdp_avg:.3f} kg/día</b>",
    ]

    xs = [0, t_a, t_b, t_c]
    ys = [
        kg_birth,
        ms["cria"]["kg_out"],
        ms["recria"]["kg_out"],
        ms["eng_int"]["kg_out"],
    ]
    chart = _svg_sparkline(xs, ys, color="#1565c0")
    return _mini_block_html("#1565c0", "🐂", "Modelo productivo",
                             bullets, chart)


# ── Mini-bloque: Costos ─────────────────────────────────────────────────────

_CONCEPT_LABELS = {
    "compra":    "Compra",
    "alim":      "Alimentación",
    "sanidad":   "Sanidad",
    "mortandad": "Mortandad",
    "mo":        "Operación",
    "com":       "Comercial.",
}


def _costos_mini_html() -> str:
    co = cp._build_costos()
    concepts = list(_CONCEPT_LABELS.keys())

    # Sumas por concepto a nivel sistema (todos los stages × cabezas)
    totals = {c: sum(co[k][c] * co[k]["cabezas"]
                     for k in ("cria", "recria", "eng_int"))
              for c in concepts}
    total_sum = sum(totals.values())

    sum_total = sum(co[k]["total_usd"]
                    for k in ("cria", "recria", "eng_int"))
    sum_cab = sum(co[k]["cabezas"]
                  for k in ("cria", "recria", "eng_int"))
    costo_cab_avg = sum_total / sum_cab if sum_cab > 0 else 0.0

    if total_sum > 0:
        top_driver = max(totals, key=totals.get)
        top_pct = totals[top_driver] / total_sum * 100
        driver_text = (f"Driver principal: "
                       f"<b>{_CONCEPT_LABELS[top_driver]} "
                       f"({top_pct:.0f}%)</b>")
    else:
        driver_text = "Driver principal: <b>—</b>"

    bullets = [
        f"USD <b>{costo_cab_avg:,.0f}/cab</b> (promedio sistema)",
        driver_text,
        f"USD <b>{sum_total:,.0f}</b> costo total del sistema",
    ]

    items = [(_CONCEPT_LABELS[c], totals[c]) for c in concepts]
    chart = _hbars_html(items, color="#fb7185", top_n=4)
    return _mini_block_html("#dc2626", "💸", "Costos", bullets, chart)


# ── Mini-bloque: Ingresos ───────────────────────────────────────────────────

def _ingresos_mini_html() -> str:
    ing = ip._build_ingresos()
    pc = float(st.session_state.get(K.COMERCIAL_PRECIO_COMPRA,
                                     DEFAULTS["precio_compra"]))

    sum_total = sum(ing[k]["ingreso_total"]
                    for k in ("cria", "recria", "eng_int"))
    sum_cab_vend = sum(ing[k]["cab_vend"]
                       for k in ("cria", "recria", "eng_int"))
    avg_ing_cab = (sum_total / sum_cab_vend
                   if sum_cab_vend > 0 else 0.0)

    bullets = [
        f"USD <b>{avg_ing_cab:,.0f}/cab</b> (ingreso promedio)",
        f"USD <b>{sum_total:,.0f}</b> ingreso total del sistema",
    ]

    # Curva de valor del animal a lo largo del ciclo
    t_a = ing["cria"]["dias"]
    t_b = t_a + ing["recria"]["dias"]
    t_c = t_b + ing["eng_int"]["dias"]
    xs = [0, t_a, t_b, t_c]
    ys = [
        ing["cria"]["kg_in"]   * pc,
        ing["cria"]["kg_out"]  * ing["cria"]["precio_venta"],
        ing["recria"]["kg_out"] * ing["recria"]["precio_venta"],
        ing["eng_int"]["kg_out"] * ing["eng_int"]["precio_venta"],
    ]
    chart = _svg_sparkline(xs, ys, color="#16a34a")
    return _mini_block_html("#16a34a", "💵", "Ingresos", bullets, chart)


# ── Tres columnas: mini resúmenes ───────────────────────────────────────────

def _three_minis_html() -> str:
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;'
        'gap:12px;margin-top:18px;">'
        f'{_modelo_productivo_mini_html()}'
        f'{_costos_mini_html()}'
        f'{_ingresos_mini_html()}'
        '</div>'
    )


# ── Helper: hbars con valores firmados (positivos verde / negativos rojo) ───

def _hbars_signed_html(items: list[tuple[str, float]],
                        pos_color: str = "#16a34a",
                        neg_color: str = "#dc2626",
                        top_n: int = 4) -> str:
    """Mini barras horizontales firmadas (margen/cab por etapa)."""
    if not items:
        return ""
    items_sorted = sorted(items, key=lambda x: -x[1])[:top_n]
    max_abs = max(abs(v) for _, v in items_sorted) or 1.0
    rows = ""
    for label, val in items_sorted:
        pct = max(0.0, abs(val) / max_abs * 100)
        col = pos_color if val >= 0 else neg_color
        sign = "+" if val >= 0 else "−"
        rows += (
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'margin-bottom:4px;font-size:0.66rem;line-height:1;">'
            f'<span style="flex:0 0 78px;color:#475569;font-weight:600;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f'{label}</span>'
            f'<div style="flex:1;background:#eef2f7;height:6px;'
            f'border-radius:3px;overflow:hidden;">'
            f'<div style="background:{col};height:100%;'
            f'width:{pct:.1f}%;border-radius:3px;"></div></div>'
            f'<span style="flex:0 0 64px;color:{col};font-weight:700;'
            f'text-align:right;font-variant-numeric:tabular-nums;">'
            f'{sign}{abs(val):,.0f}</span></div>'
        )
    return rows


# ── Helper: limpia el var_label del tornado ("💲  Precio venta  (±20%)") ────

def _clean_tornado_label(raw: str) -> str:
    """Devuelve sólo el nombre limpio de la variable (sin icon ni delta)."""
    s = raw
    if "(" in s:
        s = s.split("(")[0]
    parts = s.strip().split()
    # descartar primer token si es un icono (no alfanumérico mayoritariamente)
    if parts and not parts[0][:1].isalpha():
        parts = parts[1:]
    return " ".join(parts).strip()


# ── Mini-bloque: Margen Bruto ───────────────────────────────────────────────

_STAGE_SHORT = {
    "cria":    "Cría",
    "recria":  "Recría",
    "eng_int": "Engorde",
}

_STAGES_KEYS = ["cria", "recria", "eng_int"]


def _margen_bruto_mini_html() -> str:
    marg = pm._build_margenes()

    # Top etapa por margen/cab
    top_key = max(_STAGES_KEYS, key=lambda k: marg[k]["margen_bruto_cab"])
    top_marg_cab = marg[top_key]["margen_bruto_cab"]
    top_marg_kg = marg[top_key]["margen_kg"]

    sum_total_margen = sum(marg[k]["margen_bruto_total"]
                            for k in _STAGES_KEYS)

    sign_cab = "+" if top_marg_cab >= 0 else "−"
    sign_kg = "+" if top_marg_kg >= 0 else "−"
    sign_tot = "+" if sum_total_margen >= 0 else "−"

    bullets = [
        f"Top: <b>{_STAGE_SHORT[top_key]}</b> con "
        f"USD <b>{sign_cab}{abs(top_marg_cab):,.0f}/cab</b>",
        f"Margen unitario: <b>{sign_kg}USD {abs(top_marg_kg):.2f}/kg</b>",
        f"Margen total sistema: USD <b>{sign_tot}{abs(sum_total_margen):,.0f}</b>",
    ]

    items = [(_STAGE_SHORT[k], marg[k]["margen_bruto_cab"])
             for k in _STAGES_KEYS]
    chart = _hbars_signed_html(items, pos_color="#d97706",
                                neg_color="#dc2626", top_n=4)

    return _mini_block_html("#d97706", "📊", "Margen bruto",
                             bullets, chart)


# ── Mini-bloque: Sensibilidad y Riesgo ──────────────────────────────────────

def _sensibilidad_mini_html() -> str:
    """Mini bloque: variable crítica + precio equilibrio + robustez/riesgo
    para la etapa con mayor margen bruto/cab."""
    marg = pm._build_margenes()
    sens = ps._build_sensibilidad()
    risk_rows = ps._build_risk_return(sens)
    risk_by_key = {r["key"]: r for r in risk_rows}

    top_key = max(_STAGES_KEYS, key=lambda k: marg[k]["margen_bruto_cab"])
    s_top = sens[top_key]

    rows, _baseline = ps._tornado_data(s_top, "margen_cab")
    if rows:
        biggest = max(rows, key=lambda r: r["swing"])
        crit_var = _clean_tornado_label(biggest["var_label"])
        crit_swing = biggest["swing"]
    else:
        crit_var = "—"
        crit_swing = 0.0

    pe = s_top.get("precio_equilibrio", float("nan"))
    pv = s_top.get("pv", 0.0)
    if pe == pe and pv > 0:
        headroom_pct = (pv - pe) / pv * 100.0
        pe_text = (f"Precio equilibrio: <b>USD {pe:.2f}/kg</b> "
                   f"(margen +{headroom_pct:.0f}%)")
    else:
        pe_text = "Precio equilibrio: <b>N/A</b>"

    robustez_top = risk_by_key[top_key]["robustness"]
    riesgo_top = risk_by_key[top_key]["risk_composite"]

    bullets = [
        f"Variable crítica en <b>{_STAGE_SHORT[top_key]}</b>: "
        f"<b>{crit_var}</b> (swing USD {crit_swing:,.0f}/cab)",
        pe_text,
        f"Robustez <b>{robustez_top:.0f}/100</b> · "
        f"Riesgo <b>{riesgo_top:.0f}/100</b>",
    ]

    top_rows = sorted(rows, key=lambda r: -r["swing"])[:4]
    items = [(_clean_tornado_label(r["var_label"]), r["swing"])
             for r in top_rows]
    chart = _hbars_html(items, color="#7c3aed", top_n=4)

    return _mini_block_html("#7c3aed", "🌪", "Sensibilidad y riesgo",
                             bullets, chart)


# ── Dos columnas: segunda fila de mini resúmenes ────────────────────────────

def _three_minis_html_2() -> str:
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr;'
        'gap:12px;margin-top:12px;">'
        f'{_margen_bruto_mini_html()}'
        f'{_sensibilidad_mini_html()}'
        '</div>'
    )


# ── 6. A4 page (contenedor centrado, blanco, sombra suave) ──────────────────

def _render_a4_page() -> None:
    st.markdown(
        f'<div style="max-width:880px;margin:0 auto;background:white;'
        f'border:1px solid #e4eaf4;border-radius:14px;'
        f'box-shadow:0 4px 24px rgba(13,27,66,0.08);'
        f'padding:36px 44px 44px;min-height:600px;'
        f'font-family:Inter,Arial,sans-serif;">'
        f'{_header_html()}'
        f'{_title_html()}'
        f'{_executive_summary_html()}'
        f'{_three_minis_html()}'
        f'{_three_minis_html_2()}'
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
