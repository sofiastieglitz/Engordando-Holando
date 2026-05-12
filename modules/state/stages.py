"""
Helpers para la lógica modular de etapas activas.

El dashboard puede correr en modo integrado (Cría → Recría → Engorde) o
modular (cualquier slice contiguo: solo Cría, solo Recría, solo Engorde,
Cría+Recría, Recría+Engorde). Este módulo centraliza:

  - qué etapas están activas
  - cuál es la primera (kg de entrada editable)
  - encadenamiento de kg entre etapas activas consecutivas
  - validación de contiguidad

Todas las páginas (Modelo Productivo, Costos, Márgenes, Sensibilidad, KPIs)
deben usar estos helpers para respetar la selección global del usuario.
"""
from __future__ import annotations

import streamlit as st

import modules.state.keys as K
from modules.state.defaults import DEFAULTS
from modules.state.persist import read, mirror

# Orden canónico del flujo biológico
ALL_STAGES: list[str] = ["cria", "recria", "eng_int"]

_TOGGLE_KEY: dict[str, str] = {
    "cria":    K.STAGE_CRIA_ON,
    "recria":  K.STAGE_RECRIA_ON,
    "eng_int": K.STAGE_ENG_ON,
}

# Por etapa: key del K.*_KG_ENTRADA (input cuando es 1ª activa) y default.
_KG_ENTRADA_KEY: dict[str, tuple[str, float]] = {
    "cria":    (K.A_KG_ENTRADA, DEFAULTS["a_kg_entrada"]),
    "recria":  (K.B_KG_ENTRADA, DEFAULTS["b_kg_entrada"]),
    "eng_int": (K.C_KG_ENTRADA, DEFAULTS["c_kg_entrada"]),
}

# kg_out de cada etapa cuando está encadenada (= kg_in de la siguiente).
_KG_OUT_KEY: dict[str, tuple[str, float]] = {
    "cria":    (K.ANIMAL_PESO_ENTRADA, DEFAULTS["peso_inicial"]),
    "recria":  (K.B_PESO_SALIDA,       DEFAULTS["r_peso_salida"]),
    "eng_int": (K.C_PESO_FINAL,        DEFAULTS["t_peso_final"]),
}


def is_active(stage: str) -> bool:
    """True si la etapa está activada en el modelo.

    Lectura robusta: shadow > widget-key > True (default cuando es la
    primera vez que se accede). Esto garantiza que la activación
    sobreviva la navegación entre slides.
    """
    return bool(read(_TOGGLE_KEY[stage], True))


def active_stages() -> list[str]:
    """Etapas activas en orden Cría → Recría → Engorde."""
    return [s for s in ALL_STAGES if is_active(s)]


def is_first_active(stage: str) -> bool:
    """True si la etapa es la primera del slice activo (sin predecesora)."""
    a = active_stages()
    return bool(a) and a[0] == stage


def is_last_active(stage: str) -> bool:
    a = active_stages()
    return bool(a) and a[-1] == stage


def kg_in_for(stage: str) -> float:
    """Peso de entrada efectivo de la etapa.

    - Si la etapa es la primera activa (modular o integrado), se lee de
      su K.*_KG_ENTRADA (input editable, sin restricciones de valor).
    - Si la etapa está encadenada (hay una etapa activa antes), se hereda
      del kg_out de la etapa previa en el orden canónico.
    """
    if is_first_active(stage):
        key, dflt = _KG_ENTRADA_KEY[stage]
        return float(read(key, dflt))
    idx = ALL_STAGES.index(stage)
    prev_stage = ALL_STAGES[idx - 1]
    key, dflt = _KG_OUT_KEY[prev_stage]
    return float(read(key, dflt))


def kg_out_for(stage: str) -> float:
    """Peso de salida de la etapa (= kg vendidos / pasados a la siguiente)."""
    key, dflt = _KG_OUT_KEY[stage]
    return float(read(key, dflt))


def enforce_contiguity() -> None:
    """Si la selección no es un slice contiguo, fuerza Recría a ON.

    El único patrón inválido posible (con 3 etapas) es Cría=ON, Engorde=ON,
    Recría=OFF. En ese caso se prende Recría para mantener un slice contiguo.

    Debe llamarse ANTES de instanciar los checkboxes del rerun actual:
    una vez instanciado un widget, Streamlit prohíbe escribir a su key
    (StreamlitAPIException).

    Lee vía `read()` (shadow > ss > default). El shadow es la fuente de
    verdad bajo el nuevo patrón de `_num`/checkboxes con widget-key
    separado: el `on_change` lo actualiza inmediatamente cuando el
    usuario hace click, así que `read()` siempre refleja la última
    selección. Escribimos en ambos (mirror al shadow + ss para back-compat).
    """
    cria   = bool(read(K.STAGE_CRIA_ON,   True))
    recria = bool(read(K.STAGE_RECRIA_ON, True))
    eng    = bool(read(K.STAGE_ENG_ON,    True))
    if cria and eng and not recria:
        mirror(K.STAGE_RECRIA_ON, True)
        try:
            st.session_state[K.STAGE_RECRIA_ON] = True
        except Exception:
            pass


def mode_label() -> str:
    """Etiqueta humana del modo activo: 'Cría → Recría → Engorde',
    'Sólo Engorde', 'Recría + Engorde', etc."""
    a = active_stages()
    if not a:
        return "Sin etapas activas"
    pretty = {"cria": "Cría", "recria": "Recría", "eng_int": "Engorde"}
    if len(a) == 1:
        return f"Sólo {pretty[a[0]]}"
    if len(a) == len(ALL_STAGES):
        return " → ".join(pretty[s] for s in a)
    return " + ".join(pretty[s] for s in a)
