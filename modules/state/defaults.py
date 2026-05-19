"""
Valores por defecto del modelo.

Política: TODOS los valores numéricos inician en 0 (ó 0.0). El usuario es la
única fuente de verdad. Los valores se establecen exclusivamente vía la slide
"Parámetros" (manual) o el botón "↺ Restablecer defaults" (vuelve a 0).

DEFAULTS  — dict plano, consumido por page_parametros.py (widgets UI) y como
            fallback de lectura en todas las páginas (page_costos, margenes,
            sensibilidad, etc.) vía `_g(key, DEFAULTS[xxx])`.
*_DEFAULTS — dicts estructurados, consumidos por init_state.py para sembrar
             session_state. Comparten los mismos valores numéricos (0).
"""

# ── Dict plano (consumido por page_parametros.py + fallback de lectura) ───────
DEFAULTS: dict = {
    # Comunes
    "n_terneros":    0,
    "peso_inicial":  0.0,
    "precio_compra": 0.0,
    "tipo_cambio":   0.0,
    "tasa_interes":  0.0,

    # A — Cría
    "d_precio_venta":   0.0,
    "d_dias":           0,
    "d_mortalidad":     0.0,
    "d_sanidad":        0.0,
    "d_mo_mes":         0.0,
    "d_flete":          0.0,
    "d_otros":          0.0,

    # B — Recría
    "r_peso_salida":    0.0,
    "r_precio_venta":   0.0,
    "r_gdp":            0.0,
    "r_mortalidad":     0.0,
    "r_ing1_pct":       0.0,
    "r_ing1_precio":    0.0,
    "r_ing2_pct":       0.0,
    "r_ing2_precio":    0.0,
    "r_sanidad":        0.0,
    "r_mo_mes":         0.0,
    "r_flete_entrada":  0.0,
    "r_flete_salida":   0.0,
    "r_otros":          0.0,

    # C — Engorde
    "t_peso_final":     0.0,
    "t_precio_venta":   0.0,
    "t_gdp":            0.0,
    "t_mortalidad":     0.0,
    "t_ing1_pct":       0.0,
    "t_ing1_precio":    0.0,
    "t_ing2_pct":       0.0,
    "t_ing2_precio":    0.0,
    "t_sanidad":        0.0,
    "t_flete_entrada":  0.0,
    "t_flete_salida":   0.0,
    "t_amortizacion":   0.0,
    "t_mo_mes":         0.0,
    "t_otros":          0.0,

    # Infraestructura
    "infra_corrales_cant": 0,
    "infra_vida_util":     0,

    # Cría (A) — adicionales
    "a_kg_entrada":    0.0,
    "a_gdp":           0.0,
    "a_comision_pct":  0.0,
    # NOTE: a_ca / r_ca / t_ca eliminados — la conversión es derivada
    # desde la tabla de ración (ver modules.state.derived.ca_for).

    # Recría (B) — adicionales
    "b_dias":          0,
    "b_kg_entrada":    0.0,
    "b_pc":            0.0,
    "b_comision_pct":  0.0,

    # Engorde (C) — adicionales
    "c_dias":          0,
    "c_kg_entrada":    0.0,
    "c_pc":            0.0,
    "c_comision_pct":  0.0,

    # Comercialización — fletes
    "a_fe":     0.0,

    # Operación — combustible + servicios por etapa (USD/mes)
    "a_combustible":   0.0,
    "b_combustible":   0.0,
    "c_combustible":   0.0,

    "a_servicios":     0.0,
    "b_servicios":     0.0,
    "c_servicios":     0.0,

    # Estructura — valor infraestructura GLOBAL + asignación per-etapa
    "infra_valor_total": 0.0,

    "a_asig_pct":      0.0,
    "b_asig_pct":      0.0,
    "c_asig_pct":      0.0,

    "a_amort_anos":    0,
    "b_amort_anos":    0,
    "c_amort_anos":    0,

    "a_mantenimiento": 0.0,
    "b_mantenimiento": 0.0,
    "c_mantenimiento": 0.0,
}

# ── Dicts estructurados (consumidos por init_state.py) ────────────────────────

ANIMAL_DEFAULTS: dict = {
    "n_terneros":  int(DEFAULTS["n_terneros"]),
    "peso_inicial": float(DEFAULTS["peso_inicial"]),
    "A": {
        "dias":       int(DEFAULTS["d_dias"]),
        "mortalidad": float(DEFAULTS["d_mortalidad"]),
        "sanidad":    float(DEFAULTS["d_sanidad"]),
        "mo_mes":     float(DEFAULTS["d_mo_mes"]),
    },
    "B": {
        "peso_salida": float(DEFAULTS["r_peso_salida"]),
        "gdp":         float(DEFAULTS["r_gdp"]),
        "mortalidad":  float(DEFAULTS["r_mortalidad"]),
        "sanidad":     float(DEFAULTS["r_sanidad"]),
        "mo_mes":      float(DEFAULTS["r_mo_mes"]),
    },
    "C": {
        "peso_final":  float(DEFAULTS["t_peso_final"]),
        "gdp":         float(DEFAULTS["t_gdp"]),
        "mortalidad":  float(DEFAULTS["t_mortalidad"]),
        "sanidad":     float(DEFAULTS["t_sanidad"]),
        "mo_mes":      float(DEFAULTS["t_mo_mes"]),
    },
}

FEED_DEFAULTS: dict = {
    "B": {
        "ing1_pct":    float(DEFAULTS["r_ing1_pct"]),
        "ing1_precio": float(DEFAULTS["r_ing1_precio"]),
        "ing2_pct":    float(DEFAULTS["r_ing2_pct"]),
        "ing2_precio": float(DEFAULTS["r_ing2_precio"]),
    },
    "C": {
        "ing1_pct":    float(DEFAULTS["t_ing1_pct"]),
        "ing1_precio": float(DEFAULTS["t_ing1_precio"]),
        "ing2_pct":    float(DEFAULTS["t_ing2_pct"]),
        "ing2_precio": float(DEFAULTS["t_ing2_precio"]),
    },
}

INFRA_DEFAULTS: dict = {
    "C": {
        "amortizacion": float(DEFAULTS["t_amortizacion"]),
    },
    "corrales_cant":    int(DEFAULTS["infra_corrales_cant"]),
    "corrales_costo":   0.0,
    "mixer_costo":      0.0,
    "maquinaria_costo": 0.0,
    "vida_util":        int(DEFAULTS["infra_vida_util"]),
    "admin_anual":      0.0,
    "personal_anual":   0.0,
}

COMMERCIAL_DEFAULTS: dict = {
    "precio_compra": float(DEFAULTS["precio_compra"]),
    "tipo_cambio":   float(DEFAULTS["tipo_cambio"]),
    "tasa_interes":  float(DEFAULTS["tasa_interes"]),
    "comision_pct":  0.0,
    "superficie_ha": 0.0,
    "A": {
        "precio_venta": float(DEFAULTS["d_precio_venta"]),
        "flete_salida": float(DEFAULTS["d_flete"]),
        "otros":        float(DEFAULTS["d_otros"]),
    },
    "B": {
        "precio_venta":  float(DEFAULTS["r_precio_venta"]),
        "flete_entrada": float(DEFAULTS["r_flete_entrada"]),
        "flete_salida":  float(DEFAULTS["r_flete_salida"]),
        "otros":         float(DEFAULTS["r_otros"]),
    },
    "C": {
        "precio_venta":  float(DEFAULTS["t_precio_venta"]),
        "flete_entrada": float(DEFAULTS["t_flete_entrada"]),
        "flete_salida":  float(DEFAULTS["t_flete_salida"]),
        "otros":         float(DEFAULTS["t_otros"]),
    },
}
