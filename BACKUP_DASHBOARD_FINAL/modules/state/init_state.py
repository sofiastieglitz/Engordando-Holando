"""
Inicialización centralizada de session_state.

Reemplaza _init_state() de sidebar.py. Usa constantes de keys.py y
valores de defaults.py para que agregar un parámetro nuevo requiera
tocar un solo archivo (este), no cuatro.
"""
import streamlit as st
import modules.state.keys as K
from modules.state.defaults import (
    DEFAULTS,
    ANIMAL_DEFAULTS,
    FEED_DEFAULTS,
    INFRA_DEFAULTS,
    COMMERCIAL_DEFAULTS,
)


def init_state() -> None:
    """
    Establece todas las claves de session_state con sus valores por defecto
    si todavía no existen. Idempotente: llamadas subsiguientes no sobreescriben
    el estado del usuario.

    Orden: comunes → A → B → C → infraestructura (nuevas) → comercial (nuevas).
    """
    _pairs: dict = {
        # ── Comunes ────────────────────────────────────────────────────────────
        K.ANIMAL_CANTIDAD:          ANIMAL_DEFAULTS["n_terneros"],
        K.ANIMAL_PESO_ENTRADA:      int(ANIMAL_DEFAULTS["peso_inicial"]),
        K.COMERCIAL_PRECIO_COMPRA:  COMMERCIAL_DEFAULTS["precio_compra"],
        K.FINANCIERO_TIPO_CAMBIO:   COMMERCIAL_DEFAULTS["tipo_cambio"],
        K.FINANCIERO_TASA_INTERES:  COMMERCIAL_DEFAULTS["tasa_interes"],

        # ── A — Venta al destete ───────────────────────────────────────────────
        K.A_PRECIO_VENTA:   COMMERCIAL_DEFAULTS["A"]["precio_venta"],
        K.A_DIAS:           ANIMAL_DEFAULTS["A"]["dias"],
        K.A_MORTALIDAD:     ANIMAL_DEFAULTS["A"]["mortalidad"],
        K.A_ALIM_COSTO_DIA: FEED_DEFAULTS["A"]["costo_alim_dia"],
        K.A_SANIDAD:        ANIMAL_DEFAULTS["A"]["sanidad"],
        K.A_MO_DIA:         ANIMAL_DEFAULTS["A"]["mo_dia"],
        K.A_FLETE_SALIDA:   COMMERCIAL_DEFAULTS["A"]["flete_salida"],
        K.A_OTROS:          COMMERCIAL_DEFAULTS["A"]["otros"],

        # ── B — Venta recriado ─────────────────────────────────────────────────
        K.B_PESO_SALIDA:   int(ANIMAL_DEFAULTS["B"]["peso_salida"]),
        K.B_PRECIO_VENTA:  COMMERCIAL_DEFAULTS["B"]["precio_venta"],
        K.B_GDP:           ANIMAL_DEFAULTS["B"]["gdp"],
        K.B_MORTALIDAD:    ANIMAL_DEFAULTS["B"]["mortalidad"],
        K.B_CA:            ANIMAL_DEFAULTS["B"]["ca"],
        K.B_ING1_PCT:      FEED_DEFAULTS["B"]["ing1_pct"],
        K.B_ING1_PRECIO:   FEED_DEFAULTS["B"]["ing1_precio"],
        K.B_ING2_PCT:      FEED_DEFAULTS["B"]["ing2_pct"],
        K.B_ING2_PRECIO:   FEED_DEFAULTS["B"]["ing2_precio"],
        K.B_SANIDAD:       ANIMAL_DEFAULTS["B"]["sanidad"],
        K.B_MO_DIA:        ANIMAL_DEFAULTS["B"]["mo_dia"],
        K.B_FLETE_ENTRADA: COMMERCIAL_DEFAULTS["B"]["flete_entrada"],
        K.B_FLETE_SALIDA:  COMMERCIAL_DEFAULTS["B"]["flete_salida"],
        K.B_OTROS:         COMMERCIAL_DEFAULTS["B"]["otros"],

        # ── C — Venta terminado ────────────────────────────────────────────────
        K.C_PESO_FINAL:    int(ANIMAL_DEFAULTS["C"]["peso_final"]),
        K.C_PRECIO_VENTA:  COMMERCIAL_DEFAULTS["C"]["precio_venta"],
        K.C_GDP:           ANIMAL_DEFAULTS["C"]["gdp"],
        K.C_MORTALIDAD:    ANIMAL_DEFAULTS["C"]["mortalidad"],
        K.C_CA:            ANIMAL_DEFAULTS["C"]["ca"],
        K.C_ING1_PCT:      FEED_DEFAULTS["C"]["ing1_pct"],
        K.C_ING1_PRECIO:   FEED_DEFAULTS["C"]["ing1_precio"],
        K.C_ING2_PCT:      FEED_DEFAULTS["C"]["ing2_pct"],
        K.C_ING2_PRECIO:   FEED_DEFAULTS["C"]["ing2_precio"],
        K.C_SANIDAD:       ANIMAL_DEFAULTS["C"]["sanidad"],
        K.C_MO_DIA:        ANIMAL_DEFAULTS["C"]["mo_dia"],
        K.C_FLETE_ENTRADA: COMMERCIAL_DEFAULTS["C"]["flete_entrada"],
        K.C_FLETE_SALIDA:  COMMERCIAL_DEFAULTS["C"]["flete_salida"],
        K.C_AMORTIZACION:  INFRA_DEFAULTS["C"]["amortizacion"],
        K.C_OTROS:         COMMERCIAL_DEFAULTS["C"]["otros"],

        # ── Infraestructura — nuevas (sin UI todavía) ──────────────────────────
        K.INFRA_CORRALES_CANT:    INFRA_DEFAULTS["corrales_cant"],
        K.INFRA_CORRALES_COSTO:   INFRA_DEFAULTS["corrales_costo"],
        K.INFRA_MIXER_COSTO:      INFRA_DEFAULTS["mixer_costo"],
        K.INFRA_MAQUINARIA_COSTO: INFRA_DEFAULTS["maquinaria_costo"],
        K.INFRA_VIDA_UTIL:        INFRA_DEFAULTS["vida_util"],
        K.INFRA_ADMIN_ANUAL:      INFRA_DEFAULTS["admin_anual"],
        K.INFRA_PERSONAL_ANUAL:   INFRA_DEFAULTS["personal_anual"],

        # ── Comercialización extendida — nuevas (sin UI todavía) ───────────────
        K.COMERCIAL_COMISION_PCT:  COMMERCIAL_DEFAULTS["comision_pct"],
        K.COMERCIAL_SUPERFICIE_HA: COMMERCIAL_DEFAULTS["superficie_ha"],

        # ── Cría (A) — adicionales ─────────────────────────────────────────
        K.A_KG_ENTRADA:   DEFAULTS["a_kg_entrada"],
        K.A_GDP:          DEFAULTS["a_gdp"],
        K.A_COMISION_PCT: DEFAULTS["a_comision_pct"],

        # ── Recría (B) — adicionales ───────────────────────────────────────
        K.B_DIAS:          DEFAULTS["b_dias"],
        K.B_PRECIO_COMPRA: DEFAULTS["b_pc"],
        K.B_ALIM_DIA:      DEFAULTS["b_alim_dia"],
        K.B_COMISION_PCT:  DEFAULTS["b_comision_pct"],

        # ── Engorde interno (C) — adicionales ─────────────────────────────
        K.C_DIAS:          DEFAULTS["c_dias"],
        K.C_KG_ENTRADA:    DEFAULTS["c_kg_entrada"],
        K.C_PRECIO_COMPRA: DEFAULTS["c_pc"],
        K.C_ALIM_DIA:      DEFAULTS["c_alim_dia"],
        K.C_COMISION_PCT:  DEFAULTS["c_comision_pct"],

        # ── Engorde exportación (E) ────────────────────────────────────────
        K.E_DIAS:          DEFAULTS["e_dias"],
        K.E_KG_ENTRADA:    DEFAULTS["e_kg_entrada"],
        K.E_KG_SALIDA:     DEFAULTS["e_kg_salida"],
        K.E_GDP:           DEFAULTS["e_gdp"],
        K.E_MORTALIDAD:    DEFAULTS["e_mortalidad"],
        K.E_SANIDAD:       DEFAULTS["e_sanidad"],
        K.E_MO_DIA:        DEFAULTS["e_mo_dia"],
        K.E_ALIM_DIA:      DEFAULTS["e_alim_dia"],
        K.E_PRECIO_COMPRA: DEFAULTS["e_pc"],
        K.E_PRECIO_VENTA:  DEFAULTS["e_pv"],
        K.E_COMISION_PCT:  DEFAULTS["e_comision_pct"],

        # ── Alimentación — ración diaria ───────────────────────────────────
        K.A_RAC_DIARIA: DEFAULTS["a_rac_diaria"],
        K.B_RAC_DIARIA: DEFAULTS["b_rac_diaria"],
        K.C_RAC_DIARIA: DEFAULTS["c_rac_diaria"],
        K.E_RAC_DIARIA: DEFAULTS["e_rac_diaria"],

        # ── Comercialización — fletes nuevos ───────────────────────────────
        K.A_FLETE_ENTRADA:  DEFAULTS["a_fe"],
        K.E_FLETE_ENTRADA:  DEFAULTS["e_fe"],
        K.E_FLETE_SALIDA:   DEFAULTS["e_fs"],

        # ── Comercialización — operativos editables ────────────────────────
        K.A_COM_MO_DIA:  DEFAULTS["a_com_mo"],
        K.A_COM_SANIDAD: DEFAULTS["a_com_san"],
        K.B_COM_MO_DIA:  DEFAULTS["b_com_mo"],
        K.B_COM_SANIDAD: DEFAULTS["b_com_san"],
        K.C_COM_MO_DIA:  DEFAULTS["c_com_mo"],
        K.C_COM_SANIDAD: DEFAULTS["c_com_san"],
        K.E_COM_MO_DIA:  DEFAULTS["e_com_mo"],
        K.E_COM_SANIDAD: DEFAULTS["e_com_san"],
    }

    for key, val in _pairs.items():
        if key not in st.session_state:
            st.session_state[key] = val
