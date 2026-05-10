"""
Valores por defecto del modelo.

DEFAULTS  — dict plano, consumido por page_parametros.py (widgets UI).
*_DEFAULTS — dicts estructurados, consumidos por init_state.py.
Ambos comparten los mismos valores numéricos; no hay otra fuente.
"""

# ── Dict plano (consumido por page_parametros.py) ──────────────────────────────
# Perfil de prueba: Feedlot integrado a tambo Holando
# Cuenca del Salado / Sta Fe / Córdoba lechera, escala media-grande
# 800 terneros macho Holando ingresan por ciclo desde tambos vecinos/propios
# 3 puntos de salida: destete (95 kg) · recriado (220 kg) · terminado (430 kg)
DEFAULTS: dict = {
    # Comunes
    "n_terneros":    800,
    # peso_inicial = peso al destete = kg salida Cría = kg entrada Recría.
    # Su key en session_state es K.ANIMAL_PESO_ENTRADA ("pi"); el nombre
    # legacy "peso_inicial / pi" representa el peso de entrada a Recría.
    "peso_inicial":  95.0,          # kg al destete (= salida Cría)
    "precio_compra": 1.20,          # USD/kg — ternero Holando macho ex-tambo
    "tipo_cambio":   1100.0,        # ARS/USD ref. mayo 2026
    "tasa_interes":  8.0,           # % anual USD (capital trabajo)

    # A — Cría (45→95 kg, 60 días: recibo + iniciador)
    "d_precio_venta":   1.40,       # USD/kg destete (si vende)
    "d_dias":           60,
    "d_mortalidad":     4.0,        # % — Holstein recibo es alta
    "d_sanidad":        22.0,       # USD/cab — vacunas, antiparasitarios, neumonías
    "d_mo_mes":         0.0,        # USD/mes — fijo por etapa, no escala con cabezas
    "d_flete":          4.0,        # USD/cab (salida intra)
    "d_otros":          5.0,        # USD/cab

    # B — Recría (95→220 kg, 200 días: pastura + suplemento)
    "r_peso_salida":    220.0,      # kg
    "r_precio_venta":   2.30,       # USD/kg recriado en pie 2026
    "r_gdp":            0.625,      # kg/día = 125/200
    "r_mortalidad":     2.0,        # %
    "r_ca":             9.5,        # kg MS / kg PV (recría pastoreo)
    "r_ing1_pct":       30.0,       # % balanceado en ración
    "r_ing1_precio":    0.200,      # USD/kg MS
    "r_ing2_pct":       70.0,       # % silaje/pastura propia
    "r_ing2_precio":    0.080,      # USD/kg MS (costo de oportunidad)
    "r_sanidad":        25.0,       # USD/cab
    "r_mo_mes":         0.0,        # USD/mes — fijo por etapa
    "r_flete_entrada":  4.0,        # USD/cab
    "r_flete_salida":   6.0,        # USD/cab
    "r_otros":          8.0,        # USD/cab

    # C — Engorde (220→430 kg, 180 días: feedlot)
    "t_peso_final":     430.0,      # kg
    "t_precio_venta":   3.50,       # USD/kg gancho mercado interno 2026
    "t_gdp":            1.167,      # kg/día = 210/180
    "t_mortalidad":     2.0,        # %
    "t_ca":             7.5,        # kg MS / kg PV
    "t_ing1_pct":       80.0,       # % balanceado feedlot
    "t_ing1_precio":    0.300,      # USD/kg MS
    "t_ing2_pct":       20.0,       # % silaje maíz / heno
    "t_ing2_precio":    0.170,      # USD/kg MS
    "t_sanidad":        30.0,       # USD/cab
    "t_flete_entrada":  5.0,        # USD/cab
    "t_flete_salida":   12.0,       # USD/cab
    "t_amortizacion":   18.0,       # USD/cab (corrales + comederos + bebederos)
    "t_mo_mes":         0.0,        # USD/mes — fijo por etapa
    "t_otros":          10.0,       # USD/cab

    # Infraestructura — Fase 1 (sin widgets todavía)
    "infra_corrales_cant": 0,
    "infra_vida_util":     10,      # años

    # Cría (A) — adicionales
    "a_kg_entrada":    45,          # kg ternero al ingreso
    "a_gdp":           0.833,       # kg/día = 50/60
    "a_comision_pct":  2.0,

    # Recría (B) — adicionales
    "b_dias":          200,
    "b_kg_entrada":    95.0,        # kg al ingreso de Recría (= salida Cría
                                    # cuando hay encadenamiento, editable
                                    # cuando Recría es la 1ª etapa activa)
    "b_pc":            1.40,        # USD/kg compra recría (= venta cría)
    "b_comision_pct":  2.5,

    # Engorde (C) — adicionales
    "c_dias":          180,
    "c_kg_entrada":    220.0,
    "c_pc":            2.30,        # USD/kg compra recriado para feedlot
    "c_comision_pct":  2.5,

    # Comercialización — fletes
    "a_fe":     0.0,   # USD/cab — flete entrada Cría (origen interno)

    # Conversión cría (kg MS/kg PV) — informativo, ración líquida + iniciador
    "a_ca":            4.0,

    # Operación — combustible + servicios por etapa (USD/mes, absolutos)
    # Default 0 para no alterar cálculos hasta que el usuario los complete.
    # Costo del ciclo = USD/mes / 30 × días de tenencia.
    "a_combustible":   0.0,
    "b_combustible":   0.0,
    "c_combustible":   0.0,

    "a_servicios":     0.0,
    "b_servicios":     0.0,
    "c_servicios":     0.0,

    # Estructura — valor infraestructura GLOBAL + asignación per-etapa
    # Default 0 en infra_valor_total para no alterar cálculos hasta poblarlo
    "infra_valor_total": 0.0,       # USD inversión TOTAL en infraestructura

    # % de la infra total asignado a cada unidad productiva
    # (suma puede ser <100% si hay actividades fuera del modelo)
    "a_asig_pct":      0.0,
    "b_asig_pct":      0.0,
    "c_asig_pct":      0.0,

    "a_amort_anos":    10,          # años de vida útil
    "b_amort_anos":    10,
    "c_amort_anos":    10,

    "a_mantenimiento": 0.0,         # USD/año (absoluto, no %)
    "b_mantenimiento": 0.0,
    "c_mantenimiento": 0.0,
}

# ── Dicts estructurados (consumidos por init_state.py) ────────────────────────

ANIMAL_DEFAULTS: dict = {
    "n_terneros":  int(DEFAULTS["n_terneros"]),
    "peso_inicial": float(DEFAULTS["peso_inicial"]),
    "A": {
        "dias":       int(DEFAULTS["d_dias"]),
        "mortalidad": float(DEFAULTS["d_mortalidad"]),   # % (sin convertir)
        "sanidad":    float(DEFAULTS["d_sanidad"]),
        "mo_mes":     float(DEFAULTS["d_mo_mes"]),
    },
    "B": {
        "peso_salida": float(DEFAULTS["r_peso_salida"]),
        "gdp":         float(DEFAULTS["r_gdp"]),
        "mortalidad":  float(DEFAULTS["r_mortalidad"]),  # % (sin convertir)
        "ca":          float(DEFAULTS["r_ca"]),
        "sanidad":     float(DEFAULTS["r_sanidad"]),
        "mo_mes":      float(DEFAULTS["r_mo_mes"]),
    },
    "C": {
        "peso_final":  float(DEFAULTS["t_peso_final"]),
        "gdp":         float(DEFAULTS["t_gdp"]),
        "mortalidad":  float(DEFAULTS["t_mortalidad"]),  # % (sin convertir)
        "ca":          float(DEFAULTS["t_ca"]),
        "sanidad":     float(DEFAULTS["t_sanidad"]),
        "mo_mes":      float(DEFAULTS["t_mo_mes"]),
    },
}

FEED_DEFAULTS: dict = {
    # La alimentación es bioeconómica pura: la fuente de verdad es la
    # feed table editable (% × USD/kg MS). Mantenemos sólo los ingredientes
    # legacy de B/C para sidebar.py (Comparador). Cría sin defaults.
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
    # Fase 1 — modelo completo (en 0 hasta que UI exista)
    "corrales_cant":    0,
    "corrales_costo":   0.0,
    "mixer_costo":      0.0,
    "maquinaria_costo": 0.0,
    "vida_util":        10,
    "admin_anual":      0.0,
    "personal_anual":   0.0,
}

COMMERCIAL_DEFAULTS: dict = {
    "precio_compra": float(DEFAULTS["precio_compra"]),
    "tipo_cambio":   float(DEFAULTS["tipo_cambio"]),
    "tasa_interes":  float(DEFAULTS["tasa_interes"]),
    # Fase 1
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
