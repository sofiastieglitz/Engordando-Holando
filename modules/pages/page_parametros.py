"""
Parámetros — sección General fija + 9 tabs por categoría económico/productiva.

Estructura: la solapa principal es la CATEGORÍA; dentro de cada solapa se
muestran 3 cards (Cría · Recría · Engorde).

Tabs:
    🛒 Compra hacienda · 🌾 Alimentación · 💉 Sanidad · 👷 Operación
    🏗 Estructura · 💰 Comercialización · 🏦 Financieros · ⚠️ Mortandad
    💵 Venta hacienda
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

import streamlit as st
import pandas as pd

import modules.state.keys as K
import modules.state.stages as S
import modules.state.derived as D
from modules.state.defaults import DEFAULTS
from modules.state.persist import (
    mirror, reset_to_defaults,
    get_editor_state, save_editor_state,
    read,
)
from modules.pages.ui import page_header
from modules.sidebar import _info

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Segment metadata ──────────────────────────────────────────────────────────

_SEG = {
    "cria":    ("Cría",    "🌱", "#16a34a"),
    "recria":  ("Recría",  "🔵", "#1565c0"),
    "eng_int": ("Engorde", "🟢", "#0d9488"),
}

_STAGE_ORDER = ["cria", "recria", "eng_int"]


# ── UI helpers (consistentes con el estilo del dashboard) ─────────────────────

def _card_header(title: str, icon: str, color: str) -> None:
    st.markdown(
        f'<div style="background:{color}14;border-left:4px solid {color};'
        f'border-radius:0 8px 8px 0;padding:10px 16px;margin-bottom:14px;">'
        f'<span style="font-size:1.05rem;font-weight:700;color:{color};">'
        f'{icon}&nbsp;&nbsp;{title}</span></div>',
        unsafe_allow_html=True,
    )


def _hint(text: str) -> None:
    st.markdown(
        f'<p style="font-size:0.68rem;color:#94a3b8;font-style:italic;'
        f'margin:0 0 6px 0;line-height:1.3;">{text}</p>',
        unsafe_allow_html=True,
    )


def _num(label: str, key: str, default: float,
         lo: float | None = None, hi: float | None = None,
         step: float = 1.0, fmt: str = "%.2f") -> float:
    """number_input con persistencia bulletproof entre slides.

    Política del dashboard: cualquier número, sin mínimo ni máximo
    (los parámetros `lo`/`hi` se aceptan por compat histórica y se ignoran).

    Diseño de persistencia
    ──────────────────────
    El bug histórico: usábamos `key=<canonical>` directo en el widget.
    Cuando el usuario navegaba a otra slide, Streamlit purgaba el estado
    interno del widget (incluyendo la entrada en `_old_state`). Al volver
    a Parámetros, restore_from_backing repoblaba ss[canonical] desde el
    shadow, pero el widget igual se renderizaba con su default de tipo
    (0.0) porque Streamlit no re-sincroniza ss[canonical] → estado
    interno del widget cuando éste fue purgado.

    Fix: el widget usa una key efímera (`_w_<canonical>`); el shadow
    `_persist_<canonical>` es la fuente de verdad. En cada render:
      1. Leemos `cval` del shadow vía `read()` (con fallback a default).
      2. Escribimos `ss[widget_key] = cval` ANTES de instanciar el widget
         (permitido: el widget aún no se registró en este rerun).
      3. El widget renderiza usando `ss[widget_key]` = cval.
      4. Si el usuario cambia el valor, Streamlit dispara `on_change`,
         que copia widget → shadow (vía `mirror`). El próximo rerun
         leerá el nuevo valor desde el shadow.

    Como el widget-key (`_w_<canonical>`) puede ser purgado libremente
    sin que se pierda el dato (lo recuperamos siempre desde el shadow),
    Streamlit GC nunca rompe la persistencia.
    """
    del lo, hi  # restricciones desactivadas por política del proyecto
    cval = float(read(key, float(default)))
    widget_key = "_w_" + key

    def _sync_back() -> None:
        new_val = float(st.session_state[widget_key])
        mirror(key, new_val)
        # Best-effort: mantener ss[key] en sync para código viejo que
        # pueda leer ss[key] directo. Si la key tiene mapper stale a un
        # widget instanciado este rerun, Streamlit rechaza; lo ignoramos.
        try:
            st.session_state[key] = new_val
        except Exception:
            pass

    # Pre-render: shadow → widget key.
    st.session_state[widget_key] = cval

    st.number_input(
        label,
        min_value=None,
        max_value=None,
        step=float(step),
        format=fmt,
        key=widget_key,
        on_change=_sync_back,
    )
    return cval


def _inactive_placeholder() -> None:
    """Marcador visual para etapas desactivadas dentro de cualquier tab."""
    st.markdown(
        '<div style="background:#f8fafc;border:1px dashed #cbd5e1;'
        'border-radius:8px;padding:14px;text-align:center;color:#94a3b8;'
        'font-size:0.74rem;line-height:1.4;">'
        '🚫 Etapa desactivada<br>'
        '<span style="font-size:0.66rem;">Activala arriba para configurarla</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _three_stage_columns(render_fn: Callable[[str, str], None]) -> None:
    """Layout estándar: 3 columnas (Cría · Recría · Engorde), card header
    por etapa, contenido provisto por render_fn(stage_key, color). Si la
    etapa no está activa, muestra placeholder y omite el renderizado."""
    cols = st.columns(3, gap="small")
    for col, key in zip(cols, _STAGE_ORDER):
        title, icon, color = _SEG[key]
        with col:
            _card_header(title, icon, color)
            if S.is_active(key):
                render_fn(key, color)
            else:
                _inactive_placeholder()


# ── Feed table helpers (sin cambios respecto a la versión anterior) ───────────

def _empty_feed_table() -> pd.DataFrame:
    return pd.DataFrame({
        "Ingrediente": [""]  * 10,
        "Kg TC":       [0.0] * 10,
        "%MS":         [0.0] * 10,
        "Kg MS":       [0.0] * 10,
        "USD/kg MS":   [0.0] * 10,
    })


def _feed_table_block(table_key: str, *,
                      gdp: float, dias: int,
                      color: str) -> None:
    """Tabla editable de ingredientes (modelo nutricional Kg TC).

    Schema:
        Ingrediente · Kg TC (kg/cab/día) · %MS · Kg MS (calc) · USD/kg MS

    Derivados (en el panel debajo de la tabla):
        Kg MS_i           = Kg TC_i × %MS_i/100
        consumo_MS_dia    = Σ Kg MS_i
        consumo_MV_dia    = Σ Kg TC_i
        consumo_MS_ciclo  = consumo_MS_dia × días
        consumo_MV_ciclo  = consumo_MV_dia × días
        costo_dia_cab     = Σ (Kg MS_i × USD/kg MS_i)
        costo_ciclo_cab   = costo_dia_cab × días
        CA (derivada)     = consumo_MS_dia / GDP
        Eficiencia        = GDP / consumo_MS_dia
        precio_pond       = costo_dia_cab / consumo_MS_dia
        %MS_pond          = consumo_MS_dia / consumo_MV_dia × 100
    """
    editor_key = table_key + "_de"
    st.caption("**Composición de la ración** — definí ingredientes y "
               "kg consumidos *tal cual* por animal por día. "
               "Kg MS se calcula automáticamente.")

    # ── Inicialización con migración de esquema ──────────────────────────
    # `D.migrate_feed_df` dropea cualquier columna "%" legacy, asegura
    # las 5 columnas canónicas y recalcula Kg MS = Kg TC × %MS/100.
    stored = get_editor_state(editor_key)
    if (editor_key not in st.session_state
            and isinstance(stored, pd.DataFrame)):
        initial_df = D.migrate_feed_df(stored, rows=10)
    else:
        initial_df = _empty_feed_table()

    edited = st.data_editor(
        initial_df,
        key=editor_key,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        disabled=["Kg MS"],
        column_config={
            "Ingrediente": st.column_config.TextColumn(
                "Ingrediente", width="medium",
            ),
            "Kg TC": st.column_config.NumberColumn(
                "Kg TC", min_value=0.0,
                step=0.1, format="%.2f",
                help=("Kg tal cual consumidos por animal y por día "
                      "(MV: como sale del silo/bolsa)."),
            ),
            "%MS": st.column_config.NumberColumn(
                "%MS", min_value=0.0, max_value=100.0,
                step=0.5, format="%.1f",
                help=("Materia seca del ingrediente. "
                      "Kg MS = Kg TC × %MS / 100."),
            ),
            "Kg MS": st.column_config.NumberColumn(
                "Kg MS", format="%.3f",
                help="Calculado: Kg TC × %MS / 100. No editable.",
            ),
            "USD/kg MS": st.column_config.NumberColumn(
                "USD/kg MS", min_value=0.0, step=0.001, format="%.3f",
            ),
        },
    )

    # Recalcular Kg MS sobre el DataFrame editado y persistir COMPLETO al shadow.
    edited = edited.copy()
    kg_tc_col = pd.to_numeric(edited["Kg TC"], errors="coerce").fillna(0.0).clip(lower=0.0)
    pms_col   = pd.to_numeric(edited["%MS"],   errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
    edited["Kg MS"] = (kg_tc_col * pms_col / 100.0).astype(float)
    save_editor_state(editor_key, edited)

    # ── Cascada derivada (cab/día y cab/ciclo) ───────────────────────────
    usd_col   = pd.to_numeric(edited["USD/kg MS"], errors="coerce").fillna(0.0).clip(lower=0.0)
    name_col  = edited["Ingrediente"].astype(str).str.strip()
    mask      = (name_col != "") & (kg_tc_col > 0)

    mv_dia    = float(kg_tc_col[mask].sum())
    ms_dia    = float((kg_tc_col[mask] * pms_col[mask] / 100.0).sum())
    costo_dia = float((kg_tc_col[mask] * pms_col[mask] / 100.0
                       * usd_col[mask]).sum())

    mv_ciclo    = mv_dia    * dias
    ms_ciclo    = ms_dia    * dias
    costo_ciclo = costo_dia * dias

    ca_der    = (ms_dia / gdp) if gdp > 0 else 0.0
    efic_der  = (gdp / ms_dia) if ms_dia > 0 else 0.0
    p_pond    = (costo_dia / ms_dia) if ms_dia > 0 else 0.0
    pms_pond  = (ms_dia / mv_dia * 100.0) if mv_dia > 0 else 0.0

    # ── Fila TOTAL visual ──────────────────────────────────────────────────
    total_color = color
    total_row_html = (
        f'<div style="background:{total_color}10;border:1px solid {total_color}33;'
        f'border-radius:8px;padding:8px 12px;margin-top:6px;'
        f'display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:8px;'
        f'font-size:0.78rem;align-items:center;">'
        f'<div style="font-weight:800;color:{total_color};'
        f'text-transform:uppercase;letter-spacing:0.06em;font-size:0.66rem;">'
        f'TOTAL ración (cab/día)</div>'
        f'<div style="text-align:right;color:#0c1a2e;font-weight:700;'
        f'font-variant-numeric:tabular-nums;">{mv_dia:.2f} kg TC</div>'
        f'<div style="text-align:right;color:#0c1a2e;font-weight:700;'
        f'font-variant-numeric:tabular-nums;">{ms_dia:.2f} kg MS</div>'
        f'<div></div>'
        f'</div>'
    )
    st.markdown(total_row_html, unsafe_allow_html=True)

    # ── Panel resumen nutricional + económico ─────────────────────────────
    ms_msg_color = "#16a34a" if ms_dia > 0 else "#b45309"
    ms_msg       = ("(MS calculada)" if ms_dia > 0
                    else "(cargá Kg TC y %MS)")
    ca_msg       = (f"{ca_der:.2f} kg MS/kg carne"
                    if ca_der > 0 else "—")
    efic_msg     = (f"{efic_der:.3f} kg carne/kg MS"
                    if efic_der > 0 else "—")

    st.markdown(
        f'<div style="background:white;border:1px solid {color}22;'
        f'border-radius:8px;padding:10px 12px;margin-top:8px;'
        f'font-size:0.74rem;color:#475569;line-height:1.55;">'
        f'<div style="font-size:0.60rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">'
        f'Cascada nutricional</div>'
        f'%MS ponderado: <b style="color:{ms_msg_color};">{pms_pond:.1f}%</b> '
        f'<span style="color:#94a3b8;font-size:0.66rem;">{ms_msg}</span><br>'
        f'Conversión (derivada): <b style="color:#0c1a2e;">{ca_msg}</b><br>'
        f'Eficiencia: <b style="color:#0c1a2e;">{efic_msg}</b><br>'
        f'Precio ponderado: <b style="color:#0c1a2e;">USD {p_pond:.3f}/kg MS</b><br>'
        f'Consumo MS ciclo: <b style="color:#0c1a2e;">{ms_ciclo:,.0f} kg/cab</b> · '
        f'Consumo MV ciclo: <b style="color:#0c1a2e;">{mv_ciclo:,.0f} kg/cab</b>'
        f'<hr style="border:none;border-top:1px solid #e4eaf4;margin:6px 0;">'
        f'<b style="color:{color};">Costo alimentación: '
        f'USD {costo_dia:.2f}/cab/día · USD {costo_ciclo:,.2f}/cab ciclo</b>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Tabs por categoría ────────────────────────────────────────────────────────

def _tab_compra_hacienda() -> None:
    """Precio de compra + kg de entrada por etapa.

    El kg de entrada es editable cuando la etapa es la 1ª activa del slice
    (acepta cualquier valor: el productor puede comprar terneros de 45 kg,
    recriados de 250 kg, o novillos de 320 kg para terminar). Cuando la
    etapa está encadenada, se hereda del kg_out de la anterior.
    """
    def render(key: str, color: str) -> None:
        if key == "cria":
            _num("Precio compra (USD/kg)", K.COMERCIAL_PRECIO_COMPRA,
                 DEFAULTS["precio_compra"], 0.0, 20.0, 0.05, "%.2f")
            _num("Kg de entrada (kg)", K.A_KG_ENTRADA,
                 DEFAULTS["a_kg_entrada"], 0.0, 1000.0, 1.0, "%.0f")
            _hint("Peso al ingreso del ternero al sistema "
                  "(recibido del tambo).")
        elif key == "recria":
            _num("Precio compra (USD/kg)", K.B_PRECIO_COMPRA,
                 DEFAULTS["b_pc"], 0.0, 20.0, 0.05, "%.2f")
            if S.is_first_active("recria"):
                _num("Kg de entrada (kg)", K.B_KG_ENTRADA,
                     DEFAULTS["b_kg_entrada"], 0.0, 1000.0, 1.0, "%.0f")
                _hint("Peso del recriado al ingreso del sistema (compra "
                      "directa, sin Cría previa).")
            else:
                pi_val = float(st.session_state.get(K.ANIMAL_PESO_ENTRADA,
                                                     DEFAULTS["peso_inicial"]))
                st.caption(f"Kg de entrada: **{pi_val:.0f} kg** "
                           f"(= kg salida Cría / peso al destete)")
        elif key == "eng_int":
            _num("Precio compra (USD/kg)", K.C_PRECIO_COMPRA,
                 DEFAULTS["c_pc"], 0.0, 20.0, 0.05, "%.2f")
            if S.is_first_active("eng_int"):
                _num("Kg de entrada (kg)", K.C_KG_ENTRADA,
                     DEFAULTS["c_kg_entrada"], 0.0, 1000.0, 1.0, "%.0f")
                _hint("Peso del animal al ingreso a Engorde "
                      "(compra directa, sin Cría/Recría previas).")
            else:
                kg_in_c = float(st.session_state.get(K.B_PESO_SALIDA,
                                                      DEFAULTS["r_peso_salida"]))
                st.caption(f"Kg de entrada: **{kg_in_c:.0f} kg** "
                           f"(= kg salida Recría)")

    _three_stage_columns(render)


def _tab_alimentacion() -> None:
    """GDP + composición de ración por etapa.

    Los días de tenencia son DERIVADOS:
        días = (peso_salida − peso_entrada) / GDP

    El costo y los consumos (MS, MV) y la conversión alimenticia (CA)
    son DERIVADOS desde la tabla de ingredientes (Kg TC × %MS × USD/kg MS).
    Ya no hay input de CA: la ración es la única fuente nutricional.
    """
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 14px 0;">'
        'GDP y composición de ración por etapa. <b>Los días de tenencia, '
        'la conversión alimenticia, los consumos (MS y MV) y el costo</b> '
        'se calculan automáticamente desde la tabla. '
        'Cargá ingredientes con kg <i>tal cual</i> consumidos por animal '
        'por día.'
        '</p>',
        unsafe_allow_html=True,
    )

    cfgs = {
        "cria": {
            "expander": "🌱  Cría",
            "stage": "cria",
            "color": _SEG["cria"][2],
            "gdp_key":  K.A_GDP,     "gdp_def":  DEFAULTS["a_gdp"],
            "table_key":  "feed_table_cria",
        },
        "recria": {
            "expander": "🔵  Recría",
            "stage": "recria",
            "color": _SEG["recria"][2],
            "gdp_key":  K.B_GDP,     "gdp_def":  DEFAULTS["r_gdp"],
            "table_key":  "feed_table_recria",
        },
        "eng_int": {
            "expander": "🟢  Engorde",
            "stage": "eng_int",
            "color": _SEG["eng_int"][2],
            "gdp_key":  K.C_GDP,     "gdp_def":  DEFAULTS["t_gdp"],
            "table_key":  "feed_table_eng_int",
        },
    }

    for stage, c in cfgs.items():
        with st.expander(c["expander"], expanded=S.is_active(stage)):
            if not S.is_active(stage):
                _inactive_placeholder()
                continue

            col_left, col_right = st.columns(2)
            with col_left:
                _num("GDP (kg/día)", c["gdp_key"], c["gdp_def"],
                     0.0, 3.0, 0.01, "%.3f")
            with col_right:
                # KPI: días derivado, no editable.
                dias_calc = D.dias_for(stage)
                kg_prod   = D.kg_producidos_cab(stage)
                gdp_now   = D.gdp_for(stage)
                if gdp_now <= 0 or kg_prod <= 0:
                    dias_note = ("Falta GDP > 0 y peso salida > peso entrada "
                                 "para calcular.")
                    dias_color = "#94a3b8"
                else:
                    dias_note = f"= ({kg_prod:.0f} kg ÷ {gdp_now:.3f} kg/día)"
                    dias_color = c["color"]
                st.markdown(
                    f'<div style="background:white;border:1px solid '
                    f'{c["color"]}22;border-radius:8px;padding:10px 14px;'
                    f'margin-top:24px;">'
                    f'<div style="font-size:0.60rem;font-weight:700;'
                    f'color:{c["color"]};text-transform:uppercase;'
                    f'letter-spacing:0.07em;">Días de tenencia (derivado)</div>'
                    f'<div style="font-size:1.4rem;font-weight:800;'
                    f'color:{dias_color};line-height:1.1;margin-top:4px;'
                    f'font-variant-numeric:tabular-nums;">{dias_calc} días</div>'
                    f'<div style="font-size:0.66rem;color:#94a3b8;'
                    f'margin-top:4px;">{dias_note}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            dias = D.dias_for(stage)
            gdp  = D.gdp_for(stage)

            _feed_table_block(
                c["table_key"],
                gdp=gdp, dias=dias,
                color=c["color"],
            )


def _tab_sanidad() -> None:
    cfg = {
        "cria":    (K.A_SANIDAD, DEFAULTS["d_sanidad"]),
        "recria":  (K.B_SANIDAD, DEFAULTS["r_sanidad"]),
        "eng_int": (K.C_SANIDAD, DEFAULTS["t_sanidad"]),
    }

    def render(key: str, color: str) -> None:
        san_key, san_def = cfg[key]
        _num("Sanidad (USD/cab)", san_key, san_def, 0.0, 300.0, 0.01, "%.2f")

    _three_stage_columns(render)


def _tab_operacion() -> None:
    """Costos operativos fijos por etapa, en USD/mes (no por cabeza).

    Lógica: costos como mano de obra, combustible y servicios son fijos
    mensuales (no escalan linealmente con cabezas). El costo del ciclo
    se deriva como:

        costo_ciclo = USD/mes / 30 × días de tenencia
    """
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 14px 0;">'
        'Costos fijos mensuales de operación. El costo asignado al ciclo '
        'se deriva automáticamente de los días de tenencia '
        '(<b>USD/mes ÷ 30 × días</b>).'
        '</p>',
        unsafe_allow_html=True,
    )

    cfg = {
        "cria": (K.A_MO_MES, DEFAULTS["d_mo_mes"],
                 K.A_COMBUSTIBLE, DEFAULTS["a_combustible"],
                 K.A_SERVICIOS,   DEFAULTS["a_servicios"]),
        "recria": (K.B_MO_MES, DEFAULTS["r_mo_mes"],
                   K.B_COMBUSTIBLE, DEFAULTS["b_combustible"],
                   K.B_SERVICIOS,   DEFAULTS["b_servicios"]),
        "eng_int": (K.C_MO_MES, DEFAULTS["t_mo_mes"],
                    K.C_COMBUSTIBLE, DEFAULTS["c_combustible"],
                    K.C_SERVICIOS,   DEFAULTS["c_servicios"]),
    }

    def render(key: str, color: str) -> None:
        (mo_k, mo_d, comb_k, comb_d, serv_k, serv_d) = cfg[key]
        mo   = _num("Mano de obra (USD/mes)",   mo_k,   mo_d,
                    0.0, 1e6, 50.0, "%.0f")
        comb = _num("Combustible (USD/mes)",    comb_k, comb_d,
                    0.0, 1e6, 50.0, "%.0f")
        serv = _num("Servicios (USD/mes)",      serv_k, serv_d,
                    0.0, 1e6, 50.0, "%.0f")

        # ── Cascada derivada (USD ciclo) ───────────────────────────────────
        dias = D.dias_for(key)
        factor = dias / 30.0
        mo_ciclo   = mo   * factor
        comb_ciclo = comb * factor
        serv_ciclo = serv * factor
        total_ciclo = mo_ciclo + comb_ciclo + serv_ciclo

        st.markdown(
            f'<div style="background:white;border:1px solid {color}22;'
            f'border-radius:8px;padding:9px 12px;margin-top:6px;'
            f'font-size:0.72rem;color:#475569;line-height:1.55;">'
            f'<div style="font-size:0.60rem;font-weight:700;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">'
            f'Costo ciclo ({dias} d)</div>'
            f'Mano de obra: <b style="color:#0c1a2e;">USD {mo_ciclo:,.0f}</b><br>'
            f'Combustible: <b style="color:#0c1a2e;">USD {comb_ciclo:,.0f}</b><br>'
            f'Servicios: <b style="color:#0c1a2e;">USD {serv_ciclo:,.0f}</b>'
            f'<hr style="border:none;border-top:1px solid #e4eaf4;'
            f'margin:6px 0;">'
            f'<b style="color:{color};">Operación total ciclo: '
            f'USD {total_ciclo:,.0f}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _three_stage_columns(render)


def _tab_estructura() -> None:
    """Valor infra GLOBAL + asignación per-etapa (% del total).
    Costo etapa = (infra_total × asig%/100 / años) × días/365 + mant_USD_año × días/365."""
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 12px 0;">'
        'Valor de infraestructura <b>total</b> y % asignado a cada unidad '
        'productiva. La suma de los % no necesariamente da 100% (puede haber '
        'actividades fuera del modelo).'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Valor infra TOTAL (global) ─────────────────────────────────────────
    g1, g2 = st.columns([1, 2])
    with g1:
        _num("Valor infraestructura total (USD)", K.INFRA_VALOR_TOTAL,
             DEFAULTS["infra_valor_total"], 0.0, 1e8, 1000.0, "%.0f")
    valor_total = float(st.session_state.get(K.INFRA_VALOR_TOTAL,
                                              DEFAULTS["infra_valor_total"]))

    # Resumen visual de asignación
    pct_a = float(st.session_state.get(K.A_ASIG_PCT, DEFAULTS["a_asig_pct"]))
    pct_b = float(st.session_state.get(K.B_ASIG_PCT, DEFAULTS["b_asig_pct"]))
    pct_c = float(st.session_state.get(K.C_ASIG_PCT, DEFAULTS["c_asig_pct"]))
    pct_sum = pct_a + pct_b + pct_c
    sum_color = "#16a34a" if pct_sum <= 100.001 else "#dc2626"
    sum_msg = ("Asignación válida"
               if pct_sum <= 100.001
               else "⚠ Suma supera 100%")
    with g2:
        st.markdown(
            f'<div style="background:#f8fafd;border:1px solid #e4eaf4;'
            f'border-radius:10px;padding:11px 16px;margin-top:8px;'
            f'display:flex;align-items:center;gap:18px;">'
            f'<div><div style="font-size:0.62rem;font-weight:700;color:#7a8fa6;'
            f'text-transform:uppercase;letter-spacing:0.07em;">'
            f'Suma de % asignados</div>'
            f'<div style="font-size:1.20rem;font-weight:800;color:{sum_color};'
            f'line-height:1.1;margin-top:2px;font-variant-numeric:tabular-nums;">'
            f'{pct_sum:.1f}%</div></div>'
            f'<div style="font-size:0.72rem;color:{sum_color};font-weight:600;">'
            f'{sum_msg}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cfg = {
        "cria":   (K.A_ASIG_PCT, DEFAULTS["a_asig_pct"],
                   K.A_AMORT_ANOS, DEFAULTS["a_amort_anos"],
                   K.A_MANTENIMIENTO, DEFAULTS["a_mantenimiento"]),
        "recria": (K.B_ASIG_PCT, DEFAULTS["b_asig_pct"],
                   K.B_AMORT_ANOS, DEFAULTS["b_amort_anos"],
                   K.B_MANTENIMIENTO, DEFAULTS["b_mantenimiento"]),
        "eng_int":(K.C_ASIG_PCT, DEFAULTS["c_asig_pct"],
                   K.C_AMORT_ANOS, DEFAULTS["c_amort_anos"],
                   K.C_MANTENIMIENTO, DEFAULTS["c_mantenimiento"]),
    }
    dias_map = {
        "cria":    D.dias_for("cria"),
        "recria":  D.dias_for("recria"),
        "eng_int": D.dias_for("eng_int"),
    }

    def render(key: str, color: str) -> None:
        (asg_k, asg_d, an_k, an_d, mt_k, mt_d) = cfg[key]
        asig_pct = _num("Amortización (% para esta unidad)", asg_k, asg_d,
                        0.0, 100.0, 1.0, "%.1f")
        anos = _num("Amortización (años)", an_k, an_d,
                    0.0, 50.0, 1.0, "%.0f")
        mant_anio = _num("Mantenimiento (USD/año)", mt_k, mt_d,
                         0.0, 1e6, 100.0, "%.0f")

        # ── Derivados (cascada de cálculo visible) ─────────────────────────
        adjudicado = valor_total * asig_pct / 100.0
        amort_anual = (adjudicado / anos) if anos > 0 else 0.0
        dias = dias_map[key]
        amort_ciclo = amort_anual * dias / 365.0
        mant_ciclo  = mant_anio * dias / 365.0
        estructura_ciclo = amort_ciclo + mant_ciclo

        st.markdown(
            f'<div style="background:white;border:1px solid {color}22;'
            f'border-radius:8px;padding:9px 12px;margin-top:6px;'
            f'font-size:0.72rem;color:#475569;line-height:1.55;">'
            f'<div style="font-size:0.60rem;font-weight:700;color:{color};'
            f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">'
            f'Cascada de cálculo</div>'
            f'Adjudicado: <b style="color:#0c1a2e;">USD {adjudicado:,.0f}</b><br>'
            f'Amort. anual: <b style="color:#0c1a2e;">USD {amort_anual:,.0f}/año</b><br>'
            f'Amort. ciclo ({dias} d): <b style="color:#0c1a2e;">'
            f'USD {amort_ciclo:,.0f}</b><br>'
            f'Mant. ciclo: <b style="color:#0c1a2e;">USD {mant_ciclo:,.0f}</b>'
            f'<hr style="border:none;border-top:1px solid #e4eaf4;'
            f'margin:6px 0;">'
            f'<b style="color:{color};">Costo estructura ciclo: '
            f'USD {estructura_ciclo:,.0f}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _three_stage_columns(render)


def _tab_comercializacion() -> None:
    cfg = {
        "cria": (K.A_COMISION_PCT, DEFAULTS["a_comision_pct"],
                 K.A_FLETE_ENTRADA, DEFAULTS["a_fe"],
                 K.A_FLETE_SALIDA,  DEFAULTS["d_flete"]),
        "recria": (K.B_COMISION_PCT, DEFAULTS["b_comision_pct"],
                   K.B_FLETE_ENTRADA, DEFAULTS["r_flete_entrada"],
                   K.B_FLETE_SALIDA,  DEFAULTS["r_flete_salida"]),
        "eng_int": (K.C_COMISION_PCT, DEFAULTS["c_comision_pct"],
                    K.C_FLETE_ENTRADA, DEFAULTS["t_flete_entrada"],
                    K.C_FLETE_SALIDA,  DEFAULTS["t_flete_salida"]),
    }

    def render(key: str, color: str) -> None:
        (com_k, com_d, fe_k, fe_d, fs_k, fs_d) = cfg[key]
        _num("Comisión comercial (%)", com_k, com_d,
             0.0, 20.0, 0.5, "%.1f")
        _num("Flete entrada (USD/cab)", fe_k, fe_d,
             0.0, 200.0, 0.5, "%.1f")
        _num("Flete salida (USD/cab)", fs_k, fs_d,
             0.0, 200.0, 0.5, "%.1f")

    _three_stage_columns(render)


def _tab_financieros() -> None:
    """Globales (TC + tasa) + duración del ciclo derivada."""
    st.markdown(
        '<p style="font-size:0.84rem;color:#475569;margin:-4px 0 14px 0;">'
        'Parámetros financieros globales y duración del ciclo (suma de días '
        'de tenencia configurados en la solapa Alimentación).'
        '</p>',
        unsafe_allow_html=True,
    )

    g1, g2 = st.columns(2)
    with g1:
        _num("Tipo de cambio (ARS/USD)", K.FINANCIERO_TIPO_CAMBIO,
             DEFAULTS["tipo_cambio"], step=50.0, fmt="%.2f")
    with g2:
        _num("Tasa de interés anual (%)", K.FINANCIERO_TASA_INTERES,
             DEFAULTS["tasa_interes"], step=0.5, fmt="%.2f")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Duración del ciclo — derivada de días de tenencia por etapa
    d_a = D.dias_for("cria")
    d_b = D.dias_for("recria")
    d_c = D.dias_for("eng_int")
    d_per_stage = {"cria": d_a, "recria": d_b, "eng_int": d_c}
    active = S.active_stages()
    d_total = sum(d_per_stage[s] for s in active)
    breakdown_parts = [str(d_per_stage[s]) for s in active]
    pretty = {"cria": "Cría", "recria": "Recría", "eng_int": "Engorde"}
    breakdown_etapas = " + ".join(pretty[s] for s in active) if active else "—"
    breakdown_dias = " + ".join(breakdown_parts) if breakdown_parts else "0"

    def render(key: str, color: str) -> None:
        d = d_per_stage[key]
        st.markdown(
            f'<div style="font-size:0.62rem;font-weight:700;color:#7a8fa6;'
            f'text-transform:uppercase;letter-spacing:0.07em;">'
            f'Duración de ciclo</div>'
            f'<div style="font-size:1.45rem;font-weight:800;color:{color};'
            f'line-height:1.1;margin-top:4px;font-variant-numeric:tabular-nums;">'
            f'{d} días</div>'
            f'<div style="font-size:0.66rem;color:#94a3b8;margin-top:4px;">'
            f'Editable en solapa <b>🌾 Alimentación</b></div>',
            unsafe_allow_html=True,
        )

    _three_stage_columns(render)

    # Total ciclo (sólo etapas activas)
    st.markdown(
        f'<div style="background:#f0f9ff;border:1px solid #bae6fd;'
        f'border-radius:10px;padding:12px 18px;margin-top:14px;'
        f'display:flex;align-items:center;gap:14px;">'
        f'<span style="font-size:1.4rem;">⏱</span>'
        f'<div>'
        f'<div style="font-size:0.62rem;font-weight:700;color:#0369a1;'
        f'text-transform:uppercase;letter-spacing:0.08em;">'
        f'Duración total del ciclo</div>'
        f'<div style="font-size:1.55rem;font-weight:800;color:#0c1a2e;'
        f'line-height:1.1;margin-top:2px;font-variant-numeric:tabular-nums;">'
        f'{d_total} días</div>'
        f'<div style="font-size:0.7rem;color:#64748b;margin-top:2px;">'
        f'{breakdown_dias}  ({breakdown_etapas})</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _tab_mortandad(n_t: int) -> None:
    cfg = {
        "cria":    (K.A_MORTALIDAD, DEFAULTS["d_mortalidad"]),
        "recria":  (K.B_MORTALIDAD, DEFAULTS["r_mortalidad"]),
        "eng_int": (K.C_MORTALIDAD, DEFAULTS["t_mortalidad"]),
    }

    def render(key: str, color: str) -> None:
        mort_k, mort_d = cfg[key]
        _num("Mortandad (%)", mort_k, mort_d, 0.0, 30.0, 0.5, "%.1f")
        # Info derivada: cabezas a venta de la etapa
        mort = float(st.session_state.get(mort_k, mort_d))
        nv = max(int(n_t * (1 - mort / 100.0)), 0)
        _info(f"A venta: **{nv:,}**  ·  Bajas: **{n_t - nv}**")

    _three_stage_columns(render)


def _tab_venta_hacienda() -> None:
    def render(key: str, color: str) -> None:
        if key == "cria":
            _num("Precio venta (USD/kg)", K.A_PRECIO_VENTA,
                 DEFAULTS["d_precio_venta"], 0.0, 20.0, 0.05, "%.2f")
            _num("Kg de salida (destete)", K.ANIMAL_PESO_ENTRADA,
                 DEFAULTS["peso_inicial"], 0, 300, 1, "%.0f")
        elif key == "recria":
            _num("Precio venta (USD/kg)", K.B_PRECIO_VENTA,
                 DEFAULTS["r_precio_venta"], 0.0, 20.0, 0.05, "%.2f")
            _num("Kg de salida (kg)", K.B_PESO_SALIDA,
                 DEFAULTS["r_peso_salida"], 0, 600, 5, "%.0f")
        elif key == "eng_int":
            _num("Precio venta (USD/kg)", K.C_PRECIO_VENTA,
                 DEFAULTS["t_precio_venta"], 0.0, 20.0, 0.05, "%.2f")
            _num("Kg de salida (kg)", K.C_PESO_FINAL,
                 DEFAULTS["t_peso_final"], 0, 800, 5, "%.0f")

    _three_stage_columns(render)


# ── Main render ───────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Parámetros",
        "Configuración completa del modelo, organizada por categoría "
        "económica. Los cambios se aplican en tiempo real.",
    )

    # ── Botón explícito para volver a los defaults (única vía permitida) ──
    # Los valores del usuario son la única fuente de verdad: solo se
    # reemplazan por defaults si se pulsa este botón.
    col_reset_l, col_reset_r = st.columns([5, 1])
    with col_reset_r:
        if st.button("↺ Restablecer defaults",
                     help=("Borra todos los valores cargados y restaura los "
                           "defaults del modelo. Esta es la única forma de "
                           "perder los parámetros ingresados."),
                     use_container_width=True):
            reset_to_defaults()
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # GENERAL — N° de terneros + selector de etapas activas
    # ══════════════════════════════════════════════════════════════════════
    with st.container():
        st.markdown(
            '<div style="background:#f0f9ff;border:1px solid #bae6fd;'
            'border-radius:10px;padding:4px 18px 14px 18px;margin-bottom:18px;">'
            '<p style="font-size:0.72rem;font-weight:700;color:#0369a1;'
            'text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 6px 0;">'
            '⚙️ &nbsp;Parámetros globales</p></div>',
            unsafe_allow_html=True,
        )
        col_sl, col_info = st.columns([1, 2])
        with col_sl:
            _num("N° de terneros", K.ANIMAL_CANTIDAD,
                 DEFAULTS["n_terneros"], step=1.0, fmt="%.0f")
        with col_info:
            n_t_now = int(st.session_state.get(K.ANIMAL_CANTIDAD,
                                                DEFAULTS["n_terneros"]))
            st.info(
                f"**{n_t_now:,} terneros** ingresan al sistema. "
                "Base de todos los cálculos del tablero.",
                icon="🐄",
            )

        # ── Selector de etapas activas (modular vs integrado) ──────────────
        st.markdown(
            '<p style="font-size:0.70rem;font-weight:700;color:#0369a1;'
            'text-transform:uppercase;letter-spacing:0.07em;margin:14px 0 4px 0;">'
            '🧩 &nbsp;Etapas activas</p>'
            '<p style="font-size:0.74rem;color:#475569;margin:0 0 8px 0;'
            'line-height:1.4;">Definí qué etapas analizar. La selección debe '
            'ser un slice contiguo (Cría, Recría, Engorde, o combinaciones '
            'consecutivas). El kg de entrada de la 1ª etapa activa es '
            'editable; las siguientes se encadenan.</p>',
            unsafe_allow_html=True,
        )
        # Contigüidad: corregir el slice ANTES de instanciar los checkboxes.
        # `enforce_contiguity` ya lee shadow + ss para detectar el click
        # más reciente del usuario y, si hace falta, fuerza Recría=True
        # tanto en ss como en el shadow.
        S.enforce_contiguity()

        # Persistencia bulletproof — mismo patrón que `_num`:
        # canonical = shadow `_persist_<key>`, widget = `_w_<key>` efímero.
        # El shadow sobrevive a la navegación; el widget-key Streamlit lo
        # puede purgar libremente sin pérdida.
        def _stage_checkbox(label: str, canonical: str) -> None:
            widget_key = "_w_" + canonical
            cval = bool(read(canonical, True))

            def _sync_back() -> None:
                new_val = bool(st.session_state[widget_key])
                mirror(canonical, new_val)
                try:
                    st.session_state[canonical] = new_val
                except Exception:
                    pass

            st.session_state[widget_key] = cval
            st.checkbox(label, key=widget_key, on_change=_sync_back)

        c_a, c_b, c_c, c_label = st.columns([1, 1, 1, 2])
        with c_a:
            _stage_checkbox("🌱 Cría",    K.STAGE_CRIA_ON)
        with c_b:
            _stage_checkbox("🔵 Recría",  K.STAGE_RECRIA_ON)
        with c_c:
            _stage_checkbox("🟢 Engorde", K.STAGE_ENG_ON)

        active = S.active_stages()
        with c_label:
            if not active:
                msg_color = "#dc2626"
                msg = "⚠ Activá al menos una etapa"
            else:
                msg_color = "#0369a1"
                msg = f"Modo: <b>{S.mode_label()}</b>"
            st.markdown(
                f'<div style="background:white;border:1px solid #bae6fd;'
                f'border-radius:8px;padding:8px 14px;margin-top:24px;'
                f'font-size:0.78rem;color:{msg_color};">{msg}</div>',
                unsafe_allow_html=True,
            )

    n_t = int(st.session_state.get(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))

    # ══════════════════════════════════════════════════════════════════════
    # 9 TABS POR CATEGORÍA · cada tab → 3 cards por etapa
    # ══════════════════════════════════════════════════════════════════════
    tabs = st.tabs([
        "🛒  Compra hacienda",
        "🌾  Alimentación",
        "💉  Sanidad",
        "👷  Operación",
        "🏗  Estructura",
        "💰  Comercialización",
        "🏦  Financieros",
        "⚠️  Mortandad",
        "💵  Venta hacienda",
    ])

    with tabs[0]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_compra_hacienda()

    with tabs[1]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_alimentacion()

    with tabs[2]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_sanidad()

    with tabs[3]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_operacion()

    with tabs[4]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_estructura()

    with tabs[5]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_comercializacion()

    with tabs[6]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_financieros()

    with tabs[7]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_mortandad(n_t)

    with tabs[8]:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _tab_venta_hacienda()
