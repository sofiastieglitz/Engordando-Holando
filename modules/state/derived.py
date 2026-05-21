"""
Derivados — cálculos automáticos sobre el estado base.

Modelo nutricional (nuevo, post-refactor):
  La tabla de alimentación es la ÚNICA fuente de verdad. El usuario carga
  por ingrediente:
      Kg tal cual (kg/cab/día) · %MS · USD/kg MS
  El sistema deriva:
      Kg MS_i              = Kg TC_i × %MS_i / 100              (kg/cab/día)
      consumo_MS_dia_cab   = Σ Kg MS_i                          (kg MS/cab/día)
      consumo_MV_dia_cab   = Σ Kg TC_i                          (kg MV/cab/día)
      consumo_MS_cab       = consumo_MS_dia_cab × días          (kg MS/cab ciclo)
      consumo_MV_cab       = consumo_MV_dia_cab × días          (kg MV/cab ciclo)
      costo_alim_dia_cab   = Σ (Kg MS_i × USD/kg MS_i)          (USD/cab/día)
      costo_alim_cab       = costo_alim_dia_cab × días          (USD/cab ciclo)
      ca                   = consumo_MS_dia_cab / GDP           (kg MS/kg carne)
      precio_ponderado     = costo_alim_dia_cab / consumo_MS_dia_cab
      pct_ms_promedio      = consumo_MS_dia_cab / consumo_MV_dia_cab × 100

La conversión alimenticia (CA) y el precio ponderado pasan a ser
DERIVADOS exclusivamente — no hay ningún input editable de CA en el
dashboard.

Validaciones:
  - max(x, 0) defensivo en pesos / GDP / Kg TC / %MS / USD.
  - Divisores → cero ⇒ resultado 0 (no NaN).
  - Tabla vacía ⇒ todos los derivados son 0.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import modules.state.keys as K
import modules.state.stages as S
from modules.state.persist import get_editor_shadow, read


# ── Mapeo etapa → claves de session_state ────────────────────────────────────

_GDP_KEY = {"cria": K.A_GDP, "recria": K.B_GDP, "eng_int": K.C_GDP}

_FEED_EDITOR_KEY = {
    "cria":    "feed_table_cria_de",
    "recria":  "feed_table_recria_de",
    "eng_int": "feed_table_eng_int_de",
}


def _g(key: str, default: float = 0.0) -> float:
    """Lectura robusta: shadow > widget-key > default."""
    return float(read(key, default))


# ── Valores cargados (passthrough con conversión) ────────────────────────────

def gdp_for(stage: str) -> float:
    return _g(_GDP_KEY[stage], 0.0)


def kg_in_for(stage: str) -> float:
    return float(S.kg_in_for(stage))


def kg_out_for(stage: str) -> float:
    return float(S.kg_out_for(stage))


def kg_producidos_cab(stage: str) -> float:
    return max(kg_out_for(stage) - kg_in_for(stage), 0.0)


# ── Tiempo ────────────────────────────────────────────────────────────────────

def dias_for(stage: str) -> int:
    """días = (peso_salida − peso_entrada) / GDP."""
    kg_prod = kg_producidos_cab(stage)
    gdp = gdp_for(stage)
    if gdp <= 0 or kg_prod <= 0:
        return 0
    return int(round(kg_prod / gdp))


def dias_total() -> int:
    return sum(dias_for(s) for s in S.active_stages())


# ── Tabla de alimentación: schema canónico ───────────────────────────────────

_FEED_COLS = ["Ingrediente", "Kg TC", "%MS", "Kg MS", "USD/kg MS"]
_FEED_ROWS = 10


def _empty_feed_df(rows: int = _FEED_ROWS) -> pd.DataFrame:
    return pd.DataFrame({
        "Ingrediente": [""]  * rows,
        "Kg TC":       [0.0] * rows,
        "%MS":         [0.0] * rows,
        "Kg MS":       [0.0] * rows,
        "USD/kg MS":   [0.0] * rows,
    })


def migrate_feed_df(df: pd.DataFrame, rows: int = _FEED_ROWS) -> pd.DataFrame:
    """Garantiza el schema canónico [Ingrediente, Kg TC, %MS, Kg MS, USD/kg MS].

    Migraciones soportadas:
      - Tablas viejas con columna "%" (modelo % en ración): se descarta "%"
        y se inicializa Kg TC = 0 (el usuario re-ingresa el consumo TC).
        Ingrediente / %MS / USD/kg MS se preservan.
      - Tablas sin "%MS" o sin "Kg MS": columnas creadas en 0.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _empty_feed_df(rows)
    out = df.copy()
    if "Ingrediente" not in out.columns:
        out["Ingrediente"] = ""
    if "Kg TC" not in out.columns:
        out["Kg TC"] = 0.0
    if "%MS" not in out.columns:
        out["%MS"] = 0.0
    if "Kg MS" not in out.columns:
        out["Kg MS"] = 0.0
    if "USD/kg MS" not in out.columns:
        out["USD/kg MS"] = 0.0
    # Recalcular Kg MS para asegurar consistencia con Kg TC × %MS/100
    kg_tc = pd.to_numeric(out["Kg TC"], errors="coerce").fillna(0.0)
    pms   = pd.to_numeric(out["%MS"],   errors="coerce").fillna(0.0)
    out["Kg MS"] = (kg_tc * pms / 100.0).astype(float)
    out = out[_FEED_COLS]
    if len(out) < rows:
        pad = _empty_feed_df(rows - len(out))
        out = pd.concat([out, pad], ignore_index=True)
    elif len(out) > rows:
        out = out.iloc[:rows].reset_index(drop=True)
    return out


def _read_feed_raw(stage: str) -> pd.DataFrame:
    """Estado actual del editor de ración (10 filas, schema canónico).

    Estrategia: SHADOW (baseline completo del último save) + DELTA del
    widget aplicada por encima. La delta-on-top permite capturar incluso
    edits que el usuario tipeó pero todavía no se commitearon al shadow.

    Race-condition que esto cubre:
      El usuario tipea en una celda de la tabla en Parámetros y, sin
      blurear, clickea otra slide en el nav. Streamlit:
        1) Captura el nuevo valor en `ss[editor_key]` (delta).
        2) Cambia la página activa al destino del nav.
        3) Dispara UN rerun para la nueva página.
      En ese rerun, `_feed_table_block` NO corre, por lo que el shadow
      no se actualiza. Si leyéramos sólo el shadow, los consumidores
      (sidebar / page_costos / page_margenes) recibirían el estado
      pre-tipeo y mostrarían cálculos desfasados. Aplicar la delta
      sobre el shadow elimina ese desfase.

    Reglas de seguridad de datos (NO MODIFICAR):
      - La base SIEMPRE es el shadow (no un DataFrame vacío). Si no
        existe shadow, recién ahí caemos a un DF vacío de 10 filas.
      - La delta sólo puede *modificar* celdas existentes; con
        `num_rows="fixed"` no hay `added_rows` ni `deleted_rows` que
        deban procesarse. Si en el futuro se permite agregar filas,
        agregar esa lógica acá Y mantener el shadow como la fuente
        de verdad de filas previas.
    """
    editor_key = _FEED_EDITOR_KEY[stage]

    # 1) Base: shadow (DF completo del último save) o DF vacío de 10 filas.
    shadow = get_editor_shadow(editor_key)
    base = migrate_feed_df(shadow) if shadow is not None else _empty_feed_df()

    # 2) Aplicar delta-dict del widget vivo (si la hay) sobre el shadow.
    delta = st.session_state.get(editor_key)
    if isinstance(delta, dict):
        out = base.copy()
        for idx_str, changes in delta.get("edited_rows", {}).items():
            try:
                idx = int(idx_str)
            except (ValueError, TypeError):
                continue
            if 0 <= idx < len(out):
                for col, v in changes.items():
                    if col in out.columns:
                        out.at[idx, col] = v
        return migrate_feed_df(out)

    return base


def feed_df_active(stage: str) -> pd.DataFrame:
    """Filas con ingrediente no-vacío y Kg TC > 0. Recalcula Kg MS."""
    raw = _read_feed_raw(stage)
    name  = raw["Ingrediente"].astype(str).str.strip()
    kg_tc = pd.to_numeric(raw["Kg TC"],     errors="coerce").fillna(0.0).clip(lower=0.0)
    pms   = pd.to_numeric(raw["%MS"],       errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
    usd   = pd.to_numeric(raw["USD/kg MS"], errors="coerce").fillna(0.0).clip(lower=0.0)
    mask  = (name != "") & (kg_tc > 0)
    kg_ms = kg_tc * pms / 100.0
    return pd.DataFrame({
        "Ingrediente": name[mask].values,
        "Kg TC":       kg_tc[mask].values,
        "%MS":         pms[mask].values,
        "Kg MS":       kg_ms[mask].values,
        "USD/kg MS":   usd[mask].values,
    })


# ── Consumos diarios (desde la tabla directamente) ───────────────────────────

def consumo_mv_dia_cab(stage: str) -> float:
    """Σ Kg tal cual de la ración, kg MV/cab/día."""
    df = feed_df_active(stage)
    return float(df["Kg TC"].sum()) if not df.empty else 0.0


def consumo_ms_dia_cab(stage: str) -> float:
    """Σ Kg MS de la ración, kg MS/cab/día."""
    df = feed_df_active(stage)
    return float(df["Kg MS"].sum()) if not df.empty else 0.0


def consumo_ms_cab(stage: str) -> float:
    """Consumo MS del ciclo, kg MS/cab = dia × días."""
    return consumo_ms_dia_cab(stage) * dias_for(stage)


def consumo_mv_cab(stage: str) -> float:
    """Consumo MV del ciclo, kg MV/cab = dia × días."""
    return consumo_mv_dia_cab(stage) * dias_for(stage)


# ── Costo alimentación (derivado de la tabla) ────────────────────────────────

def costo_alim_dia_cab(stage: str) -> float:
    """USD/cab/día = Σ (Kg MS_i × USD/kg MS_i)."""
    df = feed_df_active(stage)
    if df.empty:
        return 0.0
    return float((df["Kg MS"] * df["USD/kg MS"]).sum())


def costo_alim_cab(stage: str) -> float:
    """USD/cab del ciclo = costo_dia × días."""
    return costo_alim_dia_cab(stage) * dias_for(stage)


# ── Conversión y precio ponderado (ambos DERIVADOS) ──────────────────────────

def ca_for(stage: str) -> float:
    """Conversión alimenticia derivada: kg MS / kg carne = MS_dia / GDP.

    Antes era un input editable (K.*_CA); ahora la única fuente nutricional
    es la tabla, así que CA se calcula con consistencia perfecta.
    """
    gdp = gdp_for(stage)
    if gdp <= 0:
        return 0.0
    return consumo_ms_dia_cab(stage) / gdp


def eficiencia_for(stage: str) -> float:
    """kg carne / kg MS = GDP / MS_dia. Inversa de la CA."""
    ms_dia = consumo_ms_dia_cab(stage)
    if ms_dia <= 0:
        return 0.0
    return gdp_for(stage) / ms_dia


def precio_ponderado(stage: str) -> float:
    """USD/kg MS ponderado por consumo real = costo_dia / MS_dia."""
    ms_dia = consumo_ms_dia_cab(stage)
    if ms_dia <= 0:
        return 0.0
    return costo_alim_dia_cab(stage) / ms_dia


def pct_ms_promedio(stage: str) -> float:
    """%MS de la ración total = MS_dia / MV_dia × 100."""
    mv_dia = consumo_mv_dia_cab(stage)
    if mv_dia <= 0:
        return 0.0
    return consumo_ms_dia_cab(stage) / mv_dia * 100.0


# ── Consumo por ingrediente (vista para reportes y modelo productivo) ────────

def consumo_ingredientes(stage: str) -> pd.DataFrame:
    """Por ingrediente activo: Kg TC, %MS, Kg MS, USD/kg MS,
    kg_MS_dia (=Kg MS), kg_MV_dia (=Kg TC), usd_dia (=Kg MS × USD).

    Si la ración está vacía, devuelve un DF vacío con las columnas esperadas.
    """
    df = feed_df_active(stage)
    cols_out = [*_FEED_COLS, "kg_MS_dia", "kg_MV_dia", "usd_dia"]
    if df.empty:
        return pd.DataFrame(columns=cols_out)
    out = df.copy()
    out["kg_MS_dia"] = out["Kg MS"]
    out["kg_MV_dia"] = out["Kg TC"]
    out["usd_dia"]   = out["Kg MS"] * out["USD/kg MS"]
    return out
