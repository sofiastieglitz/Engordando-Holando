"""
Valores por defecto del modelo.

DEFAULTS  — dict plano, consumido por page_parametros.py (widgets UI).
*_DEFAULTS — dicts estructurados, consumidos por init_state.py.
Ambos comparten los mismos valores numéricos; no hay otra fuente.
"""

# ── Dict plano (consumido por page_parametros.py) ──────────────────────────────
DEFAULTS: dict = {
    # Comunes
    "n_terneros":    100,
    "peso_inicial":  90.0,          # kg al destete
    "precio_compra": 1.00,          # USD/kg — ternero Holstein macho
    "tipo_cambio":   1000.0,        # ARS/USD
    "tasa_interes":  6.0,           # % anual (capital inmovilizado)

    # A — Venta al destete
    "d_precio_venta":   1.20,       # USD/kg
    "d_dias":           45,         # días de tenencia
    "d_mortalidad":     2.0,        # %
    "d_costo_alim_dia": 0.10,       # USD/cab/día (leche artificial + iniciador)
    "d_sanidad":        15.0,       # USD/cab
    "d_mo_dia":         0.0,        # USD/cab/día
    "d_flete":          5.0,        # USD/cab (salida)
    "d_otros":          5.0,        # USD/cab

    # B — Venta recriado
    "r_peso_salida":    220.0,      # kg al momento de venta
    "r_precio_venta":   2.50,       # USD/kg
    "r_gdp":            0.800,      # kg/día
    "r_mortalidad":     3.0,        # %
    "r_ca":             8.0,        # kg MS / kg PV
    "r_ing1_pct":       70.0,       # % Balanceado en ración
    "r_ing1_precio":    0.130,      # USD/kg MS
    "r_ing2_pct":       30.0,       # % Forraje en ración
    "r_ing2_precio":    0.107,      # USD/kg MS
    "r_sanidad":        20.0,       # USD/cab
    "r_mo_dia":         0.02,       # USD/cab/día
    "r_flete_entrada":  5.0,        # USD/cab
    "r_flete_salida":   7.0,        # USD/cab
    "r_otros":          8.0,        # USD/cab

    # C — Venta terminado
    "t_peso_final":     430.0,      # kg al momento de faena/venta
    "t_precio_venta":   3.80,       # USD/kg
    "t_gdp":            0.850,      # kg/día
    "t_mortalidad":     2.0,        # %
    "t_ca":             7.5,        # kg MS / kg PV
    "t_ing1_pct":       80.0,       # % Balanceado en ración
    "t_ing1_precio":    0.295,      # USD/kg MS
    "t_ing2_pct":       20.0,       # % Forraje en ración
    "t_ing2_precio":    0.175,      # USD/kg MS
    "t_sanidad":        25.0,       # USD/cab
    "t_flete_entrada":  5.0,        # USD/cab
    "t_flete_salida":   10.0,       # USD/cab
    "t_amortizacion":   12.0,       # USD/cab (instalaciones, total ciclo)
    "t_mo_dia":         0.05,       # USD/cab/día
    "t_otros":          10.0,       # USD/cab

    # Infraestructura — Fase 1 (sin widgets todavía)
    "infra_corrales_cant": 0,
    "infra_vida_util":     10,      # años

    # Cría (A) — adicionales
    "a_kg_entrada":    40,
    "a_gdp":           0.400,
    "a_comision_pct":  2.0,

    # Recría (B) — adicionales
    "b_dias":          163,
    "b_pc":            1.00,
    "b_alim_dia":      1.00,
    "b_comision_pct":  2.0,

    # Engorde interno (C) — adicionales
    "c_dias":          400,
    "c_kg_entrada":    220.0,
    "c_pc":            1.80,
    "c_alim_dia":      2.00,
    "c_comision_pct":  2.0,

    # Engorde exportación (E) — todos nuevos
    "e_dias":          150,
    "e_kg_entrada":    220.0,
    "e_kg_salida":     480.0,
    "e_gdp":           1.000,
    "e_mortalidad":    1.5,
    "e_sanidad":       30.0,
    "e_mo_dia":        0.05,
    "e_alim_dia":      2.50,
    "e_pc":            2.50,
    "e_pv":            4.50,
    "e_comision_pct":  2.0,

    # Alimentación — ración diaria
    "a_rac_diaria":    3.0,
    "b_rac_diaria":    6.0,
    "c_rac_diaria":    8.0,
    "e_rac_diaria":    9.0,

    # Comercialización — fletes nuevos
    "a_fe":     0.0,   # USD/cab — flete entrada Cría
    "e_fe":     5.0,   # USD/cab — flete entrada Eng. exportación
    "e_fs":    10.0,   # USD/cab — flete salida Eng. exportación

    # Comercialización — operativos editables (tab independiente de Animales)
    "a_com_mo":   0.0,
    "a_com_san": 15.0,
    "b_com_mo":   0.02,
    "b_com_san": 20.0,
    "c_com_mo":   0.05,
    "c_com_san": 25.0,
    "e_com_mo":   0.05,
    "e_com_san": 30.0,
}

# ── Dicts estructurados (consumidos por init_state.py) ────────────────────────

ANIMAL_DEFAULTS: dict = {
    "n_terneros":  int(DEFAULTS["n_terneros"]),
    "peso_inicial": float(DEFAULTS["peso_inicial"]),
    "A": {
        "dias":       int(DEFAULTS["d_dias"]),
        "mortalidad": float(DEFAULTS["d_mortalidad"]),   # % (sin convertir)
        "sanidad":    float(DEFAULTS["d_sanidad"]),
        "mo_dia":     float(DEFAULTS["d_mo_dia"]),
    },
    "B": {
        "peso_salida": float(DEFAULTS["r_peso_salida"]),
        "gdp":         float(DEFAULTS["r_gdp"]),
        "mortalidad":  float(DEFAULTS["r_mortalidad"]),  # % (sin convertir)
        "ca":          float(DEFAULTS["r_ca"]),
        "sanidad":     float(DEFAULTS["r_sanidad"]),
        "mo_dia":      float(DEFAULTS["r_mo_dia"]),
    },
    "C": {
        "peso_final":  float(DEFAULTS["t_peso_final"]),
        "gdp":         float(DEFAULTS["t_gdp"]),
        "mortalidad":  float(DEFAULTS["t_mortalidad"]),  # % (sin convertir)
        "ca":          float(DEFAULTS["t_ca"]),
        "sanidad":     float(DEFAULTS["t_sanidad"]),
        "mo_dia":      float(DEFAULTS["t_mo_dia"]),
    },
}

FEED_DEFAULTS: dict = {
    "A": {
        "costo_alim_dia": float(DEFAULTS["d_costo_alim_dia"]),
    },
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
