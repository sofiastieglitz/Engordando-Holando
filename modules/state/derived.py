"""
Derivados — cálculos automáticos sobre el estado base.

Este módulo es la ÚNICA fuente de los siguientes valores derivados:
  - Días de tenencia por etapa (`dias_for`) — antes era input manual,
    ahora se calcula: días = (peso_salida − peso_entrada) / GDP.
  - Consumo MS por ciclo y por día (`consumo_ms_cab`, `consumo_ms_dia_cab`).
  - Consumo MV por día (`consumo_mv_dia_cab`), derivado vía %MS de la
    composición de la ración.
  - Per-ingrediente: kg MS/día y kg MV/día por cabeza (`consumo_ingredientes`).
  - Precio ponderado y %MS promedio de la ración (`precio_ponderado`,
    `pct_ms_promedio`).

Todas las funciones son puras sobre `st.session_state` y los shadows de
la tabla de alimentación. Garantizan que Costos, Márgenes, Sensibilidad,
Modelo Productivo, Ingresos y Reportes vean valores idénticos sin
duplicar lógica.

Validaciones:
  - max(x, 0) defensivo en pesos / GDP / CA.
  - Divisores → cero ⇒ resultado 0 (no NaN).
  - Tabla vacía o sin %MS ⇒ MV = 0 (no se inventa).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import modules.state.keys as K
import modules.state.stages as S
from modules.state.persist import get_editor_state, read


# ── Mapeo etapa → claves de session_state ────────────────────────────────────

_GDP_KEY = {"cria": K.A_GDP, "recria": K.B_GDP, "eng_int": K.C_GDP}
_CA_KEY  = {"cria": K.A_CA,  "recria": K.B_CA,  "eng_int": K.C_CA}

_FEED_EDITOR_KEY = {
    "cria":    "feed_table_cria_de",
    "recria":  "feed_table_recria_de",
    "eng_int": "feed_table_eng_int_de",
}


def _g(key: str, default: float = 0.0) -> float:
    """Lectura robusta: shadow > widget-key > default.

    Garantiza que los valores cargados en Parámetros sean visibles para
    los cálculos derivados incluso cuando Streamlit purga las widget-keys
    al navegar a otra slide.
    """
    return float(read(key, default))


# ── Valores cargados (passthrough con conversión) ────────────────────────────

def gdp_for(stage: str) -> float:
    return _g(_GDP_KEY[stage], 0.0)


def ca_for(stage: str) -> float:
    return _g(_CA_KEY[stage], 0.0)


def kg_in_for(stage: str) -> float:
    return float(S.kg_in_for(stage))


def kg_out_for(stage: str) -> float:
    return float(S.kg_out_for(stage))


def kg_producidos_cab(stage: str) -> float:
    return max(kg_out_for(stage) - kg_in_for(stage), 0.0)


# ── Tiempo ────────────────────────────────────────────────────────────────────

def dias_for(stage: str) -> int:
    """Días de tenencia derivados: (peso_salida − peso_entrada) / GDP.

    Antes era un input editable. Ahora se recalcula en cada lectura, así
    el resto del dashboard (costos, márgenes, sensibilidad, etc.) ve el
    mismo número sin que el usuario tenga que mantenerlo coherente.

    Validaciones:
      - GDP ≤ 0 ó kg_producidos ≤ 0 ⇒ 0 días.
      - Resultado entero (redondeo al entero más cercano).
    """
    kg_prod = kg_producidos_cab(stage)
    gdp = gdp_for(stage)
    if gdp <= 0 or kg_prod <= 0:
        return 0
    return int(round(kg_prod / gdp))


def dias_total() -> int:
    """Suma de días sobre las etapas activas (slice contiguo)."""
    return sum(dias_for(s) for s in S.active_stages())


# ── Consumo MS ────────────────────────────────────────────────────────────────

def consumo_ms_cab(stage: str) -> float:
    """Consumo MS TOTAL del ciclo, kg MS/cab.

    consumo_MS = kg_producidos × CA
    """
    return kg_producidos_cab(stage) * max(ca_for(stage), 0.0)


def consumo_ms_dia_cab(stage: str) -> float:
    """Consumo MS DIARIO, kg MS/cab/día.

    consumo_MS/día = GDP × CA
    """
    return max(gdp_for(stage), 0.0) * max(ca_for(stage), 0.0)


# ── Tabla de alimentación: lectura normalizada ───────────────────────────────

_FEED_COLS = ["Ingrediente", "%", "%MS", "USD/kg MS"]


def _empty_feed_df(rows: int = 10) -> pd.DataFrame:
    return pd.DataFrame({
        "Ingrediente": [""]   * rows,
        "%":           [0.0]  * rows,
        "%MS":         [0.0]  * rows,
        "USD/kg MS":   [0.0]  * rows,
    })


def migrate_feed_df(df: pd.DataFrame, rows: int = 10) -> pd.DataFrame:
    """Garantiza el esquema canónico [Ingrediente, %, %MS, USD/kg MS].

    - Inserta %MS=0.0 si no existe (migración de tablas previas a 3 cols).
    - Reordena columnas al canónico.
    - Trunca/expande al número de filas pedido.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _empty_feed_df(rows)
    out = df.copy()
    if "%MS" not in out.columns:
        out["%MS"] = 0.0
    if "Ingrediente" not in out.columns:
        out["Ingrediente"] = ""
    if "%" not in out.columns:
        out["%"] = 0.0
    if "USD/kg MS" not in out.columns:
        out["USD/kg MS"] = 0.0
    out = out[_FEED_COLS]
    if len(out) < rows:
        pad = _empty_feed_df(rows - len(out))
        out = pd.concat([out, pad], ignore_index=True)
    elif len(out) > rows:
        out = out.iloc[:rows].reset_index(drop=True)
    return out


def _read_feed_raw(stage: str) -> pd.DataFrame:
    """DataFrame crudo del shadow (10 filas). Útil cuando un dict-delta
    está en ss y necesitamos reconstruir; el orquestador en
    page_parametros guarda DataFrames completos en el shadow tras editar."""
    val = get_editor_state(_FEED_EDITOR_KEY[stage])
    if isinstance(val, pd.DataFrame):
        return migrate_feed_df(val)
    if isinstance(val, dict):
        df = _empty_feed_df()
        for idx_str, changes in val.get("edited_rows", {}).items():
            try:
                idx = int(idx_str)
            except (ValueError, TypeError):
                continue
            if 0 <= idx < len(df):
                for col, v in changes.items():
                    if col in df.columns:
                        df.at[idx, col] = v
        return df
    return _empty_feed_df()


def feed_df_active(stage: str) -> pd.DataFrame:
    """Filas con ingrediente no-vacío y % > 0, columnas canónicas."""
    raw = _read_feed_raw(stage)
    name = raw["Ingrediente"].astype(str).str.strip()
    pct = pd.to_numeric(raw["%"], errors="coerce").fillna(0.0)
    pms = pd.to_numeric(raw["%MS"], errors="coerce").fillna(0.0)
    usd = pd.to_numeric(raw["USD/kg MS"], errors="coerce").fillna(0.0)
    mask = (name != "") & (pct > 0)
    return pd.DataFrame({
        "Ingrediente": name[mask].values,
        "%":           pct[mask].values,
        "%MS":         pms[mask].values,
        "USD/kg MS":   usd[mask].values,
    })


# ── Métricas agregadas de la ración ──────────────────────────────────────────

def total_pct(stage: str) -> float:
    df = feed_df_active(stage)
    return float(df["%"].sum())


def precio_ponderado(stage: str) -> float:
    """USD/kg MS ponderado por % de cada ingrediente."""
    df = feed_df_active(stage)
    total = float(df["%"].sum())
    if total <= 0:
        return 0.0
    return float((df["%"] * df["USD/kg MS"]).sum() / total)


def pct_ms_promedio(stage: str) -> float:
    """%MS promedio ponderado por % de la ración."""
    df = feed_df_active(stage)
    total = float(df["%"].sum())
    if total <= 0:
        return 0.0
    return float((df["%"] * df["%MS"]).sum() / total)


# ── Consumo MV (derivado del %MS) ────────────────────────────────────────────

def consumo_mv_dia_cab(stage: str) -> float:
    """Consumo MV diario kg/cab. Suma kg_MV_i sobre ingredientes activos.

    kg_MS_i/día = (%_i / Σ%) × consumo_MS/día
    kg_MV_i/día = kg_MS_i/día / (%MS_i / 100)   [si %MS_i > 0]

    Si un ingrediente tiene %MS=0, no se puede convertir y se omite.
    """
    ms_dia = consumo_ms_dia_cab(stage)
    if ms_dia <= 0:
        return 0.0
    df = feed_df_active(stage)
    total = float(df["%"].sum())
    if total <= 0:
        return 0.0
    total_mv = 0.0
    for _, r in df.iterrows():
        pct_i = float(r["%"])
        pms_i = float(r["%MS"])
        if pms_i <= 0:
            continue
        ms_i = pct_i / total * ms_dia
        total_mv += ms_i / (pms_i / 100.0)
    return total_mv


def consumo_ingredientes(stage: str) -> pd.DataFrame:
    """Por ingrediente activo: kg MS/día/cab y kg MV/día/cab.

    Columnas: Ingrediente, %, %MS, USD/kg MS, kg_MS_dia, kg_MV_dia.
    Si la ración está vacía o consumo_MS_día = 0, devuelve un DF vacío.
    """
    df = feed_df_active(stage)
    if df.empty:
        return pd.DataFrame(columns=[*_FEED_COLS, "kg_MS_dia", "kg_MV_dia"])
    ms_dia = consumo_ms_dia_cab(stage)
    total = float(df["%"].sum())
    df = df.copy()
    if ms_dia <= 0 or total <= 0:
        df["kg_MS_dia"] = 0.0
        df["kg_MV_dia"] = 0.0
        return df
    df["kg_MS_dia"] = df["%"] / total * ms_dia
    df["kg_MV_dia"] = df.apply(
        lambda r: (r["kg_MS_dia"] / (r["%MS"] / 100.0))
                  if float(r["%MS"]) > 0 else 0.0,
        axis=1,
    )
    return df
