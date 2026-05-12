import streamlit as st

import modules.state.keys as K
import modules.state.derived as D
from modules.state import init_state
from modules.state.defaults import DEFAULTS
from modules.state.persist import mirror, read


# ── Widget helpers (usados por page_parametros.py) ────────────────────────────
#
# Importante:
#   - NO clampear ss[key] en cada rerun. Streamlit's slider ya impone los
#     bounds min/max; clampear nosotros era un anti-patrón que reescribía
#     el valor del usuario en cada render y arrastraba la complicación de
#     la GC de widget-keys de Streamlit.
#   - DESPUÉS de renderizar el widget, llamamos `mirror(key, val)` para
#     copiar el valor al shadow store (modules.state.persist). El shadow
#     es lo que sobrevive a la navegación entre slides; el widget-key
#     puro lo limpia Streamlit cuando el widget no se rendere.

def _sl_f(label: str, lo: float, hi: float, val: float, step: float,
          fmt: str = "%.2f", key: str = "") -> float:
    if not key:
        return float(st.slider(label, lo, hi, float(val), step, format=fmt))
    if key not in st.session_state:
        st.session_state[key] = float(val)
    result = float(st.slider(label, lo, hi, step=step, format=fmt, key=key))
    mirror(key, result)
    return result


def _sl_i(label: str, lo: int, hi: int, val: int, step: int = 1,
          key: str = "") -> int:
    if not key:
        return int(st.slider(label, lo, hi, int(val), step))
    if key not in st.session_state:
        st.session_state[key] = int(val)
    result = int(st.slider(label, lo, hi, step=step, key=key))
    mirror(key, result)
    return result


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

    # Lecturas vía `read()` (shadow > widget-key > default): los params se
    # construyen en cada rerun y deben ser robustos a la purga de
    # widget-keys que Streamlit hace al navegar a otra slide.
    _g = read

    # ── Parámetros de animales ────────────────────────────────────────────────
    # Días por etapa = derivado (D.dias_for) — ya no es input editable.
    animal_params: dict = {
        "n_terneros":  int(_g(K.ANIMAL_CANTIDAD, DEFAULTS["n_terneros"])),
        "peso_inicial": float(_g(K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"])),
        "A": {
            "dias":       D.dias_for("cria"),
            "mortalidad": float(_g(K.A_MORTALIDAD, DEFAULTS["d_mortalidad"])) / 100,
            "sanidad":    float(_g(K.A_SANIDAD,    DEFAULTS["d_sanidad"])),
            "mo_mes":     float(_g(K.A_MO_MES,     DEFAULTS["d_mo_mes"])),
        },
        "B": {
            "peso_salida": float(_g(K.B_PESO_SALIDA, DEFAULTS["r_peso_salida"])),
            "gdp":         float(_g(K.B_GDP,         DEFAULTS["r_gdp"])),
            "mortalidad":  float(_g(K.B_MORTALIDAD,  DEFAULTS["r_mortalidad"])) / 100,
            "ca":          float(_g(K.B_CA,          DEFAULTS["r_ca"])),
            "sanidad":     float(_g(K.B_SANIDAD,     DEFAULTS["r_sanidad"])),
            "mo_mes":      float(_g(K.B_MO_MES,      DEFAULTS["r_mo_mes"])),
            "dias":        D.dias_for("recria"),
        },
        "C": {
            "peso_final":  float(_g(K.C_PESO_FINAL, DEFAULTS["t_peso_final"])),
            "gdp":         float(_g(K.C_GDP,        DEFAULTS["t_gdp"])),
            "mortalidad":  float(_g(K.C_MORTALIDAD, DEFAULTS["t_mortalidad"])) / 100,
            "ca":          float(_g(K.C_CA,         DEFAULTS["t_ca"])),
            "sanidad":     float(_g(K.C_SANIDAD,    DEFAULTS["t_sanidad"])),
            "mo_mes":      float(_g(K.C_MO_MES,     DEFAULTS["t_mo_mes"])),
            "dias":        D.dias_for("eng_int"),
        },
    }

    # ── Parámetros de alimentación ─────────────────────────────────────────────
    # La fuente de verdad es la feed table editable de page_parametros (modelo
    # bioeconómico puro). Los keys ing1/2 abajo son legacy para Comparador
    # (scenarios.py); A ya no se expone porque no tiene equivalente.
    b_p1 = float(_g(K.B_ING1_PCT,    DEFAULTS["r_ing1_pct"]))
    b_x1 = float(_g(K.B_ING1_PRECIO, DEFAULTS["r_ing1_precio"]))
    b_p2 = float(_g(K.B_ING2_PCT,    DEFAULTS["r_ing2_pct"]))
    b_x2 = float(_g(K.B_ING2_PRECIO, DEFAULTS["r_ing2_precio"]))
    c_p1 = float(_g(K.C_ING1_PCT,    DEFAULTS["t_ing1_pct"]))
    c_x1 = float(_g(K.C_ING1_PRECIO, DEFAULTS["t_ing1_precio"]))
    c_p2 = float(_g(K.C_ING2_PCT,    DEFAULTS["t_ing2_pct"]))
    c_x2 = float(_g(K.C_ING2_PRECIO, DEFAULTS["t_ing2_precio"]))

    feed_params: dict = {
        "B": {
            "ing1_pct":       b_p1,
            "ing1_precio":    b_x1,
            "ing2_pct":       b_p2,
            "ing2_precio":    b_x2,
            "precio_alimento": _weighted_price(b_p1, b_x1, b_p2, b_x2),
        },
        "C": {
            "ing1_pct":       c_p1,
            "ing1_precio":    c_x1,
            "ing2_pct":       c_p2,
            "ing2_precio":    c_x2,
            "precio_alimento": _weighted_price(c_p1, c_x1, c_p2, c_x2),
        },
    }

    # ── Parámetros de infraestructura ──────────────────────────────────────────
    infra_params: dict = {
        "C": {
            "amortizacion": float(_g(K.C_AMORTIZACION, DEFAULTS["t_amortizacion"])),
        },
        "corrales_cant":    int(_g(K.INFRA_CORRALES_CANT,    DEFAULTS["infra_corrales_cant"])),
        "corrales_costo":   float(_g(K.INFRA_CORRALES_COSTO, 0.0)),
        "mixer_costo":      float(_g(K.INFRA_MIXER_COSTO,      0.0)),
        "maquinaria_costo": float(_g(K.INFRA_MAQUINARIA_COSTO, 0.0)),
        "vida_util":        int(_g(K.INFRA_VIDA_UTIL, DEFAULTS["infra_vida_util"])),
        "admin_anual":      float(_g(K.INFRA_ADMIN_ANUAL,    0.0)),
        "personal_anual":   float(_g(K.INFRA_PERSONAL_ANUAL, 0.0)),
    }

    # ── Parámetros de comercialización ────────────────────────────────────────
    commercial_params: dict = {
        "precio_compra": float(_g(K.COMERCIAL_PRECIO_COMPRA, DEFAULTS["precio_compra"])),
        "tipo_cambio":   float(_g(K.FINANCIERO_TIPO_CAMBIO,  DEFAULTS["tipo_cambio"])),
        "tasa_interes":  float(_g(K.FINANCIERO_TASA_INTERES, DEFAULTS["tasa_interes"])) / 100,
        "comision_pct":  float(_g(K.COMERCIAL_COMISION_PCT,  0.0)),
        "superficie_ha": float(_g(K.COMERCIAL_SUPERFICIE_HA, 0.0)),
        "A": {
            "precio_venta": float(_g(K.A_PRECIO_VENTA, DEFAULTS["d_precio_venta"])),
            "flete_salida": float(_g(K.A_FLETE_SALIDA, DEFAULTS["d_flete"])),
            "otros":        float(_g(K.A_OTROS,        DEFAULTS["d_otros"])),
        },
        "B": {
            "precio_venta":  float(_g(K.B_PRECIO_VENTA,  DEFAULTS["r_precio_venta"])),
            "flete_entrada": float(_g(K.B_FLETE_ENTRADA, DEFAULTS["r_flete_entrada"])),
            "flete_salida":  float(_g(K.B_FLETE_SALIDA,  DEFAULTS["r_flete_salida"])),
            "otros":         float(_g(K.B_OTROS,         DEFAULTS["r_otros"])),
        },
        "C": {
            "precio_venta":  float(_g(K.C_PRECIO_VENTA,  DEFAULTS["t_precio_venta"])),
            "flete_entrada": float(_g(K.C_FLETE_ENTRADA, DEFAULTS["t_flete_entrada"])),
            "flete_salida":  float(_g(K.C_FLETE_SALIDA,  DEFAULTS["t_flete_salida"])),
            "otros":         float(_g(K.C_OTROS,         DEFAULTS["t_otros"])),
        },
    }

    return {
        "animal_params":     animal_params,
        "feed_params":       feed_params,
        "infra_params":      infra_params,
        "commercial_params": commercial_params,
    }
