# Backup — Engordando Holando

Snapshot íntegra del dashboard al **2026-05-10**.

## Contenido

- `app.py` — entry point Streamlit.
- `modules/` — paquete completo (pages, state, economics, tabs, sidebar, ui).
- `requirements.txt` — dependencias declaradas (4 paquetes top-level).
- `requirements-frozen.txt` — pip freeze del venv en uso, versiones exactas de
  todas las dependencias transitivas. Generado al momento del backup.
- `Informacion/` — documentación de referencia y assets de imágenes.
- `*.docx`, `*.xlsx` — documentos de soporte (especificación, parámetros,
  ideas de mejora).
- `Parametros y formulas de dashboard de engorde holando.docx` —
  documentación técnica completa de fórmulas y parámetros.
- `_build_word_doc.py` — generador del .docx de fórmulas (opcional, requiere
  `python-docx`).

## Excluido del backup

- `venv/` — entorno virtual (regenerable, ~409 MB).
- `__pycache__/` — bytecode (regenerable).
- `BACKUP_DASHBOARD_FINAL/` — backup viejo (redundante).
- `.claude/` — settings locales del IDE.
- Archivos lock de Office (`~$*.docx`, `~$*.xlsx`).

## Restauración / ejecución independiente

Desde la carpeta de este backup:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements-frozen.txt
venv\Scripts\python.exe -m streamlit run app.py
```

Si preferís usar el `requirements.txt` declarativo en lugar del freeze, hay
que agregarle manualmente `streamlit-option-menu` (ese paquete está en uso
en `app.py:11` pero no estaba listado en el `requirements.txt` original):

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt streamlit-option-menu
```

## Estado funcional al momento del backup

- 7 slides activas en navegación: Parámetros, Modelo Productivo, Costos,
  Ingresos, Margen Bruto, Sensibilidad y Riesgo, Reportes.
- Slide "Recomendación Estratégica" eliminada (lógica integrada en Reportes).
- Modelo bioeconómico puro: alimentación = (kg_out − kg_in) × CA × precio
  ponderado de la ración. No quedan entradas USD/cab/día manuales.
- Operación en USD/mes (MO + combustible + servicios) por etapa.
- Mortandad como ingreso perdido en Costos; sin doble contabilización en
  Margen Bruto y Sensibilidad (asimetría implícita cab_in vs cab_vend).
- Costo financiero sobre capital total (compra + alim + sanidad + op + estr
  + com) × tasa%/100 × días/365.
- ROI eliminado de todas las pages activas.
- Tornado: 6 variables (precio compra, precio venta, precio maíz, GDP,
  mortandad, flete) con altura adaptativa.

## Verificación

- 67 archivos copiados, ~20 MB.
- `python -m compileall` sobre la raíz del backup → exit 0 (toda la sintaxis
  parsea correctamente).
- Estructura de paquetes intacta: `modules/pages/`, `modules/state/`,
  `modules/economics/`, `modules/tabs/`.
