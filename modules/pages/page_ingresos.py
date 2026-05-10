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


def _g(key: str, default: float) -> float:
    return float(st.session_state.get(key, default))


# ── Modelo comercial ─────────────────────────────────────────────────────────

def _build_ingresos() -> dict:
    """
    Calcula los datos comerciales por las 3 etapas productivas.

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
    a_kg_in   = S.kg_in_for("cria")
    a_kg_out  = S.kg_out_for("cria")
    a_dias    = int(_g(K.A_DIAS,          DEFAULTS["d_dias"]))
    a_mort    = _g(K.A_MORTALIDAD,        DEFAULTS["d_mortalidad"])
    a_pv      = _g(K.A_PRECIO_VENTA,      DEFAULTS["d_precio_venta"])

    # ── Recría ────────────────────────────────────────────────────────────
    b_kg_in   = S.kg_in_for("recria")
    b_kg_out  = S.kg_out_for("recria")
    b_dias    = int(_g(K.B_DIAS,          DEFAULTS["b_dias"]))
    b_mort    = _g(K.B_MORTALIDAD,        DEFAULTS["r_mortalidad"])
    b_pv      = _g(K.B_PRECIO_VENTA,      DEFAULTS["r_precio_venta"])

    # ── Engorde ────────────────────────────────────────────────────────────
    c_kg_in   = S.kg_in_for("eng_int")
    c_kg_out  = S.kg_out_for("eng_int")
    c_dias    = int(_g(K.C_DIAS,          DEFAULTS["c_dias"]))
    c_mort    = _g(K.C_MORTALIDAD,        DEFAULTS["t_mortalidad"])
    c_pv      = _g(K.C_PRECIO_VENTA,      DEFAULTS["t_precio_venta"])

    # ── Cabezas: cascada sólo entre etapas activas ─────────────────────────
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

    def block(kg_in: float, kg_out: float, dias: int, mort_pct: float,
              cab_in: int, precio_venta: float, active: bool) -> dict:
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
            "active": active,
        }

    data = {
        "cria":    block(a_kg_in,  a_kg_out, a_dias, a_mort, cab_in_cria,    a_pv,
                         S.is_active("cria")),
        "recria":  block(b_kg_in,  b_kg_out, b_dias, b_mort, cab_in_recria,  b_pv,
                         S.is_active("recria")),
        "eng_int": block(c_kg_in,  c_kg_out, c_dias, c_mort, cab_in_eng_int, c_pv,
                         S.is_active("eng_int")),
    }

    return data


# ── 1. Resumen superior — KPIs comparativas ──────────────────────────────────

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
            f'text-transform:uppercase;letter-spacing:0.07em;">Ingreso / cab</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:#0c1a2e;'
            f'line-height:1.1;letter-spacing:-0.02em;margin:2px 0 10px;">'
            f'USD&nbsp;{s["ingreso_cab"]:,.1f}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:8px;border-top:1px solid #f0f4fa;padding-top:9px;">'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["ingreso_total"]:,.0f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Ingreso Total</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">{s["cab_vend"]:,} cab</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Vendidas</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">USD&nbsp;{s["precio_venta"]:.2f}</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Precio /kg</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#1e3a5f;'
            f'line-height:1.2;">{s["kg_vendidos"]:,.0f} kg</div>'
            f'<div style="font-size:0.60rem;font-weight:700;color:#94a3b8;'
            f'text-transform:uppercase;letter-spacing:0.05em;'
            f'margin-top:1px;">Kg vendidos</div>'
            f'</div>'
            f'</div>'
            f'<div style="margin-top:10px;padding-top:8px;'
            f'border-top:1px solid #f0f4fa;text-align:center;">'
            f'<span style="font-size:0.72rem;color:#475569;font-weight:600;">'
            f'⚖️ {s["kg_out"]:.0f} kg/cab</span>'
            f'</div>'
            f'</div></div>'
        )
        col.markdown(card_html, unsafe_allow_html=True)


# ── Gráfico comparativo principal ────────────────────────────────────────────

def _bars_two_panels(data: dict) -> go.Figure:
    """Dos paneles lado a lado: Ingreso/cab y Ingreso total por etapa ACTIVA."""
    from plotly.subplots import make_subplots

    stages = S.active_stages()
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
    """Curva continua del valor bruto del animal (USD/cab) sobre las etapas
    ACTIVAS. Arranca en el ingreso a la 1ª etapa activa (peso × precio_compra
    de esa etapa) y termina en la venta de la última.
    """
    active = S.active_stages()
    fig = go.Figure()
    if not active:
        fig.add_annotation(
            text="Sin etapas activas — activá al menos una en Parámetros",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=14, color="#94a3b8"),
        )
        fig.update_layout(height=520, plot_bgcolor="rgba(248,250,252,1)",
                          paper_bgcolor="rgba(0,0,0,0)")
        return fig

    # Precio de compra contextual según primera etapa activa
    pc_global = _g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])
    b_pc      = _g(K.B_PRECIO_COMPRA,         DEFAULTS["b_pc"])
    c_pc      = _g(K.C_PRECIO_COMPRA,         DEFAULTS["c_pc"])
    pc_first = {"cria": pc_global, "recria": b_pc, "eng_int": c_pc}[active[0]]

    fills = {
        "cria":    "rgba(22,163,74,0.08)",
        "recria":  "rgba(21,101,192,0.08)",
        "eng_int": "rgba(13,148,136,0.08)",
    }

    # Construir timeline acumulado y valores por etapa activa
    xs: list[float] = [0]
    ys: list[float] = [data[active[0]]["kg_in"] * pc_first]
    stage_segments: list[tuple[str, float, float]] = []
    t = 0
    for stage in active:
        s = data[stage]
        t0 = t
        t += s["dias"]
        xs.append(t)
        ys.append(s["kg_out"] * s["precio_venta"])
        stage_segments.append((stage, t0, t))
    t_total = t

    # Bandas y divisores entre etapas activas
    for stage, t0, t1 in stage_segments:
        fig.add_vrect(x0=t0, x1=t1, fillcolor=fills[stage],
                      layer="below", line_width=0)
    for _, _, t1 in stage_segments[:-1]:
        fig.add_vline(x=t1, line_dash="dot",
                      line_color="rgba(100,116,139,0.30)", line_width=1.5)

    # Halo + curva principal
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color="rgba(124,58,237,0.18)", width=14,
                  shape="spline", smoothing=0.5),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color="#7c3aed", width=3.5,
                  shape="spline", smoothing=0.5),
        marker=dict(size=12, color="#7c3aed", symbol="circle",
                    line=dict(color="white", width=3)),
        showlegend=False,
        hovertemplate="<b>Día %{x}</b><br>Valor: USD %{y:,.0f}/cab<extra></extra>",
    ))

    # Hitos contextuales
    first_stage = active[0]
    start_color = "#94a3b8"
    start_label = {"cria": "🐣 Compra ternero",
                   "recria": "🐂 Compra recriado",
                   "eng_int": "🐂 Compra engorde"}[first_stage]
    transition_label = {
        ("cria", "recria"):    ("🥛 Destete",    "#16a34a"),
        ("recria", "eng_int"): ("🔵 Fin recría", "#1565c0"),
    }
    end_pretty = {"cria": "destete", "recria": "recriado",
                  "eng_int": "final"}[active[-1]]

    milestones: list[tuple[float, float, str, str]] = [
        (0, ys[0], start_label, start_color),
    ]
    for i in range(len(active) - 1):
        prev_s, next_s = active[i], active[i + 1]
        label, color = transition_label.get((prev_s, next_s),
                                             ("📍 Transición", "#64748b"))
        milestones.append((stage_segments[i][2], ys[i + 1], label, color))
    milestones.append((t_total, ys[-1], f"💰 Venta {end_pretty}", "#0d9488"))

    for x, y, label, color in milestones:
        fig.add_annotation(
            x=x, y=y,
            text=(f"<b>{label}</b>"
                  f"<br><span style='color:#475569;font-size:9px;'>"
                  f"USD {y:,.0f} · día {x:.0f}</span>"),
            showarrow=True, arrowhead=0, arrowwidth=1,
            arrowcolor="rgba(124,58,237,0.4)",
            ax=0, ay=-50,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor=color, borderwidth=1, borderpad=5,
        )

    # Etiquetas de etapa bajo el eje X (sólo activas)
    stage_pretty = {
        "cria":    ("🌱 Cría",    "#16a34a"),
        "recria":  ("🔵 Recría",  "#1565c0"),
        "eng_int": ("🟢 Engorde", "#0d9488"),
    }
    for stage, t0, t1 in stage_segments:
        name, color = stage_pretty[stage]
        fig.add_annotation(
            x=(t0 + t1) / 2, y=-0.18, xref="x", yref="paper",
            text=(f"<b style='color:{color};'>{name}</b>"
                  f"<br><span style='color:#94a3b8;font-size:9px;'>"
                  f"{int(t1 - t0)} días</span>"),
            showarrow=False, font=dict(size=11), align="center",
        )

    fig.update_layout(
        height=520,
        margin=dict(t=80, b=110, l=80, r=40),
        xaxis=dict(
            title=None,
            range=[-15, t_total + 25],
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
    is_active = s.get("active", True)

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

    header_bg = (f"linear-gradient(135deg,{color},{color}dd)"
                 if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")
    chip = (
        f'<span style="background:rgba(255,255,255,0.22);'
        f'border-radius:14px;padding:3px 10px;font-size:0.68rem;'
        f'font-weight:700;white-space:nowrap;">'
        f'{s["dias"]} días · {s["mort_pct"]:.1f}% mort</span>'
        if is_active else
        '<span style="background:rgba(255,255,255,0.22);'
        'border-radius:14px;padding:3px 10px;font-size:0.62rem;'
        'font-weight:700;white-space:nowrap;">INACTIVA</span>'
    )
    card_bg     = bg if is_active else "#f8fafc"
    card_border = border if is_active else "#e2e8f0"

    return (
        f'<div style="background:{card_bg};border:1px solid {card_border};'
        f'border-radius:14px;overflow:hidden;'
        f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;">'
        f'<div style="background:{header_bg};'
        f'padding:13px 16px;color:white;display:flex;'
        f'justify-content:space-between;align-items:center;gap:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.15rem;">{meta["icon"]}</span>'
        f'<span style="font-size:0.95rem;font-weight:700;">{meta["title"]}</span>'
        f'</div>{chip}</div>'
        f'<div style="padding:14px 14px 16px;">'
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
                f'<div style="opacity:{opacity};">'
                f'{_stage_card_html(key, data[key])}</div>',
                unsafe_allow_html=True,
            )
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
