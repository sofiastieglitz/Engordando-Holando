"""
Margen Bruto — Visualización de la creación de valor económico
por las 3 etapas productivas (Cría · Recría · Engorde).

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
import modules.state.stages as S
import modules.state.derived as D
from modules.state.defaults import DEFAULTS
from modules.state.persist import get_editor_state, read
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

_FEED_KEYS = {
    "cria":    "feed_table_cria_de",
    "recria":  "feed_table_recria_de",
    "eng_int": "feed_table_eng_int_de",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _g(key: str, default: float) -> float:
    """Lectura robusta: shadow > widget-key > default."""
    return float(read(key, default))


def _read_feed_df(editor_key: str) -> pd.DataFrame:
    """Lee la tabla de ración vía `get_editor_state` (widget→shadow)."""
    base = pd.DataFrame({
        "Ingrediente": [""] * 10,
        "%":           [0.0] * 10,
        "USD/kg MS":   [0.0] * 10,
    })
    val = get_editor_state(editor_key)
    if val is None:
        return base
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


def _alim_usd_cab(kg_in: float, kg_out: float, ca: float,
                  feed_key: str) -> float:
    """USD/cab — modelo bioeconómico puro.
    consumo_MS = (kg_out − kg_in) × CA   ;   costo = consumo_MS × precio_pond
    """
    df = _read_feed_df(feed_key)
    name = df["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(df["%"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(df["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)

    consumo_ms = max(kg_out - kg_in, 0.0) * max(ca, 0.0)
    if not mask.any() or consumo_ms <= 0:
        return 0.0
    pcts = pct[mask].values
    usds = usd[mask].values
    total_pct = float(pcts.sum())
    if total_pct <= 0:
        return 0.0
    precio_pond = float((pcts * usds).sum() / total_pct)
    return float(consumo_ms * precio_pond)


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
        compra, alim, sanidad, op, estr, com,
        financiero                                (USD/cab — buckets de costo)
        mortandad_cab, mortandad_total            (USD — ingreso perdido)
        costo_cab, costo_total                    (USD — sin mortandad,
                                                  ya implícita en cab_vend)
        margen_bruto_cab, margen_bruto_total      (USD)
        margen_kg                                 (USD/kg producido)
        usd_cab_dia                               (USD/cab/día)
        retorno_incremental                       (USD/cab vs etapa previa)
        kg_prod_total                             (kg producidos)
    """
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

    # ── Lecturas ──────────────────────────────────────────────────────────
    a_kg_in   = S.kg_in_for("cria")
    a_kg_out  = S.kg_out_for("cria")
    a_dias    = D.dias_for("cria")
    a_mort    = _g(K.A_MORTALIDAD,        DEFAULTS["d_mortalidad"])
    a_san     = _g(K.A_SANIDAD,           DEFAULTS["d_sanidad"])
    a_mo_mes  = _g(K.A_MO_MES,            DEFAULTS["d_mo_mes"])
    a_ca      = _g(K.A_CA,                DEFAULTS["a_ca"])
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
    b_ca      = _g(K.B_CA,                DEFAULTS["r_ca"])
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
    c_ca      = _g(K.C_CA,                DEFAULTS["t_ca"])
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
    tasa_pct    = _g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])

    # ── Cabezas en cascada (sólo dentro del slice activo) ─────────────────
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

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

    # ── Operación pura USD/cab (sólo MO + combustible + servicios) ────────
    def op_cab(mo_mes: float, comb_mes: float, serv_mes: float,
               dias: int, cab_in: int) -> float:
        op_total_ciclo = (mo_mes + comb_mes + serv_mes) / 30.0 * dias
        return (op_total_ciclo / cab_in) if cab_in > 0 else 0.0

    # ── Estructura USD/cab (amortización proporcional + mantenimiento) ────
    def estructura_cab(asig_pct: float, amort_anos: float, mant_anio: float,
                       dias: int, cab_in: int) -> float:
        if cab_in <= 0:
            return 0.0
        adjudicado = valor_total * max(asig_pct, 0.0) / 100.0
        amort_anual = (adjudicado / amort_anos) if amort_anos > 0 else 0.0
        amort_ciclo = amort_anual * dias / 365.0
        mant_ciclo  = max(mant_anio, 0.0) * dias / 365.0
        return (amort_ciclo + mant_ciclo) / cab_in

    def block(
        kg_in: float, kg_out: float, dias: int, mort_pct: float,
        cab_in: int, precio_venta: float,
        compra: float, alim: float, sanidad: float,
        op: float, estr: float, com: float,
        active: bool,
    ) -> dict:
        cab_vend = surv(cab_in, mort_pct)

        # Costos directos por cabeza ingresada (alineado con page_costos.py)
        capital    = compra + alim + sanidad + op + estr + com
        financiero = capital * (tasa_pct / 100.0) * dias / 365.0
        # No se incluye mortandad como sobrecosto: ya está implícita en la
        # diferencia entre cab_in (incurre el costo) y cab_vend (genera ingreso).
        costo_cab   = capital + financiero
        costo_total = costo_cab * cab_in

        # Ingresos (alineado con page_ingresos.py)
        ingreso_cab   = kg_out * precio_venta
        ingreso_total = ingreso_cab * cab_vend

        # Mortandad como ingreso perdido (sólo display / waterfall)
        mortandad_cab = (mort_pct / 100.0) * kg_out * precio_venta
        mortandad_total = mortandad_cab * cab_in

        # Margen bruto: cab_vend × ingreso_cab − cab_in × costo_cab
        margen_bruto_total = ingreso_total - costo_total
        margen_bruto_cab = (margen_bruto_total / cab_in
                            if cab_in > 0 else 0.0)

        # kg producidos: sólo las cabezas vivas a venta producen kg vendibles
        kg_prod_total = max(kg_out - kg_in, 0.0) * cab_vend

        margen_kg = (margen_bruto_total / kg_prod_total
                     if kg_prod_total > 0 else 0.0)
        usd_cab_dia = margen_bruto_cab / dias if dias > 0 else 0.0

        return {
            "kg_in": kg_in, "kg_out": kg_out, "dias": dias,
            "mort_pct": mort_pct,
            "cab_in": cab_in, "cab_vend": cab_vend,
            "precio_venta": precio_venta,
            "ingreso_cab": ingreso_cab, "ingreso_total": ingreso_total,
            "compra": compra, "alim": alim, "sanidad": sanidad,
            "op": op, "estr": estr, "com": com,
            "financiero": financiero,
            "mortandad_cab": mortandad_cab,
            "mortandad_total": mortandad_total,
            "costo_cab": costo_cab, "costo_total": costo_total,
            "margen_bruto_cab": margen_bruto_cab,
            "margen_bruto_total": margen_bruto_total,
            "margen_kg": margen_kg,
            "usd_cab_dia": usd_cab_dia,
            "kg_prod_total": kg_prod_total,
            "active": active,
        }

    data = {
        "cria": block(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            cab_in=cab_in_cria, precio_venta=a_pv,
            compra  = pc_global * a_kg_in,
            alim    = _alim_usd_cab(a_kg_in, a_kg_out, a_ca, _FEED_KEYS["cria"]),
            sanidad = a_san,
            op      = op_cab(a_mo_mes, a_combust, a_servic, a_dias, cab_in_cria),
            estr    = estructura_cab(a_asig, a_amanos, a_mant, a_dias, cab_in_cria),
            com     = (a_com_pct / 100.0) * a_pv * a_kg_out + a_fe + a_fs,
            active  = S.is_active("cria"),
        ),
        "recria": block(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            cab_in=cab_in_recria, precio_venta=b_pv,
            compra  = b_pc * b_kg_in,
            alim    = _alim_usd_cab(b_kg_in, b_kg_out, b_ca, _FEED_KEYS["recria"]),
            sanidad = b_san,
            op      = op_cab(b_mo_mes, b_combust, b_servic, b_dias, cab_in_recria),
            estr    = estructura_cab(b_asig, b_amanos, b_mant, b_dias, cab_in_recria),
            com     = (b_com_pct / 100.0) * b_pv * b_kg_out + b_fe + b_fs,
            active  = S.is_active("recria"),
        ),
        "eng_int": block(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            cab_in=cab_in_eng_int, precio_venta=c_pv,
            compra  = c_pc * c_kg_in,
            alim    = _alim_usd_cab(c_kg_in, c_kg_out, c_ca, _FEED_KEYS["eng_int"]),
            sanidad = c_san,
            op      = op_cab(c_mo_mes, c_combust, c_servic, c_dias, cab_in_eng_int),
            estr    = estructura_cab(c_asig, c_amanos, c_mant, c_dias, cab_in_eng_int),
            com     = (c_com_pct / 100.0) * c_pv * c_kg_out + c_fe + c_fs,
            active  = S.is_active("eng_int"),
        ),
    }

    # ── Retorno incremental: sólo entre etapas ACTIVAS consecutivas ───────
    prev = None
    for key in S.ALL_STAGES:
        if not data[key]["active"]:
            data[key]["retorno_incremental"] = 0.0
            continue
        actual = data[key]["margen_bruto_cab"]
        data[key]["retorno_incremental"] = (actual - prev
                                            if prev is not None else 0.0)
        prev = actual

    return data


# ── 1. Resumen superior — KPIs comparativas ──────────────────────────────────

def _summary_kpis(data: dict) -> None:
    cols = st.columns(3, gap="small")
    active_list = S.active_stages()
    first_active = active_list[0] if active_list else None
    for col, key in zip(cols, ["cria", "recria", "eng_int"]):
        meta = _SEG[key]
        s = data[key]
        is_active = s.get("active", True)

        sign = "+" if s["margen_bruto_cab"] >= 0 else "−"
        margin_color = "#16a34a" if s["margen_bruto_cab"] >= 0 else "#dc2626"
        ret_inc = s["retorno_incremental"]
        if not is_active:
            ret_html = (
                '<span style="color:#94a3b8;font-size:0.65rem;'
                'font-weight:600;">—</span>'
            )
        elif key == first_active:
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

        opacity = "1" if is_active else "0.42"
        header_bg = (f"linear-gradient(135deg,{meta['color']},{meta['color']}dd)"
                     if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")
        right_chip = (
            '' if is_active else
            '<span style="background:rgba(255,255,255,0.22);border-radius:14px;'
            'padding:2px 8px;font-size:0.58rem;font-weight:700;'
            'margin-left:auto;">INACTIVA</span>'
        )

        # HTML concatenado (sin indentación interna): Markdown trata 4+
        # espacios al inicio de línea como bloque de código.
        card_html = (
            f'<div style="background:#ffffff;border:1px solid {meta["border"]};'
            f'border-radius:14px;padding:0;overflow:hidden;'
            f'box-shadow:0 1px 6px rgba(13,27,66,0.06);height:100%;'
            f'opacity:{opacity};">'
            f'<div style="background:{header_bg};padding:10px 16px;color:white;'
            f'display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
            f'<span style="font-size:0.86rem;font-weight:700;">{meta["title"]}</span>'
            f'{right_chip}'
            f'</div>'
            f'<div style="padding:14px 16px 12px;">'
            f'<div style="font-size:0.62rem;font-weight:700;color:#7a8fa6;'
            f'text-transform:uppercase;letter-spacing:0.07em;">'
            f'Margen bruto / cab</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:{margin_color};'
            f'line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">'
            f'{sign}USD&nbsp;{abs(s["margen_bruto_cab"]):,.1f}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;'
            f'gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["margen_bruto_total"]:,.0f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Margen Total</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["margen_kg"]:.2f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Margen / kg</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["usd_cab_dia"]:.2f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">USD/cab/día</div>'
            f'</div>'
            f'</div>'
            f'<div style="margin-top:10px;padding-top:8px;'
            f'border-top:1px solid #f0f4fa;text-align:center;">'
            f'<span style="font-size:0.62rem;color:#94a3b8;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.06em;">'
            f'Retorno incremental</span><br>'
            f'{ret_html}'
            f'</div>'
            f'</div></div>'
        )
        col.markdown(card_html, unsafe_allow_html=True)


# ── Gráfico comparativo: margen / cab y margen total ─────────────────────────

def _bars_two_panels(data: dict) -> go.Figure:
    stages = S.active_stages()
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
    bruto para las etapas activas (USD totales del sistema).

    Diseño SaaS/agtech: paleta suave, etiquetas USD destacadas, margen en
    color de la etapa cuando es positivo y rojo cuando es negativo.
    Anotación con USD/cab/día bajo cada grupo para lectura rápida.
    """
    stages = S.active_stages()
    x_labels = [f"{_SEG[k]['icon']}  {_SEG[k]['title']}" for k in stages]

    ingresos = [data[k]["ingreso_total"]      for k in stages]
    costos   = [data[k]["costo_total"]        for k in stages]
    margenes = [data[k]["margen_bruto_total"] for k in stages]

    fig = go.Figure()

    # Ingresos — emerald sólido (paleta corporate, alineada con Alimentación
    # de la slide Costos)
    fig.add_trace(go.Bar(
        name="Ingresos",
        x=x_labels, y=ingresos,
        marker=dict(color="#10b981",
                    line=dict(color="white", width=1.4)),
        text=[f"USD {v:,.0f}" for v in ingresos],
        textposition="outside",
        textfont=dict(size=10, color="#047857"),
        hovertemplate="<b>Ingresos</b><br>%{x}<br>"
                      "USD %{y:,.0f}<extra></extra>",
        offsetgroup="ing",
    ))

    # Costos — coral coherente con Mortandad de Costos
    fig.add_trace(go.Bar(
        name="Costos",
        x=x_labels, y=costos,
        marker=dict(color="#f87171",
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

    # Anotaciones bajo el eje X: USD/cab/día por etapa
    for i, k in enumerate(stages):
        ucd = data[k]["usd_cab_dia"]
        ucd_color = "#16a34a" if ucd >= 0 else "#dc2626"
        fig.add_annotation(
            x=x_labels[i], y=-0.16, xref="x", yref="paper",
            text=(f"<span style='color:#94a3b8;font-size:9px;'>USD/cab/día</span>"
                  f"<br><b style='color:{ucd_color};font-size:11px;'>"
                  f"USD {ucd:.2f}</b>"),
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

_TRANSITIONS_ALL = [
    ("cria",    "recria",  "🌱 → 🔵", "Cría → Recría"),
    ("recria",  "eng_int", "🔵 → 🟢", "Recría → Engorde"),
]


def _active_transitions() -> list[tuple[str, str, str, str]]:
    """Sólo transiciones entre etapas ACTIVAS y consecutivas en el flujo."""
    active = S.active_stages()
    if len(active) < 2:
        return []
    transitions = []
    for prev_key, next_key, arrow, label in _TRANSITIONS_ALL:
        if prev_key in active and next_key in active:
            # Verificar que sean consecutivas en el slice activo
            if active.index(next_key) - active.index(prev_key) == 1:
                transitions.append((prev_key, next_key, arrow, label))
    return transitions


def _value_added_transitions(data: dict) -> list[dict]:
    """Calcula valor agregado por transición consecutiva entre etapas activas."""
    rows: list[dict] = []
    for prev_key, next_key, arrow, label in _active_transitions():
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
    Waterfall del margen bruto/cab a lo largo del slice activo:
        primera etapa activa (base) → +Δ por cada transición → TOTAL.
    """
    active = S.active_stages()
    if not active:
        return go.Figure()  # caller maneja vacío

    base_key = active[0]
    last_key = active[-1]
    margen_base  = data[base_key]["margen_bruto_cab"]
    margen_final = data[last_key]["margen_bruto_cab"]

    base_meta = _SEG[base_key]
    x_labels = [f"{base_meta['icon']} {base_meta['title']}<br>"
                "<span style='color:#94a3b8;font-size:9px;'>base</span>"]
    measure  = ["absolute"]
    y_vals   = [margen_base]
    text     = [f"<b>USD {margen_base:,.1f}</b>"]

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
        increasing={"marker": {"color": "#10b981",
                                "line": {"color": "white", "width": 1.5}}},
        decreasing={"marker": {"color": "#f87171",
                                "line": {"color": "white", "width": 1.5}}},
        totals={"marker": {"color": "#6366f1",
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
    active = S.active_stages()
    if len(active) < 2:
        st.info(
            "📌 Hace falta al menos 2 etapas activas para evaluar valor "
            "agregado entre transiciones. Activá otra etapa en Parámetros.",
            icon="ℹ️",
        )
        return

    transitions = _value_added_transitions(data)

    st.plotly_chart(
        _waterfall_value_chart(data, transitions),
        width="stretch",
        key="margen_value_waterfall",
    )

    if transitions:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        cols = st.columns(max(len(transitions), 1), gap="small")
        for col, t in zip(cols, transitions):
            with col:
                st.markdown(_transition_card_html(t), unsafe_allow_html=True)


# ── Matriz estratégica comparativa ───────────────────────────────────────────

_MATRIX_TITLES = {
    "cria":    "Cría",
    "recria":  "Recría",
    "eng_int": "Engorde",
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

    Sólo evalúa etapas ACTIVAS (las inactivas no participan del ranking).
    """
    stages = S.active_stages()

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
        ("👥", "Cabezas vendidas",    f"{s['cab_vend']:,}",            "#0c1a2e"),
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
    keys = ["cria", "recria", "eng_int"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            is_active = data[key].get("active", True)
            opacity = "1" if is_active else "0.42"
            st.markdown(
                f'<div style="opacity:{opacity};">{_stage_card_html(key, data[key])}</div>',
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
        'El USD/cab/día de cada etapa figura debajo del grupo.'
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
