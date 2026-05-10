from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd
import plotly.express as px

from modules.config import COLORES_ESCENARIO

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


def render_tab_ingresos(comp: "Comparador") -> None:
    esc_todos = [comp.destete, comp.recria, comp.terminado]

    col_g1, col_g2 = st.columns(2)

    # ── Ingresos vs costos por escenario ──────────────────────────────────────
    with col_g1:
        st.markdown("#### Ingresos, Costos y Margen por escenario")
        rows = []
        for e in esc_todos:
            rows += [
                {"Escenario": e.nombre, "Concepto": "Ingreso bruto", "USD": e.ingreso_bruto},
                {"Escenario": e.nombre, "Concepto": "Costo variable", "USD": e.costo_variable_total},
                {"Escenario": e.nombre, "Concepto": "Margen neto", "USD": e.margen_neto},
            ]
        df_comp = pd.DataFrame(rows)
        fig = px.bar(
            df_comp,
            x="Escenario",
            y="USD",
            color="Concepto",
            barmode="group",
            color_discrete_map={
                "Ingreso bruto": "#27ae60",
                "Costo variable": "#e74c3c",
                "Margen neto": "#2d9cdb",
            },
            text_auto=True,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#7f8c8d")
        fig.update_layout(
            height=400, margin=dict(t=10, b=10),
            yaxis_title="USD", legend=dict(orientation="h", y=-0.25),
        )
        fig.update_traces(texttemplate="%{y:$,.0f}", textposition="outside", textfont_size=9)
        st.plotly_chart(fig, use_container_width=True)

    # ── Ingreso por kg y por cabeza ───────────────────────────────────────────
    with col_g2:
        st.markdown("#### Ingreso por kg vivo vendido")
        df_kgv = pd.DataFrame([
            {
                "Escenario": e.nombre,
                "N° vendidos": e.n_vendidos,
                "Precio venta (USD/kg)": e.precio_venta_usd_kg,
                "Peso salida (kg)": e.peso_salida,
                "Ingreso/vendido (USD)": round(e.ingreso_bruto / max(e.n_vendidos, 1), 0),
                "Margen/entrado (USD)": round(e.margen_por_cab, 0),
            }
            for e in esc_todos
        ])
        st.dataframe(
            df_kgv.style.format({
                "Precio venta (USD/kg)": "${:.2f}",
                "Ingreso/vendido (USD)": "${:,.0f}",
                "Margen/entrado (USD)": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.markdown("#### Composición ingreso vs. costo (% sobre ingreso)")
        rows_pct = []
        for e in esc_todos:
            ib = max(e.ingreso_bruto, 1)
            rows_pct.append({
                "Escenario": e.nombre,
                "Costo (%)": round(e.costo_variable_total / ib * 100, 1),
                "Margen (%)": round(e.margen_neto / ib * 100, 1),
            })
        df_pct = pd.DataFrame(rows_pct)
        df_pct_m = df_pct.melt(id_vars="Escenario", var_name="Componente", value_name="%")
        fig2 = px.bar(
            df_pct_m,
            x="Escenario",
            y="%",
            color="Componente",
            barmode="stack",
            color_discrete_map={"Costo (%)": "#e74c3c", "Margen (%)": "#27ae60"},
        )
        fig2.update_layout(
            height=260, margin=dict(t=10, b=10),
            yaxis_title="% del ingreso bruto",
            legend=dict(orientation="h", y=-0.35),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Tabla resumen de ingresos ──────────────────────────────────────────────
    st.markdown("#### Tabla de ingresos detallada")
    df_ing = pd.DataFrame([
        {
            "Escenario": e.nombre,
            "N° entrados": e.n_cabezas,
            "N° vendidos": e.n_vendidos,
            "Peso salida (kg)": e.peso_salida,
            "Precio (USD/kg)": e.precio_venta_usd_kg,
            "Kg totales vendidos": round(e.n_vendidos * e.peso_salida, 0),
            "Ingreso bruto (USD)": round(e.ingreso_bruto, 0),
            "Costo variable (USD)": round(e.costo_variable_total, 0),
            "Margen bruto (USD)": round(e.margen_bruto, 0),
            "Margen neto (USD)": round(e.margen_neto, 0),
        }
        for e in esc_todos
    ])
    st.dataframe(
        df_ing.style.format({
            "Precio (USD/kg)": "${:.2f}",
            "Kg totales vendidos": "{:,.0f}",
            "Ingreso bruto (USD)": "${:,.0f}",
            "Costo variable (USD)": "${:,.0f}",
            "Margen bruto (USD)": "${:,.0f}",
            "Margen neto (USD)": "${:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
