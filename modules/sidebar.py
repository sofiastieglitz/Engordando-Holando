import streamlit as st

import modules.state.keys as K
from modules.state import init_state


# ── Widget helpers (usados por page_parametros.py) ────────────────────────────

def _sl_f(label: str, lo: float, hi: float, val: float, step: float,
          fmt: str = "%.2f", key: str = "") -> float:
    if not key:
        return float(st.slider(label, lo, hi, float(val), step, format=fmt))
    if key not in st.session_state:
        st.session_state[key] = float(val)
    else:
        st.session_state[key] = float(max(lo, min(hi, float(st.session_state[key]))))
    return float(st.slider(label, lo, hi, step=step, format=fmt, key=key))


def _sl_i(label: str, lo: int, hi: int, val: int, step: int = 1,
          key: str = "") -> int:
    if not key:
        return int(st.slider(label, lo, hi, int(val), step))
    if key not in st.session_state:
        st.session_state[key] = int(val)
    else:
        st.session_state[key] = int(max(lo, min(hi, int(float(st.session_state[key])))))
    return int(st.slider(label, lo, hi, step=step, key=key))


def _info(text: str) -> None:
    st.caption(f"→ {text}")


def _weighted_price(pct1: float, pr1: float, pct2: float, pr2: float) -> float:
    total = pct1 + pct2
    return (pct1 * pr1 + pct2 * pr2) / max(total, 0.01)


# ── Entry point principal ─────────────────────────────────────────────────────

def render_sidebar() -> dict:
    """
    Inicializa el estado y construye los 4 dicts de parámetros categorizados.

    Retorna un dict con exactamente 4 claves:
      params["animal_params"]     — parámetros biológicos y productivos
      params["feed_params"]       — parámetros de alimentación
      params["infra_params"]      — parámetros de infraestructura
      params["commercial_params"] — parámetros comerciales y financieros
    """
    init_state()

    ss = st.session_state

    # ── Parámetros de animales ────────────────────────────────────────────────
    animal_params: dict = {
        "n_terneros":  int(ss[K.ANIMAL_CANTIDAD]),
        "peso_inicial": float(ss[K.ANIMAL_PESO_ENTRADA]),
        "A": {
            "dias":       int(ss[K.A_DIAS]),
            "mortalidad": float(ss[K.A_MORTALIDAD]) / 100,   # % → decimal
            "sanidad":    float(ss[K.A_SANIDAD]),
            "mo_mes":     float(ss[K.A_MO_MES]),
        },
        "B": {
            "peso_salida": float(ss[K.B_PESO_SALIDA]),
            "gdp":         float(ss[K.B_GDP]),
            "mortalidad":  float(ss[K.B_MORTALIDAD]) / 100,
            "ca":          float(ss[K.B_CA]),
            "sanidad":     float(ss[K.B_SANIDAD]),
            "mo_mes":      float(ss[K.B_MO_MES]),
        },
        "C": {
            "peso_final":  float(ss[K.C_PESO_FINAL]),
            "gdp":         float(ss[K.C_GDP]),
            "mortalidad":  float(ss[K.C_MORTALIDAD]) / 100,
            "ca":          float(ss[K.C_CA]),
            "sanidad":     float(ss[K.C_SANIDAD]),
            "mo_mes":      float(ss[K.C_MO_MES]),
        },
    }

    # ── Parámetros de alimentación ─────────────────────────────────────────────
    # La fuente de verdad es la feed table editable de page_parametros (modelo
    # bioeconómico puro). Los keys ing1/2 abajo son legacy para Comparador
    # (scenarios.py); A ya no se expone porque no tiene equivalente.
    feed_params: dict = {
        "B": {
            "ing1_pct":       float(ss[K.B_ING1_PCT]),
            "ing1_precio":    float(ss[K.B_ING1_PRECIO]),
            "ing2_pct":       float(ss[K.B_ING2_PCT]),
            "ing2_precio":    float(ss[K.B_ING2_PRECIO]),
            "precio_alimento": _weighted_price(
                ss[K.B_ING1_PCT], ss[K.B_ING1_PRECIO],
                ss[K.B_ING2_PCT], ss[K.B_ING2_PRECIO],
            ),
        },
        "C": {
            "ing1_pct":       float(ss[K.C_ING1_PCT]),
            "ing1_precio":    float(ss[K.C_ING1_PRECIO]),
            "ing2_pct":       float(ss[K.C_ING2_PCT]),
            "ing2_precio":    float(ss[K.C_ING2_PRECIO]),
            "precio_alimento": _weighted_price(
                ss[K.C_ING1_PCT], ss[K.C_ING1_PRECIO],
                ss[K.C_ING2_PCT], ss[K.C_ING2_PRECIO],
            ),
        },
    }

    # ── Parámetros de infraestructura ──────────────────────────────────────────
    infra_params: dict = {
        "C": {
            "amortizacion": float(ss[K.C_AMORTIZACION]),
        },
        "corrales_cant":    int(ss[K.INFRA_CORRALES_CANT]),
        "corrales_costo":   float(ss[K.INFRA_CORRALES_COSTO]),
        "mixer_costo":      float(ss[K.INFRA_MIXER_COSTO]),
        "maquinaria_costo": float(ss[K.INFRA_MAQUINARIA_COSTO]),
        "vida_util":        int(ss[K.INFRA_VIDA_UTIL]),
        "admin_anual":      float(ss[K.INFRA_ADMIN_ANUAL]),
        "personal_anual":   float(ss[K.INFRA_PERSONAL_ANUAL]),
    }

    # ── Parámetros de comercialización ────────────────────────────────────────
    commercial_params: dict = {
        "precio_compra": float(ss[K.COMERCIAL_PRECIO_COMPRA]),
        "tipo_cambio":   float(ss[K.FINANCIERO_TIPO_CAMBIO]),
        "tasa_interes":  float(ss[K.FINANCIERO_TASA_INTERES]) / 100,  # % → decimal
        "comision_pct":  float(ss[K.COMERCIAL_COMISION_PCT]),
        "superficie_ha": float(ss[K.COMERCIAL_SUPERFICIE_HA]),
        "A": {
            "precio_venta": float(ss[K.A_PRECIO_VENTA]),
            "flete_salida": float(ss[K.A_FLETE_SALIDA]),
            "otros":        float(ss[K.A_OTROS]),
        },
        "B": {
            "precio_venta":  float(ss[K.B_PRECIO_VENTA]),
            "flete_entrada": float(ss[K.B_FLETE_ENTRADA]),
            "flete_salida":  float(ss[K.B_FLETE_SALIDA]),
            "otros":         float(ss[K.B_OTROS]),
        },
        "C": {
            "precio_venta":  float(ss[K.C_PRECIO_VENTA]),
            "flete_entrada": float(ss[K.C_FLETE_ENTRADA]),
            "flete_salida":  float(ss[K.C_FLETE_SALIDA]),
            "otros":         float(ss[K.C_OTROS]),
        },
    }

    return {
        "animal_params":     animal_params,
        "feed_params":       feed_params,
        "infra_params":      infra_params,
        "commercial_params": commercial_params,
    }
