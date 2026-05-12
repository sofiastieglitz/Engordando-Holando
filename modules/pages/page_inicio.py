"""
Inicio — Carátula del dashboard.

Slide de portada: identifica el producto y la autoría sin mostrar
indicadores. Es la primera slide del nav y la default al abrir el
dashboard. Mantiene la firma render(params, comp) por compatibilidad
con el router de app.py (los args no se usan).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


_CARATULA_HTML = """
<div style="
    display:flex; flex-direction:column; align-items:center;
    justify-content:center; text-align:center;
    min-height: calc(100vh - 220px);
    padding: 40px 32px;
    background:
        radial-gradient(circle at 18% 22%, rgba(21,101,192,0.10), transparent 55%),
        radial-gradient(circle at 82% 78%, rgba(13,148,136,0.08), transparent 55%),
        linear-gradient(180deg, #ffffff 0%, #f5f9fd 100%);
    border: 1px solid #dce8f5;
    border-radius: 24px;
    box-shadow: 0 4px 24px rgba(13,27,66,0.06);
">

  <!-- Logo / glyph -->
  <div style="
      width:88px; height:88px; border-radius:22px;
      background: linear-gradient(135deg,#1565c0,#0d47a1);
      box-shadow: 0 10px 28px rgba(21,101,192,0.45);
      display:flex; align-items:center; justify-content:center;
      font-size: 46px; margin-bottom: 28px;
  ">🐄</div>

  <!-- Tag superior -->
  <div style="
      font-size: 0.72rem; font-weight: 700; color: #1565c0;
      text-transform: uppercase; letter-spacing: 0.18em;
      padding: 6px 14px; border-radius: 999px;
      background: rgba(21,101,192,0.08);
      border: 1px solid rgba(21,101,192,0.25);
      margin-bottom: 22px;
  ">Dashboard estratégico</div>

  <!-- Título principal -->
  <h1 style="
      font-size: clamp(1.6rem, 3.2vw, 2.6rem);
      font-weight: 800; color: #0c1a2e;
      line-height: 1.15; letter-spacing: -0.025em;
      margin: 0 0 18px 0; max-width: 920px;
  ">Herramienta de toma de decisiones estratégicas
     en la empresa agropecuaria</h1>

  <!-- Subtítulo -->
  <div style="
      font-size: clamp(1.05rem, 1.6vw, 1.35rem);
      font-weight: 700; color: #1565c0;
      letter-spacing: 0.01em;
      margin: 12px 0 4px 0;
  ">Engordando Holando</div>

  <!-- Firma -->
  <div style="
      font-size: clamp(0.82rem, 1vw, 0.95rem);
      font-weight: 600; font-style: italic;
      color: #5d7a95; letter-spacing: 0.04em;
      margin-top: 4px;
  ">by Sofía Stieglitz</div>

  <!-- Separador decorativo -->
  <div style="
      height: 3px; width: 80px;
      background: linear-gradient(90deg,#1565c0,#0d9488);
      border-radius: 2px; margin: 30px 0 22px 0;
  "></div>

  <!-- Pie de orientación -->
  <div style="
      font-size: 0.78rem; color: #64748b; max-width: 640px;
      line-height: 1.55;
  ">Navegá las solapas del menú lateral para configurar parámetros,
  visualizar el modelo productivo, analizar costos, márgenes y
  sensibilidad, y generar reportes ejecutivos.</div>

</div>
"""


def render(params: dict, comp: "Comparador") -> None:
    st.markdown(_CARATULA_HTML, unsafe_allow_html=True)
