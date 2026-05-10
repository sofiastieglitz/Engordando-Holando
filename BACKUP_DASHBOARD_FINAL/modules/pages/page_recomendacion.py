"""
Recomendación Estratégica — interpretación automática del negocio ganadero.

Sintetiza datos de Modelo Productivo, Costos, Ingresos, Margen Bruto y
Sensibilidad y Riesgo para emitir:
  - recomendación ejecutiva,
  - score estratégico ponderado por etapa,
  - matriz comparativa,
  - fortalezas y debilidades automáticas,
  - alertas estratégicas,
  - conclusión final.

Lee parámetros vía session_state y reutiliza las funciones de los modelos
económicos existentes (page_sensibilidad y page_margenes) sin modificarlos.
Mantiene la firma render(params, comp) por compatibilidad con el router.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st

from modules.pages.ui import page_header, section
from modules.pages import page_sensibilidad as ps
from modules.pages import page_margenes as pm

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Etapas y paletas ────────────────────────────────────────────────────────

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

_STAGES = ["cria", "recria", "eng_int", "eng_exp"]


# ── Dimensiones (key, label, icon, direction)
# direction: 'higher' = mayor es mejor; 'lower' = menor es mejor

_DIMENSIONS = [
    ("margen",     "Margen Bruto",        "💵", "higher"),
    ("roi",        "ROI operativo",       "📈", "higher"),
    ("robustez",   "Robustez",            "🛡",  "higher"),
    ("liquidez",   "Liquidez",            "💧", "higher"),
    ("riesgo",     "Riesgo (bajo)",       "⚠",  "lower"),
    ("capital",    "Capital requerido",   "🏦", "lower"),
    ("duracion",   "Duración ciclo",      "⏳", "lower"),
    ("sens_maiz",  "Sensibilidad maíz",   "🌽", "lower"),
]

_DIM_LABEL = {k: lbl for k, lbl, _, _ in _DIMENSIONS}
_DIM_ICON  = {k: ico for k, _, ico, _ in _DIMENSIONS}


# ── Presets de ponderación (deben sumar 100) ────────────────────────────────

_PRESETS: dict[str, dict[str, int]] = {
    "Conservador": {
        "margen": 5,  "roi": 5,  "robustez": 25, "liquidez": 20,
        "riesgo": 25, "capital": 10, "duracion": 5, "sens_maiz": 5,
    },
    "Balanceado": {  # 12 + 13 alternados → 100
        "margen": 12, "roi": 13, "robustez": 12, "liquidez": 13,
        "riesgo": 12, "capital": 13, "duracion": 12, "sens_maiz": 13,
    },
    "Agresivo": {
        "margen": 30, "roi": 25, "robustez": 5,  "liquidez": 5,
        "riesgo": 5,  "capital": 5,  "duracion": 5,  "sens_maiz": 20,
    },
    "Liquidez rápida": {
        "margen": 10, "roi": 10, "robustez": 5,  "liquidez": 30,
        "riesgo": 10, "capital": 10, "duracion": 20, "sens_maiz": 5,
    },
    "Maximizar margen": {
        "margen": 50, "roi": 20, "robustez": 5,  "liquidez": 5,
        "riesgo": 5,  "capital": 5,  "duracion": 5,  "sens_maiz": 5,
    },
}

_PRESET_DEFAULT = "Balanceado"


def _ensure_slider_state() -> None:
    """Inicializa los sliders con el preset Balanceado si no existen."""
    base = _PRESETS[_PRESET_DEFAULT]
    for k, _, _, _ in _DIMENSIONS:
        key = f"rec_w_{k}"
        if key not in st.session_state:
            st.session_state[key] = int(base[k])


def _apply_preset(preset_name: str) -> None:
    """Callback de botones de preset: actualiza session_state en sliders."""
    p = _PRESETS[preset_name]
    for k, val in p.items():
        st.session_state[f"rec_w_{k}"] = int(val)


def _get_weights() -> dict[str, int]:
    return {k: int(st.session_state.get(f"rec_w_{k}",
                                         _PRESETS[_PRESET_DEFAULT][k]))
            for k, _, _, _ in _DIMENSIONS}


# ── Recolección de datos desde Sensibilidad y Margen Bruto ──────────────────

def _gather_stage_data() -> dict:
    """
    Reutiliza los modelos económicos de page_sensibilidad y page_margenes
    para evitar duplicación. Devuelve un dict por etapa con todas las
    métricas necesarias para scoring.
    """
    sens = ps._build_sensibilidad()           # base + breakeven
    risk_rows = ps._build_risk_return(sens)   # robustez + sub-scores de riesgo
    risk_by_key = {r["key"]: r for r in risk_rows}
    marg = pm._build_margenes()               # margen, ROI, USD/cab/día

    out: dict = {}
    for k in _STAGES:
        s_se = sens[k]
        s_ri = risk_by_key[k]
        s_ma = marg[k]
        out[k] = {
            "title":              _SEG[k]["title"],
            "meta":               _SEG[k],
            # Dimensiones de scoring (raw)
            "margen":             s_ma["margen_bruto_cab"],
            "margen_total":       s_ma["margen_bruto_total"],
            "roi":                s_ma["roi_operativo"] * 100.0,   # %
            "robustez":           s_ri["robustness"],              # 0-100
            "liquidez":           (365.0 / s_se["dias"]
                                   if s_se["dias"] > 0 else 0.0),  # ciclos/año
            "riesgo":             s_ri["risk_composite"],          # 0-100
            "capital":            s_ma["costo_total"],             # USD
            "duracion":           s_se["dias"],                    # días
            "sens_maiz":          s_ri["score_maiz"],              # 0-100
            # Extras para texto
            "usd_cab_dia":        s_ma["usd_cab_dia"],
            "score_volatilidad":  s_ri["score_volatilidad"],
            "mort_pct":           s_se["mort_pct"],
            "cab_in":             s_se["cab_in"],
            "kg_out":             s_se["kg_out"],
        }
    return out


# ── Normalización 0-100 entre etapas ────────────────────────────────────────

def _normalize(values: list[float], direction: str) -> list[float]:
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-9:
        return [50.0] * len(values)
    if direction == "higher":
        return [(v - lo) / (hi - lo) * 100.0 for v in values]
    return [(hi - v) / (hi - lo) * 100.0 for v in values]


def _compute_dim_scores(data: dict) -> dict:
    """Para cada dimensión: dict de stage_key -> score 0-100 normalizado."""
    out: dict = {}
    for dim_key, _, _, direction in _DIMENSIONS:
        vals = [data[k][dim_key] for k in _STAGES]
        norm = _normalize(vals, direction)
        out[dim_key] = {_STAGES[i]: norm[i] for i in range(len(_STAGES))}
    return out


def _compute_strategic_scores(dim_scores: dict, weights: dict) -> dict:
    """Score estratégico por etapa = Σ(score_dim × peso) / Σpesos."""
    total_w = sum(weights.values())
    if total_w == 0:
        return {k: 0.0 for k in _STAGES}
    out = {}
    for k in _STAGES:
        s = sum(dim_scores[d][k] * weights[d]
                for d, _, _, _ in _DIMENSIONS)
        out[k] = s / total_w
    return out


def _winner(strat_scores: dict) -> tuple[str, str | None]:
    """Devuelve (top_key, runner_up_key_si_está_a_≤5_puntos)."""
    sorted_s = sorted(strat_scores.items(), key=lambda x: -x[1])
    top = sorted_s[0]
    if len(sorted_s) > 1:
        second = sorted_s[1]
        if (top[1] - second[1]) <= 5.0:
            return top[0], second[0]
    return top[0], None


# ── Fortalezas y debilidades ────────────────────────────────────────────────

_THRESH_FORTALEZA = 65.0
_THRESH_DEBILIDAD = 35.0


def _strengths_weaknesses(dim_scores: dict) -> dict:
    """Por etapa: top-4 fortalezas (score ≥ 65) y debilidades (score ≤ 35)."""
    out = {}
    for k in _STAGES:
        fort, debi = [], []
        for dim_key, label, icon, _ in _DIMENSIONS:
            score = dim_scores[dim_key][k]
            if score >= _THRESH_FORTALEZA:
                fort.append((score, label, icon))
            elif score <= _THRESH_DEBILIDAD:
                debi.append((score, label, icon))
        fort.sort(key=lambda x: -x[0])
        debi.sort(key=lambda x: x[0])
        out[k] = {"fortalezas": fort[:4], "debilidades": debi[:4]}
    return out


# ── Alertas estratégicas auto-generadas ─────────────────────────────────────

def _generate_alerts(data: dict, dim_scores: dict, strat_scores: dict) -> list[dict]:
    alerts: list[dict] = []

    # 1. Margen negativo
    for k in _STAGES:
        if data[k]["margen"] <= 0:
            alerts.append({
                "icon": "🚨", "level": "critical",
                "msg": (f"<b>{data[k]['title']}</b> opera con margen negativo "
                        f"(USD {data[k]['margen']:+,.0f}/cab)."),
            })

    # 2. Sensibilidad al maíz
    most_maiz = max(_STAGES, key=lambda k: data[k]["sens_maiz"])
    if data[most_maiz]["sens_maiz"] >= 50:
        alerts.append({
            "icon": "🌽", "level": "warning",
            "msg": (f"Negocio muy sensible al precio del maíz en "
                    f"<b>{data[most_maiz]['title']}</b> "
                    f"(score {data[most_maiz]['sens_maiz']:.0f}/100). "
                    f"Coberturas o contratos a precio fijo recomendados."),
        })

    # 3. Volatilidad alta
    most_vol = max(_STAGES, key=lambda k: data[k]["score_volatilidad"])
    if data[most_vol]["score_volatilidad"] >= 70:
        alerts.append({
            "icon": "📊", "level": "warning",
            "msg": (f"<b>{data[most_vol]['title']}</b> presenta alta "
                    f"volatilidad de margen "
                    f"(score {data[most_vol]['score_volatilidad']:.0f}/100)."),
        })

    # 4. Mejor estabilidad
    most_robust = max(_STAGES, key=lambda k: data[k]["robustez"])
    alerts.append({
        "icon": "🛡", "level": "good",
        "msg": (f"<b>{data[most_robust]['title']}</b> muestra la mejor "
                f"estabilidad económica "
                f"(robustez {data[most_robust]['robustez']:.0f}/100)."),
    })

    # 5. Capital alto
    avg_cap = sum(data[k]["capital"] for k in _STAGES) / len(_STAGES)
    most_cap = max(_STAGES, key=lambda k: data[k]["capital"])
    if data[most_cap]["capital"] > avg_cap * 1.5:
        alerts.append({
            "icon": "🏦", "level": "info",
            "msg": (f"<b>{data[most_cap]['title']}</b> requiere alta inversión "
                    f"de capital "
                    f"(USD {data[most_cap]['capital']:,.0f})."),
        })

    # 6. Engorde interno requiere alta eficiencia
    eng_int = data["eng_int"]
    if eng_int["sens_maiz"] >= 50 and eng_int["duracion"] >= 300:
        alerts.append({
            "icon": "🎯", "level": "warning",
            "msg": ("<b>Engorde interno</b> requiere alta eficiencia de "
                    "conversión para amortizar el ciclo largo y la "
                    "exposición al precio del maíz."),
        })

    # 7. Mortandad alta
    most_mort = max(_STAGES, key=lambda k: data[k]["mort_pct"])
    if data[most_mort]["mort_pct"] >= 4.0:
        alerts.append({
            "icon": "⚠", "level": "warning",
            "msg": (f"<b>{data[most_mort]['title']}</b> tiene mortandad "
                    f"elevada ({data[most_mort]['mort_pct']:.1f}%). "
                    f"Reforzar sanidad y manejo."),
        })

    # 8. Top score estratégico (positivo)
    top_strat = max(strat_scores, key=strat_scores.get)
    alerts.append({
        "icon": "🏆", "level": "good",
        "msg": (f"Según tus ponderaciones, <b>{data[top_strat]['title']}</b> "
                f"obtiene el mayor score estratégico "
                f"(<b>{strat_scores[top_strat]:.0f}/100</b>)."),
    })

    return alerts


# ── Conclusión final auto-generada ──────────────────────────────────────────

def _build_conclusion(data: dict, strat_scores: dict, dim_scores: dict) -> str:
    top_key, runner_up = _winner(strat_scores)
    top = data[top_key]

    # Top-3 dimensiones donde la ganadora destaca
    top_dims = sorted(
        [(dim_key, dim_scores[dim_key][top_key])
         for dim_key, _, _, _ in _DIMENSIONS
         if dim_scores[dim_key][top_key] >= 60],
        key=lambda x: -x[1],
    )[:4]
    if top_dims:
        labels = [_DIM_LABEL[dk].lower() for dk, _ in top_dims]
        bullets = ", ".join(f"<b>{lbl}</b>" for lbl in labels)
    else:
        bullets = "<b>combinación equilibrada</b> de dimensiones"

    if runner_up is not None:
        runner = data[runner_up]
        intro = (
            f"En el escenario actual, <b>{top['title']}</b> y "
            f"<b>{runner['title']}</b> presentan la mejor combinación "
            f"según tus ponderaciones, con scores muy similares "
            f"({strat_scores[top_key]:.0f} vs "
            f"{strat_scores[runner_up]:.0f}/100). Ambas estrategias son "
            f"recomendables — la elección final depende de las restricciones "
            f"operativas y financieras del productor."
        )
    else:
        intro = (
            f"En el escenario actual, <b>{top['title']}</b> presenta la "
            f"mejor combinación entre las dimensiones ponderadas, "
            f"con un score estratégico de "
            f"<b>{strat_scores[top_key]:.0f}/100</b>."
        )

    detalle = (
        f"Sus ventajas principales son: {bullets}. "
        f"Margen bruto de <b>USD {top['margen']:+,.0f}/cab</b>, "
        f"ROI operativo de <b>{top['roi']:.1f}%</b>, "
        f"capital comprometido <b>USD {top['capital']:,.0f}</b>, "
        f"ciclo de <b>{int(top['duracion'])} días</b>."
    )

    return f"{intro}<br><br>{detalle}"


# ── Render: hero ────────────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 80: return "#16a34a"
    if score >= 60: return "#65a30d"
    if score >= 40: return "#d97706"
    return "#dc2626"


def _render_hero(data: dict, strat_scores: dict) -> None:
    top_key, runner_up = _winner(strat_scores)
    top = data[top_key]
    color = top["meta"]["color"]
    score = strat_scores[top_key]

    if runner_up is not None:
        runner = data[runner_up]
        rcolor = runner["meta"]["color"]
        title_html = (
            f'<span style="color:{color};">{top["meta"]["icon"]} '
            f'{top["title"].upper()}</span>'
            f' <span style="color:#94a3b8;font-weight:600;">+</span> '
            f'<span style="color:{rcolor};">{runner["meta"]["icon"]} '
            f'{runner["title"].upper()}</span>'
        )
        sub_text = (
            f'Top-2 con scores muy similares: '
            f'<b style="color:{color};">{score:.0f}/100</b> · '
            f'<b style="color:{rcolor};">'
            f'{strat_scores[runner_up]:.0f}/100</b>'
        )
    else:
        title_html = (
            f'<span style="color:{color};">{top["meta"]["icon"]} '
            f'{top["title"].upper()}</span>'
        )
        sub_text = (
            f'Score estratégico: '
            f'<b style="color:{color};">{score:.0f} / 100</b>'
        )

    st.markdown(
        f"""<div style="background:linear-gradient(135deg,{color}14,{color}05);
                    border:2px solid {color}55;border-radius:18px;
                    padding:26px 32px;margin-bottom:18px;">
            <div style="font-size:0.70rem;font-weight:700;color:{color};
                        text-transform:uppercase;letter-spacing:0.12em;
                        margin-bottom:8px;">
                Estrategia recomendada actualmente
            </div>
            <div style="font-size:2rem;font-weight:800;line-height:1.1;
                        letter-spacing:-0.03em;margin-bottom:12px;">
                {title_html}
            </div>
            <div style="font-size:0.92rem;color:#475569;line-height:1.5;">
                {sub_text}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Render: panel de ponderación ────────────────────────────────────────────

def _render_weighting_panel() -> dict:
    """Renderiza presets + sliders y devuelve los pesos actuales."""
    # Presets
    st.markdown(
        '<p style="font-size:0.66rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.07em;'
        'margin:0 0 6px 0;">Presets estratégicos</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(_PRESETS))
    preset_icons = {
        "Conservador":      "🛡",
        "Balanceado":       "⚖",
        "Agresivo":         "🚀",
        "Liquidez rápida":  "💧",
        "Maximizar margen": "💰",
    }
    for col, name in zip(cols, _PRESETS.keys()):
        with col:
            st.button(
                f"{preset_icons[name]} {name}",
                key=f"rec_preset_{name}",
                on_click=_apply_preset, args=(name,),
                width="stretch",
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Sliders en 2 columnas
    st.markdown(
        '<p style="font-size:0.66rem;font-weight:700;color:#7a8fa6;'
        'text-transform:uppercase;letter-spacing:0.07em;'
        'margin:6px 0 6px 0;">Ponderaciones (%)</p>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, (k, label, icon, _) in enumerate(_DIMENSIONS):
        with cols[i % 2]:
            st.slider(
                f"{icon} {label}",
                min_value=0, max_value=100, step=1,
                key=f"rec_w_{k}",
            )

    weights = _get_weights()
    total = sum(weights.values())

    if total == 100:
        st.success(f"✅ Total ponderación = **100%**", icon="✅")
    elif total < 100:
        st.warning(
            f"⚠ Total ponderación = **{total}%** "
            f"(faltan {100 - total} pp para llegar a 100%). "
            f"El score se normaliza automáticamente, pero conviene ajustar."
        )
    else:
        st.warning(
            f"⚠ Total ponderación = **{total}%** "
            f"(supera 100% por {total - 100} pp). "
            f"El score se normaliza automáticamente."
        )

    return weights


# ── Render: 4 cards de score estratégico por etapa ──────────────────────────

def _render_strategic_score_cards(data: dict, strat_scores: dict,
                                   dim_scores: dict) -> None:
    cols = st.columns(4, gap="small")
    sorted_keys = sorted(_STAGES, key=lambda k: -strat_scores[k])
    rank_map = {k: i + 1 for i, k in enumerate(sorted_keys)}
    medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: ""}

    for col, k in zip(cols, _STAGES):
        meta = data[k]["meta"]
        score = strat_scores[k]
        sc_color = _score_color(score)
        rank = rank_map[k]
        medal = medals.get(rank, "")

        # Top-3 dimensiones de la etapa
        top_dims = sorted(
            [(_DIM_LABEL[dk], _DIM_ICON[dk], dim_scores[dk][k])
             for dk, _, _, _ in _DIMENSIONS],
            key=lambda x: -x[2],
        )[:3]
        bars = ""
        for label, icon, val in top_dims:
            bar_color = _score_color(val)
            bars += (
                f'<div style="margin-bottom:5px;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:0.66rem;color:#475569;margin-bottom:2px;">'
                f'<span>{icon} {label}</span>'
                f'<span style="color:{bar_color};font-weight:700;">'
                f'{val:.0f}</span></div>'
                f'<div style="background:#eef2f7;border-radius:3px;height:5px;'
                f'overflow:hidden;">'
                f'<div style="background:{bar_color};height:100%;'
                f'width:{min(100, val):.1f}%;border-radius:3px;"></div>'
                f'</div></div>'
            )

        col.markdown(
            f"""<div style="background:white;border:1px solid {meta['border']};
                        border-radius:14px;overflow:hidden;
                        box-shadow:0 1px 6px rgba(13,27,66,0.06);
                        height:100%;">
                <div style="background:linear-gradient(135deg,
                            {meta['color']},{meta['color']}dd);
                            padding:11px 16px;color:white;
                            display:flex;justify-content:space-between;
                            align-items:center;gap:8px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:1.05rem;">{meta['icon']}</span>
                        <span style="font-size:0.86rem;font-weight:700;">
                            {meta['title']}</span>
                    </div>
                    <span style="background:rgba(255,255,255,0.22);
                                 border-radius:14px;padding:3px 8px;
                                 font-size:0.65rem;font-weight:700;
                                 white-space:nowrap;">
                        {medal} #{rank}</span>
                </div>
                <div style="padding:14px 16px 14px;text-align:center;">
                    <div style="font-size:0.62rem;font-weight:700;color:#7a8fa6;
                                text-transform:uppercase;letter-spacing:0.07em;">
                        Score estratégico
                    </div>
                    <div style="font-size:2.2rem;font-weight:800;
                                color:{sc_color};line-height:1;
                                letter-spacing:-0.03em;margin:4px 0 6px;">
                        {score:.0f}<span style="font-size:0.95rem;
                            color:#94a3b8;font-weight:600;"> / 100</span>
                    </div>
                    <div style="border-top:1px solid #f0f4fa;
                                margin-top:10px;padding-top:10px;
                                text-align:left;">
                        <div style="font-size:0.58rem;color:#94a3b8;
                                    font-weight:700;text-transform:uppercase;
                                    letter-spacing:0.05em;margin-bottom:6px;">
                            Top dimensiones
                        </div>
                        {bars}
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )


# ── Render: matriz comparativa multi-dimensional ────────────────────────────

def _format_dim_value(dim_key: str, raw: float) -> str:
    """Formato amigable del valor crudo de cada dimensión."""
    if dim_key == "margen":
        return f"USD {raw:+,.0f}"
    if dim_key == "roi":
        return f"{raw:+.1f}%"
    if dim_key in ("robustez", "riesgo", "sens_maiz"):
        return f"{raw:.0f}/100"
    if dim_key == "liquidez":
        return f"{raw:.1f} c/año"
    if dim_key == "capital":
        return f"USD {raw:,.0f}"
    if dim_key == "duracion":
        return f"{int(raw)} d"
    return f"{raw}"


def _render_strategic_matrix(data: dict, dim_scores: dict) -> None:
    th_base = ('padding:11px 12px;font-size:0.62rem;font-weight:700;'
               'color:#7a8fa6;text-transform:uppercase;letter-spacing:0.07em;'
               'background:#f8fafd;border-bottom:1.5px solid #e4eaf4;')
    th_l = th_base + 'text-align:left;'
    th_c = th_base + 'text-align:center;'

    headers = ""
    for dim_key, label, icon, _ in _DIMENSIONS:
        headers += f'<th style="{th_c}">{icon} {label}</th>'

    body = ""
    for i, k in enumerate(_STAGES):
        meta = data[k]["meta"]
        bg_row = "#ffffff" if i % 2 == 0 else "#fbfcfe"

        modelo_cell = (
            f'<td style="padding:13px 14px;background:{bg_row};'
            f'border-bottom:1px solid #f0f4fa;min-width:160px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div style="width:30px;height:30px;border-radius:7px;'
            f'background:{meta["color"]}1f;display:flex;'
            f'align-items:center;justify-content:center;'
            f'font-size:0.95rem;flex-shrink:0;">{meta["icon"]}</div>'
            f'<span style="font-size:0.84rem;font-weight:800;color:#0c1a2e;">'
            f'{meta["title"]}</span></div></td>'
        )

        cells = ""
        for dim_key, _, _, _ in _DIMENSIONS:
            raw = data[k][dim_key]
            score = dim_scores[dim_key][k]
            sc_color = _score_color(score)
            value_str = _format_dim_value(dim_key, raw)
            cells += (
                f'<td style="padding:13px 12px;background:{bg_row};'
                f'border-bottom:1px solid #f0f4fa;text-align:center;'
                f'vertical-align:middle;min-width:110px;">'
                f'<div style="font-size:0.78rem;font-weight:700;color:#0c1a2e;'
                f'line-height:1.1;font-variant-numeric:tabular-nums;">'
                f'{value_str}</div>'
                f'<div style="background:#eef2f7;border-radius:3px;height:4px;'
                f'overflow:hidden;margin-top:5px;">'
                f'<div style="background:{sc_color};height:100%;'
                f'width:{min(100, score):.1f}%;border-radius:3px;"></div>'
                f'</div>'
                f'<div style="font-size:0.58rem;color:{sc_color};'
                f'font-weight:700;margin-top:2px;">{score:.0f}/100</div>'
                f'</td>'
            )

        body += f'<tr>{modelo_cell}{cells}</tr>'

    st.markdown(
        f'<div style="background:white;border:1px solid #e4eaf4;'
        f'border-radius:14px;overflow-x:auto;'
        f'box-shadow:0 2px 10px rgba(13,27,66,0.06);">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:Inter,Arial,sans-serif;min-width:1100px;">'
        f'<thead><tr><th style="{th_l}">Modelo</th>{headers}</tr></thead>'
        f'<tbody>{body}</tbody>'
        f'</table>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Render: fortalezas y debilidades por etapa ──────────────────────────────

def _render_pros_cons(data: dict, sw: dict) -> None:
    cols = st.columns(2, gap="small")
    for i, k in enumerate(_STAGES):
        with cols[i % 2]:
            meta = data[k]["meta"]
            color = meta["color"]
            fort = sw[k]["fortalezas"]
            debi = sw[k]["debilidades"]

            fort_html = ""
            if fort:
                for score, label, icon in fort:
                    fort_html += (
                        f'<div style="display:flex;align-items:center;gap:8px;'
                        f'padding:5px 0;font-size:0.80rem;color:#166534;">'
                        f'<span style="color:#16a34a;font-weight:700;">✓</span> '
                        f'<span style="font-size:0.78rem;">{icon}</span>'
                        f'<span>{label}</span>'
                        f'<span style="margin-left:auto;color:#16a34a;'
                        f'font-weight:700;font-size:0.74rem;'
                        f'font-variant-numeric:tabular-nums;">'
                        f'{score:.0f}</span></div>'
                    )
            else:
                fort_html = (
                    '<div style="padding:6px 0;font-size:0.76rem;'
                    'color:#94a3b8;font-style:italic;">'
                    'Sin fortalezas destacadas vs. peers</div>'
                )

            debi_html = ""
            if debi:
                for score, label, icon in debi:
                    debi_html += (
                        f'<div style="display:flex;align-items:center;gap:8px;'
                        f'padding:5px 0;font-size:0.80rem;color:#991b1b;">'
                        f'<span style="color:#dc2626;font-weight:700;">✗</span> '
                        f'<span style="font-size:0.78rem;">{icon}</span>'
                        f'<span>{label}</span>'
                        f'<span style="margin-left:auto;color:#dc2626;'
                        f'font-weight:700;font-size:0.74rem;'
                        f'font-variant-numeric:tabular-nums;">'
                        f'{score:.0f}</span></div>'
                    )
            else:
                debi_html = (
                    '<div style="padding:6px 0;font-size:0.76rem;'
                    'color:#94a3b8;font-style:italic;">'
                    'Sin debilidades críticas vs. peers</div>'
                )

            st.markdown(
                f"""<div style="background:#f8fafd;border:1px solid #e4eaf4;
                            border-radius:14px;overflow:hidden;
                            box-shadow:0 1px 6px rgba(13,27,66,0.05);
                            margin-bottom:14px;">
                    <div style="background:linear-gradient(135deg,
                                {color},{color}dd);
                                padding:11px 16px;color:white;
                                display:flex;align-items:center;gap:8px;">
                        <span style="font-size:1.05rem;">{meta['icon']}</span>
                        <span style="font-size:0.92rem;font-weight:700;">
                            {meta['title']}</span>
                    </div>
                    <div style="padding:14px 16px;
                                display:grid;grid-template-columns:1fr 1fr;
                                gap:14px;">
                        <div>
                            <div style="font-size:0.62rem;color:#16a34a;
                                        font-weight:800;text-transform:uppercase;
                                        letter-spacing:0.06em;margin-bottom:5px;">
                                ✓ Fortalezas
                            </div>
                            {fort_html}
                        </div>
                        <div>
                            <div style="font-size:0.62rem;color:#dc2626;
                                        font-weight:800;text-transform:uppercase;
                                        letter-spacing:0.06em;margin-bottom:5px;">
                                ✗ Debilidades
                            </div>
                            {debi_html}
                        </div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


# ── Render: alertas estratégicas ────────────────────────────────────────────

def _alert_style(level: str) -> tuple[str, str]:
    return {
        "critical": ("#dc2626", "#fef2f2"),
        "warning":  ("#d97706", "#fffbeb"),
        "info":     ("#1565c0", "#eff6ff"),
        "good":     ("#16a34a", "#f0fdf4"),
    }.get(level, ("#64748b", "#f1f5f9"))


def _render_alerts(alerts: list[dict]) -> None:
    for a in alerts:
        color, bg = _alert_style(a["level"])
        st.markdown(
            f'<div style="background:{bg};border:1px solid {color}55;'
            f'border-left:4px solid {color};border-radius:8px;'
            f'padding:11px 14px;margin-bottom:8px;'
            f'display:flex;align-items:flex-start;gap:11px;">'
            f'<span style="font-size:1.05rem;flex-shrink:0;line-height:1.4;">'
            f'{a["icon"]}</span>'
            f'<span style="font-size:0.85rem;color:#0c1a2e;'
            f'line-height:1.45;">{a["msg"]}</span></div>',
            unsafe_allow_html=True,
        )


# ── Render: conclusión final ────────────────────────────────────────────────

def _render_conclusion(text: str) -> None:
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#f0f9ff,#eff6ff);'
        f'border:1.5px solid #bfdbfe;border-radius:14px;'
        f'padding:22px 28px;font-size:0.95rem;line-height:1.7;'
        f'color:#1e3a5f;">'
        f'<div style="font-size:0.66rem;color:#1565c0;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">'
        f'📌 Conclusión final</div>'
        f'{text}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Entry point ─────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Recomendación Estratégica",
        "Síntesis e interpretación automática del negocio: ponderá las "
        "dimensiones que más te importan y obtené la estrategia recomendada "
        "según tu perfil.",
    )

    # Inicializar estado de sliders ANTES de leer pesos
    _ensure_slider_state()

    # 1. Datos derivados de Sensibilidad y Margen Bruto
    data = _gather_stage_data()
    dim_scores = _compute_dim_scores(data)

    # 2. Leer pesos actuales del session_state (= última interacción del usuario)
    weights = _get_weights()
    strat_scores = _compute_strategic_scores(dim_scores, weights)

    # 3. Hero de recomendación (siempre arriba, refleja el último input)
    _render_hero(data, strat_scores)

    # 4. Panel de ponderación + presets (sliders triggerean rerun)
    section("Ponderación estratégica")
    _render_weighting_panel()

    st.divider()

    # 5. Score estratégico por etapa (4 cards)
    section("Score estratégico por etapa")
    _render_strategic_score_cards(data, strat_scores, dim_scores)

    st.divider()

    # 6. Matriz estratégica (tabla 4×8)
    section("Matriz estratégica")
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 12px 0;">'
        'Comparación multi-dimensional con valor crudo, barra de score '
        '0–100 normalizado entre etapas, y rating numérico.'
        '</p>',
        unsafe_allow_html=True,
    )
    _render_strategic_matrix(data, dim_scores)

    st.divider()

    # 7. Fortalezas y debilidades
    section("Fortalezas y debilidades por etapa")
    sw = _strengths_weaknesses(dim_scores)
    _render_pros_cons(data, sw)

    st.divider()

    # 8. Alertas estratégicas
    section("Alertas estratégicas")
    alerts = _generate_alerts(data, dim_scores, strat_scores)
    _render_alerts(alerts)

    st.divider()

    # 9. Conclusión final
    _render_conclusion(_build_conclusion(data, strat_scores, dim_scores))
