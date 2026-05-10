================================================================
  BACKUP_DASHBOARD_FINAL  —  Copia de seguridad completa
  Dashboard "AgroPlanificacion - Tablero Ganadero"
================================================================

Fecha del backup : 2026-05-09
Origen           : G:\My Drive\3 TRABAJO\Feedlot Holando
Destino          : G:\My Drive\3 TRABAJO\Feedlot Holando\BACKUP_DASHBOARD_FINAL

----------------------------------------------------------------
  OBJETIVO
----------------------------------------------------------------

Guardar una copia estable y autoejecutable del estado actual del
dashboard antes de proximas modificaciones. Esta copia preserva:

  - El codigo fuente completo (app.py + modules/).
  - Los archivos de referencia (Informacion/).
  - Los modelos Excel utilizados como insumo.
  - La documentacion de proyecto (.docx, README.md).
  - El archivo de dependencias (requirements.txt).

NO se incluyen entornos virtuales, caches ni archivos temporales.

----------------------------------------------------------------
  ESTADO ESTABLE (foto al 2026-05-09)
----------------------------------------------------------------

Dashboard: AgroPlanificacion — Tablero Ganadero
Stack    : Streamlit 1.57.0 + Plotly + Pandas (Python 3.14)

Paginas / solapas activas (8):
  1. Parametros
  2. Modelo Productivo
  3. Costos
  4. Ingresos
  5. Margen Bruto
  6. Sensibilidad y Riesgo
  7. Recomendacion Estrategica
  8. Reportes  (One Pager A4 con resumen ejecutivo + 6 mini-bloques)

Modelo productivo: 4 etapas en cascada
  cria  ->  recria  ->  engorde interno  ->  engorde exportacion

Pagina Reportes — bloques implementados:
  - Header ejecutivo (logo + empresa + responsable + fecha)
  - Hero con estrategia recomendada + 5 KPIs (margen, USD/cab/dia,
    ROI, riesgo, robustez)
  - Fila 1 mini-bloques: Modelo Productivo / Costos / Ingresos
  - Fila 2 mini-bloques: Margen Bruto / Sensibilidad / Recomendacion
  - Aun NO incluye generacion de PDF (etapa posterior)

----------------------------------------------------------------
  ESTRUCTURA DE LA COPIA
----------------------------------------------------------------

BACKUP_DASHBOARD_FINAL/
  app.py                              <- entry-point Streamlit
  requirements.txt                    <- dependencias Python
  README.md                           <- README original del proyecto
  README_BACKUP.txt                   <- este archivo
  modelo_feedlot.xlsx                 <- modelo Excel base
  Estructura_Dashboard_Feedlot.xlsx   <- mapeo de la estructura
  codigo de code v0.5.docx            <- documentacion de codigo
  Ideas de mejora.docx                <- backlog de mejoras
  modules/                            <- codigo fuente
    economics/                          modelos de calculo
    pages/                              renderers de cada solapa
    state/                              session_state + defaults + keys
    tabs/                               legacy / auxiliares
  Informacion/                        <- material de referencia
    Ejemplo tablero control Charly/
    *.pdf, *.kml, otros documentos

----------------------------------------------------------------
  COMO RESTAURAR / EJECUTAR DESDE EL BACKUP
----------------------------------------------------------------

1. Copiar la carpeta BACKUP_DASHBOARD_FINAL a una ubicacion de
   trabajo (o trabajar dentro de ella misma).

2. Crear entorno virtual e instalar dependencias:

       python -m venv venv
       .\venv\Scripts\Activate.ps1
       pip install -r requirements.txt

3. Ejecutar el dashboard:

       streamlit run app.py

----------------------------------------------------------------
  EXCLUSIONES (lo que NO se copio)
----------------------------------------------------------------

  - venv/                  (entorno virtual local)
  - __pycache__/           (caches de Python en cualquier nivel)
  - *.pyc, *.pyo           (bytecode compilado)
  - ~$*                    (lock files temporales de Office)
  - .pytest_cache/         (cache de tests)

----------------------------------------------------------------
  GARANTIA DE NO MODIFICACION
----------------------------------------------------------------

  - El proyecto original NO fue modificado durante el backup.
  - Toda la copia se realizo con robocopy / Copy-Item en modo
    lectura sobre el origen.
  - La logica, los calculos y la navegacion del dashboard
    permanecen identicos al estado pre-backup.

================================================================
  Fin del README_BACKUP
================================================================
