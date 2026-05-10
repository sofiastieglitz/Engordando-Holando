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
