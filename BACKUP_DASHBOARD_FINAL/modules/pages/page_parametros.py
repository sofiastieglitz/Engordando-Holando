"""
Parámetros — sección General fija + 3 tabs: Animales | Alimentación | Comercialización
4 segmentos: Cría · Recría · Engorde interno · Engorde exportación
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.pages.ui import page_header, section
from modules.sidebar import _sl_f, _sl_i, _info

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


# ── Segment metadata ──────────────────────────────────────────────────────────

_SEG = {
    "cria":    ("Cría",                "🌱", "#16a34a"),
    "recria":  ("Recría",              "🔵", "#1565c0"),
    "eng_int": ("Engorde interno",     "🟢", "#0d9488"),
    "eng_exp": ("Engorde exportación", "🌐", "#7c3aed"),
}


# ── UI helpers ────────────────────────────────────────────────────────────────

def _card_header(title: str, icon: str, color: str) -> None:
    st.markdown(
        f'<div style="background:{color}14;border-left:4px solid {color};'
        f'border-radius:0 8px 8px 0;padding:10px 16px;margin-bottom:14px;">'
        f'<span style="font-size:1.05rem;font-weight:700;color:{color};">'
        f'{icon}&nbsp;&nbsp;{title}</span></div>',
        unsafe_allow_html=True,
    )


def _subsection(label: str) -> None:
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;color:#7a8fa6;'
        f'text-transform:uppercase;letter-spacing:0.07em;margin:10px 0 6px 0;">'
        f'{label}</p>',
        unsafe_allow_html=True,
    )


def _num(label: str, key: str, default: float,
         lo: float = 0.0, hi: float = 1e9,
         step: float = 1.0, fmt: str = "%.2f") -> float:
    """number_input con inicialización segura de session_state."""
    if key not in st.session_state:
        st.session_state[key] = float(default)
    else:
        # clamp para evitar out-of-range en reruns
        try:
            st.session_state[key] = float(
                max(lo, min(hi, float(st.session_state[key])))
            )
        except (ValueError, TypeError):
            st.session_state[key] = float(default)
    return float(
        st.number_input(
            label,
            min_value=float(lo),
            max_value=float(hi),
            step=float(step),
            format=fmt,
            key=key,
        )
    )


# ── Feed table ────────────────────────────────────────────────────────────────

def _empty_feed_table() -> pd.DataFrame:
    return pd.DataFrame({
        "Ingrediente": [""] * 10,
        "%":           [0.0] * 10,
        "USD/kg MS":   [0.0] * 10,
    })


def _feed_section(
    title: str, icon: str, color: str,
    rac_key: str, rac_default: float,
    table_key: str,
) -> None:
    """Renders ración diaria slider + tabla editable con key explícito único."""
    _card_header(title, icon, color)

    rac = _sl_f(
        "Ración diaria (kg MS/cab/día)", 0.5, 30.0,
        rac_default, 0.5, fmt="%.1f", key=rac_key,
    )

    # Cada data_editor tiene un key ÚNICO derivado de table_key.
    # NO pre-inicializar ss[editor_key]: data_editor gestiona su propio estado.
    # _empty_feed_table() sólo se usa en el primer render (cuando el key no existe).
    # En reruns posteriores, data_editor lee directamente de ss[editor_key].
    editor_key = table_key + "_de"

    st.caption("**Composición de la ración** — editá directamente en la tabla:")
    edited = st.data_editor(
        _empty_feed_table(),
        key=editor_key,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        column_config={
            "Ingrediente": st.column_config.TextColumn("Ingrediente", width="medium"),
            "%": st.column_config.NumberColumn(
                "% en ración", min_value=0.0, max_value=100.0,
                step=0.5, format="%.1f",
            ),
            "USD/kg MS": st.column_config.NumberColumn(
                "USD/kg MS", min_value=0.0, step=0.001, format="%.3f",
            ),
        },
    )
    # No asignar a ss[editor_key] después del widget — Streamlit lo gestiona solo.

    tot_pct = float(edited["%"].sum())
    mask = (edited["%"] > 0) & (edited["USD/kg MS"] > 0)
    if mask.any():
        p_pond = float(
            (edited.loc[mask, "%"] * edited.loc[mask, "USD/kg MS"]).sum()
            / edited.loc[mask, "%"].sum()
        )
        costo = rac * p_pond
        _info(
            f"% total ración: **{tot_pct:.1f}%**  ·  "
            f"Precio ponderado: **USD {p_pond:.3f}/kg MS**  ·  "
            f"Costo estimado: **USD {costo:.3f}/cab/día**"
        )
    else:
        _info(f"% total ración: **{tot_pct:.1f}%**  ·  Completá ingredientes y precios")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ── Bloque comercial (module-level para no redefinir en cada render) ───────────

def _com_block(
    col,
    seg_key: str,
    pc_key: str, pc_def: float,
    pv_key: str, pv_def: float,
    com_key: str, com_def: float,
    fe_key: str, fe_def: float,
    fs_key: str, fs_def: float,
    mo_key: str, mo_def: float,
    san_key: str, san_def: float,
) -> None:
    title, icon, color = _SEG[seg_key]
    with col:
        _card_header(title, icon, color)
        _subsection("Parámetros comerciales")
        _num("Precio de compra (USD/kg)", pc_key, pc_def,  0.10, 20.0,  0.05, "%.2f")
        _num("Precio de venta (USD/kg)",  pv_key, pv_def,  0.10, 20.0,  0.05, "%.2f")
        _num("Comisión comercial (%)",    com_key, com_def, 0.0, 20.0,  0.5,  "%.1f")
        _num("Flete entrada (USD/cab)",   fe_key, fe_def,   0.0, 200.0, 0.5,  "%.1f")
        _num("Flete salida (USD/cab)",    fs_key, fs_def,   0.0, 200.0, 0.5,  "%.1f")
        _subsection("Parámetros operativos")
        mc1, mc2 = st.columns(2)
        with mc1:
            _num("Mano de obra (USD/día)",      mo_key, mo_def,   0.0, 10.0,  0.01, "%.2f")
        with mc2:
            _num("Sanidad (USD/cab)",          san_key, san_def, 0.0, 300.0, 1.0,  "%.0f")


# ── Main render ───────────────────────────────────────────────────────────────

def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Parámetros",
        "Configuración completa del modelo. Los cambios se aplican en tiempo real.",
    )

    # ══════════════════════════════════════════════════════════════════════
    # GENERAL — sección fija, siempre visible sobre las tabs
    # ══════════════════════════════════════════════════════════════════════
    with st.container():
        st.markdown(
            '<div style="background:#f0f9ff;border:1px solid #bae6fd;'
            'border-radius:10px;padding:4px 18px 14px 18px;margin-bottom:18px;">'
            '<p style="font-size:0.72rem;font-weight:700;color:#0369a1;'
            'text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 6px 0;">'
            '⚙️ &nbsp;Parámetro global</p></div>',
            unsafe_allow_html=True,
        )
        # El slider va FUERA del div para renderizarse correctamente
        col_sl, col_info = st.columns([1, 2])
        with col_sl:
            _sl_i(
                "N° de terneros", 10, 2000,
                DEFAULTS["n_terneros"], step=10, key=K.ANIMAL_CANTIDAD,
            )
        with col_info:
            n_t = int(st.session_state.get(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))
            st.info(
                f"**{n_t:,} terneros** ingresan al sistema. "
                "Base de todos los cálculos del tablero.",
                icon="🐄",
            )

    n_t = int(st.session_state.get(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"]))

    # ══════════════════════════════════════════════════════════════════════
    # TABS: Animales | Alimentación | Comercialización
    # ══════════════════════════════════════════════════════════════════════
    tab_animales, tab_alim, tab_comercial = st.tabs([
        "🐂  Animales",
        "🌾  Alimentación",
        "💰  Comercialización",
    ])

    # ──────────────────────────────────────────────────────────────────────
    # TAB ANIMALES
    # ──────────────────────────────────────────────────────────────────────
    with tab_animales:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        col_c, col_e = st.columns(2)

        # ── Cría ──────────────────────────────────────────────────────────
        with col_a:
            _card_header(*_SEG["cria"])
            _num("Días de tenencia",       K.A_DIAS,            DEFAULTS["d_dias"],          1,    365,  1,    "%.0f")
            _num("Kg de entrada",          K.A_KG_ENTRADA,      DEFAULTS["a_kg_entrada"],    5,    200,  1,    "%.0f")
            _num("Kg de salida (destete)", K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"],  20,   300,  1,    "%.0f")
            _num("GDP (kg/día)",           K.A_GDP,             DEFAULTS["a_gdp"],           0.05, 3.0,  0.05, "%.3f")
            _num("Mortandad (%)",          K.A_MORTALIDAD,      DEFAULTS["d_mortalidad"],    0.0,  30.0, 0.5,  "%.1f")
            _num("Sanidad (USD/cab)",      K.A_SANIDAD,         DEFAULTS["d_sanidad"],       0.0,  300., 1.0,  "%.0f")
            _num("Mano de obra (USD/cab/día)", K.A_MO_DIA,      DEFAULTS["d_mo_dia"],        0.0,  10.0, 0.01, "%.2f")
            _num("Alimentación (USD/cab/día)", K.A_ALIM_COSTO_DIA, DEFAULTS["d_costo_alim_dia"], 0.0, 20.0, 0.05, "%.2f")
            mort_a = float(st.session_state.get(K.A_MORTALIDAD, DEFAULTS["d_mortalidad"]))
            nv_a = max(int(n_t * (1 - mort_a / 100)), 0)
            _info(f"A venta: **{nv_a:,}**  ·  Bajas: **{n_t - nv_a}**")

        # ── Recría ────────────────────────────────────────────────────────
        with col_b:
            _card_header(*_SEG["recria"])
            pi_val = float(st.session_state.get(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"]))
            _num("Días de tenencia",   K.B_DIAS,       DEFAULTS["b_dias"],         1,   730,  1,    "%.0f")
            st.caption(f"Kg de entrada: **{pi_val:.0f} kg** (= kg salida Cría)")
            _num("Kg de salida",       K.B_PESO_SALIDA, DEFAULTS["r_peso_salida"], 50,  600,  5,    "%.0f")
            _num("GDP (kg/día)",       K.B_GDP,         DEFAULTS["r_gdp"],         0.1, 3.0,  0.05, "%.3f")
            _num("Mortandad (%)",      K.B_MORTALIDAD,  DEFAULTS["r_mortalidad"],  0.0, 30.0, 0.5,  "%.1f")
            _num("Sanidad (USD/cab)",  K.B_SANIDAD,     DEFAULTS["r_sanidad"],     0.0, 300., 1.0,  "%.0f")
            _num("Mano de obra (USD/cab/día)", K.B_MO_DIA, DEFAULTS["r_mo_dia"],  0.0, 10.0, 0.01, "%.2f")
            _num("Alimentación (USD/cab/día)", K.B_ALIM_DIA, DEFAULTS["b_alim_dia"], 0.0, 20.0, 0.05, "%.2f")
            mort_b  = float(st.session_state.get(K.B_MORTALIDAD, DEFAULTS["r_mortalidad"]))
            nv_b    = max(int(n_t * (1 - mort_b / 100)), 0)
            kg_ob   = float(st.session_state.get(K.B_PESO_SALIDA, DEFAULTS["r_peso_salida"]))
            _info(f"A venta: **{nv_b:,}**  ·  Bajas: **{n_t - nv_b}**  ·  Δ Peso: **{kg_ob - pi_val:.0f} kg**")

        # ── Engorde interno ───────────────────────────────────────────────
        with col_c:
            _card_header(*_SEG["eng_int"])
            kg_in_c = float(st.session_state.get(K.B_PESO_SALIDA, DEFAULTS["r_peso_salida"]))
            _num("Días de tenencia",   K.C_DIAS,       DEFAULTS["c_dias"],         1,   730,  1,    "%.0f")
            st.caption(f"Kg de entrada: **{kg_in_c:.0f} kg** (= kg salida Recría)")
            _num("Kg de salida",       K.C_PESO_FINAL, DEFAULTS["t_peso_final"],   100, 800,  5,    "%.0f")
            _num("GDP (kg/día)",       K.C_GDP,        DEFAULTS["t_gdp"],          0.1, 3.0,  0.05, "%.3f")
            _num("Mortandad (%)",      K.C_MORTALIDAD, DEFAULTS["t_mortalidad"],   0.0, 30.0, 0.5,  "%.1f")
            _num("Sanidad (USD/cab)",  K.C_SANIDAD,    DEFAULTS["t_sanidad"],      0.0, 300., 1.0,  "%.0f")
            _num("Mano de obra (USD/cab/día)", K.C_MO_DIA,   DEFAULTS["t_mo_dia"],    0.0, 10.0, 0.01, "%.2f")
            _num("Alimentación (USD/cab/día)", K.C_ALIM_DIA, DEFAULTS["c_alim_dia"], 0.0, 20.0, 0.05, "%.2f")
            mort_c  = float(st.session_state.get(K.C_MORTALIDAD, DEFAULTS["t_mortalidad"]))
            nv_c    = max(int(n_t * (1 - mort_c / 100)), 0)
            kg_oc   = float(st.session_state.get(K.C_PESO_FINAL, DEFAULTS["t_peso_final"]))
            _info(f"A venta: **{nv_c:,}**  ·  Bajas: **{n_t - nv_c}**  ·  Δ Peso: **{kg_oc - kg_in_c:.0f} kg**")

        # ── Engorde exportación ───────────────────────────────────────────
        with col_e:
            _card_header(*_SEG["eng_exp"])
            _num("Días de tenencia",   K.E_DIAS,        DEFAULTS["e_dias"],        1,   730,  1,    "%.0f")
            _num("Kg de entrada",      K.E_KG_ENTRADA,  DEFAULTS["e_kg_entrada"],  50,  600,  5,    "%.0f")
            _num("Kg de salida",       K.E_KG_SALIDA,   DEFAULTS["e_kg_salida"],   100, 800,  5,    "%.0f")
            _num("GDP (kg/día)",       K.E_GDP,         DEFAULTS["e_gdp"],         0.1, 3.0,  0.05, "%.3f")
            _num("Mortandad (%)",      K.E_MORTALIDAD,  DEFAULTS["e_mortalidad"],  0.0, 30.0, 0.5,  "%.1f")
            _num("Sanidad (USD/cab)",  K.E_SANIDAD,     DEFAULTS["e_sanidad"],     0.0, 300., 1.0,  "%.0f")
            _num("Mano de obra (USD/cab/día)", K.E_MO_DIA,    DEFAULTS["e_mo_dia"],   0.0, 10.0, 0.01, "%.2f")
            _num("Alimentación (USD/cab/día)", K.E_ALIM_DIA,  DEFAULTS["e_alim_dia"], 0.0, 20.0, 0.05, "%.2f")
            mort_e  = float(st.session_state.get(K.E_MORTALIDAD, DEFAULTS["e_mortalidad"]))
            nv_e    = max(int(n_t * (1 - mort_e / 100)), 0)
            kg_ie   = float(st.session_state.get(K.E_KG_ENTRADA, DEFAULTS["e_kg_entrada"]))
            kg_oe   = float(st.session_state.get(K.E_KG_SALIDA,  DEFAULTS["e_kg_salida"]))
            _info(f"A venta: **{nv_e:,}**  ·  Bajas: **{n_t - nv_e}**  ·  Δ Peso: **{kg_oe - kg_ie:.0f} kg**")

    # ──────────────────────────────────────────────────────────────────────
    # TAB ALIMENTACIÓN
    # ──────────────────────────────────────────────────────────────────────
    with tab_alim:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        with st.expander("🌱  Cría", expanded=True):
            _feed_section(
                *_SEG["cria"],
                rac_key=K.A_RAC_DIARIA, rac_default=DEFAULTS["a_rac_diaria"],
                table_key="feed_table_cria",
            )
        with st.expander("🔵  Recría", expanded=False):
            _feed_section(
                *_SEG["recria"],
                rac_key=K.B_RAC_DIARIA, rac_default=DEFAULTS["b_rac_diaria"],
                table_key="feed_table_recria",
            )
        with st.expander("🟢  Engorde interno", expanded=False):
            _feed_section(
                *_SEG["eng_int"],
                rac_key=K.C_RAC_DIARIA, rac_default=DEFAULTS["c_rac_diaria"],
                table_key="feed_table_eng_int",
            )
        with st.expander("🌐  Engorde exportación", expanded=False):
            _feed_section(
                *_SEG["eng_exp"],
                rac_key=K.E_RAC_DIARIA, rac_default=DEFAULTS["e_rac_diaria"],
                table_key="feed_table_eng_exp",
            )

    # ──────────────────────────────────────────────────────────────────────
    # TAB COMERCIALIZACIÓN
    # ──────────────────────────────────────────────────────────────────────
    with tab_comercial:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        section("Parámetros financieros globales")
        fg1, fg2, _ = st.columns([1, 1, 1])
        with fg1:
            _sl_f(
                "Tipo de cambio (ARS/USD)", 200.0, 5000.0,
                DEFAULTS["tipo_cambio"], 50.0, fmt="%.0f",
                key=K.FINANCIERO_TIPO_CAMBIO,
            )
        with fg2:
            _sl_f(
                "Tasa de interés anual (%)", 0.0, 30.0,
                DEFAULTS["tasa_interes"], 0.5, fmt="%.1f",
                key=K.FINANCIERO_TASA_INTERES,
            )
        st.divider()

        col_a, col_b = st.columns(2)
        col_c, col_e = st.columns(2)

        _com_block(
            col_a, "cria",
            pc_key=K.COMERCIAL_PRECIO_COMPRA, pc_def=DEFAULTS["precio_compra"],
            pv_key=K.A_PRECIO_VENTA,          pv_def=DEFAULTS["d_precio_venta"],
            com_key=K.A_COMISION_PCT,          com_def=DEFAULTS["a_comision_pct"],
            fe_key=K.A_FLETE_ENTRADA,          fe_def=DEFAULTS["a_fe"],
            fs_key=K.A_FLETE_SALIDA,           fs_def=DEFAULTS["d_flete"],
            mo_key=K.A_COM_MO_DIA,             mo_def=DEFAULTS["a_com_mo"],
            san_key=K.A_COM_SANIDAD,           san_def=DEFAULTS["a_com_san"],
        )
        _com_block(
            col_b, "recria",
            pc_key=K.B_PRECIO_COMPRA,  pc_def=DEFAULTS["b_pc"],
            pv_key=K.B_PRECIO_VENTA,   pv_def=DEFAULTS["r_precio_venta"],
            com_key=K.B_COMISION_PCT,  com_def=DEFAULTS["b_comision_pct"],
            fe_key=K.B_FLETE_ENTRADA,  fe_def=DEFAULTS["r_flete_entrada"],
            fs_key=K.B_FLETE_SALIDA,   fs_def=DEFAULTS["r_flete_salida"],
            mo_key=K.B_COM_MO_DIA,     mo_def=DEFAULTS["b_com_mo"],
            san_key=K.B_COM_SANIDAD,   san_def=DEFAULTS["b_com_san"],
        )
        _com_block(
            col_c, "eng_int",
            pc_key=K.C_PRECIO_COMPRA,  pc_def=DEFAULTS["c_pc"],
            pv_key=K.C_PRECIO_VENTA,   pv_def=DEFAULTS["t_precio_venta"],
            com_key=K.C_COMISION_PCT,  com_def=DEFAULTS["c_comision_pct"],
            fe_key=K.C_FLETE_ENTRADA,  fe_def=DEFAULTS["t_flete_entrada"],
            fs_key=K.C_FLETE_SALIDA,   fs_def=DEFAULTS["t_flete_salida"],
            mo_key=K.C_COM_MO_DIA,     mo_def=DEFAULTS["c_com_mo"],
            san_key=K.C_COM_SANIDAD,   san_def=DEFAULTS["c_com_san"],
        )
        _com_block(
            col_e, "eng_exp",
            pc_key=K.E_PRECIO_COMPRA,  pc_def=DEFAULTS["e_pc"],
            pv_key=K.E_PRECIO_VENTA,   pv_def=DEFAULTS["e_pv"],
            com_key=K.E_COMISION_PCT,  com_def=DEFAULTS["e_comision_pct"],
            fe_key=K.E_FLETE_ENTRADA,  fe_def=DEFAULTS["e_fe"],
            fs_key=K.E_FLETE_SALIDA,   fs_def=DEFAULTS["e_fs"],
            mo_key=K.E_COM_MO_DIA,     mo_def=DEFAULTS["e_com_mo"],
            san_key=K.E_COM_SANIDAD,   san_def=DEFAULTS["e_com_san"],
        )
