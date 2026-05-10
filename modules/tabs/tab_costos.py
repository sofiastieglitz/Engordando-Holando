from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules.config import COLORES_ESCENARIO

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


def _chart_pie_costos(e) -> go.Figure:
    costos_dict = {k: v for k, v in e.costos.as_dict().items() if v > 0}
    palette = [
        "#2d9cdb", "#f5a623", "#1a6b3c", "#e74c3c",
        "#9b59b6", "#1abc9c", "#e67e22", "#7f8c8d",
    ]
    labels = list(costos_dict.keys())
    values = list(costos_dict.values())
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        textinfo="label+percent",
        textposition="auto",
        textfont=dict(size=11),
        marker=dict(
            colors=palette[: len(labels)],
            line=dict(color="white", width=2),
        ),
        hovertemplate="<b>%{label}</b><br>USD %{value:,.0f} — %{percent:.1%}<extra></extra>",
        pull=[0.03] * len(labels),
    ))
    fig.update_layout(
        height=380,
        margin=dict(t=20, b=20, l=10, r=10),
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(
            text=(
                f"<b>USD {e.costo_variable_total:,.0f}</b><br>"
                "<span style='font-size:11px;color:#7f8c8d'>Total costos</span>"
            ),
            x=0.5, y=0.5, font=dict(size=12),
            showarrow=False, align="center",
        )],
    )
    return fig


def render_tab_costos(comp: "Comparador") -> None:
    esc_todos = [comp.destete, comp.recria, comp.terminado]

    # ── Composición de costos (donut) ─────────────────────────────────────────
    st.markdown("#### Composición de costos por escenario")
    esc_map = {e.nombre: e for e in esc_todos}
    sel = st.selectbox("Ver composición para:", list(esc_map.keys()), key="pie_escenario")
    col_pie, col_info = st.columns([2, 1])
    with col_pie:
        st.plotly_chart(_chart_pie_costos(esc_map[sel]), use_container_width=True)
    with col_info:
        e_sel = esc_map[sel]
        df_pie_tabla = pd.DataFrame([
            {
                "Categoría": k,
                "USD": round(v, 0),
                "% total": round(v / max(e_sel.costo_variable_total, 1) * 100, 1),
            }
            for k, v in e_sel.costos.as_dict().items()
            if v > 0
        ])
        st.dataframe(
            df_pie_tabla.style.format({"USD": "${:,.0f}", "% total": "{:.1f}%"}),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ── Gráfico comparativo por categoría ─────────────────────────────────────
    col_g, col_t = st.columns([3, 2])

    with col_g:
        st.markdown("#### Costos por categoría y escenario")
        df_larga = comp.tabla_costos_larga()
        df_larga = df_larga[df_larga["USD"] > 0]
        fig = px.bar(
            df_larga,
            x="Categoría",
            y="USD",
            color="Escenario",
            barmode="group",
            color_discrete_map=COLORES_ESCENARIO,
            text_auto=True,
        )
        fig.update_layout(
            height=400,
            margin=dict(t=10, b=10),
            yaxis_title="USD",
            legend=dict(orientation="h", y=-0.25),
        )
        fig.update_traces(texttemplate="%{y:$,.0f}", textposition="outside", textfont_size=10)
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        st.markdown("#### Costo total rodeo por categoría (USD)")
        df_tabla = comp.tabla_costos().set_index("Escenario")
        df_tabla = df_tabla.T
        df_tabla.index.name = "Categoría"
        df_tabla = df_tabla.reset_index()
        st.dataframe(
            df_tabla.style.format(
                {c: "${:,.0f}" for c in df_tabla.columns if c != "Categoría"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ── Costo por kg ganado ───────────────────────────────────────────────────
    st.markdown("#### Costo por kg ganado y capital inmovilizado")
    col_cpkg, col_cap = st.columns(2)

    with col_cpkg:
        df_cpkg = pd.DataFrame([
            {
                "Escenario": e.nombre,
                "Costo variable total (USD)": round(e.costo_variable_total, 0),
                "Kg ganados totales": round(e.kg_ganados_total, 0),
                "Costo/kg ganado (USD)": round(e.costo_por_kg_ganado, 2),
                "Costo/cab (USD)": round(e.costo_variable_total / e.n_cabezas, 0),
            }
            for e in esc_todos
        ])
        st.dataframe(
            df_cpkg.style.format({
                "Costo variable total (USD)": "${:,.0f}",
                "Kg ganados totales": "{:,.0f}",
                "Costo/kg ganado (USD)": "${:.2f}",
                "Costo/cab (USD)": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with col_cap:
        df_cap = pd.DataFrame([
            {"Escenario": e.nombre, "Capital inmovilizado (USD)": round(e.capital_inmovilizado, 0)}
            for e in esc_todos
        ])
        fig2 = px.bar(
            df_cap,
            x="Escenario",
            y="Capital inmovilizado (USD)",
            color="Escenario",
            color_discrete_map=COLORES_ESCENARIO,
            text_auto=True,
        )
        fig2.update_layout(
            showlegend=False, height=280,
            margin=dict(t=10, b=10), yaxis_title="USD",
        )
        fig2.update_traces(texttemplate="%{y:$,.0f}", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)
