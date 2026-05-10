"""
Ingresos — Visualización comercial del sistema ganadero.

Foco exclusivamente comercial: ventas, facturación, kilos comercializados
y evolución del valor bruto del animal por etapa productiva.
NO incluye costos, márgenes, ROI ni rentabilidad.

Lee parámetros directamente desde session_state (mismas claves que usa
page_parametros.py y page_modelo_productivo.py). Mantiene la firma
render(params, comp) por compatibilidad con el router de app.py.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
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

# Rendimiento de carcasa típico para Holstein engordado (% peso vivo → res)
_RENDIMIENTO_CARCASA = 0.58


def _g(key: str, default: float) -> float:
    return float(st.session_state.get(key, default))


# ── Modelo comercial ─────────────────────────────────────────────────────────

def _build_ingresos() -> dict:
    """
    Calcula los datos comerciales por las 4 etapas productivas.

    Por etapa devuelve:
        kg_in, kg_out, dias, mort_pct
        cab_in, cab_vend                    (cabezas que ingresan / vendidas)
        precio_venta                        (USD/kg)
        kg_vendidos                         (cab_vend × kg_out)
        ingreso_cab                         (kg_out × precio_venta)
        ingreso_total                       (ingreso_cab × cab_vend)
    """
    n_t = int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))

    # ── Cría ──────────────────────────────────────────────────────────────
    a_kg_in   = _g(K.A_KG_ENTRADA,        DEFAULTS["a_kg_entrada"])
    a_kg_out  = _g(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"])  # destete
    a_dias    = int(_g(K.A_DIAS,          DEFAULTS["d_dias"]))
    a_mort    = _g(K.A_MORTALIDAD,        DEFAULTS["d_mortalidad"])
    a_pv      = _g(K.A_PRECIO_VENTA,      DEFAULTS["d_precio_venta"])

    # ── Recría ────────────────────────────────────────────────────────────
    b_kg_in   = a_kg_out                                    # encadenado
    b_kg_out  = _g(K.B_PESO_SALIDA,       DEFAULTS["r_peso_salida"])
    b_dias    = int(_g(K.B_DIAS,          DEFAULTS["b_dias"]))
    b_mort    = _g(K.B_MORTALIDAD,        DEFAULTS["r_mortalidad"])
    b_pv      = _g(K.B_PRECIO_VENTA,      DEFAULTS["r_precio_venta"])

    # ── Engorde interno ───────────────────────────────────────────────────
    c_kg_in   = b_kg_out                                    # encadenado
    c_kg_out  = _g(K.C_PESO_FINAL,        DEFAULTS["t_peso_final"])
    c_dias    = int(_g(K.C_DIAS,          DEFAULTS["c_dias"]))
    c_mort    = _g(K.C_MORTALIDAD,        DEFAULTS["t_mortalidad"])
    c_pv      = _g(K.C_PRECIO_VENTA,      DEFAULTS["t_precio_venta"])

    # ── Engorde exportación ───────────────────────────────────────────────
    e_kg_in   = _g(K.E_KG_ENTRADA,        DEFAULTS["e_kg_entrada"])
    e_kg_out  = _g(K.E_KG_SALIDA,         DEFAULTS["e_kg_salida"])
    e_dias    = int(_g(K.E_DIAS,          DEFAULTS["e_dias"]))
    e_mort    = _g(K.E_MORTALIDAD,        DEFAULTS["e_mortalidad"])
    e_pv      = _g(K.E_PRECIO_VENTA,      DEFAULTS["e_pv"])

    # ── Cabezas: cascada IN → OUT (post-mortandad de cada etapa) ──────────
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100.0)), 0)

    cab_in_cria    = n_t
    cab_in_recria  = surv(cab_in_cria,    a_mort)
    cab_in_eng_int = surv(cab_in_recria,  b_mort)
    cab_in_eng_exp = surv(cab_in_eng_int, c_mort)

    def block(kg_in: float, kg_out: float, dias: int, mort_pct: float,
              cab_in: int, precio_venta: float) -> dict:
        cab_vend      = surv(cab_in, mort_pct)
        ingreso_cab   = kg_out * precio_venta
        ingreso_total = ingreso_cab * cab_vend
        kg_vendidos   = cab_vend * kg_out
        return {
            "kg_in": kg_in, "kg_out": kg_out, "dias": dias,
            "mort_pct": mort_pct,
            "cab_in": cab_in, "cab_vend": cab_vend,
            "precio_venta": precio_venta,
            "kg_vendidos": kg_vendidos,
            "ingreso_cab": ingreso_cab,
            "ingreso_total": ingreso_total,
        }

    data = {
        "cria":    block(a_kg_in,  a_kg_out, a_dias, a_mort, cab_in_cria,    a_pv),
        "recria":  block(b_kg_in,  b_kg_out, b_dias, b_mort, cab_in_recria,  b_pv),
        "eng_int": block(c_kg_in,  c_kg_out, c_dias, c_mort, cab_in_eng_int, c_pv),
        "eng_exp": block(e_kg_in,  e_kg_out, e_dias, e_mort, cab_in_eng_exp, e_pv),
    }

    # ── Datos extra para Engorde exportación ──────────────────────────────
    eng_exp = data["eng_exp"]
    rendimiento  = _RENDIMIENTO_CARCASA
    kg_carcasa   = eng_exp["kg_out"] * rendimiento
    precio_export = eng_exp["precio_venta"]
    bonificacion = max(eng_exp["precio_venta"] - data["eng_int"]["precio_venta"], 0.0)
    eng_exp.update({
        "rendimiento":   rendimiento,
        "kg_carcasa":    kg_carcasa,
        "precio_export": precio_export,
        "bonificacion":  bonificacion,
        "ingreso_carcasa_cab":   kg_carcasa * precio_export,
        "ingreso_carcasa_total": kg_carcasa * precio_export * eng_exp["cab_vend"],
    })

    return data


# ── 1. Resumen superior — KPIs comparativas ──────────────────────────────────

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
                        Ingreso / cab
                    </div>
                    <div style="font-size:1.55rem;font-weight:800;color:#0c1a2e;
                                line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">
                        USD&nbsp;{s['ingreso_cab']:,.1f}
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;
                                gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['ingreso_total']:,.0f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Ingreso Total</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">{s['cab_vend']:,} cab</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Vendidas</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">USD&nbsp;{s['precio_venta']:.2f}</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Precio /kg</div>
                        </div>
                        <div>
                            <div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;
                                        line-height:1.2;">{s['kg_vendidos']:,.0f} kg</div>
                            <div style="font-size:0.60rem;font-weight:700;color:#94a3b8;
                                        text-transform:uppercase;letter-spacing:0.05em;
                                        margin-top:1px;">Kg vendidos</div>
                        </div>
                    </div>
                    <div style="margin-top:10px;padding-top:8px;
                                border-top:1px solid #f0f4fa;text-align:center;">
                        <span style="font-size:0.72rem;color:#475569;font-weight:600;">
                            ⚖️ {s['kg_out']:.0f} kg/cab
                        </span>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )


# ── Gráfico comparativo principal ────────────────────────────────────────────

def _bars_two_panels(data: dict) -> go.Figure:
    """Dos paneles lado a lado: Ingreso/cab y Ingreso total por etapa."""
    from plotly.subplots import make_subplots

    stages = ["cria", "recria", "eng_int", "eng_exp"]
    x_labels = [f"{_SEG[k]['icon']}<br>{_SEG[k]['title']}" for k in stages]
    colors = [_SEG[k]["color"] for k in stages]

    ing_cab   = [data[k]["ingreso_cab"]   for k in stages]
    ing_total = [data[k]["ingreso_total"] for k in stages]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Ingreso por cabeza (USD)",
                        "Ingreso total (USD)"),
        horizontal_spacing=0.14,
    )

    fig.add_trace(go.Bar(
        x=x_labels, y=ing_cab,
        marker=dict(color=colors,
                    line=dict(color="white", width=1.2)),
        text=[f"USD {v:,.0f}" for v in ing_cab],
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        hovertemplate="<b>%{x}</b><br>USD %{y:,.2f} / cab<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=x_labels, y=ing_total,
        marker=dict(color=colors,
                    line=dict(color="white", width=1.2)),
        text=[f"USD {v:,.0f}" for v in ing_total],
        textposition="outside",
        textfont=dict(size=11, color="#0c1a2e"),
        hovertemplate="<b>%{x}</b><br>USD %{y:,.0f}<extra></extra>",
        showlegend=False,
    ), row=1, col=2)

    # Cabecera de subplots con estilo
    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=12, color="#475569", family="Inter, Arial")

    fig.update_layout(
        height=420,
        margin=dict(t=60, b=40, l=50, r=30),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif"),
        bargap=0.40,
        hoverlabel=dict(
            bgcolor="white", bordercolor="#e4eaf4",
            font=dict(size=12, color="#0c1a2e"),
        ),
    )
    fig.update_xaxes(
        tickfont=dict(size=11, color="#0c1a2e"),
        gridcolor="rgba(0,0,0,0)", zeroline=False,
    )
    fig.update_yaxes(
        gridcolor="#eef2f7",
        tickformat=",.0f", ticksuffix=" ",
        zeroline=False,
        tickfont=dict(size=10, color="#64748b"),
    )
    return fig


# ── Evolución del valor bruto del animal ─────────────────────────────────────

def _value_evolution_chart(data: dict) -> go.Figure:
    """
    Curva continua del valor bruto del animal (USD/cab) en función de los días
    acumulados del ciclo:
        Compra → Cría → Destete → Recría → Eng. interno → Eng. exportación.

    Para cada hito se calcula valor = peso × precio_venta_de_la_etapa.
    El valor inicial usa precio_compra (no precio_venta).
    """
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])

    # Tiempos acumulados
    t_cria    = data["cria"]["dias"]
    t_recria  = t_cria   + data["recria"]["dias"]
    t_eng_int = t_recria + data["eng_int"]["dias"]
    t_eng_exp = t_eng_int + data["eng_exp"]["dias"]

    # Pesos en cada hito
    kg_birth   = data["cria"]["kg_in"]
    kg_destete = data["cria"]["kg_out"]
    kg_recria  = data["recria"]["kg_out"]
    kg_eng_int = data["eng_int"]["kg_out"]
    kg_eng_exp = data["eng_exp"]["kg_out"]

    # Valores en cada hito (USD/cab)
    v_birth   = kg_birth   * pc_global
    v_destete = kg_destete * data["cria"]["precio_venta"]
    v_recria  = kg_recria  * data["recria"]["precio_venta"]
    v_eng_int = kg_eng_int * data["eng_int"]["precio_venta"]
    v_eng_exp = kg_eng_exp * data["eng_exp"]["precio_venta"]

    # Bandas por etapa
    fills = {
        "cria":    "rgba(22,163,74,0.08)",
        "recria":  "rgba(21,101,192,0.08)",
        "eng_int": "rgba(13,148,136,0.08)",
        "eng_exp": "rgba(124,58,237,0.08)",
    }

    fig = go.Figure()

    bands = [
        (0,         t_cria,    fills["cria"]),
        (t_cria,    t_recria,  fills["recria"]),
        (t_recria,  t_eng_int, fills["eng_int"]),
        (t_eng_int, t_eng_exp, fills["eng_exp"]),
    ]
    for x0, x1, fill in bands:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=fill,
                      layer="below", line_width=0)

    for xd in [t_cria, t_recria, t_eng_int]:
        fig.add_vline(x=xd, line_dash="dot",
                      line_color="rgba(100,116,139,0.30)", line_width=1.5)

    xs = [0, t_cria, t_recria, t_eng_int, t_eng_exp]
    ys = [v_birth, v_destete, v_recria, v_eng_int, v_eng_exp]

    # Halo
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color="rgba(124,58,237,0.18)", width=14,
                  shape="spline", smoothing=0.5),
        showlegend=False, hoverinfo="skip",
    ))
    # Línea principal
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color="#7c3aed", width=3.5,
                  shape="spline", smoothing=0.5),
        marker=dict(size=12, color="#7c3aed", symbol="circle",
                    line=dict(color="white", width=3)),
        showlegend=False,
        hovertemplate="<b>Día %{x}</b><br>Valor: USD %{y:,.0f}/cab<extra></extra>",
    ))

    # Hitos comerciales
    milestones = [
        (0,         v_birth,   "🐣 Compra",         "#94a3b8"),
        (t_cria,    v_destete, "🥛 Destete",        "#16a34a"),
        (t_recria,  v_recria,  "🔵 Fin recría",     "#1565c0"),
        (t_eng_int, v_eng_int, "🟢 Eng. interno",   "#0d9488"),
        (t_eng_exp, v_eng_exp, "🌐 Exportación",    "#7c3aed"),
    ]
    for x, y, label, color in milestones:
        fig.add_annotation(
            x=x, y=y,
            text=(f"<b>{label}</b>"
                  f"<br><span style='color:#475569;font-size:9px;'>"
                  f"USD {y:,.0f} · día {x}</span>"),
            showarrow=True,
            arrowhead=0, arrowwidth=1,
            arrowcolor="rgba(124,58,237,0.4)",
            ax=0, ay=-50,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor=color,
            borderwidth=1,
            borderpad=5,
        )

    # Etiquetas de etapa abajo del eje X
    stage_labels = [
        (t_cria/2,                    "🌱 Cría",              data["cria"]["dias"],    "#16a34a"),
        ((t_cria + t_recria)/2,       "🔵 Recría",            data["recria"]["dias"],  "#1565c0"),
        ((t_recria + t_eng_int)/2,    "🟢 Eng. interno",      data["eng_int"]["dias"], "#0d9488"),
        ((t_eng_int + t_eng_exp)/2,   "🌐 Eng. exportación",  data["eng_exp"]["dias"], "#7c3aed"),
    ]
    for xc, name, dur, color in stage_labels:
        fig.add_annotation(
            x=xc, y=-0.18, xref="x", yref="paper",
            text=(f"<b style='color:{color};'>{name}</b>"
                  f"<br><span style='color:#94a3b8;font-size:9px;'>{dur} días</span>"),
            showarrow=False, font=dict(size=11), align="center",
        )

    fig.update_layout(
        height=520,
        margin=dict(t=80, b=110, l=80, r=40),
        xaxis=dict(
            title=None,
            range=[-15, t_eng_exp + 25],
            gridcolor="#eef2f7", zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            ticksuffix=" d",
        ),
        yaxis=dict(
            title=dict(text="Valor bruto del animal (USD/cab)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7", zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            tickprefix="USD ",
            tickformat=",.0f",
        ),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter, Arial, sans-serif"),
        hovermode="x unified",
    )
    return fig


# ── Detalle por etapa: cards comerciales ─────────────────────────────────────

def _metric_tile(label: str, value: str, color: str, icon: str = "") -> str:
    icon_html = (f'<span style="font-size:0.78rem;">{icon}</span>'
                 if icon else "")
    return (
        f'<div style="background:white;border:1px solid {color}28;'
        f'border-radius:8px;padding:10px 12px;">'
        f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;'
        f'display:flex;align-items:center;gap:4px;">'
        f'{icon_html}{label}</div>'
        f'<div style="font-size:0.95rem;font-weight:700;color:#0c1a2e;'
        f'line-height:1.15;white-space:nowrap;">{value}</div>'
        f'</div>'
    )


def _stage_card_html(key: str, s: dict) -> str:
    meta = _SEG[key]
    color, bg, border = meta["color"], meta["bg"], meta["border"]

    metrics = [
        ("👥",  "Cabezas vendidas", f"{s['cab_vend']:,}"),
        ("⚖️", "Peso venta",       f"{s['kg_out']:.0f} kg"),
        ("💲", "Precio venta/kg",  f"USD {s['precio_venta']:.2f}"),
        ("📦", "Kg vendidos",      f"{s['kg_vendidos']:,.0f} kg"),
        ("💵", "Ingreso/cab",      f"USD {s['ingreso_cab']:,.1f}"),
        ("🧾", "Ingreso total",    f"USD {s['ingreso_total']:,.0f}"),
    ]
    tiles = "".join(_metric_tile(lbl, val, color, icon)
                    for icon, lbl, val in metrics)

    # Bloque especial Exportación
    export_block = ""
    if key == "eng_exp":
        bonif = s["bonificacion"]
        bonif_pct = (bonif / s["precio_venta"] * 100.0
                     if s["precio_venta"] > 0 else 0.0)
        bonif_str = (f"USD {bonif:.2f} (+{bonif_pct:.1f}%)"
                     if bonif > 0 else "—")
        export_metrics = [
            ("📈", "Rendim. carcasa",   f"{s['rendimiento']*100:.1f}%"),
            ("🥩", "Kg carcasa",        f"{s['kg_carcasa']:.0f} kg/cab"),
            ("🌐", "Precio exportación", f"USD {s['precio_export']:.2f}/kg"),
            ("✨", "Bonif. vs interno",  bonif_str),
        ]
        export_tiles = "".join(_metric_tile(lbl, val, color, icon)
                               for icon, lbl, val in export_metrics)

        export_block = (
            f'<div style="margin-top:14px;padding-top:12px;'
            f'border-top:1.5px dashed {color}55;">'
            f'<div style="font-size:0.66rem;font-weight:700;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'<span style="height:3px;width:14px;background:{color};'
            f'border-radius:2px;"></span>'
            f'🌐 Detalle exportación</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:8px;">{export_tiles}</div>'
            f'<div style="margin-top:10px;background:white;border:1px solid '
            f'{color}33;border-radius:8px;padding:10px 12px;">'
            f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-bottom:4px;">Ingreso ref. carcasa</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:#0c1a2e;'
            f'line-height:1.15;">USD {s["ingreso_carcasa_cab"]:,.1f} / cab '
            f'<span style="color:#94a3b8;font-size:0.78rem;font-weight:600;">'
            f'· Total USD {s["ingreso_carcasa_total"]:,.0f}</span></div>'
            f'</div>'
            f'</div>'
        )

    chip = (
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{s["dias"]} días · {s["mort_pct"]:.1f}% mort</span>'
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
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
        f'{tiles}</div>'
        f'{export_block}'
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


# ── Entry point ──────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Ingresos",
        "Visualización comercial: ventas, facturación, kilos comercializados "
        "y evolución del valor bruto del animal por etapa productiva.",
    )

    data = _build_ingresos()

    # ── Resumen superior ──────────────────────────────────────────────────
    section("Comparativa por etapa")
    _summary_kpis(data)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.plotly_chart(
        _bars_two_panels(data),
        use_container_width=True,
        key="ingresos_bars_compare",
    )

    st.divider()

    # ── Evolución del valor bruto ─────────────────────────────────────────
    section("Evolución del valor bruto del animal")
    st.plotly_chart(
        _value_evolution_chart(data),
        use_container_width=True,
        key="ingresos_value_evolution",
    )

    st.divider()

    # ── Detalle comercial por etapa ───────────────────────────────────────
    section("Detalle comercial por etapa")
    _stage_grid(data)
