"""
Persistencia robusta de session_state entre slides.

Problema que resuelve
─────────────────────
Streamlit elimina del `session_state` las claves de widgets que NO se
renderizan durante un script run. Cuando el usuario navega de
"Parámetros" a "Costos", los widgets de Parámetros no se vuelven a
dibujar, y al final de ese rerun Streamlit borra sus keys. En el rerun
siguiente, `init_state()` ve que la key falta y la repone con el valor
default — pisando el valor cargado por el usuario.

Solución (shadow keys)
──────────────────────
Para cada widget-key `K`, mantenemos una shadow-key `_persist_K` que
NO está atada a ningún widget, por lo que Streamlit no la limpia.

Flujo en cada rerun:
  1. `restore_from_backing()` corre en init_state, ANTES de que ninguna
     slide se renderice → copia shadow → widget-key.
  2. La slide se renderiza. Si es Parámetros, los widgets pueden
     escribir nuevos valores en `session_state[K]`.
  3. Los helpers `_num` / `_sl_f` / `_sl_i` llaman `mirror(K, val)`
     después de que el widget se renderiza → copia widget → shadow.

Resultado: el shadow siempre contiene el último valor del usuario y
sobrevive la navegación entre slides. La única forma de perderlo es
llamar a `reset_to_defaults()` explícitamente.
"""
from __future__ import annotations
from typing import Any

import streamlit as st

import modules.state.keys as K


# ── Lista exhaustiva de claves de widgets que deben persistir ─────────────────
# Cualquier key que un widget escribe y otra slide lee, va acá. Si agregás
# un parámetro nuevo, sumalo a esta lista o se va a comportar mal entre slides.

PERSISTENT_KEYS: list[str] = [
    # Globales
    K.ANIMAL_CANTIDAD,
    K.ANIMAL_PESO_ENTRADA,
    K.COMERCIAL_PRECIO_COMPRA,
    K.FINANCIERO_TIPO_CAMBIO,
    K.FINANCIERO_TASA_INTERES,
    K.COMERCIAL_COMISION_PCT,
    K.COMERCIAL_SUPERFICIE_HA,

    # Toggles de etapas activas
    K.STAGE_CRIA_ON,
    K.STAGE_RECRIA_ON,
    K.STAGE_ENG_ON,

    # Cría (A) — días NO se persiste: es derivado (D.dias_for("cria"))
    K.A_MORTALIDAD, K.A_SANIDAD, K.A_MO_MES,
    K.A_FLETE_ENTRADA, K.A_FLETE_SALIDA, K.A_OTROS,
    K.A_KG_ENTRADA, K.A_GDP, K.A_COMISION_PCT, K.A_CA,
    K.A_COMBUSTIBLE, K.A_SERVICIOS,
    K.A_ASIG_PCT, K.A_AMORT_ANOS, K.A_MANTENIMIENTO,
    K.A_PRECIO_VENTA,

    # Recría (B) — días NO se persiste
    K.B_PESO_SALIDA, K.B_PRECIO_VENTA, K.B_GDP, K.B_MORTALIDAD,
    K.B_CA, K.B_ING1_PCT, K.B_ING1_PRECIO, K.B_ING2_PCT, K.B_ING2_PRECIO,
    K.B_SANIDAD, K.B_MO_MES, K.B_FLETE_ENTRADA, K.B_FLETE_SALIDA, K.B_OTROS,
    K.B_KG_ENTRADA, K.B_PRECIO_COMPRA, K.B_COMISION_PCT,
    K.B_COMBUSTIBLE, K.B_SERVICIOS,
    K.B_ASIG_PCT, K.B_AMORT_ANOS, K.B_MANTENIMIENTO,

    # Engorde (C) — días NO se persiste
    K.C_PESO_FINAL, K.C_PRECIO_VENTA, K.C_GDP, K.C_MORTALIDAD,
    K.C_CA, K.C_ING1_PCT, K.C_ING1_PRECIO, K.C_ING2_PCT, K.C_ING2_PRECIO,
    K.C_SANIDAD, K.C_MO_MES, K.C_FLETE_ENTRADA, K.C_FLETE_SALIDA, K.C_OTROS,
    K.C_KG_ENTRADA, K.C_PRECIO_COMPRA, K.C_COMISION_PCT,
    K.C_COMBUSTIBLE, K.C_SERVICIOS,
    K.C_ASIG_PCT, K.C_AMORT_ANOS, K.C_MANTENIMIENTO,
    K.C_AMORTIZACION,

    # Infraestructura
    K.INFRA_VALOR_TOTAL,
    K.INFRA_CORRALES_CANT, K.INFRA_CORRALES_COSTO,
    K.INFRA_MIXER_COSTO, K.INFRA_MAQUINARIA_COSTO,
    K.INFRA_VIDA_UTIL, K.INFRA_ADMIN_ANUAL, K.INFRA_PERSONAL_ANUAL,
]

# Keys de st.data_editor (tablas de ración por etapa). Streamlit las trata
# como widget-keys también: si la tabla no se renderiza, se purgan.
EDITOR_KEYS: list[str] = [
    "feed_table_cria_de",
    "feed_table_recria_de",
    "feed_table_eng_int_de",
]

# Widget-keys de page_reportes (text_input, date_input, checkbox).
# Tienen el mismo problema de GC al navegar fuera de Reportes.
REPORT_KEYS: list[str] = [
    "report_empresa",
    "report_responsable",
    "report_fecha",
    "report_include_logo",
]

_BACKING_PREFIX = "_persist_"


def _backing(key: str) -> str:
    return _BACKING_PREFIX + key


# ── Mapper de Streamlit: cleanup de entradas stale ────────────────────────────

def purge_stale_widget_mappings() -> None:
    """Limpia entradas stale del `_key_id_mapper` interno de Streamlit.

    Por qué existe
    ──────────────
    En el patrón actual los widgets usan keys efímeras (`_w_<key>`) y el
    canonical vive en `<key>` como state plano (nunca atado a un widget).
    Pero en sesiones donde el código viejo SÍ usó `<key>` como key de
    widget, Streamlit dejó la entrada `<key> → widget_id_stale` en el
    mapper. Esa entrada sobrevive entre reruns y hace que:
      1) `ss[<key>] = v` se almacene bajo `widget_id_stale` en `_old_state`.
      2) Al final del rerun, `_remove_stale_widgets` borre esa entrada
         (es element_id sin widget activo).
      3) En el rerun siguiente, `<key>` aparezca como ausente, perdiendo
         el valor canonical.

    Limpiar el mapper rompe la indirección: writes/reads a `ss[<key>]`
    quedan como state plano, persistente entre reruns.

    Best-effort
    ───────────
    Toca un atributo privado de Streamlit. Si la API interna cambia,
    fallamos silenciosamente y el dashboard sigue funcionando — en el
    peor caso volvemos al bug visible y se resuelve con un refresh
    del navegador (sesión nueva).
    """
    ss = st.session_state
    try:
        real = getattr(ss, "_state", ss)
        mapper = getattr(real, "_key_id_mapper", None)
        if mapper is None:
            return
        for k in PERSISTENT_KEYS:
            if k in mapper:
                mapper.delete(k)
    except Exception:
        pass


# ── API pública ────────────────────────────────────────────────────────────────

def restore_from_backing() -> None:
    """Rehidrata widget-keys desde sus shadows, SOLO si están ausentes.

    Regla crítica:
        ss[k] = ss[backing]   ⇐   k NO está en session_state

    Por qué la condición es indispensable:
      - Si el usuario acaba de modificar el widget, Streamlit ya colocó el
        valor recién tipeado en ss[k] antes de que arranque el rerun. Si
        sobreescribimos acá (incondicionalmente), pisamos el input del
        usuario con el valor viejo del shadow → el campo "rebota" al
        valor previo y se ve como si no se pudiera editar.
      - Si Streamlit eliminó ss[k] (porque la slide con el widget no se
        renderó en el rerun pasado), entonces ss[k] NO existe y SÍ
        queremos copiar desde el shadow.

    Por eso solo restauramos cuando la key falta. La presencia de ss[k]
    siempre representa el valor más fresco posible (el usuario o el
    rerun anterior).

    EDITOR_KEYS (tablas de ración) NO se restauran acá: Streamlit
    prohíbe escribir programáticamente a la key de un st.data_editor
    (`StreamlitValueAssignmentNotAllowedError`). Para ellas la persistencia
    funciona vía `data=` argument + lectura del shadow en consumidores
    (ver `get_editor_state` abajo).
    """
    ss = st.session_state
    for k in PERSISTENT_KEYS:
        if k in ss:
            continue   # ya tiene valor fresco — no pisar
        b = _backing(k)
        if b in ss:
            ss[k] = ss[b]
    for k in REPORT_KEYS:
        if k in ss:
            continue
        b = _backing(k)
        if b in ss:
            ss[k] = ss[b]


def get_editor_state(editor_key: str) -> Any:
    """Devuelve el estado más fresco de un st.data_editor.

    - Si ss[editor_key] existe (el widget se renderó en este rerun), lo
      devuelve directamente. Puede ser un dict-delta o un DataFrame.
    - Si NO existe (Streamlit lo eliminó porque navegamos a otra slide),
      cae al shadow store, que mantiene el último estado completo guardado
      por `_feed_table_block` después de cada render.

    Usado por todos los consumidores (page_costos, page_margenes,
    page_modelo_productivo, page_sensibilidad) para leer la tabla de
    ración sin depender de la widget-key (cuya persistencia es
    administrada por Streamlit y se pierde al navegar).
    """
    ss = st.session_state
    if editor_key in ss:
        return ss[editor_key]
    return ss.get(_backing(editor_key))


def save_editor_state(editor_key: str, value: Any) -> None:
    """Guarda el estado completo de un st.data_editor en el shadow store.

    Streamlit no nos deja escribir ss[editor_key] directamente, pero el
    shadow (`_persist_<editor_key>`) es una key no-widget, así que la
    escritura es válida. Esto es lo que permite que la tabla de ración
    sobreviva la navegación entre slides.

    Convención: el caller pasa el DataFrame COMPLETO post-edición
    (`edited.copy()`), no el dict-delta. Los consumidores luego pueden
    leer el DataFrame directamente sin reconstruir nada.
    """
    st.session_state[_backing(editor_key)] = value


def mirror(key: str, value: Any) -> None:
    """Copia widget → shadow después de que el widget se renderiza.

    Los helpers `_num`/`_sl_f`/`_sl_i`/data_editor del usuario llaman
    esto inmediatamente después de leer el valor del widget. Idempotente.
    """
    st.session_state[_backing(key)] = value


def read(key: str, default: Any) -> Any:
    """Devuelve el valor más fresco para una key persistida.

    Prioridad de lectura:
      1. shadow `_persist_<key>` — sobrevive a la navegación entre slides
         siempre, porque no es widget-key (Streamlit no la GC).
      2. widget-key `<key>` — válido cuando la slide del widget está activa.
      3. `default` — para la primera sesión o post-reset.

    Las páginas consumidoras (Costos, Margen, Sensibilidad, etc.) deben
    usar esto en lugar de `ss.get(key, default)` directo. Garantiza que
    los valores cargados por el usuario en Parámetros sobrevivan la
    navegación incluso si Streamlit purgó la widget-key antes de que
    `restore_from_backing()` corriera.
    """
    ss = st.session_state
    b = _backing(key)
    if b in ss:
        return ss[b]
    if key in ss:
        return ss[key]
    return default


def mirror_current(key: str) -> None:
    """Conveniencia: copia ss[key] al shadow correspondiente.

    Útil para widgets cuyo valor no devolvemos explícitamente (checkboxes,
    data_editor). Si la key no está en session_state, no hace nada.
    """
    ss = st.session_state
    if key in ss:
        ss[_backing(key)] = ss[key]


def reset_to_defaults() -> None:
    """Limpia TODAS las shadow-keys y widget-keys persistidas.

    En el próximo rerun, `init_state()` re-aplicará los defaults a las
    keys faltantes (las propias del dashboard). Útil para el botón
    'Restablecer defaults'.
    """
    ss = st.session_state
    for k in (list(PERSISTENT_KEYS)
              + list(EDITOR_KEYS)
              + list(REPORT_KEYS)):
        ss.pop(k, None)
        ss.pop(_backing(k), None)
