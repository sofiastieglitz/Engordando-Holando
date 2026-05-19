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
from modules.state.persist import restore_from_backing, purge_stale_widget_mappings


def init_state() -> None:
    """
    Establece todas las claves de session_state con sus valores por defecto
    si todavía no existen. Idempotente: llamadas subsiguientes no sobreescriben
    el estado del usuario.

    Orden:
      0. `restore_from_backing()`: rehidrata los widget-keys desde sus
         shadows. Esto es lo que permite que valores cargados en
         "Parámetros" sobrevivan la navegación a otras slides (Streamlit
         purga widget-keys cuyo widget no se rendere en el rerun).
      1. Fill de defaults para keys que TODAVÍA falten (primera sesión,
         o post-reset). Las keys ya rehidratadas por restore_from_backing
         no se tocan.
    """
    # ── 0a. Cleanup del mapper interno de Streamlit ───────────────────────
    # Los keys canónicos (K.*) ya no son widget-keys: los widgets ahora
    # usan `_w_<K>`. Si el sesión tiene entradas viejas en el mapper
    # (por código viejo o sesiones previas al refactor), se purgan acá
    # para que los writes/reads sobre ss[K] no pasen por la indirección
    # stale al widget_id, que sería barrida por el GC al fin del rerun.
    purge_stale_widget_mappings()

    # ── 0b. Rehidratación desde shadow keys ───────────────────────────────
    # Debe correr ANTES de cualquier comparación `key not in session_state`
    # porque las keys rehidratadas ya están "presentes" y no deben recibir
    # default.
    restore_from_backing()

    _pairs: dict = {
        # ── Comunes ────────────────────────────────────────────────────────────
        K.ANIMAL_CANTIDAD:          ANIMAL_DEFAULTS["n_terneros"],
        K.ANIMAL_PESO_ENTRADA:      int(ANIMAL_DEFAULTS["peso_inicial"]),
        K.COMERCIAL_PRECIO_COMPRA:  COMMERCIAL_DEFAULTS["precio_compra"],
        K.FINANCIERO_TIPO_CAMBIO:   COMMERCIAL_DEFAULTS["tipo_cambio"],
        K.FINANCIERO_TASA_INTERES:  COMMERCIAL_DEFAULTS["tasa_interes"],

        # ── A — Venta al destete ───────────────────────────────────────────────
        # K.A_DIAS / B_DIAS / C_DIAS ya NO se siembran: días es derivado
        # (modules.state.derived.dias_for) = (kg_out − kg_in) / GDP.
        K.A_PRECIO_VENTA:   COMMERCIAL_DEFAULTS["A"]["precio_venta"],
        K.A_MORTALIDAD:     ANIMAL_DEFAULTS["A"]["mortalidad"],
        K.A_SANIDAD:        ANIMAL_DEFAULTS["A"]["sanidad"],
        K.A_MO_MES:         ANIMAL_DEFAULTS["A"]["mo_mes"],
        K.A_FLETE_SALIDA:   COMMERCIAL_DEFAULTS["A"]["flete_salida"],
        K.A_OTROS:          COMMERCIAL_DEFAULTS["A"]["otros"],

        # ── B — Venta recriado ─────────────────────────────────────────────────
        K.B_PESO_SALIDA:   int(ANIMAL_DEFAULTS["B"]["peso_salida"]),
        K.B_PRECIO_VENTA:  COMMERCIAL_DEFAULTS["B"]["precio_venta"],
        K.B_GDP:           ANIMAL_DEFAULTS["B"]["gdp"],
        K.B_MORTALIDAD:    ANIMAL_DEFAULTS["B"]["mortalidad"],
        K.B_ING1_PCT:      FEED_DEFAULTS["B"]["ing1_pct"],
        K.B_ING1_PRECIO:   FEED_DEFAULTS["B"]["ing1_precio"],
        K.B_ING2_PCT:      FEED_DEFAULTS["B"]["ing2_pct"],
        K.B_ING2_PRECIO:   FEED_DEFAULTS["B"]["ing2_precio"],
        K.B_SANIDAD:       ANIMAL_DEFAULTS["B"]["sanidad"],
        K.B_MO_MES:        ANIMAL_DEFAULTS["B"]["mo_mes"],
        K.B_FLETE_ENTRADA: COMMERCIAL_DEFAULTS["B"]["flete_entrada"],
        K.B_FLETE_SALIDA:  COMMERCIAL_DEFAULTS["B"]["flete_salida"],
        K.B_OTROS:         COMMERCIAL_DEFAULTS["B"]["otros"],

        # ── C — Venta terminado ────────────────────────────────────────────────
        K.C_PESO_FINAL:    int(ANIMAL_DEFAULTS["C"]["peso_final"]),
        K.C_PRECIO_VENTA:  COMMERCIAL_DEFAULTS["C"]["precio_venta"],
        K.C_GDP:           ANIMAL_DEFAULTS["C"]["gdp"],
        K.C_MORTALIDAD:    ANIMAL_DEFAULTS["C"]["mortalidad"],
        K.C_ING1_PCT:      FEED_DEFAULTS["C"]["ing1_pct"],
        K.C_ING1_PRECIO:   FEED_DEFAULTS["C"]["ing1_precio"],
        K.C_ING2_PCT:      FEED_DEFAULTS["C"]["ing2_pct"],
        K.C_ING2_PRECIO:   FEED_DEFAULTS["C"]["ing2_precio"],
        K.C_SANIDAD:       ANIMAL_DEFAULTS["C"]["sanidad"],
        K.C_MO_MES:        ANIMAL_DEFAULTS["C"]["mo_mes"],
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
        K.B_KG_ENTRADA:    DEFAULTS["b_kg_entrada"],
        K.B_PRECIO_COMPRA: DEFAULTS["b_pc"],
        K.B_COMISION_PCT:  DEFAULTS["b_comision_pct"],

        # ── Engorde (C) — adicionales ──────────────────────────────────────
        K.C_KG_ENTRADA:    DEFAULTS["c_kg_entrada"],
        K.C_PRECIO_COMPRA: DEFAULTS["c_pc"],
        K.C_COMISION_PCT:  DEFAULTS["c_comision_pct"],

        # ── Comercialización — fletes nuevos ───────────────────────────────
        K.A_FLETE_ENTRADA:  DEFAULTS["a_fe"],

        # NOTA: K.A_CA / K.B_CA / K.C_CA fueron eliminados. La conversión
        # alimenticia es derivada desde la tabla de ración en
        # modules.state.derived (no se siembra en session_state).

        # ── Operación — combustible + servicios por etapa ──────────────────
        K.A_COMBUSTIBLE: DEFAULTS["a_combustible"],
        K.B_COMBUSTIBLE: DEFAULTS["b_combustible"],
        K.C_COMBUSTIBLE: DEFAULTS["c_combustible"],

        K.A_SERVICIOS:   DEFAULTS["a_servicios"],
        K.B_SERVICIOS:   DEFAULTS["b_servicios"],
        K.C_SERVICIOS:   DEFAULTS["c_servicios"],

        # ── Estructura — valor infra GLOBAL + % asignado por etapa ─────────
        K.INFRA_VALOR_TOTAL: DEFAULTS["infra_valor_total"],

        K.A_ASIG_PCT: DEFAULTS["a_asig_pct"],
        K.B_ASIG_PCT: DEFAULTS["b_asig_pct"],
        K.C_ASIG_PCT: DEFAULTS["c_asig_pct"],

        K.A_AMORT_ANOS:  DEFAULTS["a_amort_anos"],
        K.B_AMORT_ANOS:  DEFAULTS["b_amort_anos"],
        K.C_AMORT_ANOS:  DEFAULTS["c_amort_anos"],

        K.A_MANTENIMIENTO: DEFAULTS["a_mantenimiento"],
        K.B_MANTENIMIENTO: DEFAULTS["b_mantenimiento"],
        K.C_MANTENIMIENTO: DEFAULTS["c_mantenimiento"],

        # ── Etapas activas (modular vs integrado) ──────────────────────────
        K.STAGE_CRIA_ON:   True,
        K.STAGE_RECRIA_ON: True,
        K.STAGE_ENG_ON:    True,
    }

    for key, val in _pairs.items():
        if key not in st.session_state:
            st.session_state[key] = val
