# Feedlot Holando — Simulación Económica

Simulador de viabilidad económica para la integración vertical de terneros machos provenientes de tambos Holstein.

## Stack

- **Python 3.10+**
- **Streamlit** — interfaz web interactiva
- **Pandas** — manipulación de datos tabulares
- **Plotly** — visualizaciones interactivas
- **NumPy** — cálculos numéricos

## Estructura del proyecto

```
feedlot-holando/
├── app.py                        # Entrada principal de la app
├── requirements.txt
├── README.md
└── modules/
    ├── __init__.py
    ├── config.py                 # Constantes y valores por defecto
    ├── sidebar.py                # Panel lateral con parámetros de entrada
    └── tabs/
        ├── __init__.py
        ├── tab_parametros.py     # Resumen de parámetros del sistema
        ├── tab_costos.py         # Estructura y distribución de costos
        ├── tab_ingresos.py       # Proyección de ingresos
        ├── tab_resultados.py     # Resultados económicos y KPIs
        └── tab_sensibilidad.py   # Análisis de sensibilidad por precio
```

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Si `streamlit` no está en el PATH:

```bash
python -m streamlit run app.py
```

## Deployment

La app está publicada en **<https://engordando-holando.streamlit.app/>** vía Streamlit Community Cloud, conectado a este repo en la branch `main`.

**Cada push a `main` redeploya automáticamente** (~1-2 min). No hay paso manual de deploy.

### Cómo publicar cambios

```powershell
.\scripts\deploy.ps1 "mensaje del commit"
```

El script muestra los cambios, pide confirmación, hace `add + commit + push` y avisa la URL. Para saltearse la confirmación: `-Force`.

### Verificar qué versión está publicada

Mirá el footer del sidebar: muestra el commit hash + fecha del último deploy (ej. `b50cba2 · 2026-05-19 14:15`). Si el hash coincide con `git rev-parse --short HEAD` local, estás viendo lo último.

### Si seguís viendo la versión vieja

1. Esperá 2 min — Streamlit Cloud tarda en rebuildear.
2. Hacé **Ctrl+F5** (Windows) o **Cmd+Shift+R** (Mac) — bypass del cache del navegador.
3. Verificá el hash en el sidebar contra `git rev-parse --short HEAD`.
4. Si el hash remoto sigue siendo viejo, revisá los logs en <https://share.streamlit.io/> (probablemente falló un import o el requirements).

### Importante sobre persistencia de parámetros

Los parámetros que el usuario edita viven en `st.session_state` y persisten **mientras dura la sesión del navegador**. Un redeploy mata las sesiones activas (limitación de Streamlit Cloud sin DB externa); los valores ingresados antes del redeploy se pierden. Esto es comportamiento esperado y no se puede evitar sin agregar infraestructura adicional.

El sistema de shadow-keys (`modules/state/persist.py`) garantiza que los parámetros **sobrevivan a la navegación entre páginas** dentro de la misma sesión — eso sí está cubierto.

## Navegación

| Tab | Descripción |
|-----|-------------|
| 📋 Parámetros | Resumen de los parámetros del rodeo y precios activos |
| 💸 Costos | Estructura de costos y distribución porcentual |
| 📈 Ingresos | Proyección de ingresos y comparación con costos |
| 📊 Resultados | Estado de resultados, KPIs y cascada de rentabilidad |
| 🔬 Sensibilidad | Análisis de margen ante variaciones en el precio de venta |

## Parámetros de entrada (sidebar)

- Escenario: Pesimista / Base / Optimista
- N° de terneros, peso inicial y final, días de engorde
- Precio de compra del ternero (USD/kg)
- Precio de venta del novillo (USD/kg)
- Tipo de cambio (ARS/USD)

## Estado

`v0.1` — Arquitectura, navegación y placeholders funcionales. Módulos de cálculo en desarrollo.
