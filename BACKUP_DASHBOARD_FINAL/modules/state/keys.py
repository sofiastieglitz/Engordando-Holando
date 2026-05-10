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
A_ALIM_COSTO_DIA = "d_al"
A_SANIDAD        = "d_sa"
A_MO_DIA         = "d_moe"
A_FLETE_SALIDA   = "d_fl"
A_OTROS          = "d_ot"

# ── B — Venta recriado ─────────────────────────────────────────────────────────
B_PESO_SALIDA   = "r_ps"
B_PRECIO_VENTA  = "r_pv"
B_GDP           = "r_gd"
B_MORTALIDAD    = "r_mo"
B_CA            = "r_ca"
B_ING1_PCT      = "r_p1"
B_ING1_PRECIO   = "r_x1"
B_ING2_PCT      = "r_p2"
B_ING2_PRECIO   = "r_x2"
B_SANIDAD       = "r_sa"
B_MO_DIA        = "r_moe"
B_FLETE_ENTRADA = "r_fe"
B_FLETE_SALIDA  = "r_fs"
B_OTROS         = "r_ot"

# ── C — Venta terminado ────────────────────────────────────────────────────────
C_PESO_FINAL    = "t_pf"
C_PRECIO_VENTA  = "t_pv"
C_GDP           = "t_gd"
C_MORTALIDAD    = "t_mo"
C_CA            = "t_ca"
C_ING1_PCT      = "t_p1"
C_ING1_PRECIO   = "t_x1"
C_ING2_PCT      = "t_p2"
C_ING2_PRECIO   = "t_x2"
C_SANIDAD       = "t_sa"
C_MO_DIA        = "t_moe"
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
B_PRECIO_COMPRA = "b_pc"
B_ALIM_DIA      = "b_alim_dia"
B_COMISION_PCT  = "b_comision_pct"

# ── Engorde interno (C) — campos adicionales ──────────────────────────────────
C_DIAS          = "c_dias"
C_KG_ENTRADA    = "c_kg_entrada"
C_PRECIO_COMPRA = "c_pc"
C_ALIM_DIA      = "c_alim_dia"
C_COMISION_PCT  = "c_comision_pct"

# ── Engorde exportación (E) — todos nuevos ────────────────────────────────────
E_DIAS          = "e_dias"
E_KG_ENTRADA    = "e_kg_entrada"
E_KG_SALIDA     = "e_kg_salida"
E_GDP           = "e_gdp"
E_MORTALIDAD    = "e_mo"
E_SANIDAD       = "e_sa"
E_MO_DIA        = "e_moe"
E_ALIM_DIA      = "e_alim_dia"
E_PRECIO_COMPRA = "e_pc"
E_PRECIO_VENTA  = "e_pv"
E_COMISION_PCT  = "e_comision_pct"

# ── Alimentación — ración diaria ──────────────────────────────────────────────
A_RAC_DIARIA    = "a_rac_diaria"
B_RAC_DIARIA    = "b_rac_diaria"
C_RAC_DIARIA    = "c_rac_diaria"
E_RAC_DIARIA    = "e_rac_diaria"

# ── Comercialización — fletes nuevos ──────────────────────────────────────────
A_FLETE_ENTRADA     = "a_fe"
E_FLETE_ENTRADA     = "e_fe"
E_FLETE_SALIDA      = "e_fs"

# ── Comercialización — operativos editables (independientes del tab Animales) ─
A_COM_MO_DIA    = "a_com_mo"
A_COM_SANIDAD   = "a_com_san"
B_COM_MO_DIA    = "b_com_mo"
B_COM_SANIDAD   = "b_com_san"
C_COM_MO_DIA    = "c_com_mo"
C_COM_SANIDAD   = "c_com_san"
E_COM_MO_DIA    = "e_com_mo"
E_COM_SANIDAD   = "e_com_san"
