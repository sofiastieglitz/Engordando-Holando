from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import plotly.express as px
import pandas as pd

from modules.pages.ui import page_header, section, kpi_card, scenario_card
from modules.config import COLORES_ESCENARIO

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Escenarios",
        "Comparación técnico-económica completa entre las tres alternativas de producción",
    )

    esc_todos = [comp.destete, comp.recria, comp.terminado]
    mejor = comp.mejor_escenario()

    # ── Scenario cards ────────────────────────────────────────────────────────
    section("Resultados por escenario")
    c1, c2, c3 = st.columns(3)
    for col, e in zip([c1, c2, c3], esc_todos):
        scenario_card(col, e)

    st.divider()

    # ── Ingreso vs costo vs margen ────────────────────────────────────────────
    section("Ingreso, Costo Variable y Margen Neto")
    rows = []
    for e in esc_todos:
        rows += [
            {"Escenario": e.nombre, "Concepto": "Ingreso bruto",  "USD": e.ingreso_bruto},
            {"Escenario": e.nombre, "Concepto": "Costo variable", "USD": e.costo_variable_total},
            {"Escenario": e.nombre, "Concepto": "Margen neto",    "USD": e.margen_neto},
        ]
    fig = px.bar(
        pd.DataFrame(rows),
        x="Escenario", y="USD", color="Concepto", barmode="group",
        color_discrete_map={
            "Ingreso bruto":  "#27ae60",
            "Costo variable": "#e74c3c",
            "Margen neto":    "#2d9cdb",
        },
        text_auto=True,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#7f8c8d")
    fig.update_layout(
        height=400, margin=dict(t=10, b=10), yaxis_title="USD",
        legend=dict(orientation="h", y=-0.2),
        plot_bgcolor="rgba(248,249,252,1)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(texttemplate="%{y:$,.0f}", textposition="outside", textfont_size=9)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── ROI + capital scatter ─────────────────────────────────────────────────
    section("ROI anual y exposición de capital")
    left, right = st.columns(2)

    with left:
        df_roi = pd.DataFrame([
            {"Escenario": e.nombre, "ROI anual (%)": round(e.roi_anual, 2)}
            for e in esc_todos
        ])
        fig_roi = px.bar(
            df_roi, x="ROI anual (%)", y="Escenario", orientation="h",
            color="Escenario", color_discrete_map=COLORES_ESCENARIO, text_auto=True,
        )
        fig_roi.add_vline(x=0, line_dash="dash", line_color="#7f8c8d")
        fig_roi.update_layout(showlegend=False, height=240,
                              margin=dict(t=10, b=10), xaxis_title="ROI anual (%)")
        fig_roi.update_traces(texttemplate="%{x:.1f}%", textposition="outside")
        st.plotly_chart(fig_roi, use_container_width=True)

    with right:
        df_sc = pd.DataFrame([
            {
                "Escenario": e.nombre,
                "Capital inmovilizado (USD)": round(e.capital_inmovilizado, 0),
                "Margen neto (USD)": round(e.margen_neto, 0),
                "Días": e.dias,
            }
            for e in esc_todos
        ])
        fig_sc = px.scatter(
            df_sc, x="Capital inmovilizado (USD)", y="Margen neto (USD)",
            color="Escenario", size="Días", size_max=50,
            color_discrete_map=COLORES_ESCENARIO, text="Escenario",
        )
        fig_sc.add_hline(y=0, line_dash="dash", line_color="#e74c3c")
        fig_sc.update_layout(showlegend=False, height=280, margin=dict(t=10, b=10))
        fig_sc.update_traces(textposition="top center")
        st.plotly_chart(fig_sc, use_container_width=True)

    st.divider()

    # ── Full comparison table ─────────────────────────────────────────────────
    section("Tabla comparativa completa")
    st.dataframe(comp.tabla_comparacion(), use_container_width=True, hide_index=True)
