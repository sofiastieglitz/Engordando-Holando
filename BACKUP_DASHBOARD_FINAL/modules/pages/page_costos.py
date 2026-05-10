"""
Costos — Visualización económica de los costos del sistema ganadero
por las 4 etapas productivas (Cría · Recría · Engorde interno · Engorde
exportación).

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

# Paleta suave SaaS/agtech para el desglose de conceptos
_CONCEPT_COLORS: dict[str, str] = {
    "Compra":           "#64748b",  # slate
    "Alimentación":     "#10b981",  # emerald
    "Sanidad":          "#f59e0b",  # amber
    "Mortandad":        "#f87171",  # soft red
    "Mano de obra":     "#a78bfa",  # soft purple
    "Comercialización": "#22d3ee",  # cyan
}

_CONCEPT_ICONS: dict[str, str] = {
    "Compra":           "🛒",
    "Alimentación":     "🌾",
    "Sanidad":          "💉",
    "Mortandad":        "⚠️",
    "Mano de obra":     "👷",
    "Comercialización": "🚛",
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


def _alim_usd_cab(rac_dia: float, dias: int, feed_key: str,
                  fallback_usd_dia: float) -> float:
    """USD/cab de alimentación = Σ(kg_ms_etapa × USD/kg MS) por ingrediente.
    Si la tabla está vacía → fallback ALIM_DIA × días."""
    df = _read_feed_df(feed_key)
    name = df["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(df["%"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(df["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)
    if not mask.any():
        return float(fallback_usd_dia) * float(dias)
    total = 0.0
    for p, u in zip(pct[mask].values, usd[mask].values):
        kg_ms_etapa = rac_dia * (p / 100.0) * dias
        total += kg_ms_etapa * u
    return float(total)


# ── Modelo de costos por etapa ───────────────────────────────────────────────

def _build_costos() -> dict:
    """
    Calcula el desglose de costos por las 4 etapas productivas.

    Retorna dict con clave por etapa ("cria", "recria", "eng_int", "eng_exp")
    y para cada una:
        kg_in, kg_out, dias, mort_pct, cabezas
        compra, alim, sanidad, mo, com, mortandad      (USD/cab)
        total_cab                                       (USD/cab)
        total_usd                                       (USD totales etapa)
        kg_prod_total                                   (kg totales producidos)
        usd_kg                                          (USD/kg producido)
    """
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

    # ── Lecturas por etapa ────────────────────────────────────────────────
    a_kg_in   = _g(K.A_KG_ENTRADA,        DEFAULTS["a_kg_entrada"])
    a_kg_out  = _g(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"])  # destete
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

    b_kg_in   = a_kg_out                                   # encadenado
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

    c_kg_in   = b_kg_out                                   # encadenado
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

    # ── Cabezas en cascada (post-mortandad) ────────────────────────────────
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    cab_cria    = n_t
    cab_recria  = surv(cab_cria,    a_mort)
    cab_eng_int = surv(cab_recria,  b_mort)
    cab_eng_exp = surv(cab_eng_int, c_mort)

    # ── Costos por cab (formulas del usuario) ──────────────────────────────
    def block(
        kg_in: float, kg_out: float, dias: int, mort_pct: float,
        compra: float, alim: float, sanidad: float, mo: float, com: float,
        cabezas: int,
    ) -> dict:
        # Mortandad = pérdida atribuible: costo acumulado × mortandad %
        acumulado = compra + alim + sanidad + mo + com
        mortandad = acumulado * mort_pct / 100.0
        total_cab = acumulado + mortandad
        total_usd = total_cab * cabezas
        kg_prod = max(kg_out - kg_in, 0.0) * cabezas
        usd_kg = total_usd / kg_prod if kg_prod > 0 else 0.0
        return {
            "kg_in": kg_in, "kg_out": kg_out, "dias": dias,
            "mort_pct": mort_pct, "cabezas": cabezas,
            "compra": compra, "alim": alim, "sanidad": sanidad,
            "mo": mo, "com": com, "mortandad": mortandad,
            "total_cab": total_cab, "total_usd": total_usd,
            "kg_prod_total": kg_prod, "usd_kg": usd_kg,
        }

    return {
        "cria": block(
            kg_in=a_kg_in, kg_out=a_kg_out, dias=a_dias, mort_pct=a_mort,
            compra  = pc_global * a_kg_in,
            alim    = _alim_usd_cab(a_rac, a_dias, _FEED_KEYS["cria"], a_alim_d),
            sanidad = a_san,
            mo      = a_mo_dia * a_dias,
            com     = (a_com_pct / 100.0) * a_pv * a_kg_out + a_fe + a_fs,
            cabezas = cab_cria,
        ),
        "recria": block(
            kg_in=b_kg_in, kg_out=b_kg_out, dias=b_dias, mort_pct=b_mort,
            compra  = b_pc * b_kg_in,
            alim    = _alim_usd_cab(b_rac, b_dias, _FEED_KEYS["recria"], b_alim_d),
            sanidad = b_san,
            mo      = b_mo_dia * b_dias,
            com     = (b_com_pct / 100.0) * b_pv * b_kg_out + b_fe + b_fs,
            cabezas = cab_recria,
        ),
        "eng_int": block(
            kg_in=c_kg_in, kg_out=c_kg_out, dias=c_dias, mort_pct=c_mort,
            compra  = c_pc * c_kg_in,
            alim    = _alim_usd_cab(c_rac, c_dias, _FEED_KEYS["eng_int"], c_alim_d),
            sanidad = c_san,
            mo      = c_mo_dia * c_dias,
            com     = (c_com_pct / 100.0) * c_pv * c_kg_out + c_fe + c_fs,
            cabezas = cab_eng_int,
        ),
        "eng_exp": block(
            kg_in=e_kg_in, kg_out=e_kg_out, dias=e_dias, mort_pct=e_mort,
            compra  = e_pc * e_kg_in,
            alim    = _alim_usd_cab(e_rac, e_dias, _FEED_KEYS["eng_exp"], e_alim_d),
            sanidad = e_san,
            mo      = e_mo_dia * e_dias,
            com     = (e_com_pct / 100.0) * e_pv * e_kg_out + e_fe + e_fs,
            cabezas = cab_eng_exp,
        ),
    }


# ── Resumen superior: 4 KPIs + barras apiladas ───────────────────────────────

def _summary_kpis(data: dict) -> None:
    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["cria", "recria", "eng_int", "eng_exp"]):
        meta = _SEG[key]
        s = data[key]
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
                        Costo total / cab
                    </div>
                    <div style="font-size:1.55rem;font-weight:800;color:#0c1a2e;
                                line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">
                        USD&nbsp;{s['total_cab']:,.1f}
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;
                                gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['total_usd']:,.0f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Costo Total</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['usd_kg']:.2f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">USD/kg producido</div>
                        </div>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )


def _stacked_bar(data: dict) -> go.Figure:
    """Barras apiladas: una barra por etapa, segmentos = conceptos (USD/cab)."""
    stages = ["cria", "recria", "eng_int", "eng_exp"]
    x_labels = [f"{_SEG[k]['icon']}  {_SEG[k]['title']}" for k in stages]

    # Mapeo concepto -> clave del dict
    concept_to_key = {
        "Compra":           "compra",
        "Alimentación":     "alim",
        "Sanidad":          "sanidad",
        "Mortandad":        "mortandad",
        "Mano de obra":     "mo",
        "Comercialización": "com",
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
    "Mortandad":        "mortandad",
    "Mano de obra":     "mo",
    "Comercialización": "com",
}


# ── Barras apiladas: concepto en X, etapas como segmentos ────────────────────

def _stacked_bar_by_concept(data: dict) -> go.Figure:
    """Una barra por concepto; cada barra apila las 4 etapas (USD totales).
    Permite ver la composición por tipo de costo a lo largo del ciclo."""
    stages = ["cria", "recria", "eng_int", "eng_exp"]
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
    return (
        f'<div style="background:linear-gradient(135deg,{meta["color"]},'
        f'{meta["color"]}dd);padding:11px 16px;color:white;'
        f'border-radius:12px 12px 0 0;display:flex;'
        f'justify-content:space-between;align-items:center;gap:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.05rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.92rem;font-weight:700;">{meta["title"]}</span>'
        f'</div>'
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{cabezas:,} cab · {s["dias"]} d · USD {s["total_usd"]:,.0f}'
        f'</span></div>'
    )


def _stage_grid(data: dict) -> None:
    cols = st.columns(2, gap="small")
    keys = ["cria", "recria", "eng_int", "eng_exp"]
    for i, key in enumerate(keys):
        with cols[i % 2]:
            meta = _SEG[key]
            st.markdown(
                f'<div style="background:{meta["bg"]};'
                f'border:1px solid {meta["border"]};border-radius:14px;'
                f'overflow:hidden;box-shadow:0 1px 6px rgba(13,27,66,0.05);'
                f'margin-bottom:14px;">'
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
