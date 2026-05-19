"""
Constantes para todas las claves de session_state.

Fase actual: los valores apuntan a los strings abreviados existentes
para mantener compatibilidad con los widgets de page_parametros.py.
En Fase 4 (limpieza) los strings se renombran a nombres descriptivos
y se hace la migración con alias en init_state.py.
"""

# ── Comunes ────────────────────────────────────────────────────────────────────
ANIMAL_CANTIDAD         = "n_t"
ANIMAL_PESO_ENTRADA     = "pi"
COMERCIAL_PRECIO_COMPRA = "pc"
FINANCIERO_TIPO_CAMBIO  = "tc"
FINANCIERO_TASA_INTERES = "ti"

# ── A — Venta al destete ───────────────────────────────────────────────────────
A_PRECIO_VENTA   = "d_pv"
A_DIAS           = "d_di"
A_MORTALIDAD     = "d_mo"
A_SANIDAD        = "d_sa"
A_MO_MES         = "d_mo_mes"
A_FLETE_SALIDA   = "d_fl"
A_OTROS          = "d_ot"

# ── B — Venta recriado ─────────────────────────────────────────────────────────
B_PESO_SALIDA   = "r_ps"
B_PRECIO_VENTA  = "r_pv"
B_GDP           = "r_gd"
B_MORTALIDAD    = "r_mo"
B_ING1_PCT      = "r_p1"
B_ING1_PRECIO   = "r_x1"
B_ING2_PCT      = "r_p2"
B_ING2_PRECIO   = "r_x2"
B_SANIDAD       = "r_sa"
B_MO_MES        = "r_mo_mes"
B_FLETE_ENTRADA = "r_fe"
B_FLETE_SALIDA  = "r_fs"
B_OTROS         = "r_ot"

# ── C — Venta terminado ────────────────────────────────────────────────────────
C_PESO_FINAL    = "t_pf"
C_PRECIO_VENTA  = "t_pv"
C_GDP           = "t_gd"
C_MORTALIDAD    = "t_mo"
C_ING1_PCT      = "t_p1"
C_ING1_PRECIO   = "t_x1"
C_ING2_PCT      = "t_p2"
C_ING2_PRECIO   = "t_x2"
C_SANIDAD       = "t_sa"
C_MO_MES        = "t_mo_mes"
C_FLETE_ENTRADA = "t_fe"
C_FLETE_SALIDA  = "t_fs"
C_AMORTIZACION  = "t_am"
C_OTROS         = "t_ot"

# ── Infraestructura — nuevas (Fase 1) ─────────────────────────────────────────
# Estos keys no tienen widgets todavía; init_state los inicializa en 0
# para que estén disponibles cuando se construya la UI de infra.
INFRA_CORRALES_CANT     = "infra_corrales_cant"
INFRA_CORRALES_COSTO    = "infra_corrales_costo"
INFRA_MIXER_COSTO       = "infra_mixer_costo"
INFRA_MAQUINARIA_COSTO  = "infra_maquinaria_costo"
INFRA_VIDA_UTIL         = "infra_vida_util"
INFRA_ADMIN_ANUAL       = "infra_admin_anual"
INFRA_PERSONAL_ANUAL    = "infra_personal_anual"

# ── Comercialización extendida — nuevas (Fase 1) ───────────────────────────────
COMERCIAL_COMISION_PCT  = "comercial_comision_pct"
COMERCIAL_SUPERFICIE_HA = "comercial_superficie_ha"

# ── Cría (A) — campos adicionales ─────────────────────────────────────────────
A_KG_ENTRADA    = "a_kg_entrada"
A_GDP           = "a_gdp"
A_COMISION_PCT  = "a_comision_pct"

# ── Recría (B) — campos adicionales ───────────────────────────────────────────
B_DIAS          = "b_dias"
B_KG_ENTRADA    = "b_kg_entrada"   # editable cuando Recría es la 1ª etapa activa
B_PRECIO_COMPRA = "b_pc"
B_COMISION_PCT  = "b_comision_pct"

# ── Engorde (C) — campos adicionales ──────────────────────────────────────────
C_DIAS          = "c_dias"
C_KG_ENTRADA    = "c_kg_entrada"
C_PRECIO_COMPRA = "c_pc"
C_COMISION_PCT  = "c_comision_pct"

# ── Comercialización — fletes nuevos ──────────────────────────────────────────
A_FLETE_ENTRADA     = "a_fe"

# NOTA: la conversión alimenticia (A_CA / B_CA / C_CA) fue eliminada como
# input editable. Ahora se DERIVA desde la tabla de ración en
# `modules.state.derived.ca_for(stage) = consumo_MS_dia / GDP`. La única
# fuente nutricional es la tabla `feed_table_<stage>_de`.

# ── Operación adicional (combustible + servicios) por etapa, USD/mes ─────────
A_COMBUSTIBLE   = "a_combustible"
B_COMBUSTIBLE   = "b_combustible"
C_COMBUSTIBLE   = "c_combustible"

A_SERVICIOS     = "a_servicios"
B_SERVICIOS     = "b_servicios"
C_SERVICIOS     = "c_servicios"

# ── Estructura ────────────────────────────────────────────────────────────────
# Valor infra es GLOBAL (un único activo) y se asigna parcialmente a cada
# etapa vía un % editable. La suma de los 3 % no necesariamente da 100%
# (puede haber actividades fuera del modelo).
INFRA_VALOR_TOTAL = "infra_valor_total"   # USD totales

A_ASIG_PCT      = "a_asig_pct"            # % infra asignado a Cría
B_ASIG_PCT      = "b_asig_pct"            # % infra asignado a Recría
C_ASIG_PCT      = "c_asig_pct"            # % infra asignado a Engorde

A_AMORT_ANOS    = "a_amort_anos"
B_AMORT_ANOS    = "b_amort_anos"
C_AMORT_ANOS    = "c_amort_anos"

A_MANTENIMIENTO = "a_mantenimiento"       # USD/año
B_MANTENIMIENTO = "b_mantenimiento"
C_MANTENIMIENTO = "c_mantenimiento"

# ── Etapas activas (modular vs integrado) ─────────────────────────────────────
# Toggles globales: cuáles etapas están activas en el modelo. Las selecciones
# permitidas son slices contiguos: {Cría}, {Recría}, {Engorde},
# {Cría+Recría}, {Recría+Engorde}, {Cría+Recría+Engorde}.
STAGE_CRIA_ON   = "stage_cria_on"
STAGE_RECRIA_ON = "stage_recria_on"
STAGE_ENG_ON    = "stage_eng_on"
