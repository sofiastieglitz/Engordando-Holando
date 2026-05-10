"""
Costos — Visualización económica de los costos del sistema ganadero
por las 3 etapas productivas (Cría · Recría · Engorde).

Lee parámetros directamente desde session_state (mismas claves que usa
page_parametros.py y page_modelo_productivo.py). No modifica navegación
ni la lógica de parámetros existente; mantiene la firma render(params, comp)
por compatibilidad con el router de app.py.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import modules.state.keys as K
import modules.state.stages as S
from modules.state.defaults import DEFAULTS
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

# Paleta suave SaaS/agtech para el desglose de conceptos.
# Orden: Compra → Alimentación → Sanidad → Operación → Estructura →
#        Comercialización → Financieros → Mortandad
_CONCEPT_COLORS: dict[str, str] = {
    "Compra":           "#64748b",  # slate
    "Alimentación":     "#10b981",  # emerald
    "Sanidad":          "#f59e0b",  # amber
    "Operación":        "#a78bfa",  # soft purple
    "Estructura":       "#fb923c",  # orange
    "Comercialización": "#22d3ee",  # cyan
    "Financieros":      "#6366f1",  # indigo
    "Mortandad":        "#f87171",  # soft red
}

_CONCEPT_ICONS: dict[str, str] = {
    "Compra":           "🛒",
    "Alimentación":     "🌾",
    "Sanidad":          "💉",
    "Operación":        "👷",
    "Estructura":       "🏗",
    "Comercialización": "🚛",
    "Financieros":      "🏦",
    "Mortandad":        "⚠️",
}

_CONCEPTS = list(_CONCEPT_COLORS.keys())


# ── Helpers de lectura ───────────────────────────────────────────────────────

def _g(key: str, default: float) -> float:
    return float(st.session_state.get(key, default))


def _read_feed_df(editor_key: str) -> pd.DataFrame:
    """Reconstruye el DataFrame de la tabla de alimentación desde session_state.
    Misma lógica que page_modelo_productivo._read_feed_df()."""
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


def _alim_usd_cab(kg_in: float, kg_out: float, ca: float,
                  feed_key: str) -> float:
    """USD/cab de alimentación — modelo bioeconómico puro.

    consumo_MS = max(kg_out − kg_in, 0) × CA
    precio_pond = Σ(% × USD/kg MS) / Σ %
    costo_cab  = consumo_MS × precio_pond

    Si la tabla está vacía o no hay kg producidos, devuelve 0.
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


# ── Modelo de costos por etapa ───────────────────────────────────────────────

def _build_costos() -> dict:
    """Calcula el desglose de costos por las 3 etapas productivas.

    Modelo bioeconómico modular: respeta etapas activas (S.active_stages)
    y encadenamiento de kg (S.kg_in_for / kg_out_for).

    Categorías por etapa (USD/cab):
        compra      = pc × kg_in
        alim        = (kg_out − kg_in) × CA × precio_pond_ration
        sanidad     = K.*_SANIDAD
        op          = (mo_mes + comb_mes + serv_mes) / 30 × días / cabezas
        estr        = (infra × asig%/100 / años + mant_año) × días/365 / cabezas
        com         = comisión×pv×kg_out + flete_entrada + flete_salida
        financiero  = (compra+alim+san+op+estr+com) × tasa/100 × días/365
        mortandad   = mort/100 × kg_out × pv      (ingreso perdido por cab muerta)

    Total etapa:
        total_cab   = compra + alim + san + op + estr + com + financiero + mortandad
        total_usd   = total_cab × cab_in
    """
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])
    tasa_pct  = _g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])

    # ── Lecturas por etapa ────────────────────────────────────────────────
    # kg_in respeta lógica modular (S.kg_in_for): si la etapa es la 1ª
    # activa, lee K.*_KG_ENTRADA editable; si está encadenada, hereda del
    # kg_out de la anterior.
    a_kg_in   = S.kg_in_for("cria")
    a_kg_out  = S.kg_out_for("cria")
    a_dias    = int(_g(K.A_DIAS,          DEFAULTS["d_dias"]))
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
    b_dias    = int(_g(K.B_DIAS,          DEFAULTS["b_dias"]))
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
    c_dias    = int(_g(K.C_DIAS,          DEFAULTS["c_dias"]))
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

    # Valor infra TOTAL (global) — se asigna parcialmente vía *_ASIG_PCT
    valor_total = _g(K.INFRA_VALOR_TOTAL, DEFAULTS["infra_valor_total"])

    # ── Cabezas en cascada (sólo dentro del slice activo) ──────────────────
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    active = S.active_stages()
    morts = {"cria": a_mort, "recria": b_mort, "eng_int": c_mort}
    cab_map: dict[str, int] = {"cria": 0, "recria": 0, "eng_int": 0}
    if active:
        cab_map[active[0]] = n_t
        for i in range(1, len(active)):
            prev_s = active[i - 1]
            cab_map[active[i]] = surv(cab_map[prev_s], morts[prev_s])
    cab_cria    = cab_map["cria"]
    cab_recria  = cab_map["recria"]
    cab_eng_int = cab_map["eng_int"]

    # ── Operación USD/cab (MO + combustible + servicios) ──────────────────
    # MO/comb/servicios son ABSOLUTOS USD/mes; el ciclo = USD/mes ÷ 30 × días,
    # repartido entre cabezas → USD/cab.
    def op_cab(mo_mes: float, comb_mes: float, serv_mes: float,
               dias: int, cabezas: int) -> float:
        op_total_ciclo = (mo_mes + comb_mes + serv_mes) / 30.0 * dias
        return (op_total_ciclo / cabezas) if cabezas > 0 else 0.0

    # ── Estructura USD/cab (amortización proporcional + mantenimiento) ────
    # Amortización: (valor_total × asig%/100) / años → /365 × días
    # Mantenimiento: USD/año / 365 × días
    # La suma de % asignados puede ser <100% (resto de actividades fuera del modelo).
    def estructura_cab(asig_pct: float, amort_anos: float, mant_anio: float,
                       dias: int, cabezas: int) -> float:
        if cabezas <= 0:
            return 0.0
        adjudicado = valor_total * max(asig_pct, 0.0) / 100.0
        amort_anual = (adjudicado / amort_anos) if amort_anos > 0 else 0.0
        amort_ciclo = amort_anual * dias / 365.0
        mant_ciclo  = max(mant_anio, 0.0) * dias / 365.0
        return (amort_ciclo + mant_ciclo) / cabezas

    # ── Costos por cab (modelo bioeconómico completo) ─────────────────────
    def block(
        kg_in: float, kg_out: float, dias: int, mort_pct: float,
        precio_venta: float,
        compra: float, alim: float, sanidad: float,
        op: float, estr: float, com: float,
        cabezas: int, active: bool,
    ) -> dict:
        # Capital inmovilizado durante el ciclo (USD/cab) → costo financiero
        capital   = compra + alim + sanidad + op + estr + com
        financiero = capital * (tasa_pct / 100.0) * dias / 365.0
        # Mortandad = ingreso perdido por cabezas muertas (oportunidad)
        # USD/cab equivalente: (mort_pct/100) × kg_out × precio_venta
        mortandad = (mort_pct / 100.0) * kg_out * precio_venta
        total_cab = capital + financiero + mortandad
        total_usd = total_cab * cabezas
        # kg vendibles: sólo las cabezas que sobreviven producen kg comercializables
        cab_vend = max(int(cabezas * (1 - mort_pct / 100.0)), 0)
        kg_prod = max(kg_out - kg_in, 0.0) * cab_vend
        usd_kg = total_usd / kg_prod if kg_prod > 0 else 0.0
        return {
            "kg_in": kg_in, "kg_out": kg_out, "dias": dias,
            "mort_pct": mort_pct, "cabezas": cabezas,
            "compra": compra, "alim": alim, "sanidad": sanidad,
            "op": op, "estr": estr, "com": com,
            "financiero": financiero, "mortandad": mortandad,
            "total_cab": total_cab, "total_usd": total_usd,
            "kg_prod_total": kg_prod, "usd_kg": usd_kg,
            "active": active,
        }

    return {
        "cria": block(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            precio_venta=a_pv,
            compra  = pc_global * a_kg_in,
            alim    = _alim_usd_cab(a_kg_in, a_kg_out, a_ca, _FEED_KEYS["cria"]),
            sanidad = a_san,
            op      = op_cab(a_mo_mes, a_combust, a_servic, a_dias, cab_cria),
            estr    = estructura_cab(a_asig, a_amanos, a_mant, a_dias, cab_cria),
            com     = (a_com_pct / 100.0) * a_pv * a_kg_out + a_fe + a_fs,
            cabezas = cab_cria,
            active  = S.is_active("cria"),
        ),
        "recria": block(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            precio_venta=b_pv,
            compra  = b_pc * b_kg_in,
            alim    = _alim_usd_cab(b_kg_in, b_kg_out, b_ca, _FEED_KEYS["recria"]),
            sanidad = b_san,
            op      = op_cab(b_mo_mes, b_combust, b_servic, b_dias, cab_recria),
            estr    = estructura_cab(b_asig, b_amanos, b_mant, b_dias, cab_recria),
            com     = (b_com_pct / 100.0) * b_pv * b_kg_out + b_fe + b_fs,
            cabezas = cab_recria,
            active  = S.is_active("recria"),
        ),
        "eng_int": block(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            precio_venta=c_pv,
            compra  = c_pc * c_kg_in,
            alim    = _alim_usd_cab(c_kg_in, c_kg_out, c_ca, _FEED_KEYS["eng_int"]),
            sanidad = c_san,
            op      = op_cab(c_mo_mes, c_combust, c_servic, c_dias, cab_eng_int),
            estr    = estructura_cab(c_asig, c_amanos, c_mant, c_dias, cab_eng_int),
            com     = (c_com_pct / 100.0) * c_pv * c_kg_out + c_fe + c_fs,
            cabezas = cab_eng_int,
            active  = S.is_active("eng_int"),
        ),
    }


# ── Resumen superior: 3 KPIs + barras apiladas ───────────────────────────────

def _summary_kpis(data: dict) -> None:
    cols = st.columns(3, gap="small")
    for col, key in zip(cols, ["cria", "recria", "eng_int"]):
        meta = _SEG[key]
        s = data[key]
        is_active = s.get("active", True)
        opacity = "1" if is_active else "0.42"
        header_bg = (f"linear-gradient(135deg,{meta['color']},{meta['color']}dd)"
                     if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")
        right_chip = (
            '' if is_active else
            '<span style="background:rgba(255,255,255,0.22);border-radius:14px;'
            'padding:2px 8px;font-size:0.58rem;font-weight:700;'
            'margin-left:auto;">INACTIVA</span>'
        )
        # HTML sin indentación interna: Markdown trata 4+ espacios al inicio
        # de línea como bloque de código y muestra los tags como texto crudo.
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
            f'Costo total / cab</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:#0c1a2e;'
            f'line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">'
            f'USD&nbsp;{s["total_cab"]:,.1f}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["total_usd"]:,.0f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Costo Total</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["usd_kg"]:.2f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">USD/kg producido</div>'
            f'</div>'
            f'</div></div></div>'
        )
        col.markdown(card_html, unsafe_allow_html=True)


def _stacked_bar(data: dict) -> go.Figure:
    """Barras apiladas: una barra por etapa ACTIVA, segmentos = conceptos (USD/cab)."""
    stages = S.active_stages()
    x_labels = [f"{_SEG[k]['icon']}  {_SEG[k]['title']}" for k in stages]

    # Mapeo concepto -> clave del dict
    concept_to_key = {
        "Compra":           "compra",
        "Alimentación":     "alim",
        "Sanidad":          "sanidad",
        "Operación":        "op",
        "Estructura":       "estr",
        "Comercialización": "com",
        "Financieros":      "financiero",
        "Mortandad":        "mortandad",
    }

    fig = go.Figure()
    for concept in _CONCEPTS:
        key = concept_to_key[concept]
        ys = [data[s][key] for s in stages]
        fig.add_trace(go.Bar(
            name=concept,
            x=x_labels,
            y=ys,
            marker=dict(
                color=_CONCEPT_COLORS[concept],
                line=dict(color="white", width=1),
            ),
            hovertemplate=(
                f"<b>{concept}</b><br>"
                "USD %{y:,.2f} / cab"
                "<extra></extra>"
            ),
        ))

    # Anotación con total sobre cada barra
    for x, key in zip(x_labels, stages):
        total = data[key]["total_cab"]
        fig.add_annotation(
            x=x, y=total,
            text=f"<b>USD {total:,.1f}</b><br>"
                 f"<span style='color:#94a3b8;font-size:9px;'>"
                 f"USD {data[key]['usd_kg']:.2f} /kg</span>",
            showarrow=False,
            yshift=24,
            font=dict(size=11, color="#0c1a2e"),
            align="center",
        )

    fig.update_layout(
        barmode="stack",
        height=440,
        margin=dict(t=60, b=40, l=60, r=20),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.22,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#475569"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            tickfont=dict(size=11, color="#0c1a2e"),
            gridcolor="rgba(0,0,0,0)",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="USD / cabeza",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7",
            tickformat=",.0f",
            ticksuffix=" ",
            zeroline=False,
        ),
        bargap=0.42,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4eaf4",
            font=dict(size=12, color="#0c1a2e"),
        ),
    )
    return fig


_CONCEPT_KEY = {
    "Compra":           "compra",
    "Alimentación":     "alim",
    "Sanidad":          "sanidad",
    "Operación":        "op",
    "Estructura":       "estr",
    "Comercialización": "com",
    "Financieros":      "financiero",
    "Mortandad":        "mortandad",
}


# ── Barras apiladas: concepto en X, etapas como segmentos ────────────────────

def _stacked_bar_by_concept(data: dict) -> go.Figure:
    """Una barra por concepto; cada barra apila las etapas ACTIVAS (USD totales).
    Permite ver la composición por tipo de costo a lo largo del ciclo."""
    stages = S.active_stages()
    x_labels = [f"{_CONCEPT_ICONS[c]}  {c}" for c in _CONCEPTS]

    fig = go.Figure()
    for stage in stages:
        meta = _SEG[stage]
        ys = [data[stage][_CONCEPT_KEY[c]] * data[stage]["cabezas"]
              for c in _CONCEPTS]
        fig.add_trace(go.Bar(
            name=f"{meta['icon']} {meta['title']}",
            x=x_labels,
            y=ys,
            marker=dict(
                color=meta["color"],
                line=dict(color="white", width=1),
            ),
            hovertemplate=(
                f"<b>{meta['title']}</b><br>"
                "USD %{y:,.0f}"
                "<extra></extra>"
            ),
        ))

    # Total USD por concepto sobre cada barra
    for i, concept in enumerate(_CONCEPTS):
        total = sum(data[s][_CONCEPT_KEY[concept]] * data[s]["cabezas"]
                    for s in stages)
        fig.add_annotation(
            x=x_labels[i], y=total,
            text=f"<b>USD {total:,.0f}</b>",
            showarrow=False,
            yshift=14,
            font=dict(size=11, color="#0c1a2e"),
            align="center",
        )

    fig.update_layout(
        barmode="stack",
        height=440,
        margin=dict(t=60, b=40, l=60, r=20),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.22,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#475569"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            tickfont=dict(size=11, color="#0c1a2e"),
            gridcolor="rgba(0,0,0,0)",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="USD totales (sistema)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7",
            tickformat=",.0f",
            ticksuffix=" ",
            zeroline=False,
        ),
        bargap=0.42,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4eaf4",
            font=dict(size=12, color="#0c1a2e"),
        ),
    )
    return fig


# ── Detalle por etapa: donut chart por concepto ──────────────────────────────

def _stage_donut(key: str, s: dict) -> go.Figure:
    """Donut chart con la composición de costos de la etapa.
    Centro: total USD/cab + USD/kg producido."""
    meta = _SEG[key]
    labels = [f"{_CONCEPT_ICONS[c]} {c}" for c in _CONCEPTS]
    values = [max(s[_CONCEPT_KEY[c]], 0.0) for c in _CONCEPTS]
    colors = [_CONCEPT_COLORS[c] for c in _CONCEPTS]

    # Si todo es cero (parámetros vacíos), evita la torta degenerada
    if sum(values) <= 0:
        values = [1.0] * len(_CONCEPTS)
        colors_safe = ["#e5e7eb"] * len(_CONCEPTS)
        text_inside = [""] * len(_CONCEPTS)
    else:
        colors_safe = colors
        text_inside = ["%{percent}"] * len(_CONCEPTS)

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        sort=False,
        direction="clockwise",
        marker=dict(colors=colors_safe, line=dict(color="white", width=2)),
        textposition="outside",
        texttemplate="%{label}<br><b>%{percent}</b>",
        textfont=dict(size=10, color="#475569"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "USD %{value:,.2f} / cab<br>"
            "%{percent}"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    # Centro: total USD/cab + USD/kg
    fig.add_annotation(
        text=(f"<span style='font-size:11px;color:#7a8fa6;"
              f"letter-spacing:0.06em;'>TOTAL</span><br>"
              f"<span style='font-size:18px;color:#0c1a2e;font-weight:800;'>"
              f"USD {s['total_cab']:,.1f}</span><br>"
              f"<span style='font-size:10px;color:{meta['color']};"
              f"font-weight:700;'>USD {s['usd_kg']:.2f}/kg</span>"),
        x=0.5, y=0.5,
        showarrow=False,
        align="center",
    )

    fig.update_layout(
        height=320,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
    )
    return fig


def _stage_card_header(key: str, s: dict) -> str:
    meta = _SEG[key]
    cabezas = max(s["cabezas"], 0)
    is_active = s.get("active", True)
    header_bg = (f"linear-gradient(135deg,{meta['color']},{meta['color']}dd)"
                 if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")
    right_chip = (
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{cabezas:,} cab · {s["dias"]} d · USD {s["total_usd"]:,.0f}'
        f'</span>'
        if is_active else
        '<span style="background:rgba(255,255,255,0.22);'
        'border-radius:14px;padding:3px 10px;font-size:0.62rem;'
        'font-weight:700;white-space:nowrap;">INACTIVA</span>'
    )
    return (
        f'<div style="background:{header_bg};padding:11px 16px;color:white;'
        f'border-radius:12px 12px 0 0;display:flex;'
        f'justify-content:space-between;align-items:center;gap:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.92rem;font-weight:700;">{meta["title"]}</span>'
        f'</div>'
        f'{right_chip}</div>'
    )


def _stage_grid(data: dict) -> None:
    cols = st.columns(2, gap="small")
    keys = ["cria", "recria", "eng_int"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            meta = _SEG[key]
            is_active = data[key].get("active", True)
            opacity = "1" if is_active else "0.42"
            bg = meta["bg"] if is_active else "#f8fafc"
            border = meta["border"] if is_active else "#e2e8f0"
            st.markdown(
                f'<div style="background:{bg};'
                f'border:1px solid {border};border-radius:14px;'
                f'overflow:hidden;box-shadow:0 1px 6px rgba(13,27,66,0.05);'
                f'margin-bottom:14px;opacity:{opacity};">'
                f'{_stage_card_header(key, data[key])}'
                f'<div style="padding:6px 8px 4px;">',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                _stage_donut(key, data[key]),
                use_container_width=True,
                key=f"costos_donut_{key}",
            )
            st.markdown('</div></div>', unsafe_allow_html=True)


# ── Entry point ──────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Costos",
        "Estructura económica del sistema ganadero por etapa productiva: "
        "compra · alimentación · sanidad · mortandad · mano de obra · "
        "comercialización.",
    )

    data = _build_costos()

    # ── Resumen superior ──────────────────────────────────────────────────
    section("Comparativa por etapa")
    _summary_kpis(data)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.plotly_chart(
        _stacked_bar(data),
        use_container_width=True,
        key="costos_bars_by_stage",
    )

    st.markdown(
        '<p style="font-size:0.78rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin:1.6rem 0 0.4rem 0;">Composición por tipo de costo</p>'
        '<p style="font-size:0.78rem;color:#94a3b8;margin:0 0 0.6rem 0;">'
        'USD totales del sistema apilados por etapa.</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _stacked_bar_by_concept(data),
        use_container_width=True,
        key="costos_bars_by_concept",
    )

    st.divider()

    # ── Detalle por etapa ─────────────────────────────────────────────────
    section("Detalle de costos por etapa")
    _stage_grid(data)
