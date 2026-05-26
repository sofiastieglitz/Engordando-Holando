# Documentación técnica — Engordando Holando

> Dashboard de simulación económica para la integración vertical de terneros macho Holando, desde el destete hasta la faena.
>
> URL pública: <https://engordando-holando.streamlit.app/>
> Autora: Sofía Stieglitz
> Última actualización del documento: 2026-05-19

---

## Índice

1. [Objetivo del dashboard](#1-objetivo-del-dashboard)
2. [Arquitectura del modelo](#2-arquitectura-del-modelo)
3. [Vocabulario y unidades](#3-vocabulario-y-unidades)
4. [Datos que ingresa el usuario](#4-datos-que-ingresa-el-usuario)
5. [Sistema de etapas activas](#5-sistema-de-etapas-activas-modular-vs-integrado)
6. [Modelo nutricional (tabla de ración)](#6-modelo-nutricional-tabla-de-ración)
7. [Recorrido por las páginas del dashboard](#7-recorrido-por-las-páginas-del-dashboard)
8. [Fórmulas detalladas por concepto](#8-fórmulas-detalladas-por-concepto)
9. [Ejemplos numéricos](#9-ejemplos-numéricos)
10. [Indicadores productivos y financieros](#10-indicadores-productivos-y-financieros)
11. [Cómo impacta cada parámetro sobre el resultado](#11-cómo-impacta-cada-parámetro-sobre-el-resultado-final)
12. [Persistencia, cache y configuración](#12-persistencia-cache-y-configuración)
13. [Validaciones y controles internos](#13-validaciones-y-controles-internos)
14. [Supuestos y limitaciones del modelo](#14-supuestos-y-limitaciones-del-modelo)
15. [Apéndices](#15-apéndices)

---

## 1. Objetivo del dashboard

El dashboard responde **una sola pregunta** desde múltiples ángulos:

> Dado un ternero macho proveniente de un tambo Holando, ¿cuál es la mejor estrategia económica: venderlo al destete, recriarlo, o terminarlo a faena en feedlot — y bajo qué condiciones esa decisión sigue siendo robusta?

Para responderla, modela tres **escenarios productivos** comparables y permite al usuario sensibilizar cada parámetro para entender la **robustez de la decisión** frente a cambios de precios, conversiones, mortandad y otros factores.

**Público objetivo:** productores ganaderos, técnicos, asesores y empresas de la cadena lácteo-cárnica que quieran cuantificar el negocio de los machos Holando.

**No es:**

- Un sistema contable de gestión real-time.
- Un planner de feedlot operativo (no maneja lotes individuales).
- Un modelo financiero corporativo con financiación, impuestos o IVA.

---

## 2. Arquitectura del modelo

### 2.1. Los tres escenarios

| Código | Nombre | Qué representa |
|--------|--------|----------------|
| **A** | Venta al destete | El ternero se vende **inmediatamente** al destete sin engorde posterior. Peso de venta = peso inicial. Sirve como **piso económico** (mínima inversión, retorno rápido). |
| **B** | Venta recriado | Se recría hasta un peso intermedio (típicamente 200–280 kg). Etapa de transición que suele tener mejor relación margen/capital invertido. |
| **C** | Venta terminado | Ciclo completo hasta peso de faena (~380–450 kg). Mayor inversión, mayor riesgo, pero también mayor agregado de valor por animal. |

Los tres escenarios son **independientes** desde la óptica económica final (cada uno calcula su propio ingreso, costo y margen) pero **comparten parámetros base**: misma cantidad de terneros, mismo precio de compra, mismo tipo de cambio, misma tasa de interés.

### 2.2. Flujo de cálculo

```
                        ┌─────────────────────────────────┐
                        │   session_state (Streamlit)     │
                        │   inputs del usuario             │
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │  modules/state/persist.py        │
                        │  shadow keys → robusto a navegar │
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │  modules/state/derived.py        │
                        │  consumos, CA, días, precio pond.│
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │  modules/economics/scenarios.py  │
                        │  build de los 3 ResultadoEscenario│
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │  modules/economics/comparador.py │
                        │  tablas comparativas + selección │
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │  modules/pages/page_*.py         │
                        │  rendering, gráficos, KPIs       │
                        └─────────────────────────────────┘
```

### 2.3. Dos motores conviviendo

El código actual tiene **dos capas de cálculo** que conviven históricamente:

1. **`modules/economics/`** (`Comparador`, `scenarios.py`, `models.py`) — motor original simplificado: calcula ingreso/costo/margen por escenario y devuelve un objeto `ResultadoEscenario`. Se usa en la sección comparativa global y en la lógica de "mejor escenario".
2. **Cálculo per-página** (en cada `page_*.py`) — motor extendido: usa la tabla de ración detallada, agrega costos de operación, estructura, comercialización y financieros, y permite calibración independiente por etapa. Es lo que se ve en Costos, Margen Bruto, Sensibilidad y Reportes.

Las fórmulas son **consistentes** entre ambos motores, pero el motor per-página tiene **más resolución de costos** (8 categorías vs 8 también en `CostosVariables`, pero con composición ligeramente distinta — el motor per-página separa Operación de Estructura, mientras que el motor `economics/` consolida amortización y mano de obra).

---

## 3. Vocabulario y unidades

### 3.1. Glosario

| Término | Significado |
|---------|-------------|
| **kg PV** | Kilogramos de peso vivo del animal |
| **kg TC** | Kilogramos tal cual (materia verde + humedad) — peso "como sale del comedero" |
| **kg MS** | Kilogramos de materia seca (sustancia descontando agua) |
| **kg MV** | Kilogramos de materia verde — sinónimo de kg TC en este modelo |
| **%MS** | Porcentaje de materia seca de un alimento (ej: silaje 35 %, maíz grano 88 %) |
| **GDP** | Ganancia diaria de peso (kg PV/día) |
| **CA** | Conversión alimenticia: kg MS consumidos para producir 1 kg de PV |
| **MO** | Mano de obra |
| **Cab** | Cabeza (animal) |
| **USD/cab** | Dólares por cabeza |
| **USD/kg** | Dólares por kilogramo |
| **ROI** | Return on investment — retorno sobre el capital inmovilizado |

### 3.2. Sistema de unidades

| Magnitud | Unidad |
|----------|--------|
| Pesos del animal | kilogramos (kg PV) |
| Consumos | kg MS/cab/día (diario) o kg MS/cab/ciclo (acumulado) |
| Precios de carne | USD/kg vivo |
| Precios de alimento | USD/kg MS (no por kg tal cual) |
| Costos | USD totales o USD/cab |
| Tasas | porcentaje (decimal interno: 0.06 = 6 %) |
| Tiempo | días |
| Tipo de cambio | ARS/USD (informativo, todos los cálculos están en USD) |

**Por qué USD/kg MS y no USD/kg TC:** la materia seca es el verdadero aporte nutricional. Dos alimentos con el mismo precio por kg TC pero distinto %MS aportan distinta energía. Trabajar en MS permite comparar ingredientes correctamente.

---

## 4. Datos que ingresa el usuario

### 4.1. Parámetros globales (afectan a las 3 etapas)

| Parámetro | Key interna | Unidad | Default | Descripción |
|-----------|-------------|--------|---------|-------------|
| Cantidad de terneros | `ANIMAL_CANTIDAD` | cab | 0 | Lote ingresado al sistema |
| Peso inicial | `ANIMAL_PESO_ENTRADA` | kg | 0 | Peso al ingreso (típicamente 45–65 kg) |
| Precio de compra | `COMERCIAL_PRECIO_COMPRA` | USD/kg | 0 | Precio del ternero al ingreso |
| Tipo de cambio | `FINANCIERO_TIPO_CAMBIO` | ARS/USD | 0 | Solo informativo |
| Tasa de interés anual | `FINANCIERO_TASA_INTERES` | % | 0 | Costo de oportunidad del capital |

### 4.2. Por etapa (Cría/Recría/Engorde — prefijos A/B/C)

**Productivos:**

| Parámetro | Unidad | Significado |
|-----------|--------|-------------|
| Peso de salida (B/C) | kg | Peso al cierre de la etapa. Para C es el peso de faena. |
| GDP (B/C) | kg/día | Ganancia diaria objetivo |
| Mortalidad (A/B/C) | % | Tasa de pérdida durante la etapa |

**Sanidad y operación:**

| Parámetro | Unidad | Significado |
|-----------|--------|-------------|
| Sanidad | USD/cab | Costo de vacunaciones, antiparasitarios, etc., del ciclo |
| Mano de obra | USD/mes | Costo mensual del personal asignado a la etapa |
| Combustible | USD/mes | Gasoil, etc. |
| Servicios | USD/mes | Electricidad, agua, conectividad |

**Comercialización:**

| Parámetro | Unidad | Significado |
|-----------|--------|-------------|
| Precio venta | USD/kg | Precio neto al que se vende el animal de la etapa |
| Flete entrada (B/C) | USD/cab | Costo de transporte al ingresar a la etapa |
| Flete salida | USD/cab | Costo de transporte al egresar |
| Comisión | % | Comisión de venta sobre el ingreso bruto |
| Otros | USD/cab | Costos misceláneos |

**Estructura (infraestructura amortizable):**

| Parámetro | Unidad | Significado |
|-----------|--------|-------------|
| Valor infra total | USD | Inversión total en infraestructura del sistema |
| % asignado por etapa | % | Qué porción del valor total se atribuye a cada etapa |
| Años de amortización | años | Vida útil contable para depreciación lineal |
| Mantenimiento | USD/año | Gasto anual de mantenimiento por etapa |

### 4.3. Modelo nutricional (tabla de ración)

Por etapa (B y C) el usuario carga una **tabla de ingredientes** con hasta 10 filas. Por cada ingrediente:

| Columna | Unidad | Editable | Descripción |
|---------|--------|----------|-------------|
| Ingrediente | texto | sí | Nombre libre (ej: "Silaje de maíz") |
| Kg TC | kg/cab/día | sí | Consumo diario tal cual |
| %MS | % | sí | Materia seca del ingrediente |
| Kg MS | kg/cab/día | **calculado** | `= Kg TC × %MS / 100` |
| USD/kg MS | USD/kg | sí | Precio del ingrediente por kg de materia seca |

Esta tabla es la **única fuente de verdad nutricional** del modelo. De ella se derivan automáticamente:

- Conversión alimenticia (CA)
- Precio de alimento ponderado
- Consumos diarios y totales
- Costo de alimentación

### 4.4. Política de defaults

> **Todos los parámetros numéricos inician en 0.** El usuario es la única fuente de verdad. No hay "presets pesimista / base / optimista" cargados automáticamente; cada simulación parte de cero y se construye con los datos del caso real que se quiere modelar.

El botón **↺ Restablecer defaults** (en la página Parámetros) limpia todo el state y vuelve a 0.

---

## 5. Sistema de etapas activas (modular vs integrado)

El dashboard soporta cualquier **slice contiguo** de etapas:

| Modo | Etapas activas |
|------|---------------|
| Sólo Cría | Cría |
| Sólo Recría | Recría |
| Sólo Engorde | Engorde |
| Cría + Recría | Cría → Recría |
| Recría + Engorde | Recría → Engorde |
| Integrado | Cría → Recría → Engorde |

**Validación de contigüidad** (`modules/state/stages.py::enforce_contiguity`): si el usuario selecciona Cría + Engorde **sin** Recría, el sistema **fuerza** Recría a activa antes del próximo cálculo, porque biológicamente un animal no puede saltar de destete a feedlot.

**Encadenamiento de pesos** (`stages.py::kg_in_for`):
- La **primera etapa activa** lee su peso de entrada de un campo editable propio (`*_KG_ENTRADA`).
- Las **etapas subsiguientes** heredan el peso de salida de la etapa previa, sin posibilidad de edición independiente (garantiza coherencia biológica).

**Cascada de cabezas** (consumida por todas las páginas):

```
cab_in_etapa_1   = n_terneros                (input del usuario)
cab_vend_etapa_1 = floor(cab_in × (1 − mort_1/100))
cab_in_etapa_2   = cab_vend_etapa_1          (sobrevivientes)
cab_vend_etapa_2 = floor(cab_in_2 × (1 − mort_2/100))
...
```

La mortandad de una etapa **solo** reduce el lote que entra a la siguiente; no afecta retroactivamente etapas anteriores ni futuras sin entrada previa.

---

## 6. Modelo nutricional (tabla de ración)

### 6.1. Cálculos derivados

Por etapa, el módulo `modules/state/derived.py` calcula automáticamente:

| Variable | Fórmula | Unidad |
|----------|---------|--------|
| `Kg MS_i` (por ingrediente) | `Kg TC_i × %MS_i / 100` | kg MS/cab/día |
| `consumo_ms_dia_cab` | `Σ Kg MS_i` | kg MS/cab/día |
| `consumo_mv_dia_cab` | `Σ Kg TC_i` | kg MV/cab/día |
| `consumo_ms_cab` | `consumo_ms_dia_cab × días` | kg MS/cab/ciclo |
| `consumo_mv_cab` | `consumo_mv_dia_cab × días` | kg MV/cab/ciclo |
| `costo_alim_dia_cab` | `Σ (Kg MS_i × USD/kg MS_i)` | USD/cab/día |
| `costo_alim_cab` | `costo_alim_dia_cab × días` | USD/cab/ciclo |
| `ca` (conversión) | `consumo_ms_dia_cab / GDP` | kg MS / kg PV |
| `precio_ponderado` | `costo_alim_dia_cab / consumo_ms_dia_cab` | USD/kg MS |
| `pct_ms_promedio` | `consumo_ms_dia_cab / consumo_mv_dia_cab × 100` | % |
| `eficiencia` | `GDP / consumo_ms_dia_cab` | kg PV / kg MS |

### 6.2. Por qué CA y el precio del alimento son derivados, no inputs

Antes del refactor, el usuario cargaba CA y el precio del alimento por separado. Esto generaba **inconsistencias**: una CA cargada manualmente podía no corresponderse con los ingredientes y consumos reales que después se anotaban en la tabla.

Ahora la tabla es la **única fuente nutricional** y todo lo demás se deriva. Garantía: el costo de alimentación calculado **siempre** coincide con la suma de ingredientes que el usuario cargó.

### 6.3. Validaciones del modelo nutricional

- **%MS** acotada a [0, 100]
- **Kg TC** y **USD/kg MS** acotados a ≥ 0
- Filas con `Ingrediente` vacío o `Kg TC = 0` se **excluyen** del cálculo
- Tabla vacía → todos los derivados devuelven 0 (no NaN), y la página muestra un aviso

---

## 7. Recorrido por las páginas del dashboard

El sidebar tiene 8 secciones navegables. Cada una se renderiza en `modules/pages/page_*.py`.

### 7.1. Inicio

Landing/portada. No tiene cálculos ni inputs. Es la primera vista al abrir el dashboard.

### 7.2. Parámetros

Es la **única página de entrada de datos**. Organiza los inputs en 9 tabs temáticos (Compra, Alimentación, Sanidad, Operación, Estructura, Comercialización, Financieros, Mortandad, Venta) con tres cards lado a lado (Cría / Recría / Engorde).

**Componentes interactivos:**

- Sliders e inputs numéricos para cada parámetro.
- `st.data_editor` para la tabla de ración (10 filas por etapa, columna `Kg MS` autocalculada).
- Checkboxes para activar/desactivar etapas (con validación de contigüidad).
- Botón **↺ Restablecer defaults** que limpia todo a 0.

**Cálculos visibles en la propia página:**

- Días de tenencia por etapa: `(peso_salida − peso_entrada) / GDP`
- Consumo MS/MV/día y ciclo
- Conversión alimenticia derivada
- Costo de operación por ciclo
- Costo de estructura asignado por etapa
- Suma de % de asignación de infraestructura (warning si supera 100 %)

### 7.3. Modelo Productivo

Visualiza la **biología y productividad**, sin números económicos.

**Lo que muestra:**

- **Curva de crecimiento continua** (Plotly, tipo spline): peso vivo (eje Y) vs días acumulados (eje X), con hitos biológicos anotados (Nacimiento, Destete, Fin Recría, Venta final) y bandas de color por etapa.
- **3 cards por etapa** con 8 KPIs: cabezas in/out, días, kg in/out, GDP, mortandad, CA derivada, consumo MS por cabeza.
- **Tabla de consumo desagregado por ingrediente:** Kg MS/día/cab, Kg MS/etapa, USD/etapa, totales.

**Validaciones:**

- Si no hay etapas activas → anotación central "Sin etapas activas".
- Si GDP ≤ 0 o `kg_out ≤ kg_in` → aviso en lugar del cálculo.
- Si la GDP cargada difiere >5 % de la GDP derivada por la tabla, warning amarillo.

### 7.4. Costos

Desagrega el costo del sistema en **8 categorías** por etapa.

**Categorías:**

| Categoría | Fórmula |
|-----------|---------|
| Compra | `precio_compra × peso_entrada × cab_in` (etapa 1 usa precio global; etapas 2+ usan el precio de compra específico de la etapa, si lo hubiera) |
| Alimentación | `costo_alim_dia_cab × días × cab_in` |
| Sanidad | `sanidad × cab_in` |
| Operación | `(MO_mes + comb_mes + serv_mes) / 30 × días` |
| Estructura | `(amort_anual + mant_anual) × días / 365`, con `amort_anual = valor_total × asig%/100 / años` |
| Comercialización | `(comision% × precio_venta × peso_salida + flete_entrada + flete_salida) × cab_vend` |
| Financieros | `capital × tasa% × días / 365`, donde `capital = compra + alim + san + op + estr + com` |
| Mortandad | Ingreso perdido por los animales muertos: `(cab_in − cab_vend) × peso_salida × precio_venta` |

**Visualizaciones:**

- 3 KPI cards: costo total por cabeza, costo total del sistema, USD por kg producido.
- Barras apiladas: etapas activas (eje X) × 8 categorías (segmentos).
- Barras apiladas (variante invertida): categorías (eje X) × etapas (segmentos).
- Grid de donut charts por etapa con composición porcentual.

### 7.5. Ingresos

Visualización **puramente comercial**: precio × kilos × cabezas vendidas. No descuenta costos.

**KPIs:**

- Ingreso por cabeza: `peso_salida × precio_venta`
- Cabezas vendidas: `cab_in × (1 − mortandad)`
- Kg vendidos: `cab_vend × peso_salida`
- Ingreso total: `ingreso_cab × cab_vend`

**Gráficos:**

- Barras lado a lado: ingreso por cabeza vs ingreso total.
- Curva continua de evolución del **valor bruto del animal** (USD/cab) a lo largo del ciclo. El primer punto puede ser el costo de compra contextual al slice activo (si arranca en Recría, usa el precio de compra de Recría, no el global).

### 7.6. Margen Bruto

El **resultado económico** integrado: ingresos menos costos, por etapa y para el sistema completo.

**Bloques de la página:**

1. **3 KPI cards** por etapa: margen/cab, margen total, USD/kg, USD/cab/día, retorno incremental.
2. **Barras agrupadas** (Ingresos verde, Costos coral, Margen color etapa o rojo) en USD totales por etapa.
3. **Waterfall** del margen/cab a lo largo del ciclo (etapa base + deltas de transiciones).
4. **Cards de "valor agregado"** entre transiciones (Cría→Recría, Recría→Engorde) con veredicto visual.
5. **Matriz estratégica 4×4** (Modelo × [Margen, Riesgo, Capital, Liquidez]) con ratings de color automáticos.
6. **Grid de cards** por etapa con 6 tiles de métricas.

**Fórmulas clave:**

```
ingreso_cab        = peso_salida × precio_venta
ingreso_total      = ingreso_cab × cab_vend
costo_cab          = compra + alim + san + op + estr + com + financiero
costo_total        = costo_cab × cab_in
margen_bruto       = ingreso_total − costo_total
margen_cab         = margen_bruto / cab_in
margen_kg_producido = margen_bruto / (cab_vend × max(peso_salida − peso_entrada, 0))
usd_cab_dia        = margen_cab / días
retorno_incremental = margen_cab[siguiente] − margen_cab[anterior]
```

**Valor agregado entre etapas (transiciones):**

```
delta_margen     = margen_cab[B] − margen_cab[A]
delta_kg         = peso_salida[B] − peso_salida[A]
delta_dias       = días[B]
usd_per_kg_extra = delta_margen / delta_kg
usd_per_dia      = delta_margen / delta_dias
```

**Veredicto del salto de etapa:**

| Condición | Veredicto |
|-----------|-----------|
| `delta_margen > 0 AND usd_per_kg ≥ 0.50 AND usd_per_dia ≥ 0.30` | ✅ Vale la pena |
| `delta_margen > 0` (pero no cumple thresholds) | ⚠ Marginal |
| `delta_margen ≤ 0` | ❌ No conviene |

**Matriz estratégica (scoring 0–100, ranking entre etapas):**

| Eje | Indicador | Criterio |
|-----|-----------|----------|
| Margen | `margen_cab` | mayor = mejor |
| Riesgo | `días × (1 + mortandad/100)` | menor = mejor |
| Capital | `costo_total` | menor = mejor |
| Liquidez | `365 / días` (ciclos por año) | mayor = mejor |

Cada etapa recibe rating Muy alto / Alto / Medio / Bajo según su posición relativa.

### 7.7. Sensibilidad y Riesgo

**Robustez económica** del modelo: cuánto puede moverse cada variable antes de que el margen se vuelva negativo.

**Bloque 1 — Semáforos por etapa** (verde / amarillo / rojo / N/A):

| Indicador | Significado | Fórmula del límite |
|-----------|-------------|--------------------|
| Precio equilibrio | USD/kg de venta para margen = 0 | `precio_eq = costo_total / kg_vendidos` |
| Maíz máximo | USD/kg MS de alimento para margen = 0 | `α = ((1−m) × ingreso − (base − alim)) / alim` ; `precio_max = α × precio_actual` |
| GDP mínima | kg/día mínima para margen = 0 | `gdp_min = (X_min − kg_in) / días`, donde `X_min` se despeja de la condición de breakeven |
| CA máxima | Conversión máxima soportable | `ca_max = α × ca_actual` (mismo α que maíz) |
| Mortandad máxima | % de pérdida que soporta el sistema | `m_max = 1 − base / ingreso` |

**Headroom** (margen de seguridad) de cada indicador:

```
headroom_precio  = (precio_venta − precio_eq) / precio_venta × 100
headroom_maíz    = (precio_max / precio_actual − 1) × 100
headroom_gdp     = (gdp_actual − gdp_min) / gdp_actual × 100
headroom_ca      = (ca_max / ca_actual − 1) × 100
headroom_mort    = mort_max − mort_actual          (en puntos porcentuales)
```

**Umbrales de semáforo:**

| Indicador | 🟢 verde | 🟡 amarillo | 🔴 rojo |
|-----------|---------|-------------|---------|
| Precio / GDP | ≥ 30 % | ≥ 10 % | < 10 % |
| Maíz / CA | ≥ 50 % | ≥ 20 % | < 20 % |
| Mortandad | ≥ 10 pp | ≥ 5 pp | < 5 pp |

**Bloque 2 — Mini-tornados** (barras horizontales): impacto sobre el margen/cab al variar cada parámetro:

| Variable | Variación testeada |
|----------|---------------------|
| Precio compra | ±20 % |
| Precio venta | ±20 % |
| Precio maíz (alimento) | ±20 % |
| GDP | ±15 % |
| Mortandad | ±5 pp |
| Flete | ±20 % |

Por variable se calcula:

```
swing = |margen(-Δ) − margen_base| + |margen(+Δ) − margen_base|
```

A mayor swing, más sensible es el negocio a esa variable.

**Bloque 3 — Simulación interactiva**: 6 sliders (Precio compra, Precio venta, Precio maíz, GDP, Mortandad, Flete) con rangos amplios (±30 % o ±3/+10 pp para mortandad). Las cards se actualizan en tiempo real mostrando el nuevo margen total, margen/cab, USD/cab/día y el delta vs base.

**Bloque 4 — Score de riesgo compuesto** (0–100, mayor = más riesgoso):

| Componente | Fórmula | Peso |
|------------|---------|------|
| Sensibilidad al maíz | `min(100, swing_maíz / |baseline| × 50)` | 0.20 |
| Volatilidad total | `min(100, swing_total / |baseline| × 30)` | 0.25 |
| Duración del ciclo | `min(100, días / 7.30)` | 0.15 |
| Capital relativo | `min(100, costo_etapa / max(costo_peers) × 100)` | 0.20 |
| Mortandad | `min(100, mortandad × 10)` | 0.20 |

```
risk_composite = Σ(score_i × peso_i)
robustness     = max(0, min(100, 100 − risk_composite))
```

**Alertas automáticas:**

| Condición | Tipo |
|-----------|------|
| `robustness < 30` | 🔴 Crítica: "Robustez crítica" |
| `30 ≤ robustness < 50` | 🟡 Warning: "Robustez baja" |
| `swing_var ≥ 30 % del margen base` | 🟡 "Alta sensibilidad a [variable]" |

### 7.8. Reportes

**One-pager ejecutivo** en formato A4 listo para imprimir/screenshotear, sin gráficos pesados.

**Editables en la toolbar:** Empresa, Responsable, Fecha, Incluir logo (checkbox).

**Bloques del reporte:**

1. Header con logo + metadatos.
2. **Hero del margen total del sistema** (ΣUSD grande, color según signo).
3. Franja de contexto (empresa, responsable, fecha, etapas activas, cabezas).
4. **3 cards por etapa activa** con: margen/cab destacado, ingreso/costo lado a lado, riesgo/robustez.
5. **Tabla compacta** con 10 columnas: Etapa, Cab, Días, kg in/out, GDP, CA, USD/kg, USD/cab/día, Margen/cab.
6. **Bloque de riesgo**: variable más sensible (mayor swing del sistema) + robustez del sistema + top 2 alertas.

---

## 8. Fórmulas detalladas por concepto

### 8.1. Productivas

```
días_etapa             = round((peso_salida − peso_entrada) / GDP)
días_total             = Σ días_etapa (en etapas activas)
kg_producidos_cab      = peso_salida − peso_entrada
GDP_efectiva           = (peso_salida − peso_entrada) / días
CA                     = consumo_MS_dia / GDP             (kg MS por kg PV)
eficiencia             = GDP / consumo_MS_dia             (kg PV por kg MS, inversa de CA)
```

### 8.2. Consumos

```
Por ingrediente i:
    Kg_MS_i        = Kg_TC_i × %MS_i / 100

A nivel ración:
    consumo_MS_dia = Σ Kg_MS_i                   (kg MS/cab/día)
    consumo_MV_dia = Σ Kg_TC_i                   (kg MV/cab/día)
    %MS_pond       = consumo_MS_dia / consumo_MV_dia × 100

Acumulado de ciclo:
    consumo_MS_cab = consumo_MS_dia × días
    consumo_MV_cab = consumo_MV_dia × días
    consumo_MS_total = consumo_MS_cab × cab_in    (rodeo entero)
```

### 8.3. Costos por cabeza (USD/cab)

```
compra        = precio_compra × peso_entrada
alimentación  = costo_alim_dia × días
              donde costo_alim_dia = Σ (Kg_MS_i × USD/kg_MS_i)
sanidad       = sanidad_USD_cab    (input directo)
operación     = (MO_mes + combustible_mes + servicios_mes) / 30 × días / cab_in
estructura    = ((valor_total × asig% / años) + mant_anual) × días / 365 / cab_in
comercialización = comision% × precio_venta × peso_salida + flete_entrada + flete_salida
capital_base  = compra + alim + san + operación + estructura + comercialización
financieros   = capital_base × tasa% × días / 365
costo_cab     = capital_base + financieros
```

### 8.4. Costos totales (USD del sistema)

```
costo_total       = costo_cab × cab_in
mortandad_perdida = (cab_in − cab_vend) × peso_salida × precio_venta
```

> Nota: la mortandad **no se suma** a `costo_total` como un costo adicional. La pérdida está ya implícita en que se invirtió compra+alim+san en `cab_in` animales pero solo se cobran `cab_vend`. La página Costos la muestra como categoría aparte para visualización, no para sumarla dos veces.

### 8.5. Ingresos

```
ingreso_cab   = peso_salida × precio_venta
ingreso_total = ingreso_cab × cab_vend
            = peso_salida × precio_venta × cab_in × (1 − mortandad)
```

### 8.6. Márgenes

```
margen_bruto         = ingreso_total − costo_total
margen_neto          = margen_bruto − costo_fijo  (costo_fijo = 0 en el modelo actual)
margen_cab           = margen_bruto / cab_in
margen_kg_producido  = margen_bruto / kg_ganados_total
                     donde kg_ganados_total = cab_vend × (peso_salida − peso_entrada)
costo_kg_producido   = costo_total / kg_ganados_total
margen_USD_cab_dia   = margen_cab / días
```

### 8.7. Capital y retorno

```
capital_inmovilizado = (compra + costo_variable_total) / 2
                     (promedio entre inversión inicial y costo acumulado al cierre)

costo_oportunidad    = capital_inmovilizado × tasa_interes × días / 365

ROI                  = margen_neto / capital_inmovilizado × 100
ROI_anual            = ROI × 365 / días
```

### 8.8. Mejor escenario

```
mejor_escenario     = argmax(margen_neto) entre {A, B, C}
mejor_roi_anual     = argmax(ROI_anual)   entre {A, B, C}
```

---

## 9. Ejemplos numéricos

### 9.1. Ejemplo de cálculo de alimentación (Recría)

Supongamos que en Recría el usuario carga esta ración:

| Ingrediente | Kg TC | %MS | Kg MS | USD/kg MS |
|-------------|-------|-----|-------|-----------|
| Silaje de maíz | 6 | 35 | 2.10 | 0.05 |
| Maíz grano | 2 | 88 | 1.76 | 0.20 |
| Pellet de soja | 0.5 | 90 | 0.45 | 0.50 |

```
consumo_MS_dia = 2.10 + 1.76 + 0.45 = 4.31 kg MS/cab/día
consumo_MV_dia = 6 + 2 + 0.5        = 8.50 kg TC/cab/día
%MS_pond       = 4.31 / 8.50 × 100  = 50.7 %

costo_alim_dia = 2.10 × 0.05  +  1.76 × 0.20  +  0.45 × 0.50
               = 0.105 + 0.352 + 0.225
               = 0.682 USD/cab/día

precio_pond    = 0.682 / 4.31 = 0.158 USD/kg MS

Si GDP = 0.8 kg/día:
    CA           = 4.31 / 0.8 = 5.39 kg MS / kg PV
    eficiencia   = 0.8 / 4.31 = 0.186 kg PV / kg MS
```

### 9.2. Ejemplo de cálculo de un escenario (Engorde simplificado)

Supuestos: 100 terneros, peso inicial 200 kg, peso final 420 kg, GDP 1.2 kg/día, mortandad 3 %, precio compra 2.0 USD/kg, precio venta 1.8 USD/kg, costo alimento 0.7 USD/cab/día, sanidad 8 USD/cab, otros 10 USD/cab, tasa interés anual 6 %.

```
días               = (420 − 200) / 1.2 = 183 días
cab_in             = 100
cab_vend           = floor(100 × 0.97) = 97
kg_ganados_total   = 97 × (420 − 200) = 21 340 kg

compra             = 2.0 × 200 × 100        = 40 000 USD
alimentación       = 0.7 × 183 × 100        = 12 810 USD
sanidad            = 8 × 100                =     800 USD
otros              = 10 × 100               =   1 000 USD
costo_variable     = 54 610 USD
capital_inmov      = (40 000 + 54 610) / 2  = 47 305 USD
costo_oportunidad  = 47 305 × 0.06 × 183/365 = 1 423 USD

ingreso_bruto      = 97 × 420 × 1.8         = 73 332 USD
margen_bruto       = 73 332 − 54 610        = 18 722 USD
margen_cab         = 18 722 / 100           = 187 USD/cab
margen_kg          = 18 722 / 21 340        = 0.88 USD/kg producido

ROI                = 18 722 / 47 305 × 100  = 39.6 %
ROI_anual          = 39.6 × 365 / 183       = 79.0 %
```

### 9.3. Ejemplo de breakeven (sensibilidad)

Continuando el ejemplo 9.2: ¿cuál es el precio de equilibrio?

```
kg_vendidos    = 97 × 420 = 40 740 kg
precio_eq      = costo_total / kg_vendidos
               = 54 610 / 40 740 = 1.34 USD/kg

headroom_precio = (1.80 − 1.34) / 1.80 × 100 = 25.6 %
```

Como 25.6 % está entre 10 % y 30 %, el semáforo de precio sale 🟡 **amarillo** (sensible — un descenso del precio de venta del orden del 25 % volvería el negocio break-even).

---

## 10. Indicadores productivos y financieros

### 10.1. Indicadores productivos (página Modelo Productivo)

| Indicador | Cómo se calcula |
|-----------|-----------------|
| GDP efectiva | `(peso_salida − peso_entrada) / días` |
| CA derivada | `consumo_MS_dia / GDP` |
| Consumo MS/cab/día | suma de Kg MS de la tabla |
| %MS ponderado | `MS_dia / MV_dia × 100` |
| Eficiencia | `GDP / MS_dia` (inversa de CA) |
| Días de tenencia | `(peso_salida − peso_entrada) / GDP` |
| Cabezas vendidas | `floor(cab_in × (1 − mort/100))` |

### 10.2. Indicadores financieros (páginas Costos / Margen / Sensibilidad)

| Indicador | Cómo se calcula | Bueno cuando |
|-----------|------------------|--------------|
| Costo total | suma de las 7 categorías × cab | menor es mejor |
| USD/kg producido | `costo_total / kg_ganados_total` | menor es mejor |
| Margen bruto | `ingreso_total − costo_total` | positivo y alto |
| Margen/cab | `margen_bruto / cab_in` | positivo y alto |
| USD/cab/día | `margen_cab / días` | refleja productividad temporal |
| Margen/kg producido | `margen_bruto / kg_ganados_total` | mayor es mejor |
| ROI | `margen / capital_inmov × 100` | mayor es mejor |
| ROI anual | `ROI × 365 / días` | permite comparar ciclos de distinta duración |
| Headroom (5 variables) | margen de seguridad antes del breakeven | ≥ 30 % es robusto |
| Robustness (0–100) | `100 − risk_composite` | ≥ 70 es robusto |

---

## 11. Cómo impacta cada parámetro sobre el resultado final

Análisis cualitativo de la dirección de impacto (asumiendo el resto constante):

| Parámetro | ↑ del parámetro → | Por qué |
|-----------|--------------------|---------|
| **Precio de compra** | ↓ margen | Aumenta directamente el costo de Compra |
| **Precio de venta** | ↑ margen | Aumenta directamente el ingreso bruto |
| **Cantidad de terneros** | proporcional en USD totales, **neutro** en USD/cab | Escala el sistema, no cambia el unitario |
| **Peso inicial** | depende: en costos sube (más compra), en ingresos puede subir (más kg de venta) | Efecto neto suele ser pequeño |
| **Peso final** | ↑ margen | Más kg vendibles a precio de venta |
| **GDP** | ↑ margen | Menos días para alcanzar peso → menos costo de alimentación y operación |
| **Mortandad** | ↓ margen | Reduce cab_vend → menos ingreso, pero costo de compra/alim/san igual |
| **Precio del alimento** (USD/kg MS) | ↓ margen | Aumenta linealmente el costo de Alimentación |
| **Consumo MS/día** | ↓ margen | Aumenta linealmente el costo de Alimentación |
| **CA (vía consumo)** | ↓ margen | Más kg MS necesarios por kg producido → más costo |
| **Sanidad/Operación/Estructura** | ↓ margen | Suman costos fijos |
| **Tasa de interés** | ↓ margen | Aumenta el costo financiero |
| **Días de tenencia** | ↓ margen (en general) | Más operación, financieros y oportunidad — salvo que sirva para alcanzar mejor precio o más kg |
| **Comisión de venta** | ↓ margen | Resta porcentual del ingreso |
| **Flete entrada/salida** | ↓ margen | Costo fijo por cabeza |

**Sensibilidades típicas observadas** (con valores realistas del modelo):

- Las variables **más críticas** suelen ser, en orden: **precio de venta** > **precio del alimento (maíz)** > **GDP** > **precio de compra**.
- La **mortandad** suele tener impacto moderado (a menos que supere el 5 %).
- Los costos de **estructura** y **operación** son relativamente bajos cuando el lote es grande, pero pesan mucho en lotes chicos.

---

## 12. Persistencia, cache y configuración

### 12.1. Persistencia de parámetros entre páginas (`modules/state/persist.py`)

Streamlit, por defecto, **elimina del `session_state` las claves de widgets que no se renderizan** en un rerun. Cuando el usuario navega de "Parámetros" a "Costos", los widgets de Parámetros no se redibujan y sus valores se pierden.

**Solución implementada:** *shadow keys*. Por cada widget-key `K`, se mantiene una copia paralela `_persist_K` que **no** está atada a ningún widget y por lo tanto sobrevive a la navegación.

**Flujo en cada rerun:**

1. `restore_from_backing()` corre al inicio: copia `_persist_K → K` para las keys ausentes.
2. La slide se renderiza. Si es Parámetros, los widgets pueden escribir nuevos valores en `K`.
3. Los helpers (`_num`, `_sl_f`, `mirror`) copian `K → _persist_K` después de cada edición.

Las páginas consumidoras (Costos, Márgenes, Sensibilidad, Reportes) usan `persist.read(key, default)` con prioridad **shadow → widget → default** — eso garantiza el último valor del usuario incluso si Streamlit ya purgó la widget-key.

### 12.2. Persistencia entre redeploys

⚠ **Importante:** session_state vive **solo en memoria** durante la sesión del navegador. Un redeploy de Streamlit Cloud **reinicia el proceso Python** y **mata las sesiones activas**. Si un usuario tenía parámetros cargados y se redeploya, esos valores se pierden — esto es una **limitación de Streamlit Cloud** sin base de datos externa.

### 12.3. Configuración de Streamlit (`.streamlit/config.toml`)

| Opción | Valor | Por qué |
|--------|-------|---------|
| `server.runOnSave` | `false` | No re-correr automáticamente al guardar — control explícito de cuándo recargar |
| `server.headless` | `true` | Necesario en cloud (sin display server) |
| `runner.fastReruns` | `true` | Re-importa módulos al recargar, evita versiones viejas cacheadas |
| `client.showErrorDetails` | `true` | Visibilidad de errores priorizada sobre estética |
| `client.toolbarMode` | `"minimal"` | UI más limpia |
| `browser.gatherUsageStats` | `false` | Privacidad |

### 12.4. Indicador de versión

El sidebar muestra al final un footer con el commit hash y la fecha del último deploy:

```
build 6a1a290 · 2026-05-19 14:15
```

Ese identificador lo calcula `modules/version.py` en runtime ejecutando `git rev-parse --short HEAD` + `git log -1 --format=%cI` sobre el repo clonado por Streamlit Cloud. Cacheado por proceso con `lru_cache` — como cada redeploy reinicia el proceso Python, el valor siempre refleja la versión publicada.

### 12.5. Flujo de deploy

```
edición local  →  scripts/deploy.ps1 "mensaje"  →  push a origin/main
                                                          │
                                                          ▼
                                     Streamlit Cloud detecta push
                                                          │
                                                          ▼
                                     rebuild + redeploy (~1-2 min)
                                                          │
                                                          ▼
                                     URL pública con nuevo hash
```

---

## 13. Validaciones y controles internos

### 13.1. Sobre los inputs

| Input | Validación |
|-------|------------|
| `%MS` | clamp a [0, 100] |
| `Kg TC`, `USD/kg MS`, precios, costos | clamp a ≥ 0 |
| GDP | si ≤ 0, no se calcula días y la página avisa |
| Peso de salida vs entrada | si `peso_salida ≤ peso_entrada`, no se calcula días |
| Mortandad | clamp a [0, 99] (evita división por cero al despejar `1 − m`) |
| Suma de % de asignación de infra | warning si supera 100 % |

### 13.2. Sobre las etapas

- **Contigüidad forzada:** Cría + Engorde sin Recría es inválido → el sistema fuerza Recría a activa.
- **Sin etapas activas:** las páginas muestran un mensaje "Sin etapas activas" en lugar de gráficos vacíos.
- **Encadenamiento de pesos:** la etapa N+1 hereda `kg_out` de la etapa N — no puede editarse independientemente para evitar inconsistencias.

### 13.3. Defensas matemáticas

| Caso | Comportamiento |
|------|----------------|
| División por cero (días = 0, capital = 0, kg = 0) | devuelve 0, no `NaN` |
| Tabla de ración vacía | devuelve 0 en todos los derivados, página muestra aviso |
| Negativos en cálculos productivos | `max(x, 0)` defensivo |
| GDP cargada vs derivada de la tabla difieren > 5 % | warning amarillo (no bloqueante) |

### 13.4. Sobre la persistencia

- `restore_from_backing` rehidrata solo cuando la key **falta** en session_state — nunca pisa un valor que el usuario acaba de editar.
- `purge_stale_widget_mappings` limpia entradas viejas del mapper interno de Streamlit que podrían arrastrar valores stale entre reruns (best-effort, falla silenciosamente si la API interna de Streamlit cambia).

---

## 14. Supuestos y limitaciones del modelo

### 14.1. Supuestos productivos

1. **GDP constante a lo largo de la etapa.** El modelo asume crecimiento lineal entre peso de entrada y peso de salida. En realidad, la curva de crecimiento de un bovino es sigmoidea (más lenta al principio y al final). Para los rangos de peso típicos manejados (200–450 kg) la aproximación lineal introduce un error pequeño (< 5 %).
2. **CA constante a lo largo de la etapa.** Igual que GDP — en realidad la eficiencia varía con el peso. Asunción aceptable para análisis económico de horizonte ciclo completo, no para programación nutricional fina.
3. **Mortandad uniforme.** La mortandad se aplica como porcentaje constante del lote al cierre de la etapa, no en el día exacto en que muere cada animal. Esto sobre-estima ligeramente los costos atribuidos a animales que mueren en los primeros días de la etapa.
4. **Sin lotes mixtos.** El sistema modela un único lote homogéneo. No soporta lotes con pesos iniciales distintos ni entradas escalonadas.

### 14.2. Supuestos económicos

1. **Todo en USD.** El tipo de cambio aparece como input pero no se usa para conversión interna — todos los costos se asumen ya en USD. El usuario debe convertir manualmente si carga valores en pesos.
2. **Sin inflación intra-ciclo.** Precios constantes durante todo el período. Para ciclos largos (>1 año) y contextos inflacionarios significativos, esto puede subestimar costos.
3. **Sin impuestos, IVA, retenciones.** El modelo trabaja con netos. Si la comparación con datos reales del productor incluye impuestos, hay que netearlos.
4. **Capital inmovilizado calculado como promedio simple.** `(inversión_inicial + costo_total) / 2`. Aproximación razonable para ciclos cortos donde la inversión se hace al inicio y los costos se acumulan gradualmente. Para ciclos con grandes desembolsos intermedios (compras de hacienda múltiples, eventos sanitarios mayores) el promedio simple subestima el capital efectivamente comprometido en algunos momentos.
5. **Sin financiación distinta a la tasa de interés.** No hay schedule de pagos, ni amortización de un crédito específico. La tasa se aplica linealmente sobre el capital inmovilizado.
6. **Costos fijos = 0.** El modelo de `ResultadoEscenario` tiene un campo `costo_fijo` pero el código actual lo deja en 0 — la totalidad de los costos se categorizan como variables. La "estructura" (amortización + mantenimiento) se prorratea por etapa y por cabeza, comportándose como semi-fija.

### 14.3. Supuestos del modelo nutricional

1. **Ración homogénea durante toda la etapa.** No hay transiciones de ración intra-etapa (ej: una pre-iniciación → terminación dentro de Engorde).
2. **Sin pérdidas de comedero.** El consumo cargado es lo que efectivamente come el animal. En sistemas reales con desperdicio, hay que ajustar `Kg TC` para reflejar el consumo bruto (lo que se sirve), no el consumo neto (lo que ingiere).
3. **Sin diferencias por categoría animal.** La ración se asume igual para todo el lote — no se modelan diferencias entre puntas o cualquier subdivisión del rodeo.

### 14.4. Limitaciones funcionales

1. **No persiste entre sesiones.** Cargar parámetros en una sesión, cerrar el navegador, volver al día siguiente → todos los valores vuelven a 0. Si esto se vuelve crítico, requeriría agregar storage externo (Google Sheets, base de datos).
2. **No exporta a Excel/PDF nativamente.** La página Reportes genera un layout HTML pensado para screenshot o impresión del navegador. No hay export programático.
3. **Single user / single tenant.** No hay autenticación, ni separación de datos entre usuarios — cada visitante de la URL pública tiene su propia sesión en memoria, pero todos ven la misma app sin login.
4. **No corre análisis Monte Carlo.** Hay un archivo `page_montecarlo.py` en el código pero no está cableado en la navegación actual. La sensibilidad implementada es **determinista** (variar una variable a la vez), no estocástica.
5. **No modela calendario / estacionalidad.** Días son simplemente "días", no fechas. No hay precios estacionales de venta, ni costos estacionales de alimento, ni eventos calendario (vacunaciones programadas en momentos específicos).

### 14.5. Cuándo confiar en los resultados y cuándo no

**Confiables para:**

- Comparación relativa entre los 3 escenarios (¿conviene vender al destete, recriar o terminar?).
- Identificación de qué variables son críticas para la rentabilidad (sensibilidad).
- Estimación de orden de magnitud de margen, ROI y capital requerido.
- Análisis de break-even (¿hasta qué precio resistimos sin perder plata?).

**No confiables sin ajustes para:**

- Forecasting financiero exacto a 12+ meses con inflación significativa.
- Decisiones de financiación específicas (requiere modelo de flujo de caja con schedule de pagos).
- Decisiones operativas de día a día (compra de alimento, programación sanitaria).
- Comparaciones precisas con datos contables reales sin ajustar por impuestos y prorrateos contables.

---

## 15. Apéndices

### 15.1. Estructura de archivos del proyecto

```
Feedlot Holando/
├── app.py                          # Entry point: page config, CSS, nav, routing
├── requirements.txt                # Dependencias Python
├── README.md                       # Quickstart y deployment
├── DOCUMENTACION.md                # Este documento
├── .gitignore
├── .streamlit/
│   └── config.toml                 # Config Streamlit (cache, server, client)
├── scripts/
│   └── deploy.ps1                  # Helper deploy
└── modules/
    ├── sidebar.py                  # Construye los dicts de params desde el state
    ├── version.py                  # Lee commit + fecha en runtime
    ├── economics/
    │   ├── comparador.py           # Clase Comparador (motor original)
    │   ├── models.py               # Dataclasses CostosVariables, ResultadoEscenario
    │   └── scenarios.py            # calcular_destete/recria/terminado
    ├── state/
    │   ├── keys.py                 # Constantes de session_state
    │   ├── defaults.py             # Defaults (todos en 0)
    │   ├── init_state.py           # Siembra session_state
    │   ├── persist.py              # Shadow store + restore
    │   ├── stages.py               # Etapas activas / contigüidad
    │   └── derived.py              # Derivaciones nutricionales y temporales
    └── pages/
        ├── page_inicio.py
        ├── page_parametros.py
        ├── page_modelo_productivo.py
        ├── page_costos.py
        ├── page_ingresos.py
        ├── page_margenes.py
        ├── page_sensibilidad.py
        └── page_reportes.py
```

### 15.2. Lista de tablas y gráficos vs página

| Página | Tablas | Gráficos |
|--------|--------|----------|
| Inicio | — | — |
| Parámetros | Tabla de ración (editable, 10 filas × 5 cols por etapa) | — |
| Modelo Productivo | Tabla de consumo por ingrediente | Spline crecimiento + hitos |
| Costos | — | Barras apiladas (etapa × cat), barras apiladas (cat × etapa), donuts por etapa |
| Ingresos | — | Barras lado a lado, curva valor bruto del animal |
| Margen Bruto | Matriz estratégica 4×4 | Barras agrupadas, waterfall, cards transiciones |
| Sensibilidad | — | Mini-tornados, semáforos, sliders interactivos |
| Reportes | Tabla compacta 10 cols, cards por etapa | — (one-pager HTML) |

### 15.3. Referencias cruzadas

- **Decisión modular vs integrado** → `modules/state/stages.py`
- **Modelo nutricional** → `modules/state/derived.py`
- **Cálculo de ingresos/costos/margen** → `modules/economics/scenarios.py` y cada `page_*.py`
- **Persistencia** → `modules/state/persist.py`
- **Inputs del usuario** → `modules/pages/page_parametros.py`
- **Sensibilidad** → `modules/pages/page_sensibilidad.py`

### 15.4. Cómo verificar la versión publicada

1. Abrir <https://engordando-holando.streamlit.app/>.
2. En el sidebar, ver el footer `build <hash> · <fecha>`.
3. Comparar el hash con `git rev-parse --short HEAD` del repo local.
4. Si difieren: esperar 1–2 min (rebuild en curso) y hacer **Ctrl+F5** para bypassear cache del navegador.

### 15.5. Cómo desplegar cambios

```powershell
# Desde la raíz del repo
.\scripts\deploy.ps1 "mensaje del commit"
```

El script muestra los archivos modificados, pide confirmación, hace `add + commit + push`, e indica la URL pública con un recordatorio de **Ctrl+F5** para verificar.

---

*Documento mantenido en sintonía con el código. Si encontrás una fórmula del dashboard que no coincide con lo descripto acá, abrí un issue o actualizá este archivo y commiteá junto con el cambio de código.*
