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
import pandas as pd
import plotly.graph_objects as go

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

_SEMAPHORE = {
    "verde":    {"color": "#16a34a", "bg": "#f0fdf4", "label": "Robusto",  "icon": "🟢"},
    "amarillo": {"color": "#d97706", "bg": "#fffbeb", "label": "Sensible", "icon": "🟡"},
    "rojo":     {"color": "#dc2626", "bg": "#fef2f2", "label": "Crítico",  "icon": "🔴"},
    "neutro":   {"color": "#64748b", "bg": "#f1f5f9", "label": "N/A",      "icon": "⚪"},
}

_SEVERITY = {"verde": 0, "amarillo": 1, "rojo": 2, "neutro": -1}


def _g(key: str, default: float) -> float:
    return float(st.session_state.get(key, default))


def _is_nan(x) -> bool:
    try:
        return isnan(x)
    except (TypeError, ValueError):
        return False


# ── Lectura de tabla de alimentación ─────────────────────────────────────────

def _read_feed_df(editor_key: str) -> pd.DataFrame:
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


def _alim_breakdown(rac_dia: float, dias: int, feed_key: str,
                    fallback_usd_dia: float) -> tuple[float, float, float]:
    """
    (alim_usd_cab, kg_ms_total, precio_promedio_usd_kg_ms).

    Si la tabla de ingredientes está vacía, usa el fallback ALIM_DIA × días
    e infiere el precio promedio asumiendo consumo = rac_dia × días.
    """
    df = _read_feed_df(feed_key)
    name = df["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(df["%"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(df["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)

    if mask.any():
        kg_ms_total = 0.0
        alim_usd = 0.0
        for p, u in zip(pct[mask].values, usd[mask].values):
            kg_ms = rac_dia * (p / 100.0) * dias
            kg_ms_total += kg_ms
            alim_usd += kg_ms * u
        precio_avg = (alim_usd / kg_ms_total) if kg_ms_total > 0 else 0.0
        return alim_usd, kg_ms_total, precio_avg

    alim_usd = float(fallback_usd_dia) * float(dias)
    kg_ms_total = float(rac_dia) * float(dias)
    precio_avg = (alim_usd / kg_ms_total) if kg_ms_total > 0 else 0.0
    return alim_usd, kg_ms_total, precio_avg


# ── Lectura de parámetros base ───────────────────────────────────────────────

def _stage_inputs() -> dict:
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

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

    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    cab_in_cria    = n_t
    cab_in_recria  = surv(cab_in_cria,    a_mort)
    cab_in_eng_int = surv(cab_in_recria,  b_mort)
    cab_in_eng_exp = surv(cab_in_eng_int, c_mort)

    def gdp(kg_in: float, kg_out: float, dias: int) -> float:
        return (kg_out - kg_in) / dias if dias > 0 else 0.0

    return {
        "cria": dict(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            rac_dia=a_rac, feed_key=_FEED_KEYS["cria"], alim_dia_fb=a_alim_d,
            compra=pc_global * a_kg_in, san=a_san, mo_dia=a_mo_dia,
            com_pct=a_com_pct, pv=a_pv, fe=a_fe, fs=a_fs,
            cab_in=cab_in_cria, gdp_actual=gdp(a_kg_in, a_kg_out, a_dias),
        ),
        "recria": dict(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            rac_dia=b_rac, feed_key=_FEED_KEYS["recria"], alim_dia_fb=b_alim_d,
            compra=b_pc * b_kg_in, san=b_san, mo_dia=b_mo_dia,
            com_pct=b_com_pct, pv=b_pv, fe=b_fe, fs=b_fs,
            cab_in=cab_in_recria, gdp_actual=gdp(b_kg_in, b_kg_out, b_dias),
        ),
        "eng_int": dict(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            rac_dia=c_rac, feed_key=_FEED_KEYS["eng_int"], alim_dia_fb=c_alim_d,
            compra=c_pc * c_kg_in, san=c_san, mo_dia=c_mo_dia,
            com_pct=c_com_pct, pv=c_pv, fe=c_fe, fs=c_fs,
            cab_in=cab_in_eng_int, gdp_actual=gdp(c_kg_in, c_kg_out, c_dias),
        ),
        "eng_exp": dict(
            kg_in=e_kg_in, kg_out=e_kg_out, dias=e_dias, mort_pct=e_mort,
            rac_dia=e_rac, feed_key=_FEED_KEYS["eng_exp"], alim_dia_fb=e_alim_d,
            compra=e_pc * e_kg_in, san=e_san, mo_dia=e_mo_dia,
            com_pct=e_com_pct, pv=e_pv, fe=e_fe, fs=e_fs,
            cab_in=cab_in_eng_exp, gdp_actual=gdp(e_kg_in, e_kg_out, e_dias),
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

    Modelo económico (consistente con page_costos / page_margenes):
        ingreso_cab   = kg_out × pv
        com_cab       = (com_pct/100) × pv × kg_out + fe + fs
        base          = compra + alim + san + mo + com
        costo_cab     = base × (1 + m)
        margen_total  = cab_in × ((1 - m) × ingreso_cab − (1 + m) × base)

    Donde m = mort_pct / 100.
    """
    alim_actual, kg_ms_total, precio_alim_actual = _alim_breakdown(
        s["rac_dia"], s["dias"], s["feed_key"], s["alim_dia_fb"]
    )
    mo_cab    = s["mo_dia"] * s["dias"]
    com_cab   = (s["com_pct"] / 100.0) * s["pv"] * s["kg_out"] + s["fe"] + s["fs"]
    base      = s["compra"] + alim_actual + s["san"] + mo_cab + com_cab
    m         = s["mort_pct"] / 100.0
    one_minus_m = 1 - m
    one_plus_m  = 1 + m

    ingreso_cab   = s["kg_out"] * s["pv"]
    costo_cab     = base * one_plus_m
    margen_cab    = ingreso_cab - costo_cab
    cab_vend      = max(int(s["cab_in"] * one_minus_m), 0)
    ingreso_total = ingreso_cab * cab_vend
    costo_total   = costo_cab * s["cab_in"]
    margen_total  = ingreso_total - costo_total
    kg_vendidos   = cab_vend * s["kg_out"]

    kg_aumento = max(s["kg_out"] - s["kg_in"], 0.0)
    ca_actual = (kg_ms_total / kg_aumento) if kg_aumento > 0 else 0.0

    # ── Precio equilibrio (USD por kg vendido) ──
    if kg_vendidos > 0:
        precio_equilibrio = costo_total / kg_vendidos
    else:
        precio_equilibrio = float("nan")

    # ── Mortandad máxima tolerable: (1−m)×I = (1+m)×base ──
    if (ingreso_cab + base) > 0:
        m_max = (ingreso_cab - base) / (ingreso_cab + base)
        mort_max_pct = max(0.0, 100.0 * m_max)
    else:
        mort_max_pct = float("nan")

    # ── Multiplicador α de la componente alim para que margen=0 ──
    # (1−m)×I = (1+m)×(base − alim + α×alim)
    # α = ((1−m)/(1+m))×I/alim − (base − alim)/alim
    if alim_actual > 0 and one_plus_m > 0:
        objetivo = (one_minus_m / one_plus_m) * ingreso_cab
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
    # X × pv × ((1−m) − (1+m)×com_share) = (1+m) × K_const
    K_const = (s["compra"] + alim_actual + s["san"] + mo_cab
               + s["fe"] + s["fs"])
    com_share = s["com_pct"] / 100.0
    denom = s["pv"] * (one_minus_m - one_plus_m * com_share)
    if denom > 0 and s["dias"] > 0:
        X_min = one_plus_m * K_const / denom
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
    return {k: {**inputs[k], **_compute_breakeven(inputs[k])}
            for k in ["cria", "recria", "eng_int", "eng_exp"]}


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

    # Maíz / precio alim: headroom = (max / actual − 1) × 100
    pa_max, pa_act = s["precio_alim_max"], s["precio_alim_actual"]
    if pa_act > 0 and not _is_nan(pa_max):
        h = (pa_max / pa_act - 1.0) * 100.0
    else:
        h = None
    out["maiz_max"] = {**_sem_for(h, 50, 20),
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
    # Maíz / precio alim
    rows += _metric_row(
        "🌽", "Maíz máx. tolerable",
        _fmt(sems["maiz_max"]["value"], "usd_kg_ms"),
        _fmt(sems["maiz_max"]["ref"], "usd_kg_ms"),
        hr_pct(sems["maiz_max"]["headroom"]),
        sems["maiz_max"],
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
    keys = ["cria", "recria", "eng_int", "eng_exp"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            st.markdown(_stage_card_html(key, data[key]),
                        unsafe_allow_html=True)
            st.markdown("<div style='height:14px'></div>",
                        unsafe_allow_html=True)


# ── Tornado chart ────────────────────────────────────────────────────────────

# Variables a sensibilizar (delta_kind: 'rel' = porcentaje relativo, 'pp' = pp absolutos)
_TORNADO_VARS = [
    {"key": "precio_maiz",  "label": "Precio maíz",   "icon": "🌽",
     "delta": 0.20, "kind": "rel"},
    {"key": "precio_venta", "label": "Precio venta",  "icon": "💲",
     "delta": 0.20, "kind": "rel"},
    {"key": "gdp",          "label": "GDP",           "icon": "📈",
     "delta": 0.15, "kind": "rel"},
    {"key": "conversion",   "label": "Conversión",    "icon": "🔄",
     "delta": 0.15, "kind": "rel"},
    {"key": "mortandad",    "label": "Mortandad",     "icon": "⚠️",
     "delta": 5.0,  "kind": "pp"},
    {"key": "flete",        "label": "Flete",         "icon": "🚛",
     "delta": 0.20, "kind": "rel"},
    {"key": "tasa",         "label": "Tasa interés",  "icon": "🏦",
     "delta": 0.10, "kind": "rel"},
]

_METRIC_OPTIONS = {
    "margen_cab":  ("Margen bruto / cab", "USD/cab"),
    "roi_op_pct":  ("ROI operativo",      "%"),
    "usd_cab_dia": ("USD / cab / día",    "USD/cab/día"),
}


def _evaluate_with_overrides(s: dict, ov: dict) -> dict:
    """
    Recalcula métricas con un dict de overrides. Claves opcionales:
        precio_maiz_mult   (default 1.0)  — multiplica alim cab
        precio_venta_mult  (default 1.0)  — multiplica pv (afecta ingreso y comisión)
        gdp_mult           (default 1.0)  — escala kg_aumento
        conv_mult          (default 1.0)  — multiplica alim cab (separado de precio)
        mort_pp_delta      (default 0.0)  — suma puntos porcentuales a mort
        flete_mult         (default 1.0)  — multiplica fe + fs
        tasa_mult          (default 1.0)  — multiplica tasa de interés

    Para visualizar el efecto de la tasa de interés sobre el margen, esta
    página agrega un componente de costo financiero local
    `costo_fin = compra × tasa/100 × días/365` (sólo en este análisis;
    no afecta la lógica económica de page_costos / page_margenes).
    """
    pv          = s["pv"] * ov.get("precio_venta_mult", 1.0)
    # Cap mort en [0, 99] para evitar (1−m)=0 que vuelve cab_vend=0 y métricas degeneradas
    mort        = min(99.0,
                      max(0.0, s["mort_pct"] + ov.get("mort_pp_delta", 0.0)))
    kg_aumento  = max(s["kg_out"] - s["kg_in"], 0.0) * ov.get("gdp_mult", 1.0)
    kg_out      = s["kg_in"] + kg_aumento
    alim        = (s["alim_actual"]
                   * ov.get("precio_maiz_mult", 1.0)
                   * ov.get("conv_mult", 1.0))
    fe          = s["fe"] * ov.get("flete_mult", 1.0)
    fs          = s["fs"] * ov.get("flete_mult", 1.0)

    tasa_actual = _g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])
    tasa        = tasa_actual * ov.get("tasa_mult", 1.0)
    costo_fin   = (s["compra"] * (tasa / 100.0) * s["dias"] / 365.0
                   if s["dias"] > 0 else 0.0)

    mo_cab  = s["mo_dia"] * s["dias"]
    com_cab = (s["com_pct"] / 100.0) * pv * kg_out + fe + fs
    base    = (s["compra"] + alim + s["san"] + mo_cab + com_cab + costo_fin)
    m       = mort / 100.0

    ingreso_cab   = kg_out * pv
    costo_cab     = base * (1 + m)
    margen_cab    = ingreso_cab - costo_cab
    cab_vend      = max(int(s["cab_in"] * (1 - m)), 0)
    ingreso_total = ingreso_cab * cab_vend
    costo_total   = costo_cab * s["cab_in"]
    margen_total  = ingreso_total - costo_total

    roi_op_pct  = (margen_total / costo_total * 100.0) if costo_total > 0 else 0.0
    usd_cab_dia = margen_cab / s["dias"] if s["dias"] > 0 else 0.0

    return {
        "margen_cab":   margen_cab,
        "margen_total": margen_total,
        "roi_op_pct":   roi_op_pct,
        "usd_cab_dia":  usd_cab_dia,
        "mort_used":    mort,
    }


def _evaluate_metric(s: dict, override_key: str | None, sign: int) -> dict:
    """Wrapper para tornado: aplica UN override con un signo (+1 / −1 / 0)."""
    ov: dict = {}
    if override_key == "precio_maiz":
        ov["precio_maiz_mult"]  = 1.0 + sign * 0.20
    elif override_key == "precio_venta":
        ov["precio_venta_mult"] = 1.0 + sign * 0.20
    elif override_key == "gdp":
        ov["gdp_mult"]          = 1.0 + sign * 0.15
    elif override_key == "conversion":
        ov["conv_mult"]         = 1.0 + sign * 0.15
    elif override_key == "mortandad":
        ov["mort_pp_delta"]     = sign * 5.0
    elif override_key == "flete":
        ov["flete_mult"]        = 1.0 + sign * 0.20
    elif override_key == "tasa":
        ov["tasa_mult"]         = 1.0 + sign * 0.10
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
            "var_label":   f"{v['icon']}  {v['label']}  ({delta_label})",
            "low_metric":  low_metric,
            "high_metric": high_metric,
            "low_delta":   low_delta,
            "high_delta":  high_delta,
            "swing":       swing,
        })
    rows.sort(key=lambda r: r["swing"])  # asc → biggest at top en horizontal bar
    return rows, baseline


def _fmt_metric(v: float, unit: str) -> str:
    if _is_nan(v):
        return "N/A"
    if unit == "USD/cab" or unit == "USD/cab/día":
        return f"USD {v:+,.1f}"
    if unit == "%":
        return f"{v:+.2f} pp"
    return f"{v:+,.2f}"


def _tornado_chart(rows: list[dict], metric_label: str,
                   baseline: float, unit: str) -> go.Figure:
    """Tornado chart horizontal: variables ordenadas por swing total."""
    labels = [r["var_label"] for r in rows]

    pos_x = [max(r["low_delta"], r["high_delta"], 0.0) for r in rows]
    neg_x = [min(r["low_delta"], r["high_delta"], 0.0) for r in rows]

    pos_text = [_fmt_metric(x, unit) if abs(x) > 1e-6 else "" for x in pos_x]
    neg_text = [_fmt_metric(x, unit) if abs(x) > 1e-6 else "" for x in neg_x]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=pos_x, orientation="h",
        name="Impacto positivo",
        marker=dict(color="#34d399",
                    line=dict(color="white", width=1.2)),
        text=pos_text,
        textposition="outside",
        textfont=dict(size=10, color="#047857"),
        hovertemplate="<b>%{y}</b><br>Δ %{x:+,.2f} " + unit + "<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=labels, x=neg_x, orientation="h",
        name="Impacto negativo",
        marker=dict(color="#fb7185",
                    line=dict(color="white", width=1.2)),
        text=neg_text,
        textposition="outside",
        textfont=dict(size=10, color="#be123c"),
        hovertemplate="<b>%{y}</b><br>Δ %{x:+,.2f} " + unit + "<extra></extra>",
    ))

    if unit == "%":
        baseline_str = f"{baseline:+.1f} pp"
        x_tick_suffix = " pp"
    elif unit.startswith("USD"):
        baseline_str = f"USD {baseline:+,.1f}"
        x_tick_suffix = ""
    else:
        baseline_str = f"{baseline:+,.2f}"
        x_tick_suffix = ""

    # Línea vertical en 0 = baseline
    fig.add_vline(x=0, line_color="#0c1a2e", line_width=2)

    fig.update_layout(
        barmode="overlay",
        height=max(360, 60 + 50 * len(rows)),
        margin=dict(t=50, b=40, l=210, r=40),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        legend=dict(
            orientation="h", yanchor="top", y=1.10,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#475569"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title=dict(
                text=(f"Δ {metric_label} respecto baseline "
                      f"({baseline_str})"),
                font=dict(size=11, color="#475569"),
            ),
            gridcolor="#eef2f7", zeroline=False,
            tickformat=",.1f", ticksuffix=x_tick_suffix,
            tickfont=dict(size=10, color="#64748b"),
        ),
        yaxis=dict(
            tickfont=dict(size=11, color="#0c1a2e"),
            gridcolor="rgba(0,0,0,0)",
        ),
        bargap=0.32,
        hoverlabel=dict(bgcolor="white", bordercolor="#e4eaf4",
                        font=dict(size=12, color="#0c1a2e")),
    )
    return fig


def _top_drivers_html(rows: list[dict], unit: str) -> str:
    """Tarjetas con las top-3 variables más sensibles."""
    top3 = sorted(rows, key=lambda r: r["swing"], reverse=True)[:3]
    medals = ["🥇", "🥈", "🥉"]
    accent = ["#dc2626", "#d97706", "#65a30d"]
    cards = ""
    for i, r in enumerate(top3):
        c = accent[i]
        if unit.startswith("USD"):
            swing_str = f"USD {r['swing']:,.1f}"
        elif unit == "%":
            swing_str = f"{r['swing']:.2f} pp"
        else:
            swing_str = f"{r['swing']:,.2f}"
        cards += (
            f'<div style="flex:1;min-width:180px;background:white;'
            f'border:1px solid {c}33;border-left:4px solid {c};'
            f'border-radius:10px;padding:11px 14px;'
            f'box-shadow:0 1px 4px rgba(13,27,66,0.05);">'
            f'<div style="font-size:0.62rem;color:{c};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'display:flex;align-items:center;gap:5px;">'
            f'<span style="font-size:0.95rem;">{medals[i]}</span>'
            f'#{i+1} sensibilidad</div>'
            f'<div style="font-size:0.94rem;font-weight:800;color:#0c1a2e;'
            f'margin-top:3px;line-height:1.2;">{r["var_label"]}</div>'
            f'<div style="font-size:0.72rem;color:#475569;margin-top:3px;">'
            f'Swing total: <b style="color:{c};">{swing_str}</b></div>'
            f'</div>'
        )
    return (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;'
        f'margin:6px 0 14px 0;">{cards}</div>'
    )


def _tornado_section(data: dict) -> None:
    stage_options = ["cria", "recria", "eng_int", "eng_exp"]
    stage_titles = {k: f"{_SEG[k]['icon']} {_SEG[k]['title']}"
                    for k in stage_options}
    metric_keys = list(_METRIC_OPTIONS.keys())

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(
            '<p style="font-size:0.66rem;font-weight:700;color:#7a8fa6;'
            'text-transform:uppercase;letter-spacing:0.07em;'
            'margin:0 0 4px 0;">Etapa</p>',
            unsafe_allow_html=True,
        )
        stage = st.radio(
            "Etapa", stage_options,
            format_func=lambda k: stage_titles[k],
            horizontal=True, key="sens_tornado_stage",
            label_visibility="collapsed",
        )
    with c2:
        st.markdown(
            '<p style="font-size:0.66rem;font-weight:700;color:#7a8fa6;'
            'text-transform:uppercase;letter-spacing:0.07em;'
            'margin:0 0 4px 0;">Métrica de impacto</p>',
            unsafe_allow_html=True,
        )
        metric = st.radio(
            "Metrica", metric_keys,
            format_func=lambda k: _METRIC_OPTIONS[k][0],
            horizontal=True, key="sens_tornado_metric",
            label_visibility="collapsed",
        )

    s = data[stage]
    metric_label, unit = _METRIC_OPTIONS[metric]
    rows, baseline = _tornado_data(s, metric)

    st.markdown(_top_drivers_html(rows, unit), unsafe_allow_html=True)

    st.plotly_chart(
        _tornado_chart(rows, metric_label, baseline, unit),
        width="stretch",
        key="sens_tornado_chart",
    )

    st.caption(
        "Variables ordenadas por **swing total** (suma de impactos negativos "
        "y positivos). El baseline es la métrica actual con todos los "
        "parámetros en sus valores configurados. Para visibilidad de la tasa "
        "de interés se incluye un costo financiero local "
        "`compra × tasa/100 × días/365` que no afecta el cálculo de margen "
        "en otras páginas."
    )


# ── Simulación de escenarios ─────────────────────────────────────────────────

_SCENARIOS = [
    {
        "key": "optimista", "label": "Optimista", "icon": "🚀",
        "color": "#16a34a",
        "desc": "Precios venta +10%, alimento −10%, GDP +10%, "
                "conv. −5%, mortandad −1 pp",
        "overrides": {
            "precio_venta_mult": 1.10,
            "precio_maiz_mult":  0.90,
            "gdp_mult":          1.10,
            "conv_mult":         0.95,
            "mort_pp_delta":    -1.0,
        },
    },
    {
        "key": "base", "label": "Base", "icon": "🎯",
        "color": "#1565c0",
        "desc": "Parámetros actuales sin alterar",
        "overrides": {},
    },
    {
        "key": "malo", "label": "Malo", "icon": "📉",
        "color": "#d97706",
        "desc": "Precios venta −10%, alimento +10%, GDP −10%, "
                "conv. +10%, mortandad +2 pp",
        "overrides": {
            "precio_venta_mult": 0.90,
            "precio_maiz_mult":  1.10,
            "gdp_mult":          0.90,
            "conv_mult":         1.10,
            "mort_pp_delta":     2.0,
        },
    },
    {
        "key": "sequia", "label": "Sequía", "icon": "🌵",
        "color": "#b45309",
        "desc": "Maíz +20%, GDP −20%, conv. +15%, mortandad +1.5 pp "
                "(estrés climático)",
        "overrides": {
            "precio_maiz_mult": 1.20,
            "gdp_mult":         0.80,
            "conv_mult":        1.15,
            "mort_pp_delta":    1.5,
        },
    },
    {
        "key": "maiz_caro", "label": "Maíz caro", "icon": "🌽",
        "color": "#dc2626",
        "desc": "Maíz +40%, resto sin cambios (shock de insumos)",
        "overrides": {"precio_maiz_mult": 1.40},
    },
    {
        "key": "export_fuerte", "label": "Exportación fuerte", "icon": "🌐",
        "color": "#7c3aed",
        "desc": "Precio venta +20% (premium internacional, "
                "demanda exportadora)",
        "overrides": {"precio_venta_mult": 1.20},
    },
]


def _scenario_risk(metrics: dict) -> dict:
    """Indicador de riesgo derivado del ROI operativo."""
    roi = metrics["roi_op_pct"]
    if roi < 0:
        return {**_SEMAPHORE["rojo"],     "label": "Crítico"}
    if roi < 15.0:
        return {**_SEMAPHORE["amarillo"], "label": "Sensible"}
    return {**_SEMAPHORE["verde"], "label": "Robusto"}


def _evaluate_scenarios(data: dict) -> dict:
    """Para cada escenario evalúa las métricas en cada etapa."""
    out: dict = {}
    for sc in _SCENARIOS:
        stages: dict = {}
        for stage_key in ["cria", "recria", "eng_int", "eng_exp"]:
            metrics = _evaluate_with_overrides(data[stage_key],
                                               sc["overrides"])
            stages[stage_key] = {**metrics,
                                 "risk": _scenario_risk(metrics)}
        out[sc["key"]] = {"meta": sc, "stages": stages}
    return out


# ── Tabla ejecutiva: escenarios × etapas ─────────────────────────────────────

def _scenarios_summary_table_html(scen_data: dict) -> str:
    th_base = ('padding:11px 14px;font-size:0.66rem;font-weight:700;'
               'color:#7a8fa6;text-transform:uppercase;letter-spacing:0.08em;'
               'background:#f8fafd;border-bottom:1.5px solid #e4eaf4;')
    th_l = th_base + 'text-align:left;'
    th_c = th_base + 'text-align:center;'

    body = ""
    for i, sc in enumerate(_SCENARIOS):
        sd = scen_data[sc["key"]]
        bg_row = "#ffffff" if i % 2 == 0 else "#fbfcfe"

        scen_cell = (
            f'<td style="padding:14px 16px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;min-width:240px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div style="width:34px;height:34px;border-radius:8px;'
            f'background:{sc["color"]}1f;display:flex;align-items:center;'
            f'justify-content:center;font-size:1.05rem;flex-shrink:0;">'
            f'{sc["icon"]}</div>'
            f'<div>'
            f'<div style="font-size:0.86rem;font-weight:800;color:#0c1a2e;'
            f'line-height:1.15;">{sc["label"]}</div>'
            f'<div style="font-size:0.64rem;color:#94a3b8;font-weight:600;'
            f'margin-top:2px;line-height:1.3;max-width:280px;">'
            f'{sc["desc"]}</div>'
            f'</div></div></td>'
        )

        stage_cells = ""
        for stage_key in ["cria", "recria", "eng_int", "eng_exp"]:
            ms = sd["stages"][stage_key]
            risk = ms["risk"]
            margen = ms["margen_cab"]
            roi = ms["roi_op_pct"]
            margen_color = "#16a34a" if margen >= 0 else "#dc2626"
            sign = "+" if margen >= 0 else "−"

            stage_cells += (
                f'<td style="padding:14px 14px;background:{bg_row};'
                f'border-bottom:1px solid #f0f4fa;text-align:center;'
                f'vertical-align:middle;min-width:140px;">'
                f'<div style="font-size:0.92rem;font-weight:800;'
                f'color:{margen_color};line-height:1.1;'
                f'font-variant-numeric:tabular-nums;">'
                f'{sign}USD&nbsp;{abs(margen):,.0f}</div>'
                f'<div style="font-size:0.66rem;color:#64748b;font-weight:700;'
                f'margin-top:3px;font-variant-numeric:tabular-nums;">'
                f'ROI {roi:+.1f}%</div>'
                f'<div style="margin-top:5px;">'
                f'<span style="background:{risk["bg"]};'
                f'border:1px solid {risk["color"]}55;'
                f'color:{risk["color"]};font-size:0.62rem;font-weight:800;'
                f'padding:2px 8px;border-radius:10px;letter-spacing:0.04em;'
                f'white-space:nowrap;">● {risk["label"]}</span>'
                f'</div></td>'
            )

        body += f'<tr>{scen_cell}{stage_cells}</tr>'

    headers = ""
    for stage_key in ["cria", "recria", "eng_int", "eng_exp"]:
        meta = _SEG[stage_key]
        headers += f'<th style="{th_c}">{meta["icon"]} {meta["title"]}</th>'

    return (
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow-x:auto;'
        f'box-shadow:0 2px 10px rgba(13,27,66,0.06);">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:Inter,Arial,sans-serif;min-width:780px;">'
        f'<thead><tr>'
        f'<th style="{th_l}">Escenario</th>'
        f'{headers}'
        f'</tr></thead>'
        f'<tbody>{body}</tbody>'
        f'</table>'
        f'</div>'
    )


# ── Cards de escenario con tiles por etapa ───────────────────────────────────

def _scenario_card_html(sc: dict, stages_data: dict) -> str:
    color = sc["color"]

    tiles = ""
    for stage_key in ["cria", "recria", "eng_int", "eng_exp"]:
        meta = _SEG[stage_key]
        ms = stages_data[stage_key]
        risk = ms["risk"]
        margen = ms["margen_cab"]
        roi = ms["roi_op_pct"]
        usd_dia = ms["usd_cab_dia"]
        margen_color = "#16a34a" if margen >= 0 else "#dc2626"
        sign = "+" if margen >= 0 else "−"

        tiles += (
            f'<div style="background:white;border:1px solid {meta["color"]}28;'
            f'border-radius:10px;padding:10px 12px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:6px;">'
            f'<div style="font-size:0.64rem;color:{meta["color"]};'
            f'font-weight:800;text-transform:uppercase;letter-spacing:0.05em;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{meta["icon"]} {meta["title"]}</div>'
            f'<span style="background:{risk["bg"]};'
            f'border:1px solid {risk["color"]}55;color:{risk["color"]};'
            f'font-size:0.56rem;font-weight:800;'
            f'padding:2px 7px;border-radius:10px;letter-spacing:0.04em;'
            f'white-space:nowrap;flex-shrink:0;">● {risk["label"]}</span>'
            f'</div>'
            f'<div style="font-size:1.05rem;font-weight:800;'
            f'color:{margen_color};line-height:1.1;letter-spacing:-0.01em;'
            f'font-variant-numeric:tabular-nums;">'
            f'{sign}USD {abs(margen):,.1f}</div>'
            f'<div style="font-size:0.58rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-top:1px;">'
            f'Margen / cab</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:6px;margin-top:6px;border-top:1px solid #f1f5f9;'
            f'padding-top:6px;">'
            f'<div>'
            f'<div style="font-size:0.78rem;font-weight:800;color:#1e3a5f;'
            f'line-height:1;font-variant-numeric:tabular-nums;">'
            f'{roi:+.1f}%</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-top:1px;">'
            f'ROI op</div></div>'
            f'<div>'
            f'<div style="font-size:0.78rem;font-weight:800;color:#1e3a5f;'
            f'line-height:1;font-variant-numeric:tabular-nums;">'
            f'USD&nbsp;{usd_dia:.2f}</div>'
            f'<div style="font-size:0.56rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-top:1px;">'
            f'USD/cab/día</div></div>'
            f'</div></div>'
        )

    return (
        f'<div style="background:#f8fafd;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;">'
        f'<div style="background:linear-gradient(135deg,{color},{color}dd);'
        f'padding:13px 16px;color:white;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.25rem;">{sc["icon"]}</span>'
        f'<span style="font-size:0.95rem;font-weight:800;'
        f'letter-spacing:0.02em;text-transform:uppercase;">{sc["label"]}</span>'
        f'</div>'
        f'<div style="font-size:0.70rem;color:rgba(255,255,255,0.88);'
        f'font-weight:500;margin-top:4px;line-height:1.35;">{sc["desc"]}</div>'
        f'</div>'
        f'<div style="padding:12px;display:grid;grid-template-columns:1fr 1fr;'
        f'gap:8px;">{tiles}</div></div>'
    )


def _scenarios_section(data: dict) -> None:
    scen_data = _evaluate_scenarios(data)

    # 1. Tabla ejecutiva
    st.markdown(_scenarios_summary_table_html(scen_data),
                unsafe_allow_html=True)
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # 2. Cards 3×2
    cols = st.columns(3, gap="small")
    for i, sc in enumerate(_SCENARIOS):
        with cols[i % 3]:
            st.markdown(
                _scenario_card_html(sc, scen_data[sc["key"]]["stages"]),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:14px'></div>",
                        unsafe_allow_html=True)


# ── Interpretación estratégica del riesgo ───────────────────────────────────

_RISK_TITLES = {
    "cria":    "Cría",
    "recria":  "Recría",
    "eng_int": "Feedlot (Eng. interno)",
    "eng_exp": "Exportación",
}

# Pesos de los componentes del score compuesto (deben sumar 1.0)
_RISK_WEIGHTS = {
    "maiz":        0.20,
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
      score_maiz        = swing(precio maíz) / |baseline| × 50, cap 100
      score_volatilidad = Σswings / |baseline| × 30, cap 100
      score_duracion    = días / 7.30 (730 d = 100), cap 100
      score_capital     = capital_etapa / max(capital peers) × 100
      score_mortandad   = mort_pct × 10, cap 100
    """
    denom = _safe_denom(baseline, s["ingreso_cab"])

    # Sensibilidad al maíz
    maiz_row = next((r for r in tornado_rows if "Precio maíz" in r["var_label"]),
                    None)
    if maiz_row is not None:
        score_maiz = min(100.0, (maiz_row["swing"] / denom) * 50.0)
    else:
        score_maiz = 0.0

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
        score_maiz        * _RISK_WEIGHTS["maiz"]
        + score_volatilidad * _RISK_WEIGHTS["volatilidad"]
        + score_duracion    * _RISK_WEIGHTS["duracion"]
        + score_capital     * _RISK_WEIGHTS["capital"]
        + score_mortandad   * _RISK_WEIGHTS["mortandad"]
    )
    robustness = max(0.0, min(100.0, 100.0 - composite))

    return {
        "score_maiz":        score_maiz,
        "score_volatilidad": score_volatilidad,
        "score_duracion":    score_duracion,
        "score_capital":     score_capital,
        "score_mortandad":   score_mortandad,
        "risk_composite":    composite,
        "robustness":        robustness,
        "total_swing":       total_swing,
        "maiz_swing":        maiz_row["swing"] if maiz_row else 0.0,
    }


def _build_risk_return(data: dict) -> list[dict]:
    """Para cada etapa: margen + componentes de riesgo + score compuesto."""
    capital_max = max((data[k]["costo_total"]
                       for k in ["cria", "recria", "eng_int", "eng_exp"]),
                      default=1.0)

    rows = []
    for k in ["cria", "recria", "eng_int", "eng_exp"]:
        s = data[k]
        baseline = s["margen_cab"]
        tornado_rows, _ = _tornado_data(s, "margen_cab")
        comp = _compute_risk_components(s, baseline, tornado_rows, capital_max)
        roi_op = ((s["margen_total"] / s["costo_total"] * 100.0)
                  if s["costo_total"] > 0 else 0.0)
        rows.append({
            "key": k, "title": _RISK_TITLES[k], "meta": _SEG[k],
            "margen_cab":   baseline,
            "margen_total": s["margen_total"],
            "roi_op_pct":   roi_op,
            "dias":         s["dias"],
            "mort_pct":     s["mort_pct"],
            "capital":      s["costo_total"],
            **comp,
        })
    return rows


# ── Alertas estratégicas ─────────────────────────────────────────────────────

def _generate_alerts(rows: list[dict]) -> list[dict]:
    """Reglas para generar alertas automáticas."""
    alerts = []

    # 1. Margen negativo → crítico
    losers = [r for r in rows if r["margen_cab"] <= 0]
    for r in losers:
        alerts.append({
            "icon": "🚨", "level": "critical",
            "msg": f"<b>{r['title']}</b> opera con margen negativo en escenario base.",
        })

    # 2. Más sensible al maíz
    most_maiz = max(rows, key=lambda r: r["score_maiz"])
    if most_maiz["score_maiz"] >= 50.0:
        alerts.append({
            "icon": "🌽", "level": "warning",
            "msg": (f"<b>{most_maiz['title']}</b> es muy sensible al precio "
                    f"del maíz (score {most_maiz['score_maiz']:.0f}/100). "
                    f"Coberturas o contratos a precio fijo recomendados."),
        })

    # 3. Más volátil
    most_volatile = max(rows, key=lambda r: r["score_volatilidad"])
    if most_volatile["score_volatilidad"] >= 60.0:
        alerts.append({
            "icon": "📊", "level": "warning",
            "msg": (f"<b>{most_volatile['title']}</b> presenta alta "
                    f"volatilidad de margen "
                    f"(score {most_volatile['score_volatilidad']:.0f}/100). "
                    f"Resultados muy expuestos a cambios de precios."),
        })

    # 4. Mayor capital inmovilizado
    highest_cap = max(rows, key=lambda r: r["score_capital"])
    if highest_cap["score_capital"] >= 70.0:
        alerts.append({
            "icon": "🏦", "level": "info",
            "msg": (f"<b>{highest_cap['title']}</b> requiere la mayor "
                    f"inversión de capital "
                    f"(USD {highest_cap['capital']:,.0f}). Considerar "
                    f"costo de oportunidad y liquidez."),
        })

    # 5. Ciclo largo
    longest = max(rows, key=lambda r: r["score_duracion"])
    if longest["score_duracion"] >= 50.0:
        alerts.append({
            "icon": "⏳", "level": "warning",
            "msg": (f"<b>{longest['title']}</b> tiene ciclo largo "
                    f"({longest['dias']} días). Requiere alta eficiencia "
                    f"operativa para amortizar capital."),
        })

    # 6. Mortandad alta
    highest_mort = max(rows, key=lambda r: r["mort_pct"])
    if highest_mort["mort_pct"] >= 4.0:
        alerts.append({
            "icon": "⚠", "level": "warning",
            "msg": (f"<b>{highest_mort['title']}</b> tiene mortandad elevada "
                    f"({highest_mort['mort_pct']:.1f}%). Reforzar sanidad "
                    f"y manejo."),
        })

    # 7. Más estable (positivo)
    most_robust = max(rows, key=lambda r: r["robustness"])
    alerts.append({
        "icon": "🛡", "level": "good",
        "msg": (f"<b>{most_robust['title']}</b> es la opción con mejor "
                f"estabilidad económica "
                f"(robustez {most_robust['robustness']:.0f}/100)."),
    })

    # 8. Mayor margen (positivo)
    best_margin = max(rows, key=lambda r: r["margen_cab"])
    if best_margin["key"] != most_robust["key"]:
        alerts.append({
            "icon": "🏆", "level": "good",
            "msg": (f"<b>{best_margin['title']}</b> ofrece el mayor margen "
                    f"unitario (USD {best_margin['margen_cab']:+,.0f}/cab)."),
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
            f'margin-top:2px;">ROI {r["roi_op_pct"]:+.1f}% · '
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


# ── Card de desglose por etapa con sub-scores ────────────────────────────────

def _risk_breakdown_card_html(r: dict) -> str:
    meta = r["meta"]
    color = meta["color"]

    sub = [
        ("🌽", "Sensibilidad maíz",   r["score_maiz"]),
        ("📊", "Volatilidad margen",  r["score_volatilidad"]),
        ("⏳", "Duración ciclo",      r["score_duracion"]),
        ("🏦", "Capital inmovilizado", r["score_capital"]),
        ("⚠", "Mortandad",            r["score_mortandad"]),
    ]

    bars = ""
    for icon, lbl, score in sub:
        bar_color, _ = _risk_color(score)
        bars += (
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;font-size:0.72rem;margin-bottom:3px;">'
            f'<span style="color:#475569;font-weight:600;">{icon} {lbl}</span>'
            f'<span style="color:{bar_color};font-weight:800;'
            f'font-variant-numeric:tabular-nums;">{score:.0f}/100</span>'
            f'</div>'
            f'<div style="background:#eef2f7;border-radius:4px;height:7px;'
            f'overflow:hidden;">'
            f'<div style="background:{bar_color};height:100%;'
            f'width:{min(100, score):.1f}%;border-radius:4px;"></div>'
            f'</div></div>'
        )

    rb_color, _, rb_label = _robust_color(r["robustness"])
    return (
        f'<div style="background:#f8fafd;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;">'
        f'<div style="background:linear-gradient(135deg,{color},{color}dd);'
        f'padding:13px 16px;color:white;display:flex;'
        f'justify-content:space-between;align-items:center;gap:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.15rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.95rem;font-weight:700;">{r["title"]}</span>'
        f'</div>'
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'Robustez {r["robustness"]:.0f}/100 · {rb_label}</span>'
        f'</div>'
        f'<div style="padding:14px 16px 16px;">{bars}</div></div>'
    )


def _strategic_risk_section(data: dict) -> None:
    rows = _build_risk_return(data)

    # 1. Matriz risk-return
    st.markdown(_matrix_table_html(rows), unsafe_allow_html=True)

    # 2. Alertas estratégicas
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.78rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:0 0 0.6rem 0;">Alertas estratégicas</p>',
        unsafe_allow_html=True,
    )
    alerts = _generate_alerts(rows)
    st.markdown(_alerts_html(alerts), unsafe_allow_html=True)

    # 3. Desglose de riesgo por etapa
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.78rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:1rem 0 0.6rem 0;">Desglose del score de riesgo por etapa</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2, gap="small")
    for i, r in enumerate(rows):
        with cols[i % 2]:
            st.markdown(_risk_breakdown_card_html(r),
                        unsafe_allow_html=True)
            st.markdown("<div style='height:14px'></div>",
                        unsafe_allow_html=True)


# ── Entry point ──────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Sensibilidad y Riesgo",
        "Robustez y fragilidad económica del negocio: límites tolerables "
        "(margen=0) de precios, productividad y mortalidad por etapa. "
        "Semáforo verde/amarillo/rojo para lectura inmediata.",
    )

    data = _build_sensibilidad()

    section("Robustez por etapa")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 14px 0;">'
        '<b>Verde</b> = robusto · <b>Amarillo</b> = sensible · '
        '<b>Rojo</b> = crítico. El "margen" de cada métrica indica el '
        'cushion antes de llegar al punto de equilibrio.'
        '</p>',
        unsafe_allow_html=True,
    )
    _stage_grid(data)

    st.divider()

    # ── Tornado chart ────────────────────────────────────────────────────
    section("Sensibilidad económica — tornado chart")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 12px 0;">'
        'Variación automática de cada parámetro y su impacto sobre el '
        'negocio. Las variables más arriba en el gráfico son las que más '
        'mueven la métrica seleccionada (mayor sensibilidad).'
        '</p>',
        unsafe_allow_html=True,
    )
    _tornado_section(data)

    st.divider()

    # ── Simulación de escenarios ─────────────────────────────────────────
    section("Simulación de escenarios")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 12px 0;">'
        '6 escenarios económicos predefinidos que modifican automáticamente '
        '<b>precios, alimento, GDP, conversión y mortandad</b>. Tabla '
        'ejecutiva con margen, ROI y semáforo de riesgo por etapa, '
        'seguida de cards de detalle.'
        '</p>',
        unsafe_allow_html=True,
    )
    _scenarios_section(data)

    st.divider()

    # ── Interpretación estratégica del riesgo ────────────────────────────
    section("Interpretación estratégica del riesgo")
    st.markdown(
        '<p style="font-size:0.86rem;color:#475569;margin:-4px 0 12px 0;">'
        'Matriz <b>Modelo × Margen × Riesgo</b> con score compuesto 0–100 '
        'derivado automáticamente de sensibilidad al maíz, volatilidad de '
        'margen, duración del ciclo, capital inmovilizado y mortandad. '
        'Alertas estratégicas auto-generadas y desglose del score por etapa.'
        '</p>',
        unsafe_allow_html=True,
    )
    _strategic_risk_section(data)
