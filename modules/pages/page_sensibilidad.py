"""
Sensibilidad y Riesgo — Visualización de robustez y fragilidad económica
del negocio ganadero por las 4 etapas productivas.

Foco: límites tolerables (puntos de equilibrio) de precios, productividad
y mortalidad antes de que el margen bruto se haga 0. Indicadores
semáforo (verde/amarillo/rojo) para lectura inmediata de la robustez.

Lee parámetros directamente desde session_state. Usa las mismas fórmulas
internas que page_costos.py / page_margenes.py para mantener consistencia.
Mantiene la firma render(params, comp) por compatibilidad con el router
de app.py.
"""
from __future__ import annotations
from math import isnan
from typing import TYPE_CHECKING

import streamlit as st
import plotly.graph_objects as go

import modules.state.keys as K
import modules.state.stages as S
import modules.state.derived as D
from modules.state.defaults import DEFAULTS
from modules.state.persist import read
from modules.pages.ui import page_header, section

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Etapas y paletas ─────────────────────────────────────────────────────────

_SEG = {
    "cria":    {"title": "Cría",    "icon": "🌱",
                "color": "#16a34a", "bg": "#f0fdf4", "border": "#bbf7d0"},
    "recria":  {"title": "Recría",  "icon": "🔵",
                "color": "#1565c0", "bg": "#eff6ff", "border": "#bfdbfe"},
    "eng_int": {"title": "Engorde", "icon": "🟢",
                "color": "#0d9488", "bg": "#f0fdfa", "border": "#99f6e4"},
}

_SEMAPHORE = {
    "verde":    {"color": "#16a34a", "bg": "#f0fdf4", "label": "Robusto",  "icon": "🟢"},
    "amarillo": {"color": "#d97706", "bg": "#fffbeb", "label": "Sensible", "icon": "🟡"},
    "rojo":     {"color": "#dc2626", "bg": "#fef2f2", "label": "Crítico",  "icon": "🔴"},
    "neutro":   {"color": "#64748b", "bg": "#f1f5f9", "label": "N/A",      "icon": "⚪"},
}

_SEVERITY = {"verde": 0, "amarillo": 1, "rojo": 2, "neutro": -1}


def _g(key: str, default: float) -> float:
    """Lectura robusta: shadow > widget-key > default."""
    return float(read(key, default))


def _is_nan(x) -> bool:
    try:
        return isnan(x)
    except (TypeError, ValueError):
        return False


# ── Lectura de alimentación (todo derivado en modules.state.derived) ─────────

def _alim_breakdown(stage: str) -> tuple[float, float, float]:
    """Devuelve (alim_usd_cab, kg_ms_total_cab, precio_usd_kg_ms) para una etapa.

    Modelo nutricional puro: los tres valores vienen de la tabla de ración:
        alim_usd_cab     = Σ (Kg TC × %MS/100 × USD/kg MS) × días
        kg_ms_total_cab  = Σ (Kg TC × %MS/100) × días
        precio_usd_kg_ms = alim_usd_cab / kg_ms_total_cab   (= D.precio_ponderado)
    """
    return (
        D.costo_alim_cab(stage),
        D.consumo_ms_cab(stage),
        D.precio_ponderado(stage),
    )


# ── Lectura de parámetros base ───────────────────────────────────────────────

def _stage_inputs() -> dict:
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

    a_kg_in   = S.kg_in_for("cria")
    a_kg_out  = S.kg_out_for("cria")
    a_dias    = D.dias_for("cria")
    a_mort    = _g(K.A_MORTALIDAD,        DEFAULTS["d_mortalidad"])
    a_san     = _g(K.A_SANIDAD,           DEFAULTS["d_sanidad"])
    a_mo_mes  = _g(K.A_MO_MES,            DEFAULTS["d_mo_mes"])
    a_ca      = D.ca_for("cria")
    a_com_pct = _g(K.A_COMISION_PCT,      DEFAULTS["a_comision_pct"])
    a_pv      = _g(K.A_PRECIO_VENTA,      DEFAULTS["d_precio_venta"])
    a_fe      = _g(K.A_FLETE_ENTRADA,     DEFAULTS["a_fe"])
    a_fs      = _g(K.A_FLETE_SALIDA,      DEFAULTS["d_flete"])
    a_combust = _g(K.A_COMBUSTIBLE,       DEFAULTS["a_combustible"])
    a_servic  = _g(K.A_SERVICIOS,         DEFAULTS["a_servicios"])
    a_asig    = _g(K.A_ASIG_PCT,          DEFAULTS["a_asig_pct"])
    a_amanos  = _g(K.A_AMORT_ANOS,        DEFAULTS["a_amort_anos"])
    a_mant    = _g(K.A_MANTENIMIENTO,     DEFAULTS["a_mantenimiento"])

    b_kg_in   = S.kg_in_for("recria")
    b_kg_out  = S.kg_out_for("recria")
    b_dias    = D.dias_for("recria")
    b_mort    = _g(K.B_MORTALIDAD,        DEFAULTS["r_mortalidad"])
    b_san     = _g(K.B_SANIDAD,           DEFAULTS["r_sanidad"])
    b_mo_mes  = _g(K.B_MO_MES,            DEFAULTS["r_mo_mes"])
    b_ca      = D.ca_for("recria")
    b_com_pct = _g(K.B_COMISION_PCT,      DEFAULTS["b_comision_pct"])
    b_pc      = _g(K.B_PRECIO_COMPRA,     DEFAULTS["b_pc"])
    b_pv      = _g(K.B_PRECIO_VENTA,      DEFAULTS["r_precio_venta"])
    b_fe      = _g(K.B_FLETE_ENTRADA,     DEFAULTS["r_flete_entrada"])
    b_fs      = _g(K.B_FLETE_SALIDA,      DEFAULTS["r_flete_salida"])
    b_combust = _g(K.B_COMBUSTIBLE,       DEFAULTS["b_combustible"])
    b_servic  = _g(K.B_SERVICIOS,         DEFAULTS["b_servicios"])
    b_asig    = _g(K.B_ASIG_PCT,          DEFAULTS["b_asig_pct"])
    b_amanos  = _g(K.B_AMORT_ANOS,        DEFAULTS["b_amort_anos"])
    b_mant    = _g(K.B_MANTENIMIENTO,     DEFAULTS["b_mantenimiento"])

    c_kg_in   = S.kg_in_for("eng_int")
    c_kg_out  = S.kg_out_for("eng_int")
    c_dias    = D.dias_for("eng_int")
    c_mort    = _g(K.C_MORTALIDAD,        DEFAULTS["t_mortalidad"])
    c_san     = _g(K.C_SANIDAD,           DEFAULTS["t_sanidad"])
    c_mo_mes  = _g(K.C_MO_MES,            DEFAULTS["t_mo_mes"])
    c_ca      = D.ca_for("eng_int")
    c_com_pct = _g(K.C_COMISION_PCT,      DEFAULTS["c_comision_pct"])
    c_pc      = _g(K.C_PRECIO_COMPRA,     DEFAULTS["c_pc"])
    c_pv      = _g(K.C_PRECIO_VENTA,      DEFAULTS["t_precio_venta"])
    c_fe      = _g(K.C_FLETE_ENTRADA,     DEFAULTS["t_flete_entrada"])
    c_fs      = _g(K.C_FLETE_SALIDA,      DEFAULTS["t_flete_salida"])
    c_combust = _g(K.C_COMBUSTIBLE,       DEFAULTS["c_combustible"])
    c_servic  = _g(K.C_SERVICIOS,         DEFAULTS["c_servicios"])
    c_asig    = _g(K.C_ASIG_PCT,          DEFAULTS["c_asig_pct"])
    c_amanos  = _g(K.C_AMORT_ANOS,        DEFAULTS["c_amort_anos"])
    c_mant    = _g(K.C_MANTENIMIENTO,     DEFAULTS["c_mantenimiento"])

    # Valor infra TOTAL (global)
    valor_total = _g(K.INFRA_VALOR_TOTAL, DEFAULTS["infra_valor_total"])

    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    # Cabezas en cascada — sólo entre etapas activas consecutivas
    active_list = S.active_stages()
    morts_map = {"cria": a_mort, "recria": b_mort, "eng_int": c_mort}
    cab_in_map: dict[str, int] = {"cria": 0, "recria": 0, "eng_int": 0}
    if active_list:
        cab_in_map[active_list[0]] = n_t
        for i in range(1, len(active_list)):
            prev_s = active_list[i - 1]
            cab_in_map[active_list[i]] = surv(cab_in_map[prev_s],
                                              morts_map[prev_s])
    cab_in_cria    = cab_in_map["cria"]
    cab_in_recria  = cab_in_map["recria"]
    cab_in_eng_int = cab_in_map["eng_int"]

    def gdp(kg_in: float, kg_out: float, dias: int) -> float:
        return (kg_out - kg_in) / dias if dias > 0 else 0.0

    def estructura_cab(asig_pct: float, amort_anos: float, mant_anio: float,
                       dias: int, cab_in: int) -> float:
        adjudicado = valor_total * max(asig_pct, 0.0) / 100.0
        amort_anual = (adjudicado / amort_anos) if amort_anos > 0 else 0.0
        estructura_anual = amort_anual + max(mant_anio, 0.0)
        if cab_in > 0:
            return estructura_anual * dias / 365.0 / cab_in
        return 0.0

    # mo_dia (USD/cab/día) se deriva de los inputs USD/mes:
    #     mo_dia = (mo_mes + comb_mes + serv_mes) / 30 / cabezas
    # Así, mo_cab del ciclo = mo_dia × días sigue siendo válido en el resto
    # del cálculo (líneas que multiplican por dias para obtener USD/cab).
    def op_per_cab_dia(mo_mes: float, comb_mes: float, serv_mes: float,
                       cab_in: int) -> float:
        if cab_in <= 0:
            return 0.0
        return (mo_mes + comb_mes + serv_mes) / 30.0 / cab_in

    return {
        "cria": dict(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            ca=a_ca, stage="cria",
            compra=pc_global * a_kg_in, san=a_san,
            mo_dia=op_per_cab_dia(a_mo_mes, a_combust, a_servic, cab_in_cria),
            estructura_cab=estructura_cab(a_asig, a_amanos, a_mant,
                                          a_dias, cab_in_cria),
            com_pct=a_com_pct, pv=a_pv, fe=a_fe, fs=a_fs,
            cab_in=cab_in_cria, gdp_actual=gdp(a_kg_in, a_kg_out, a_dias),
        ),
        "recria": dict(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            ca=b_ca, stage="recria",
            compra=b_pc * b_kg_in, san=b_san,
            mo_dia=op_per_cab_dia(b_mo_mes, b_combust, b_servic, cab_in_recria),
            estructura_cab=estructura_cab(b_asig, b_amanos, b_mant,
                                          b_dias, cab_in_recria),
            com_pct=b_com_pct, pv=b_pv, fe=b_fe, fs=b_fs,
            cab_in=cab_in_recria, gdp_actual=gdp(b_kg_in, b_kg_out, b_dias),
        ),
        "eng_int": dict(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            ca=c_ca, stage="eng_int",
            compra=c_pc * c_kg_in, san=c_san,
            mo_dia=op_per_cab_dia(c_mo_mes, c_combust, c_servic, cab_in_eng_int),
            estructura_cab=estructura_cab(c_asig, c_amanos, c_mant,
                                          c_dias, cab_in_eng_int),
            com_pct=c_com_pct, pv=c_pv, fe=c_fe, fs=c_fs,
            cab_in=cab_in_eng_int, gdp_actual=gdp(c_kg_in, c_kg_out, c_dias),
        ),
    }


# ── Cálculo de puntos de equilibrio ──────────────────────────────────────────

def _compute_breakeven(s: dict) -> dict:
    """
    Para una etapa, calcula los puntos de equilibrio (margen=0) para:
        precio_equilibrio  USD/kg vendido
        precio_alim_max    USD/kg MS  (escala uniforme de la ración)
        gdp_min            kg/día      (asumiendo días fijos)
        ca_max             kg MS/kg PV
        mort_max_pct       %

    Modelo económico (alineado con page_costos / page_margenes):
        ingreso_cab   = kg_out × pv
        com_cab       = (com_pct/100) × pv × kg_out + fe + fs
        capital       = compra + alim + san + op + estr + com
        costo_fin     = capital × tasa%/100 × días/365
        base          = capital + costo_fin       (sin mortandad)
        ingreso_total = cab_vend × ingreso_cab    (cab_vend = cab_in × (1-m))
        costo_total   = cab_in × base             (incurre sobre todas)
        margen_total  = cab_in × ((1 - m) × ingreso_cab − base)

    La mortandad NO se suma como sobrecosto: ya está implícita en la
    asimetría entre cab_in (incurre el costo) y cab_vend (genera ingreso).
    """
    alim_actual, kg_ms_total, precio_alim_actual = _alim_breakdown(s["stage"])
    op_cab    = s["mo_dia"] * s["dias"]                        # USD/cab
    estr_cab  = s.get("estructura_cab", 0.0)                   # USD/cab
    com_cab   = (s["com_pct"] / 100.0) * s["pv"] * s["kg_out"] + s["fe"] + s["fs"]
    capital   = s["compra"] + alim_actual + s["san"] + op_cab + estr_cab + com_cab
    tasa_pct  = _g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])
    cf_cab    = (capital * (tasa_pct / 100.0) * s["dias"] / 365.0
                 if s["dias"] > 0 else 0.0)
    base      = capital + cf_cab
    mo_cab    = op_cab + estr_cab
    m         = s["mort_pct"] / 100.0
    one_minus_m = 1 - m

    ingreso_cab   = s["kg_out"] * s["pv"]
    costo_cab     = base                                # sin mortandad explícita
    cab_vend      = max(int(s["cab_in"] * one_minus_m), 0)
    ingreso_total = ingreso_cab * cab_vend
    costo_total   = costo_cab * s["cab_in"]
    margen_total  = ingreso_total - costo_total
    margen_cab    = (margen_total / s["cab_in"]
                     if s["cab_in"] > 0 else 0.0)
    kg_vendidos   = cab_vend * s["kg_out"]

    kg_aumento = max(s["kg_out"] - s["kg_in"], 0.0)
    ca_actual = (kg_ms_total / kg_aumento) if kg_aumento > 0 else 0.0

    # ── Precio equilibrio (USD por kg vendido) ──
    if kg_vendidos > 0:
        precio_equilibrio = costo_total / kg_vendidos
    else:
        precio_equilibrio = float("nan")

    # ── Mortandad máxima tolerable: (1−m)×I = base ──
    if ingreso_cab > 0:
        m_max = 1.0 - (base / ingreso_cab)
        mort_max_pct = max(0.0, 100.0 * m_max)
    else:
        mort_max_pct = float("nan")

    # ── Multiplicador α de la componente alim para que margen=0 ──
    # (1−m)×I = base − alim + α×alim
    # α = ((1−m)×I − (base − alim)) / alim
    if alim_actual > 0:
        objetivo = one_minus_m * ingreso_cab
        alpha = (objetivo - (base - alim_actual)) / alim_actual
    else:
        alpha = float("nan")

    if not _is_nan(alpha) and precio_alim_actual > 0:
        precio_alim_max = max(0.0, alpha * precio_alim_actual)
    else:
        precio_alim_max = float("nan")

    if not _is_nan(alpha) and ca_actual > 0:
        ca_max = max(0.0, alpha * ca_actual)
    else:
        ca_max = float("nan")

    # ── GDP mínimo: solve para kg_out_new = kg_in + GDP × dias ──
    # X × pv × ((1−m) − com_share) = K_const
    # K_const usa los costos del baseline + cf_cab (aproximación: el
    # costo financiero no se recalcula al variar kg_out).
    K_const = (s["compra"] + alim_actual + s["san"] + mo_cab
               + s["fe"] + s["fs"] + cf_cab)
    com_share = s["com_pct"] / 100.0
    denom = s["pv"] * (one_minus_m - com_share)
    if denom > 0 and s["dias"] > 0:
        X_min = K_const / denom
        gdp_min = max(0.0, (X_min - s["kg_in"]) / s["dias"])
    else:
        gdp_min = float("nan")

    return {
        "ingreso_cab":        ingreso_cab,
        "costo_cab":          costo_cab,
        "margen_cab":         margen_cab,
        "ingreso_total":      ingreso_total,
        "costo_total":        costo_total,
        "margen_total":       margen_total,
        "kg_vendidos":        kg_vendidos,
        "alim_actual":        alim_actual,
        "kg_ms_total":        kg_ms_total,
        "precio_alim_actual": precio_alim_actual,
        "ca_actual":          ca_actual,
        "precio_equilibrio":  precio_equilibrio,
        "precio_alim_max":    precio_alim_max,
        "gdp_min":            gdp_min,
        "ca_max":             ca_max,
        "mort_max_pct":       mort_max_pct,
    }


def _build_sensibilidad() -> dict:
    inputs = _stage_inputs()
    return {k: {**inputs[k], **_compute_breakeven(inputs[k]),
                "active": S.is_active(k)}
            for k in ["cria", "recria", "eng_int"]}


# ── Semáforos ────────────────────────────────────────────────────────────────

def _sem_for(headroom: float | None,
             green: float, yellow: float) -> dict:
    """headroom positivo = más cushion. green/yellow son umbrales superiores."""
    if headroom is None or _is_nan(headroom):
        return _SEMAPHORE["neutro"]
    if headroom >= green:
        return _SEMAPHORE["verde"]
    if headroom >= yellow:
        return _SEMAPHORE["amarillo"]
    return _SEMAPHORE["rojo"]


def _all_semaphores(s: dict) -> dict:
    """Calcula los 5 semáforos de una etapa con sus headroom %."""
    out = {}

    # Precio equilibrio: headroom = (pv − precio_eq) / pv × 100
    pe, pv = s["precio_equilibrio"], s["pv"]
    if pv > 0 and not _is_nan(pe):
        h = (pv - pe) / pv * 100.0
    else:
        h = None
    out["precio_eq"] = {**_sem_for(h, 30, 10),
                        "headroom": h, "value": pe, "ref": pv}

    # Precio ración: headroom = (max / actual − 1) × 100
    # OJO: el "máximo tolerable" se aplica como shock uniforme sobre TODA
    # la ración (USD/kg MS promedio), no sobre un ingrediente específico.
    # Refleja la exposición al precio promedio de la dieta cargada por el
    # usuario en Parámetros → 🌾 Alimentación.
    pa_max, pa_act = s["precio_alim_max"], s["precio_alim_actual"]
    if pa_act > 0 and not _is_nan(pa_max):
        h = (pa_max / pa_act - 1.0) * 100.0
    else:
        h = None
    out["racion_max"] = {**_sem_for(h, 50, 20),
                         "headroom": h, "value": pa_max, "ref": pa_act}

    # GDP mínimo: headroom = (actual − min) / actual × 100
    gdp_min, gdp_act = s["gdp_min"], s["gdp_actual"]
    if gdp_act > 0 and not _is_nan(gdp_min):
        h = (gdp_act - gdp_min) / gdp_act * 100.0
    else:
        h = None
    out["gdp_min"] = {**_sem_for(h, 30, 10),
                      "headroom": h, "value": gdp_min, "ref": gdp_act}

    # Conversión máxima: headroom = (max / actual − 1) × 100
    ca_max, ca_act = s["ca_max"], s["ca_actual"]
    if ca_act > 0 and not _is_nan(ca_max):
        h = (ca_max / ca_act - 1.0) * 100.0
    else:
        h = None
    out["ca_max"] = {**_sem_for(h, 50, 20),
                     "headroom": h, "value": ca_max, "ref": ca_act}

    # Mortandad máxima: headroom = mort_max − mort_actual (en pp)
    mm, ma = s["mort_max_pct"], s["mort_pct"]
    if not _is_nan(mm):
        h = mm - ma
    else:
        h = None
    out["mort_max"] = {**_sem_for(h, 10, 5),
                       "headroom": h, "value": mm, "ref": ma}

    return out


def _overall_severity(sems: dict) -> dict:
    """Devuelve el peor semáforo de la etapa (excluyendo neutros)."""
    worst_sev = -1
    worst = _SEMAPHORE["neutro"]
    for v in sems.values():
        for k_sem in _SEMAPHORE:
            if _SEMAPHORE[k_sem]["color"] == v["color"]:
                sev = _SEVERITY[k_sem]
                if sev > worst_sev:
                    worst_sev = sev
                    worst = _SEMAPHORE[k_sem]
                break
    return worst


# ── Render ───────────────────────────────────────────────────────────────────

def _fmt(v: float, kind: str) -> str:
    if _is_nan(v):
        return "N/A"
    if kind == "usd_kg":
        return f"USD {v:.2f}/kg"
    if kind == "usd_kg_ms":
        return f"USD {v:.3f}/kg MS"
    if kind == "kg_dia":
        return f"{v:.3f} kg/día"
    if kind == "ca":
        return f"{v:.2f} kg/kg"
    if kind == "pct":
        return f"{v:.1f}%"
    return f"{v}"


def _metric_row(icon: str, label: str, value_str: str, ref_str: str,
                headroom_str: str, sem: dict) -> str:
    """Una fila de métrica con semáforo + valores."""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'background:white;border:1px solid #e4eaf4;border-radius:9px;'
        f'padding:10px 12px;margin-bottom:6px;">'
        # Pill del semáforo (izquierda)
        f'<div style="background:{sem["bg"]};border:1px solid {sem["color"]}55;'
        f'color:{sem["color"]};padding:3px 8px;border-radius:12px;'
        f'font-size:0.66rem;font-weight:800;white-space:nowrap;'
        f'letter-spacing:0.04em;flex-shrink:0;min-width:78px;text-align:center;">'
        f'● {sem["label"]}</div>'
        # Contenido (centro)
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:0.62rem;color:#7a8fa6;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;'
        f'display:flex;align-items:center;gap:4px;line-height:1;">'
        f'<span style="font-size:0.78rem;">{icon}</span>{label}</div>'
        f'<div style="font-size:0.92rem;font-weight:800;color:#0c1a2e;'
        f'line-height:1.2;margin-top:3px;white-space:nowrap;'
        f'overflow:hidden;text-overflow:ellipsis;">{value_str}</div>'
        f'<div style="font-size:0.66rem;color:#94a3b8;font-weight:600;'
        f'line-height:1.2;margin-top:1px;">'
        f'actual: {ref_str}'
        f'</div></div>'
        # Headroom (derecha)
        f'<div style="text-align:right;flex-shrink:0;">'
        f'<div style="font-size:0.62rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;">Margen</div>'
        f'<div style="font-size:0.92rem;font-weight:800;color:{sem["color"]};'
        f'line-height:1.1;white-space:nowrap;">{headroom_str}</div>'
        f'</div>'
        f'</div>'
    )


def _stage_card_html(key: str, s: dict) -> str:
    meta = _SEG[key]
    color, bg, border = meta["color"], meta["bg"], meta["border"]
    sems = _all_semaphores(s)
    overall = _overall_severity(sems)

    def hr_pct(h):
        return "N/A" if (h is None or _is_nan(h)) else f"{h:+.1f}%"

    def hr_pp(h):
        return "N/A" if (h is None or _is_nan(h)) else f"{h:+.1f} pp"

    rows = ""
    # Precio equilibrio
    rows += _metric_row(
        "💲", "Precio equilibrio",
        _fmt(sems["precio_eq"]["value"], "usd_kg"),
        f"venta {_fmt(sems['precio_eq']['ref'], 'usd_kg')}",
        hr_pct(sems["precio_eq"]["headroom"]),
        sems["precio_eq"],
    )
    # Precio ración (USD/kg MS promedio, no un ingrediente específico)
    rows += _metric_row(
        "🌾", "Precio ración máx.",
        _fmt(sems["racion_max"]["value"], "usd_kg_ms"),
        _fmt(sems["racion_max"]["ref"], "usd_kg_ms"),
        hr_pct(sems["racion_max"]["headroom"]),
        sems["racion_max"],
    )
    # GDP mínimo
    rows += _metric_row(
        "📈", "GDP mínimo",
        _fmt(sems["gdp_min"]["value"], "kg_dia"),
        _fmt(sems["gdp_min"]["ref"], "kg_dia"),
        hr_pct(sems["gdp_min"]["headroom"]),
        sems["gdp_min"],
    )
    # Conversión máxima
    rows += _metric_row(
        "🔄", "Conversión máx.",
        _fmt(sems["ca_max"]["value"], "ca"),
        _fmt(sems["ca_max"]["ref"], "ca"),
        hr_pct(sems["ca_max"]["headroom"]),
        sems["ca_max"],
    )
    # Mortandad máxima
    rows += _metric_row(
        "⚠️", "Mortandad máx.",
        _fmt(sems["mort_max"]["value"], "pct"),
        _fmt(sems["mort_max"]["ref"], "pct"),
        hr_pp(sems["mort_max"]["headroom"]),
        sems["mort_max"],
    )

    chip = (
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{s["dias"]} días · {s["mort_pct"]:.1f}% mort'
        f'</span>'
    )

    overall_block = (
        f'<div style="background:{overall["bg"]};'
        f'border:1.5px solid {overall["color"]}55;border-radius:10px;'
        f'padding:10px 14px;margin-bottom:10px;text-align:center;">'
        f'<div style="font-size:0.62rem;color:{overall["color"]};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;">Robustez general</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:{overall["color"]};'
        f'margin-top:2px;">{overall["icon"]} {overall["label"]}</div>'
        f'</div>'
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
        f'{overall_block}'
        f'{rows}'
        f'</div></div>'
    )


def _stage_grid(data: dict) -> None:
    cols = st.columns(2, gap="small")
    keys = ["cria", "recria", "eng_int"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            is_active = data[key].get("active", True)
            opacity = "1" if is_active else "0.42"
            st.markdown(
                f'<div style="opacity:{opacity};">'
                f'{_stage_card_html(key, data[key])}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:14px'></div>",
                        unsafe_allow_html=True)


# ── Tornado chart ────────────────────────────────────────────────────────────

# Variables a sensibilizar (delta_kind: 'rel' = porcentaje relativo,
# 'pp' = puntos porcentuales absolutos). Alineadas con el modelo
# bioeconómico actual: compra y venta de hacienda, precio promedio de
# la ración (USD/kg MS), productividad (GDP), riesgo sanitario
# (mortandad) y logística (flete).
#
# OJO: `precio_racion` aplica un shock UNIFORME sobre el costo total de
# alimentación de la etapa (`s["alim_actual"]` ya viene como Σ de los
# ingredientes cargados por el usuario en Parámetros → 🌾 Alimentación).
# No hay supuestos de composición de balanceado ni de exposición a
# ingredientes no cargados. Si la ración es 100% balanceado, el slider
# mueve el precio del balanceado; si hay maíz + silo + soja, mueve los
# tres en igual proporción.
_TORNADO_VARS = [
    {"key": "precio_compra", "label": "Precio compra", "icon": "🛒",
     "delta": 0.20, "kind": "rel"},
    {"key": "precio_venta",  "label": "Precio venta",  "icon": "💲",
     "delta": 0.20, "kind": "rel"},
    {"key": "precio_racion", "label": "Precio ración", "icon": "🌾",
     "delta": 0.20, "kind": "rel"},
    {"key": "gdp",           "label": "GDP",           "icon": "📈",
     "delta": 0.15, "kind": "rel"},
    {"key": "mortandad",     "label": "Mortandad",     "icon": "⚠️",
     "delta": 5.0,  "kind": "pp"},
    {"key": "flete",         "label": "Flete",         "icon": "🚛",
     "delta": 0.20, "kind": "rel"},
]

def _evaluate_with_overrides(s: dict, ov: dict) -> dict:
    """
    Recalcula métricas con un dict de overrides. Claves opcionales:
        precio_compra_mult   (default 1.0)  — multiplica compra/cab
        precio_venta_mult    (default 1.0)  — multiplica pv (ingreso + comisión)
        precio_racion_mult   (default 1.0)  — multiplica alim cab (shock
                                              proporcional sobre TODA la
                                              ración, USD/kg MS promedio)
        gdp_mult             (default 1.0)  — escala kg_aumento (y alim)
        mort_pp_delta        (default 0.0)  — suma pp a mort
        flete_mult           (default 1.0)  — multiplica fe + fs

    El costo financiero se aplica sobre el CAPITAL inmovilizado durante el
    ciclo: capital × tasa%/100 × días/365 (alineado con page_costos).
    """
    pv          = s["pv"] * ov.get("precio_venta_mult", 1.0)
    # Cap mort en [0, 99] para evitar (1−m)=0 que vuelve cab_vend=0 y métricas degeneradas
    mort        = min(99.0,
                      max(0.0, s["mort_pct"] + ov.get("mort_pp_delta", 0.0)))
    kg_aumento  = max(s["kg_out"] - s["kg_in"], 0.0) * ov.get("gdp_mult", 1.0)
    kg_out      = s["kg_in"] + kg_aumento
    compra      = s["compra"] * ov.get("precio_compra_mult", 1.0)
    # Bioeconómico: alim escala con kg_carne × CA × precio_pond_dieta.
    # GDP afecta kg_carne (kg_aumento), así que también multiplica alim.
    # `precio_racion_mult` es un shock uniforme sobre USD/kg MS promedio
    # de la ración cargada — no es un ingrediente específico.
    alim        = (s["alim_actual"]
                   * ov.get("precio_racion_mult", 1.0)
                   * ov.get("gdp_mult", 1.0))
    fe          = s["fe"] * ov.get("flete_mult", 1.0)
    fs          = s["fs"] * ov.get("flete_mult", 1.0)

    op_cab     = s["mo_dia"] * s["dias"]
    estr_cab   = s.get("estructura_cab", 0.0)
    com_cab    = (s["com_pct"] / 100.0) * pv * kg_out + fe + fs
    capital    = compra + alim + s["san"] + op_cab + estr_cab + com_cab

    tasa_pct   = _g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])
    costo_fin  = (capital * (tasa_pct / 100.0) * s["dias"] / 365.0
                  if s["dias"] > 0 else 0.0)

    base    = capital + costo_fin
    m       = mort / 100.0

    # Mortandad implícita en la asimetría cab_vend (ingreso) vs cab_in (costo);
    # no se suma como sobrecosto explícito.
    ingreso_cab   = kg_out * pv
    costo_cab     = base
    cab_vend      = max(int(s["cab_in"] * (1 - m)), 0)
    ingreso_total = ingreso_cab * cab_vend
    costo_total   = costo_cab * s["cab_in"]
    margen_total  = ingreso_total - costo_total
    margen_cab    = (margen_total / s["cab_in"]
                     if s["cab_in"] > 0 else 0.0)

    usd_cab_dia = margen_cab / s["dias"] if s["dias"] > 0 else 0.0

    return {
        "margen_cab":   margen_cab,
        "margen_total": margen_total,
        "usd_cab_dia":  usd_cab_dia,
        "mort_used":    mort,
    }


def _evaluate_metric(s: dict, override_key: str | None, sign: int) -> dict:
    """Wrapper para tornado: aplica UN override con un signo (+1 / −1 / 0).

    Los deltas coinciden con `_TORNADO_VARS` (rel = porcentaje, pp = puntos
    porcentuales absolutos para mortandad).
    """
    ov: dict = {}
    if override_key == "precio_compra":
        ov["precio_compra_mult"] = 1.0 + sign * 0.20
    elif override_key == "precio_venta":
        ov["precio_venta_mult"]  = 1.0 + sign * 0.20
    elif override_key == "precio_racion":
        ov["precio_racion_mult"] = 1.0 + sign * 0.20
    elif override_key == "gdp":
        ov["gdp_mult"]           = 1.0 + sign * 0.15
    elif override_key == "mortandad":
        ov["mort_pp_delta"]      = sign * 5.0
    elif override_key == "flete":
        ov["flete_mult"]         = 1.0 + sign * 0.20
    return _evaluate_with_overrides(s, ov)


def _tornado_data(s: dict, metric_key: str) -> tuple[list[dict], float]:
    """Devuelve (rows ordenadas asc por swing, baseline)."""
    baseline = _evaluate_metric(s, None, 0)[metric_key]
    rows = []
    for v in _TORNADO_VARS:
        low_metric  = _evaluate_metric(s, v["key"], -1)[metric_key]
        high_metric = _evaluate_metric(s, v["key"], +1)[metric_key]
        low_delta   = low_metric  - baseline
        high_delta  = high_metric - baseline
        swing       = abs(low_delta) + abs(high_delta)
        delta_label = (f"±{v['delta']*100:.0f}%" if v["kind"] == "rel"
                       else f"±{v['delta']:.0f} pp")
        rows.append({
            "key":         v["key"],
            "var_label":   f"{v['icon']}  {v['label']}  ({delta_label})",
            "low_metric":  low_metric,
            "high_metric": high_metric,
            "low_delta":   low_delta,
            "high_delta":  high_delta,
            "swing":       swing,
        })
    rows.sort(key=lambda r: r["swing"])  # asc → biggest at top en horizontal bar
    return rows, baseline


# ── Mini-tornados por etapa (sensibilidad comparativa) ───────────────────────

def _mini_tornado_chart(rows: list[dict], n_top: int | None = None) -> go.Figure:
    """Tornado simplificado: TODAS las variables ordenadas por swing absoluto.
    Métrica fija margen/cab. Paleta alineada con Margen Bruto (emerald/coral).

    Si n_top se pasa explícito, recorta al top-N; por defecto muestra todas.
    """
    if n_top is None:
        top_rows = sorted(rows, key=lambda r: r["swing"], reverse=True)
    else:
        top_rows = sorted(rows, key=lambda r: r["swing"], reverse=True)[:n_top]
    top_rows.sort(key=lambda r: r["swing"])  # asc → mayor arriba en barh
    labels = [r["var_label"].split("  (")[0] for r in top_rows]
    pos_x = [max(r["low_delta"], r["high_delta"], 0.0) for r in top_rows]
    neg_x = [min(r["low_delta"], r["high_delta"], 0.0) for r in top_rows]

    # Altura adaptativa para que entren todas las variables sin solape
    chart_height = max(220, 36 * len(labels) + 50)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=pos_x, orientation="h",
        marker=dict(color="#10b981", line=dict(color="white", width=1)),
        hovertemplate="<b>%{y}</b><br>Δ %{x:+,.1f} USD<extra></extra>",
        showlegend=False,
    ))
    fig.add_trace(go.Bar(
        y=labels, x=neg_x, orientation="h",
        marker=dict(color="#f87171", line=dict(color="white", width=1)),
        hovertemplate="<b>%{y}</b><br>Δ %{x:+,.1f} USD<extra></extra>",
        showlegend=False,
    ))
    fig.add_vline(x=0, line_color="#0c1a2e", line_width=1.2)
    fig.update_layout(
        barmode="overlay",
        height=chart_height,
        margin=dict(t=8, b=22, l=140, r=22),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        xaxis=dict(
            gridcolor="#eef2f7", zeroline=False,
            tickfont=dict(size=9, color="#64748b"),
            tickformat=",.0f",
        ),
        yaxis=dict(
            tickfont=dict(size=10, color="#0c1a2e"),
            gridcolor="rgba(0,0,0,0)",
            automargin=True,
        ),
        bargap=0.30,
        hoverlabel=dict(bgcolor="white", bordercolor="#e4eaf4",
                        font=dict(size=11, color="#0c1a2e")),
    )
    return fig


def _per_stage_tornado_section(data: dict) -> None:
    """Grid con mini-tornados (margen/cab) — sólo etapas activas."""
    keys = S.active_stages()
    if not keys:
        st.info("Activá al menos una etapa para ver los tornados.",
                icon="ℹ️")
        return
    cols = st.columns(2 if len(keys) > 1 else 1, gap="small")
    for i, key in enumerate(keys):
        with cols[i % len(cols)]:
            meta = _SEG[key]
            s = data[key]
            rows, _ = _tornado_data(s, "margen_cab")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'margin:6px 0 4px 2px;">'
                f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
                f'<span style="font-size:0.86rem;font-weight:800;'
                f'color:{meta["color"]};text-transform:uppercase;'
                f'letter-spacing:0.05em;">{meta["title"]}</span>'
                f'<span style="font-size:0.64rem;color:#94a3b8;'
                f'font-weight:600;margin-left:auto;">'
                f'Δ margen/cab (USD)</span></div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                _mini_tornado_chart(rows),
                width="stretch",
                key=f"sens_minitornado_{key}",
            )
            st.markdown("<div style='height:8px'></div>",
                        unsafe_allow_html=True)


# ── Simulación interactiva con sliders ───────────────────────────────────────

_SLIDER_CONFIGS = [
    # Hacienda — compra y venta
    {"key": "precio_compra", "label": "Precio compra",      "icon": "🛒",
     "min": -30.0, "max": 30.0, "default": 0.0, "step": 1.0,
     "fmt": "%+.0f%%", "group": "Hacienda"},
    {"key": "precio_venta",  "label": "Precio venta",       "icon": "💲",
     "min": -30.0, "max": 30.0, "default": 0.0, "step": 1.0,
     "fmt": "%+.0f%%", "group": "Hacienda"},
    # Productividad y dieta — "Precio ración" es el promedio USD/kg MS
    # de la dieta cargada; mueve TODOS los ingredientes uniformemente,
    # no asume composición específica.
    {"key": "precio_racion", "label": "Precio ración",      "icon": "🌾",
     "min": -30.0, "max": 30.0, "default": 0.0, "step": 1.0,
     "fmt": "%+.0f%%", "group": "Productividad"},
    {"key": "gdp",           "label": "GDP / ADPV",         "icon": "📈",
     "min": -30.0, "max": 30.0, "default": 0.0, "step": 1.0,
     "fmt": "%+.0f%%", "group": "Productividad"},
    # Riesgo operativo
    {"key": "mortandad",     "label": "Mortandad",          "icon": "⚠️",
     "min": -3.0, "max": 10.0, "default": 0.0, "step": 0.5,
     "fmt": "%+.1f pp", "group": "Riesgo operativo"},
    {"key": "flete",         "label": "Flete",              "icon": "🚛",
     "min": -30.0, "max": 30.0, "default": 0.0, "step": 1.0,
     "fmt": "%+.0f%%", "group": "Riesgo operativo"},
]

_SLIDER_KEY_FMT = "sens_sim_{key}"

_SLIDER_TO_OVERRIDE = {
    "precio_compra": ("precio_compra_mult", "rel"),
    "precio_venta":  ("precio_venta_mult",  "rel"),
    "precio_racion": ("precio_racion_mult", "rel"),
    "gdp":           ("gdp_mult",           "rel"),
    "mortandad":     ("mort_pp_delta",      "pp"),
    "flete":         ("flete_mult",         "rel"),
}


def _sim_override_for_stage(stage_key: str) -> dict:
    """Lee los sliders y construye el dict de overrides para una etapa."""
    ov: dict = {}
    for cfg in _SLIDER_CONFIGS:
        v = float(st.session_state.get(
            _SLIDER_KEY_FMT.format(key=cfg["key"]), cfg["default"]))
        ov_key, kind = _SLIDER_TO_OVERRIDE[cfg["key"]]
        ov[ov_key] = v if kind == "pp" else 1.0 + v / 100.0
    return ov


def _reset_sim_sliders() -> None:
    for cfg in _SLIDER_CONFIGS:
        st.session_state[_SLIDER_KEY_FMT.format(key=cfg["key"])] = cfg["default"]


def _sim_card_html(stage_key: str, baseline: dict, mod: dict) -> str:
    meta = _SEG[stage_key]
    color = meta["color"]
    margen_total = mod["margen_total"]
    margen_cab   = mod["margen_cab"]
    usd_cab_dia  = mod["usd_cab_dia"]

    delta_total = mod["margen_total"] - baseline["margen_total"]
    base_abs    = abs(baseline["margen_total"])
    delta_pct   = (delta_total / base_abs * 100.0) if base_abs > 1e-3 else 0.0

    margen_color = "#16a34a" if margen_total >= 0 else "#dc2626"
    sign_total   = "+" if margen_total >= 0 else "−"
    sign_cab     = "+" if margen_cab >= 0 else "−"

    if abs(delta_total) < 1.0:
        chip_color, chip_bg = "#64748b", "#f1f5f9"
        chip_icon, chip_text = "●", "Sin cambios"
    elif delta_total > 0:
        chip_color, chip_bg, chip_icon = "#16a34a", "#f0fdf4", "▲"
        chip_text = f"+USD {delta_total:,.0f} · {delta_pct:+.1f}%"
    else:
        chip_color, chip_bg, chip_icon = "#dc2626", "#fef2f2", "▼"
        chip_text = f"−USD {abs(delta_total):,.0f} · {delta_pct:+.1f}%"

    return (
        f'<div style="background:white;border:1px solid {meta["border"]};'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.06);height:100%;">'
        f'<div style="background:linear-gradient(135deg,{color},{color}dd);'
        f'padding:11px 14px;color:white;display:flex;align-items:center;'
        f'gap:8px;">'
        f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.86rem;font-weight:700;'
        f'letter-spacing:0.02em;">{meta["title"]}</span>'
        f'</div>'
        f'<div style="padding:13px 14px 14px;text-align:center;">'
        f'<div style="font-size:1.55rem;font-weight:800;color:{margen_color};'
        f'line-height:1;letter-spacing:-0.02em;'
        f'font-variant-numeric:tabular-nums;">'
        f'{sign_total}USD&nbsp;{abs(margen_total):,.0f}</div>'
        f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-top:3px;">'
        f'Margen bruto total</div>'
        f'<div style="margin-top:9px;">'
        f'<span style="background:{chip_bg};border:1px solid {chip_color}55;'
        f'color:{chip_color};font-size:0.66rem;font-weight:800;'
        f'padding:3px 10px;border-radius:12px;letter-spacing:0.04em;'
        f'white-space:nowrap;font-variant-numeric:tabular-nums;">'
        f'{chip_icon} {chip_text}</span></div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;'
        f'gap:8px;margin-top:11px;border-top:1px solid #f1f5f9;'
        f'padding-top:9px;">'
        f'<div>'
        f'<div style="font-size:0.86rem;font-weight:800;color:#1e3a5f;'
        f'line-height:1;font-variant-numeric:tabular-nums;">'
        f'{sign_cab}USD&nbsp;{abs(margen_cab):,.0f}</div>'
        f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-top:1px;">'
        f'Margen / cab</div></div>'
        f'<div>'
        f'<div style="font-size:0.86rem;font-weight:800;color:#1e3a5f;'
        f'line-height:1;font-variant-numeric:tabular-nums;">'
        f'USD&nbsp;{usd_cab_dia:.2f}</div>'
        f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-top:1px;">'
        f'USD/cab/día</div></div>'
        f'</div></div></div>'
    )


def _interactive_simulation_section(data: dict) -> None:
    # Inicializar sliders en defaults antes de renderizar
    for cfg in _SLIDER_CONFIGS:
        sk = _SLIDER_KEY_FMT.format(key=cfg["key"])
        if sk not in st.session_state:
            st.session_state[sk] = cfg["default"]

    # Encabezado + botón Reset
    c_top1, c_top2 = st.columns([5, 1])
    with c_top1:
        st.markdown(
            '<p style="font-size:0.84rem;color:#475569;margin:0 0 6px 0;">'
            'Mové los sliders y observá el impacto sobre el margen bruto en '
            'cada etapa. Cambios expresados como % multiplicativo sobre el '
            'baseline, salvo mortandad (puntos porcentuales).'
            '</p>',
            unsafe_allow_html=True,
        )
    with c_top2:
        st.button("↺ Reset", on_click=_reset_sim_sliders,
                  key="sens_sim_reset_btn", width="stretch")

    # Sliders en 3 columnas (Mercado · Productividad · Riesgo operativo)
    groups: dict[str, list[dict]] = {}
    for cfg in _SLIDER_CONFIGS:
        groups.setdefault(cfg["group"], []).append(cfg)

    group_colors = {
        "Mercado":          "#1565c0",
        "Productividad":    "#0d9488",
        "Riesgo operativo": "#d97706",
    }

    cols = st.columns(3, gap="medium")
    for col, (group_name, group_cfgs) in zip(cols, groups.items()):
        with col:
            color = group_colors.get(group_name, "#64748b")
            st.markdown(
                f'<p style="font-size:0.62rem;font-weight:800;color:{color};'
                f'text-transform:uppercase;letter-spacing:0.08em;'
                f'margin:0 0 2px 0;">{group_name}</p>',
                unsafe_allow_html=True,
            )
            for cfg in group_cfgs:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#0c1a2e;'
                    f'font-weight:600;margin:6px 0 0 0;">'
                    f'{cfg["icon"]} {cfg["label"]}</div>',
                    unsafe_allow_html=True,
                )
                st.slider(
                    cfg["label"],
                    min_value=cfg["min"], max_value=cfg["max"],
                    step=cfg["step"],
                    key=_SLIDER_KEY_FMT.format(key=cfg["key"]),
                    format=cfg["fmt"],
                    label_visibility="collapsed",
                )

    # Cards de impacto en tiempo real (sólo etapas activas)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    active_keys = S.active_stages()
    if not active_keys:
        st.info("Activá al menos una etapa para simular impactos.",
                icon="ℹ️")
        return
    cols = st.columns(len(active_keys), gap="small")
    for col, stage_key in zip(cols, active_keys):
        s = data[stage_key]
        baseline = _evaluate_with_overrides(s, {})
        ov = _sim_override_for_stage(stage_key)
        mod = _evaluate_with_overrides(s, ov)
        with col:
            st.markdown(_sim_card_html(stage_key, baseline, mod),
                        unsafe_allow_html=True)


# ── Interpretación estratégica del riesgo ───────────────────────────────────

_RISK_TITLES = {
    "cria":    "Cría",
    "recria":  "Recría",
    "eng_int": "Engorde",
}

# Pesos de los componentes del score compuesto (deben sumar 1.0)
_RISK_WEIGHTS = {
    "racion":      0.20,
    "volatilidad": 0.25,
    "duracion":    0.15,
    "capital":     0.20,
    "mortandad":   0.20,
}


def _safe_denom(baseline: float, ingreso: float) -> float:
    """Denominador robusto para ratios de sensibilidad (evita división por
    margen pequeño, negativo o NaN)."""
    b = abs(baseline) if not _is_nan(baseline) else 0.0
    i = abs(ingreso)  if not _is_nan(ingreso)  else 0.0
    return max(b, i * 0.05, 1.0)


def _compute_risk_components(s: dict, baseline: float,
                              tornado_rows: list[dict],
                              capital_max: float) -> dict:
    """
    Calcula cada componente del riesgo (0-100, mayor = más riesgoso).

    Componentes:
      score_racion      = swing(precio ración) / |baseline| × 50, cap 100
      score_volatilidad = Σswings / |baseline| × 30, cap 100
      score_duracion    = días / 7.30 (730 d = 100), cap 100
      score_capital     = capital_etapa / max(capital peers) × 100
      score_mortandad   = mort_pct × 10, cap 100
    """
    denom = _safe_denom(baseline, s["ingreso_cab"])

    # Sensibilidad al precio promedio de la ración (USD/kg MS).
    # Matcheamos por `key` interno — no por label — para no acoplar este
    # cálculo al texto visible del tornado.
    racion_row = next((r for r in tornado_rows if r.get("key") == "precio_racion"),
                     None)
    if racion_row is not None:
        score_racion = min(100.0, (racion_row["swing"] / denom) * 50.0)
    else:
        score_racion = 0.0

    # Volatilidad: suma total de swings de las 7 variables
    total_swing = sum(r["swing"] for r in tornado_rows)
    score_volatilidad = min(100.0, (total_swing / denom) * 30.0)

    # Duración del ciclo
    score_duracion = min(100.0, s["dias"] / 7.30)

    # Capital inmovilizado relativo
    score_capital = ((s["costo_total"] / capital_max * 100.0)
                     if capital_max > 0 else 0.0)
    score_capital = min(100.0, score_capital)

    # Mortandad
    score_mortandad = min(100.0, s["mort_pct"] * 10.0)

    composite = (
        score_racion      * _RISK_WEIGHTS["racion"]
        + score_volatilidad * _RISK_WEIGHTS["volatilidad"]
        + score_duracion    * _RISK_WEIGHTS["duracion"]
        + score_capital     * _RISK_WEIGHTS["capital"]
        + score_mortandad   * _RISK_WEIGHTS["mortandad"]
    )
    robustness = max(0.0, min(100.0, 100.0 - composite))

    return {
        "score_racion":      score_racion,
        "score_volatilidad": score_volatilidad,
        "score_duracion":    score_duracion,
        "score_capital":     score_capital,
        "score_mortandad":   score_mortandad,
        "risk_composite":    composite,
        "robustness":        robustness,
        "total_swing":       total_swing,
        "racion_swing":      racion_row["swing"] if racion_row else 0.0,
    }


def _build_risk_return(data: dict) -> list[dict]:
    """Para cada etapa ACTIVA: margen + componentes de riesgo + score compuesto.
    Las inactivas se excluyen del análisis de riesgo."""
    active_keys = S.active_stages()
    capital_max = max((data[k]["costo_total"] for k in active_keys),
                      default=1.0)

    rows = []
    for k in active_keys:
        s = data[k]
        baseline = s["margen_cab"]
        tornado_rows, _ = _tornado_data(s, "margen_cab")
        comp = _compute_risk_components(s, baseline, tornado_rows, capital_max)
        usd_cab_dia = (s["margen_cab"] / s["dias"]) if s["dias"] > 0 else 0.0
        rows.append({
            "key": k, "title": _RISK_TITLES[k], "meta": _SEG[k],
            "margen_cab":   baseline,
            "margen_total": s["margen_total"],
            "usd_cab_dia":  usd_cab_dia,
            "dias":         s["dias"],
            "mort_pct":     s["mort_pct"],
            "capital":      s["costo_total"],
            **comp,
        })
    return rows


# ── Alertas estratégicas ─────────────────────────────────────────────────────

_VAR_LABELS = {
    "precio_compra": ("precio de compra",            "🛒"),
    "precio_venta":  ("precio de venta",             "💲"),
    "precio_racion": ("precio de la ración",         "🌾"),
    "gdp":           ("GDP",                         "📈"),
    "mortandad":     ("mortandad",                   "⚠"),
    "flete":         ("fletes",                      "🚛"),
}


def _generate_alerts(rows: list[dict], data: dict) -> list[dict]:
    """Alertas focalizadas en:
        1. Robustez baja por etapa (cushion antes del breakeven).
        2. Sensibilidades altas: variables del tornado con mayor swing
           respecto al margen baseline. Cada alerta indica VARIABLE + ETAPA.

    No incluye alertas de capital, duración, ranking de robustez, ni mejor
    margen (esas viven en el resumen comparativo).
    """
    alerts: list[dict] = []
    if not rows:
        return alerts

    # ── 1. Robustez baja por etapa ────────────────────────────────────────
    for r in rows:
        rob = r["robustness"]
        if rob < 30:
            alerts.append({
                "icon": "🚨", "level": "critical",
                "msg": (f"Robustez crítica en <b>{r['title']}</b> "
                        f"({rob:.0f}/100). El margen está cerca del punto "
                        f"de equilibrio."),
            })
        elif rob < 50:
            alerts.append({
                "icon": "🛡", "level": "warning",
                "msg": (f"Robustez baja en <b>{r['title']}</b> "
                        f"({rob:.0f}/100). Cushion limitado frente a "
                        f"variaciones de precios o productividad."),
            })

    # ── 2. Sensibilidades altas por etapa ─────────────────────────────────
    # Para cada etapa, leer el tornado y reportar variables con swing
    # >= 30% del valor absoluto del margen baseline.
    SENS_THRESHOLD = 0.30
    for r in rows:
        s = data[r["key"]]
        baseline = abs(r["margen_cab"])
        denom = max(baseline, 1.0)  # evita división por cero / margen ~ 0
        tornado_rows, _ = _tornado_data(s, "margen_cab")
        for t in tornado_rows:
            swing = t.get("swing", 0.0)
            ratio = swing / denom
            if ratio >= SENS_THRESHOLD:
                var_label, var_icon = _VAR_LABELS.get(
                    t["key"], (t["key"], "📊"))
                alerts.append({
                    "icon": var_icon, "level": "warning",
                    "msg": (f"Alta sensibilidad a <b>{var_label}</b> en "
                            f"<b>{r['title']}</b>: un cambio del rango "
                            f"considerado mueve el margen en "
                            f"USD&nbsp;{swing:,.0f}/cab "
                            f"({ratio*100:.0f}% del margen actual)."),
                })

    if not alerts:
        alerts.append({
            "icon": "✅", "level": "good",
            "msg": ("Sin alertas: las etapas activas presentan robustez "
                    "razonable y ninguna variable individual supera el "
                    "umbral de sensibilidad."),
        })
    return alerts


def _alert_style(level: str) -> tuple[str, str]:
    """color, bg para cada nivel."""
    return {
        "critical": ("#dc2626", "#fef2f2"),
        "warning":  ("#d97706", "#fffbeb"),
        "info":     ("#1565c0", "#eff6ff"),
        "good":     ("#16a34a", "#f0fdf4"),
    }.get(level, ("#64748b", "#f1f5f9"))


def _alerts_html(alerts: list[dict]) -> str:
    items = ""
    for a in alerts:
        color, bg = _alert_style(a["level"])
        items += (
            f'<div style="background:{bg};border:1px solid {color}55;'
            f'border-left:4px solid {color};border-radius:8px;'
            f'padding:11px 14px;margin-bottom:8px;'
            f'display:flex;align-items:flex-start;gap:11px;">'
            f'<span style="font-size:1.05rem;flex-shrink:0;line-height:1.4;">'
            f'{a["icon"]}</span>'
            f'<span style="font-size:0.84rem;color:#0c1a2e;'
            f'line-height:1.45;">{a["msg"]}</span>'
            f'</div>'
        )
    return f'<div>{items}</div>'


# ── Matriz Modelo × Margen × Riesgo ──────────────────────────────────────────

def _risk_color(score: float) -> tuple[str, str]:
    if score >= 70:   return "#dc2626", "#fef2f2"
    if score >= 40:   return "#d97706", "#fffbeb"
    return "#16a34a", "#f0fdf4"


def _robust_color(score: float) -> tuple[str, str, str]:
    if score >= 70:   return "#16a34a", "#f0fdf4", "Robusto"
    if score >= 40:   return "#d97706", "#fffbeb", "Sensible"
    return "#dc2626", "#fef2f2", "Crítico"


def _matrix_table_html(rows: list[dict]) -> str:
    th_base = ('padding:11px 14px;font-size:0.66rem;font-weight:700;'
               'color:#7a8fa6;text-transform:uppercase;letter-spacing:0.08em;'
               'background:#f8fafd;border-bottom:1.5px solid #e4eaf4;')
    th_l = th_base + 'text-align:left;'
    th_c = th_base + 'text-align:center;'

    body = ""
    for i, r in enumerate(rows):
        meta = r["meta"]
        bg_row = "#ffffff" if i % 2 == 0 else "#fbfcfe"
        margen = r["margen_cab"]
        margen_color = "#16a34a" if margen >= 0 else "#dc2626"
        sign = "+" if margen >= 0 else "−"

        risk = r["risk_composite"]
        rk_color, rk_bg = _risk_color(risk)
        rb_color, rb_bg, rb_label = _robust_color(r["robustness"])

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
            f'margin-top:2px;">USD {r["usd_cab_dia"]:.2f}/cab/día · '
            f'{r["dias"]} d</div>'
            f'</div></div></td>'
        )

        margen_cell = (
            f'<td style="padding:14px 14px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;text-align:center;'
            f'vertical-align:middle;">'
            f'<div style="font-size:1.05rem;font-weight:800;'
            f'color:{margen_color};line-height:1.1;'
            f'font-variant-numeric:tabular-nums;">'
            f'{sign}USD&nbsp;{abs(margen):,.0f}</div>'
            f'<div style="font-size:0.62rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-top:3px;">'
            f'por cab</div>'
            f'</td>'
        )

        riesgo_cell = (
            f'<td style="padding:14px 14px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;text-align:center;'
            f'vertical-align:middle;min-width:160px;">'
            f'<span style="background:{rk_bg};border:1px solid {rk_color}55;'
            f'color:{rk_color};font-size:0.78rem;font-weight:800;'
            f'padding:5px 13px;border-radius:14px;letter-spacing:0.02em;'
            f'white-space:nowrap;">● {risk:.0f}/100</span>'
            f'<div style="background:#eef2f7;border-radius:4px;height:5px;'
            f'overflow:hidden;margin-top:8px;">'
            f'<div style="background:{rk_color};height:100%;'
            f'width:{min(100, risk):.1f}%;border-radius:4px;"></div>'
            f'</div></td>'
        )

        robust_cell = (
            f'<td style="padding:14px 14px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;text-align:center;'
            f'vertical-align:middle;min-width:160px;">'
            f'<div style="font-size:1.05rem;font-weight:800;color:{rb_color};'
            f'line-height:1;font-variant-numeric:tabular-nums;">'
            f'{r["robustness"]:.0f}/100</div>'
            f'<div style="margin-top:4px;">'
            f'<span style="background:{rb_bg};border:1px solid {rb_color}55;'
            f'color:{rb_color};font-size:0.62rem;font-weight:800;'
            f'padding:2px 8px;border-radius:10px;letter-spacing:0.04em;'
            f'white-space:nowrap;">● {rb_label}</span>'
            f'</div></td>'
        )

        body += (f'<tr>{modelo_cell}{margen_cell}'
                 f'{riesgo_cell}{robust_cell}</tr>')

    return (
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow-x:auto;'
        f'box-shadow:0 2px 10px rgba(13,27,66,0.06);">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:Inter,Arial,sans-serif;min-width:720px;">'
        f'<thead><tr>'
        f'<th style="{th_l}">Modelo</th>'
        f'<th style="{th_c}">Margen bruto</th>'
        f'<th style="{th_c}">Riesgo (composite)</th>'
        f'<th style="{th_c}">Score robustez</th>'
        f'</tr></thead>'
        f'<tbody>{body}</tbody>'
        f'</table>'
        f'</div>'
    )


def _risk_summary_section(data: dict) -> None:
    """Matriz comparativa risk-return por etapa activa."""
    rows = _build_risk_return(data)
    st.markdown(_matrix_table_html(rows), unsafe_allow_html=True)


def _alerts_section(data: dict) -> None:
    """Alertas focalizadas en sensibilidades altas y robustez baja, con
    atribución explícita de variable + etapa."""
    rows = _build_risk_return(data)
    alerts = _generate_alerts(rows, data)
    st.markdown(_alerts_html(alerts), unsafe_allow_html=True)


# ── Entry point ──────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Sensibilidad y Riesgo",
        "Robustez y fragilidad económica del negocio: límites tolerables "
        "(margen=0) de precios, productividad y mortalidad por etapa. "
        "Semáforo verde/amarillo/rojo para lectura inmediata.",
    )

    data = _build_sensibilidad()

    # ── 1. Sensibilidad — Diagrama Tornado por etapa ─────────────────────
    section("Sensibilidad — Diagrama Tornado")
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 12px 0;">'
        'Variables más críticas del <b>margen / cab</b> en cada etapa.'
        '</p>',
        unsafe_allow_html=True,
    )
    _per_stage_tornado_section(data)

    st.divider()

    # ── 2. Sensibilidad interactiva (sliders) ────────────────────────────
    section("Sensibilidad interactiva")
    _interactive_simulation_section(data)

    st.divider()

    # ── 3. Robustez por etapa ────────────────────────────────────────────
    section("Robustez por etapa")
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 12px 0;">'
        'Cushion antes del punto de equilibrio (margen=0). '
        '🟢 robusto · 🟡 sensible · 🔴 crítico.'
        '</p>',
        unsafe_allow_html=True,
    )
    _stage_grid(data)

    st.divider()

    # ── 4. Resumen de Riesgo y Robustez ──────────────────────────────────
    section("Resumen de Riesgo y Robustez")
    _risk_summary_section(data)

    st.divider()

    # ── 5. Alertas (sensibilidades altas + robustez baja) ────────────────
    section("Alertas")
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 12px 0;">'
        'Sólo se reportan etapas con robustez baja y variables con alta '
        'sensibilidad sobre el margen/cab actual.'
        '</p>',
        unsafe_allow_html=True,
    )
    _alerts_section(data)
