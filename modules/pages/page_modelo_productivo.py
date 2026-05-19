"""
Modelo Productivo — Visualización del flujo biológico y operativo del animal
a lo largo del ciclo productivo:

    Nacimiento → Cría → Recría → Engorde
    (el destete es un hito dentro de Cría, no una etapa separada)

La página tiene dos bloques:
  1. Curva de crecimiento continua con hitos biológicos.
  2. Cards por etapa productiva (animales + alimentos).
"""
from __future__ import annotations
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


# ── Stage metadata ────────────────────────────────────────────────────────────

_SEG = {
    "cria":    ("Cría",    "🌱", "#16a34a"),
    "recria":  ("Recría",  "🔵", "#1565c0"),
    "eng_int": ("Engorde", "🟢", "#0d9488"),
}

_FILLS = {
    "cria":    ("rgba(22,163,74,0.08)",   "#f0fdf4", "#bbf7d0"),
    "recria":  ("rgba(21,101,192,0.08)",  "#eff6ff", "#bfdbfe"),
    "eng_int": ("rgba(13,148,136,0.08)",  "#f0fdfa", "#99f6e4"),
}

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convierte '#RRGGBB' a 'rgba(r,g,b,alpha)' para propiedades Plotly
    que NO aceptan el formato hex de 8 caracteres (#RRGGBBAA)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Stage data reader ─────────────────────────────────────────────────────────

def _read_stages() -> dict:
    """Lee parámetros por etapa. kg_in respeta lógica modular (S.kg_in_for).
    GDP es input del usuario. La conversión alimenticia (CA) es DERIVADA
    de la tabla de ración: CA = consumo_MS_dia / GDP. El consumo MS, MV
    y el costo también son derivados desde la tabla (kg TC × %MS × USD/kg MS).
    """
    return {
        "cria": {
            "kg_in":   S.kg_in_for("cria"),
            "kg_out":  S.kg_out_for("cria"),
            "dias":    D.dias_for("cria"),
            "mort":    float(read(K.A_MORTALIDAD,   DEFAULTS["d_mortalidad"])),
            "gdp":     float(read(K.A_GDP,          DEFAULTS["a_gdp"])),
            "ca":      D.ca_for("cria"),
            "active":  S.is_active("cria"),
        },
        "recria": {
            "kg_in":   S.kg_in_for("recria"),
            "kg_out":  S.kg_out_for("recria"),
            "dias":    D.dias_for("recria"),
            "mort":    float(read(K.B_MORTALIDAD,   DEFAULTS["r_mortalidad"])),
            "gdp":     float(read(K.B_GDP,          DEFAULTS["r_gdp"])),
            "ca":      D.ca_for("recria"),
            "active":  S.is_active("recria"),
        },
        "eng_int": {
            "kg_in":   S.kg_in_for("eng_int"),
            "kg_out":  S.kg_out_for("eng_int"),
            "dias":    D.dias_for("eng_int"),
            "mort":    float(read(K.C_MORTALIDAD,   DEFAULTS["t_mortalidad"])),
            "gdp":     float(read(K.C_GDP,          DEFAULTS["t_gdp"])),
            "ca":      D.ca_for("eng_int"),
            "active":  S.is_active("eng_int"),
        },
    }


# Lectura de la tabla de alimentación: vive en `modules.state.derived`.
# `D.feed_df_active(stage)` devuelve filas con Ingrediente, Kg TC, %MS,
# Kg MS y USD/kg MS para los ingredientes cargados.


# ── Growth chart — flujo biológico continuo ──────────────────────────────────

def _build_chart(d: dict) -> go.Figure:
    """Curva continua del peso vivo sobre las etapas ACTIVAS.

    El timeline arranca en el ingreso a la 1ª etapa activa y termina en la
    venta de la última. Las etapas se concatenan; los pesos se encadenan
    automáticamente (kg_out de una = kg_in de la siguiente). Los hitos
    biológicos se etiquetan según el rol de cada punto en el slice activo
    (ej. "🥛 Destete" aparece sólo si Cría y Recría están activas).
    """
    active = S.active_stages()
    fig = go.Figure()
    if not active:
        fig.add_annotation(
            text="Sin etapas activas — activá al menos una en Parámetros",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=14, color="#94a3b8"),
        )
        fig.update_layout(height=560, plot_bgcolor="rgba(248,250,252,1)",
                          paper_bgcolor="rgba(0,0,0,0)")
        return fig

    # ── Construir timeline acumulado y puntos ──────────────────────────────
    xs: list[float] = [0]
    ys: list[float] = [d[active[0]]["kg_in"]]
    stage_segments: list[tuple[str, float, float]] = []  # (stage, t0, t1)

    t = 0
    for stage in active:
        s = d[stage]
        t0 = t
        t += s["dias"]
        xs.append(t)
        ys.append(s["kg_out"])
        stage_segments.append((stage, t0, t))
    t_total = t

    # ── 1. Bandas de fondo por etapa activa ────────────────────────────────
    for stage, t0, t1 in stage_segments:
        fig.add_vrect(x0=t0, x1=t1, fillcolor=_FILLS[stage][0],
                      layer="below", line_width=0)

    # ── 2. Divisores entre etapas activas consecutivas ─────────────────────
    for _, _, t1 in stage_segments[:-1]:
        fig.add_vline(x=t1, line_dash="dot",
                      line_color="rgba(100,116,139,0.30)", line_width=1.5)

    # ── 3. Curva de crecimiento (halo + línea principal con spline) ────────
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color="rgba(21,101,192,0.18)", width=14,
                  shape="spline", smoothing=0.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines+markers",
        line=dict(color="#1565c0", width=3.5,
                  shape="spline", smoothing=0.5),
        marker=dict(size=12, color="#1565c0", symbol="circle",
                    line=dict(color="white", width=3)),
        showlegend=False,
        hovertemplate="<b>Día %{x}</b><br>Peso: %{y:.0f} kg<extra></extra>",
    ))

    # ── 4. Hitos biológicos contextuales según slice activo ────────────────
    # Punto inicial
    first_stage = active[0]
    if first_stage == "cria":
        start_label, start_color = "🐣 Nacimiento", "#16a34a"
    elif first_stage == "recria":
        start_label, start_color = "🐂 Ingreso Recría", "#1565c0"
    else:  # eng_int
        start_label, start_color = "🐂 Ingreso Engorde", "#0d9488"
    milestones: list[tuple[float, float, str, str]] = [
        (0, ys[0], start_label, start_color),
    ]
    # Puntos intermedios entre etapas activas
    transition_label = {
        ("cria", "recria"):   ("🥛 Destete",        "#1565c0"),
        ("recria", "eng_int"): ("🟢 Inicio Engorde", "#0d9488"),
    }
    for i in range(len(active) - 1):
        prev_s, next_s = active[i], active[i + 1]
        label, color = transition_label.get(
            (prev_s, next_s), ("📍 Transición", "#64748b")
        )
        x = stage_segments[i][2]
        # ys[i+1] coincide con kg_out de stage i = kg_in de stage i+1
        milestones.append((x, ys[i + 1], label, color))
    # Punto final
    end_color = "#b91c1c"
    last_stage = active[-1]
    end_pretty = {"cria": "destete", "recria": "recriado",
                  "eng_int": "final"}[last_stage]
    milestones.append((t_total, ys[-1], f"💰 Venta {end_pretty}", end_color))

    for x, y, label, color in milestones:
        fig.add_annotation(
            x=x, y=y,
            text=(f"<b>{label}</b>"
                  f"<br><span style='color:#475569;font-size:9px;'>"
                  f"{y:.0f} kg · día {x:.0f}</span>"),
            showarrow=True,
            arrowhead=0, arrowwidth=1, arrowcolor=_hex_to_rgba(color, 0.6),
            ax=0, ay=-50,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor=color,
            borderwidth=1,
            borderpad=5,
        )

    # ── 5. Labels de etapa BAJO el eje X (sólo activas) ────────────────────
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
            showarrow=False,
            font=dict(size=11),
            align="center",
        )

    fig.update_layout(
        height=560,
        margin=dict(t=80, b=110, l=70, r=40),
        xaxis=dict(
            title=None,
            range=[-15, t_total + 25],
            gridcolor="#eef2f7",
            zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            ticksuffix=" d",
        ),
        yaxis=dict(
            title=dict(text="Peso vivo (kg/animal)",
                       font=dict(size=12, color="#475569")),
            gridcolor="#eef2f7",
            zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            ticksuffix=" kg",
        ),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter, Arial, sans-serif"),
        hovermode="x unified",
    )
    return fig


# ── Sección Animales (grid moderno de 8 métricas) ────────────────────────────

def _animals_section_html(
    cabezas: int, dias: int, kg_in: float, kg_out: float,
    gdp: float, mort: float, conv: float, consumo: float,
    color: str,
) -> str:
    metrics = [
        ("🐄", "Cabezas",       f"{cabezas:,}",   "cab"),
        ("📅", "Días",          f"{dias}",        "días"),
        ("⚖️", "Peso entrada",  f"{kg_in:.0f}",   "kg"),
        ("⚖️", "Peso salida",   f"{kg_out:.0f}",  "kg"),
        ("📈", "GDP",           f"{gdp:.3f}",     "kg/día"),
        ("⚠️", "Mortandad",     f"{mort:.1f}",    "%"),
        ("🔄", "Conversión",    f"{conv:.2f}",    "kg/kg"),
        ("🌾", "Consumo MS",    f"{consumo:.0f}", "kg/cab"),
    ]
    items = ""
    for icon, label, value, unit in metrics:
        items += (
            f'<div style="background:white;border:1px solid {color}28;'
            f'border-radius:8px;padding:9px 11px;">'
            f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;'
            f'display:flex;align-items:center;gap:4px;">'
            f'<span style="font-size:0.78rem;">{icon}</span>{label}</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:#0c1a2e;'
            f'line-height:1.1;white-space:nowrap;">{value}'
            f'<span style="font-size:0.65rem;color:#94a3b8;font-weight:600;'
            f'margin-left:3px;">{unit}</span></div>'
            f'</div>'
        )
    return (
        f'<div>'
        f'<div style="font-size:0.66rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:6px;">'
        f'<span style="height:3px;width:14px;background:{color};border-radius:2px;"></span>'
        f'🐂 Animales</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">'
        f'{items}</div></div>'
    )


# ── Sección Alimentos (tabla 6 columnas) ─────────────────────────────────────

def _feed_section_html(stage: str, dias: int, color: str) -> str:
    """Tabla de ingredientes — kg TC/día, kg MS/día, kg MS/etapa y USD/etapa.

    Los valores vienen directamente de la tabla cargada por el usuario
    (modelo nutricional puro). NO se reparte vía % de participación.
    """
    df = D.feed_df_active(stage)

    header = (
        f'<div style="font-size:0.66rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:6px;">'
        f'<span style="height:3px;width:14px;background:{color};border-radius:2px;"></span>'
        f'🌾 Alimentos</div>'
    )

    if df.empty:
        return (
            f'<div style="margin-top:16px;">{header}'
            f'<div style="border:1.5px dashed {color}33;border-radius:8px;'
            f'padding:14px 12px;text-align:center;color:#94a3b8;'
            f'font-size:0.74rem;line-height:1.4;">'
            f'Sin ingredientes cargados<br>'
            f'<span style="font-size:0.66rem;">Definí en Parámetros → Alimentación</span>'
            f'</div></div>'
        )

    rows_html = ""
    total_tc_dia = 0.0
    total_ms_dia = 0.0
    total_usd_etapa = 0.0
    for i, (_, r) in enumerate(df.iterrows()):
        name      = str(r["Ingrediente"]).strip()
        kg_tc_dia = float(r["Kg TC"])
        pms       = float(r["%MS"])
        kg_ms_dia = float(r["Kg MS"])
        usd_kg    = float(r["USD/kg MS"])

        kg_ms_etapa = kg_ms_dia * max(dias, 0)
        usd_etapa   = kg_ms_etapa * usd_kg

        total_tc_dia    += kg_tc_dia
        total_ms_dia    += kg_ms_dia
        total_usd_etapa += usd_etapa

        bg = "rgba(255,255,255,0.6)" if i % 2 == 0 else "transparent"
        cell = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                'color:#374151;white-space:nowrap;')
        cell_l = ('padding:5px 6px;font-size:0.74rem;text-align:left;'
                  'color:#0c1a2e;font-weight:600;white-space:nowrap;'
                  'overflow:hidden;text-overflow:ellipsis;max-width:90px;')
        cell_strong = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                       'color:#0c1a2e;font-weight:700;white-space:nowrap;')

        rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="{cell_l}" title="{name}">{name}</td>'
            f'<td style="{cell}">{kg_tc_dia:.2f}</td>'
            f'<td style="{cell}">{pms:.1f}%</td>'
            f'<td style="{cell}">{kg_ms_dia:.2f}</td>'
            f'<td style="{cell}">{kg_ms_etapa:.0f}</td>'
            f'<td style="{cell_strong}">{usd_etapa:.2f}</td>'
            f'</tr>'
        )

    # Fila TOTAL en pie de tabla
    tf_base = ('padding:6px 6px;font-size:0.74rem;font-weight:800;'
               'color:#0c1a2e;font-variant-numeric:tabular-nums;'
               'white-space:nowrap;')
    tf_l = tf_base + 'text-align:left;'
    tf_r = tf_base + 'text-align:right;'
    total_row = (
        f'<tr style="background:{color}10;border-top:1.5px solid {color}33;">'
        f'<td style="{tf_l}">TOTAL</td>'
        f'<td style="{tf_r}">{total_tc_dia:.2f}</td>'
        f'<td style="{tf_r}">—</td>'
        f'<td style="{tf_r}">{total_ms_dia:.2f}</td>'
        f'<td style="{tf_r}">{total_ms_dia * max(dias, 0):.0f}</td>'
        f'<td style="{tf_r}">{total_usd_etapa:,.2f}</td>'
        f'</tr>'
    )

    th_base = (f'padding:5px 6px;font-size:0.60rem;font-weight:700;'
               f'color:{color};white-space:nowrap;text-transform:uppercase;'
               f'letter-spacing:0.04em;')
    th_l = th_base + 'text-align:left;'
    th_r = th_base + 'text-align:right;'

    return (
        f'<div style="margin-top:16px;">{header}'
        f'<div style="overflow-x:auto;border-radius:8px;">'
        f'<table style="width:100%;min-width:380px;border-collapse:collapse;">'
        f'<thead><tr style="background:{color}18;'
        f'border-bottom:1.5px solid {color}33;">'
        f'<th style="{th_l}">Ingrediente</th>'
        f'<th style="{th_r}">kg TC/día</th>'
        f'<th style="{th_r}">%MS</th>'
        f'<th style="{th_r}">kg MS/día</th>'
        f'<th style="{th_r}">kg MS/etapa</th>'
        f'<th style="{th_r}">USD/etapa</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}{total_row}</tbody>'
        f'</table></div></div>'
    )


# ── Cards por etapa productiva ───────────────────────────────────────────────

def _consistency_warnings_html(
    gdp: float, gdp_der: float,
    rel_tol: float = 0.05,
) -> str:
    """Warning si el GDP cargado difiere del derivado por kg/dias.
    La conversión es ahora la ÚNICA fuente del consumo (no hay derivado
    independiente que validar contra ella)."""
    items: list[str] = []
    if gdp > 0 and abs(gdp_der - gdp) / gdp > rel_tol:
        items.append(
            f"⚠ GDP derivado ({gdp_der:.3f}) difiere del cargado ({gdp:.3f})"
        )
    if not items:
        return ""
    rows = "".join(
        f'<div style="font-size:0.66rem;color:#b45309;line-height:1.4;">{x}</div>'
        for x in items
    )
    return (
        f'<div style="background:#fffbeb;border:1px solid #fde68a;'
        f'border-radius:8px;padding:7px 10px;margin-top:10px;">{rows}</div>'
    )


def _stage_cabezas(d: dict, n_t: int) -> dict[str, int]:
    """Cabezas por etapa respetando que la mortandad sólo se aplica entre
    etapas activas consecutivas (el slice activo arranca con n_t).
    Etapas inactivas: 0 (se atenúan en la UI)."""
    def surv(n: int, mort_pct: float) -> int:
        return max(int(n * (1 - mort_pct / 100)), 0)

    active = S.active_stages()
    cab: dict[str, int] = {"cria": 0, "recria": 0, "eng_int": 0}
    if not active:
        return cab
    cab[active[0]] = n_t
    for i in range(1, len(active)):
        prev_s = active[i - 1]
        cab[active[i]] = surv(cab[prev_s], d[prev_s]["mort"])
    return cab


def _segment_cards(d: dict) -> None:
    n_t = int(read(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    cab = _stage_cabezas(d, n_t)

    cols = st.columns(3, gap="small")
    for col, key in zip(cols, ["cria", "recria", "eng_int"]):
        title, icon, color = _SEG[key]
        _, bg, border = _FILLS[key]
        s = d[key]
        is_active = s["active"]

        kg_in   = s["kg_in"]
        kg_out  = s["kg_out"]
        kg_prod = max(kg_out - kg_in, 0.0)
        dias    = s["dias"]

        # Métricas principales: VALORES CARGADOS (fuente de verdad)
        gdp  = s["gdp"]
        conv = s["ca"]

        # Consumo y ración: DERIVADOS bioeconómicamente
        consumo  = kg_prod * max(conv, 0.0)
        rac_dia  = (consumo / dias) if dias > 0 else 0.0

        # Validación técnica: GDP derivada del kg/día
        gdp_der = (kg_prod / dias) if dias > 0 else 0.0

        animals_html = _animals_section_html(
            cabezas=cab[key], dias=dias, kg_in=kg_in, kg_out=kg_out,
            gdp=gdp, mort=s["mort"], conv=conv, consumo=consumo,
            color=color,
        )
        if is_active:
            warnings_html = _consistency_warnings_html(gdp, gdp_der)
        else:
            warnings_html = ""
        feed_html = _feed_section_html(
            stage=key, dias=dias, color=color,
        )

        # Atenuado para etapas inactivas
        card_opacity = "1" if is_active else "0.42"
        card_bg      = bg if is_active else "#f8fafc"
        card_border  = border if is_active else "#e2e8f0"
        header_bg    = (f"linear-gradient(135deg,{color},{color}dd)"
                        if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")
        inactive_badge = (
            '' if is_active else
            '<span style="background:rgba(255,255,255,0.22);'
            'border-radius:14px;padding:3px 10px;font-size:0.62rem;'
            'font-weight:700;white-space:nowrap;flex-shrink:0;">INACTIVA</span>'
        )
        right_chip = (
            f'<div style="background:rgba(255,255,255,0.22);'
            f'border-radius:14px;padding:3px 10px;font-size:0.70rem;'
            f'font-weight:700;white-space:nowrap;flex-shrink:0;">'
            f'{dias} días</div>'
            if is_active else inactive_badge
        )

        # HTML sin indentación inicial: Markdown trata 4+ espacios al inicio
        # de línea como bloque de código y muestra los tags como texto crudo.
        card_html = (
            f'<div style="background:{card_bg};border:1px solid {card_border};'
            f'border-radius:14px;padding:0;overflow:hidden;'
            f'box-shadow:0 1px 6px rgba(13,27,66,0.05);'
            f'height:100%;opacity:{card_opacity};">'
            f'<div style="background:{header_bg};padding:13px 16px;color:white;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;gap:8px;">'
            f'<div style="display:flex;align-items:center;gap:8px;min-width:0;">'
            f'<span style="font-size:1.15rem;flex-shrink:0;">{icon}</span>'
            f'<span style="font-size:0.95rem;font-weight:700;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{title}</span>'
            f'</div>'
            f'{right_chip}'
            f'</div></div>'
            f'<div style="padding:14px 14px 16px;">'
            f'{animals_html}{warnings_html}{feed_html}'
            f'</div></div>'
        )
        with col:
            st.markdown(card_html, unsafe_allow_html=True)


# ── Sección Consumos diarios (MS · MV · por ingrediente) ─────────────────────

def _kpi_card_html(label: str, value: str, unit: str, color: str) -> str:
    return (
        f'<div style="background:white;border:1px solid {color}28;'
        f'border-radius:8px;padding:10px 12px;text-align:left;">'
        f'<div style="font-size:0.62rem;color:{color};font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;">'
        f'{label}</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:#0c1a2e;'
        f'line-height:1.1;font-variant-numeric:tabular-nums;'
        f'white-space:nowrap;">{value}'
        f'<span style="font-size:0.65rem;color:#94a3b8;font-weight:600;'
        f'margin-left:4px;">{unit}</span></div>'
        f'</div>'
    )


def _consumo_ingredientes_table_html(stage: str, n_cab: int,
                                     color: str) -> str:
    """Tabla por ingrediente con kg MS/día/cab, kg MV/día/cab y kg MV/día rodeo."""
    df = D.consumo_ingredientes(stage)
    if df.empty or D.consumo_ms_dia_cab(stage) <= 0:
        return (
            f'<div style="border:1.5px dashed {color}33;border-radius:8px;'
            f'padding:14px 12px;text-align:center;color:#94a3b8;'
            f'font-size:0.74rem;line-height:1.4;margin-top:8px;">'
            f'Sin consumo calculable<br>'
            f'<span style="font-size:0.66rem;">'
            f'Cargá GDP, conversión y la ración en Parámetros</span>'
            f'</div>'
        )

    rows_html = ""
    for i, (_, r) in enumerate(df.iterrows()):
        name      = str(r["Ingrediente"]).strip()
        pms       = float(r["%MS"])
        kg_ms_cab = float(r["kg_MS_dia"])
        kg_mv_cab = float(r["kg_MV_dia"])
        kg_mv_rod = kg_mv_cab * max(n_cab, 0)
        bg = "rgba(255,255,255,0.6)" if i % 2 == 0 else "transparent"
        cell  = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                 'color:#374151;white-space:nowrap;')
        cell_l = ('padding:5px 6px;font-size:0.74rem;text-align:left;'
                  'color:#0c1a2e;font-weight:600;white-space:nowrap;'
                  'overflow:hidden;text-overflow:ellipsis;max-width:90px;')
        cell_strong = ('padding:5px 6px;font-size:0.72rem;text-align:right;'
                       'color:#0c1a2e;font-weight:700;white-space:nowrap;')
        rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="{cell_l}" title="{name}">{name}</td>'
            f'<td style="{cell}">{pms:.1f}%</td>'
            f'<td style="{cell}">{kg_ms_cab:.2f}</td>'
            f'<td style="{cell}">{kg_mv_cab:.2f}</td>'
            f'<td style="{cell_strong}">{kg_mv_rod:,.0f}</td>'
            f'</tr>'
        )

    th_base = (f'padding:5px 6px;font-size:0.58rem;font-weight:700;'
               f'color:{color};white-space:nowrap;text-transform:uppercase;'
               f'letter-spacing:0.04em;')
    th_l = th_base + 'text-align:left;'
    th_r = th_base + 'text-align:right;'

    return (
        f'<div style="overflow-x:auto;border-radius:8px;margin-top:10px;">'
        f'<table style="width:100%;min-width:380px;border-collapse:collapse;">'
        f'<thead><tr style="background:{color}18;'
        f'border-bottom:1.5px solid {color}33;">'
        f'<th style="{th_l}">Ingrediente</th>'
        f'<th style="{th_r}">%MS</th>'
        f'<th style="{th_r}">kg MS/d cab</th>'
        f'<th style="{th_r}">kg MV/d cab</th>'
        f'<th style="{th_r}">kg MV/d rodeo</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )


def _consumos_section(d: dict) -> None:
    """Sección 'Consumos diarios' por etapa activa.

    Por etapa muestra 4 KPIs (MS/cab, MS rodeo, MV/cab, MV rodeo) y una
    tabla con consumo desagregado por ingrediente (kg MV/día/cab y rodeo).
    Todos los valores se calculan en `modules.state.derived` (única fuente).
    """
    n_t = int(read(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
    cab_por_etapa = _stage_cabezas(d, n_t)

    cols = st.columns(3, gap="small")
    for col, stage in zip(cols, ["cria", "recria", "eng_int"]):
        title, icon, color = _SEG[stage]
        _, bg, border = _FILLS[stage]
        is_active = d[stage]["active"]

        n_cab = cab_por_etapa[stage]
        ms_cab = D.consumo_ms_dia_cab(stage)
        mv_cab = D.consumo_mv_dia_cab(stage)
        ms_rodeo = ms_cab * max(n_cab, 0)
        mv_rodeo = mv_cab * max(n_cab, 0)
        pms_pond = D.pct_ms_promedio(stage)

        # Estado nutricional general
        if ms_cab <= 0:
            badge = ('Falta cargar GDP / Conversión',
                     "#94a3b8", "rgba(255,255,255,0.18)")
        elif pms_pond <= 0:
            badge = ('Falta %MS para calcular MV',
                     "#fde68a", "rgba(255,255,255,0.18)")
        else:
            badge = (f'%MS pond: {pms_pond:.1f}%',
                     "#ffffff", "rgba(255,255,255,0.22)")

        kpis_html = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:6px;">'
            f'{_kpi_card_html("MS / cab", f"{ms_cab:.2f}", "kg/día", color)}'
            f'{_kpi_card_html("MS rodeo", f"{ms_rodeo:,.0f}", "kg/día", color)}'
            f'{_kpi_card_html("MV / cab", f"{mv_cab:.2f}", "kg/día", color)}'
            f'{_kpi_card_html("MV rodeo", f"{mv_rodeo:,.0f}", "kg/día", color)}'
            f'</div>'
        )

        table_html = (
            _consumo_ingredientes_table_html(stage, n_cab, color)
            if is_active else
            '<div style="border:1.5px dashed #cbd5e1;border-radius:8px;'
            'padding:14px;text-align:center;color:#94a3b8;font-size:0.72rem;'
            'margin-top:8px;">Etapa desactivada</div>'
        )

        card_opacity = "1" if is_active else "0.42"
        card_bg      = bg if is_active else "#f8fafc"
        card_border  = border if is_active else "#e2e8f0"
        header_bg    = (f"linear-gradient(135deg,{color},{color}dd)"
                        if is_active else "linear-gradient(135deg,#94a3b8,#cbd5e1)")

        card_html = (
            f'<div style="background:{card_bg};border:1px solid {card_border};'
            f'border-radius:14px;overflow:hidden;'
            f'box-shadow:0 1px 6px rgba(13,27,66,0.05);height:100%;'
            f'opacity:{card_opacity};">'
            f'<div style="background:{header_bg};padding:11px 14px;color:white;'
            f'display:flex;justify-content:space-between;align-items:center;'
            f'gap:8px;">'
            f'<div style="display:flex;align-items:center;gap:8px;min-width:0;">'
            f'<span style="font-size:1.05rem;flex-shrink:0;">{icon}</span>'
            f'<span style="font-size:0.92rem;font-weight:700;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{title}</span></div>'
            f'<span style="background:{badge[2]};border-radius:14px;'
            f'padding:3px 10px;font-size:0.62rem;font-weight:700;'
            f'color:{badge[1]};white-space:nowrap;">{badge[0]}</span>'
            f'</div>'
            f'<div style="padding:13px 14px 14px;">'
            f'{kpis_html}{table_html}'
            f'</div></div>'
        )
        with col:
            st.markdown(card_html, unsafe_allow_html=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Modelo Productivo",
        "Evolución biológica del animal: nacimiento → cría → recría → engorde.",
    )

    d = _read_stages()

    section("Curva de crecimiento — del nacimiento a la venta")
    st.plotly_chart(_build_chart(d), use_container_width=True)

    st.divider()

    section("Etapas productivas")
    _segment_cards(d)

    st.divider()

    section("Consumos diarios — MS · MV · por ingrediente")
    st.caption("Derivados automáticos de la tabla de ración: "
               "kg MS/cab = Σ (kg TC × %MS/100); kg MV/cab = Σ kg TC. "
               "Total rodeo = consumo/cab × cabezas activas en la etapa.")
    _consumos_section(d)
