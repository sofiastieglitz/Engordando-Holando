from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules.config import COLORES_ESCENARIO

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


def _waterfall_detallado(e) -> go.Figure:
    costos_fin = (
        e.costos.compra + e.costos.flete_entrada
        + e.costos.flete_salida + e.costos.amortizacion + e.costos.otros
    )
    texto_mo = "—" if e.costos.mano_obra == 0 else f"-${e.costos.mano_obra:,.0f}"
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=["Ingresos", "Alimentación", "Sanidad", "Mano de obra", "Compra + fletes + otros", "Margen final"],
        y=[
            e.ingreso_bruto,
            -e.costos.alimentacion,
            -e.costos.sanidad,
            -e.costos.mano_obra,
            -costos_fin,
            0,
        ],
        text=[
            f"${e.ingreso_bruto:,.0f}",
            f"-${e.costos.alimentacion:,.0f}",
            f"-${e.costos.sanidad:,.0f}",
            texto_mo,
            f"-${costos_fin:,.0f}",
            f"${e.margen_neto:,.0f}",
        ],
        textposition="outside",
        textfont={"size": 9},
        connector={"line": {"color": "#dee2e6", "width": 1}},
        increasing={"marker": {"color": "#27ae60"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#2d9cdb"}},
    ))
    fig.update_layout(
        height=390,
        margin=dict(t=50, b=10, l=10, r=10),
        yaxis_title="USD",
        showlegend=False,
        title=dict(
            text=e.nombre,
            font=dict(size=13, color=COLORES_ESCENARIO[e.nombre]),
            x=0.5,
            xanchor="center",
        ),
        plot_bgcolor="rgba(248,249,250,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#e5e5e5"),
        xaxis=dict(showgrid=False),
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#bdc3c7", line_width=1)
    return fig


def _chart_margenes_roi(esc_todos: list, colores: dict) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    nombres = [e.nombre for e in esc_todos]
    colors = [colores[n] for n in nombres]

    fig.add_trace(go.Bar(
        name="Margen bruto",
        x=nombres,
        y=[e.margen_bruto for e in esc_todos],
        marker_color=colors,
        marker_opacity=0.45,
        text=[f"${e.margen_bruto:,.0f}" for e in esc_todos],
        textposition="outside",
        textfont=dict(size=10),
        offsetgroup=0,
        hovertemplate="<b>Margen bruto</b><br>%{x}<br>USD %{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        name="Margen neto",
        x=nombres,
        y=[e.margen_neto for e in esc_todos],
        marker_color=colors,
        marker_opacity=1.0,
        text=[f"${e.margen_neto:,.0f}" for e in esc_todos],
        textposition="outside",
        textfont=dict(size=10),
        offsetgroup=1,
        hovertemplate="<b>Margen neto</b><br>%{x}<br>USD %{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        name="ROI anual (%)",
        x=nombres,
        y=[e.roi_anual for e in esc_todos],
        mode="lines+markers+text",
        marker=dict(size=10, color="#e74c3c", symbol="diamond"),
        line=dict(color="#e74c3c", width=2, dash="dot"),
        text=[f" {e.roi_anual:.1f}%" for e in esc_todos],
        textposition="top right",
        textfont=dict(size=11, color="#e74c3c"),
        hovertemplate="<b>ROI anual</b><br>%{x}<br>%{y:.1f}%<extra></extra>",
    ), secondary_y=True)

    fig.add_hline(y=0, line_dash="dash", line_color="#bdc3c7", line_width=1)
    fig.update_layout(
        barmode="group",
        height=430,
        legend=dict(orientation="h", y=-0.15, x=0),
        margin=dict(t=20, b=55, l=10, r=10),
        plot_bgcolor="rgba(248,249,250,1)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.25,
        bargroupgap=0.1,
        hovermode="x unified",
        xaxis=dict(showgrid=False),
    )
    fig.update_yaxes(
        title_text="Margen (USD)",
        showgrid=True, gridcolor="#e5e5e5",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="ROI anual (%)",
        showgrid=False,
        secondary_y=True,
    )
    return fig


def render_tab_resultados(comp: "Comparador") -> None:
    mejor = comp.mejor_escenario()
    esc_todos = [comp.destete, comp.recria, comp.terminado]

    # ── Banner ────────────────────────────────────────────────────────────────
    color = COLORES_ESCENARIO[mejor.nombre]
    vendidos_str = " | ".join(
        f"{e.nombre.split('—')[0].strip()}: {e.n_vendidos}/{e.n_cabezas} cab."
        for e in esc_todos
    )
    st.markdown(
        f"""<div style="background:{color}18; border-left:5px solid {color};
                    padding:12px 20px; border-radius:6px; margin-bottom:4px;">
            <strong>✅ Mayor margen neto:</strong> {mejor.nombre}<br>
            Margen: <strong>USD {mejor.margen_neto:,.0f}</strong> &nbsp;|&nbsp;
            ROI: <strong>{mejor.roi:.1f}%</strong> &nbsp;|&nbsp;
            ROI anual: <strong>{mejor.roi_anual:.1f}%</strong> &nbsp;|&nbsp;
            USD <strong>{mejor.margen_por_cab:,.0f}</strong>/cab<br>
            <small>Animales vendidos — {vendidos_str}</small>
        </div>""",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Comparativo: márgenes y ROI ───────────────────────────────────────────
    st.markdown("#### Comparativo — Márgenes y ROI anual")
    st.plotly_chart(_chart_margenes_roi(esc_todos, COLORES_ESCENARIO), use_container_width=True)

    st.divider()

    # ── Cascadas por escenario ────────────────────────────────────────────────
    st.markdown("#### Desglose de resultados por escenario")
    wf1, wf2, wf3 = st.columns(3)
    with wf1:
        st.plotly_chart(_waterfall_detallado(comp.destete), use_container_width=True)
    with wf2:
        st.plotly_chart(_waterfall_detallado(comp.recria), use_container_width=True)
    with wf3:
        st.plotly_chart(_waterfall_detallado(comp.terminado), use_container_width=True)

    st.divider()

    col_tab, col_charts = st.columns([3, 2])

    with col_tab:
        # ── Tabla de indicadores ──────────────────────────────────────────────
        st.markdown("#### Tabla de indicadores")
        df = comp.tabla_margenes()
        st.dataframe(
            df.style.format({
                "Ingreso bruto (USD)":       "${:,.0f}",
                "Costo variable (USD)":      "${:,.0f}",
                "Margen bruto (USD)":        "${:,.0f}",
                "Margen neto (USD)":         "${:,.0f}",
                "ROI (%)":                   "{:.1f}%",
                "ROI anual (%)":             "{:.1f}%",
                "Capital inmovilizado (USD)":"${:,.0f}",
                "Margen/cab (USD)":          "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ── Mortalidad e impacto ──────────────────────────────────────────────
        st.markdown("#### Mortalidad e impacto económico")
        df_m = pd.DataFrame([
            {
                "Escenario": e.nombre,
                "Entrados": e.n_cabezas,
                "Vendidos": e.n_vendidos,
                "Bajas": e.n_cabezas - e.n_vendidos,
                "Mort. (%)": round(e.mortalidad * 100, 1),
                "Pérdida mort. (USD)": round(e.perdida_mortalidad, 0),
                "Costo oport. (USD)": round(e.costo_oportunidad, 0),
            }
            for e in esc_todos
        ])
        st.dataframe(
            df_m.style.format({
                "Mort. (%)": "{:.1f}%",
                "Pérdida mort. (USD)": "${:,.0f}",
                "Costo oport. (USD)": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ── Eficiencia ────────────────────────────────────────────────────────
        st.markdown("#### Eficiencia por kg ganado")
        df_eff = pd.DataFrame([
            {
                "Escenario": e.nombre,
                "Kg ganados": round(e.kg_ganados_total, 0),
                "Margen/kg (USD)": round(e.margen_por_kg_ganado, 2),
                "Costo/kg (USD)": round(e.costo_por_kg_ganado, 2),
                "Margen/cab (USD)": round(e.margen_por_cab, 0),
            }
            for e in esc_todos
        ])
        st.dataframe(
            df_eff.style.format({
                "Kg ganados": "{:,.0f}",
                "Margen/kg (USD)": "${:.2f}",
                "Costo/kg (USD)": "${:.2f}",
                "Margen/cab (USD)": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with col_charts:
        # ── ROI anual ─────────────────────────────────────────────────────────
        st.markdown("#### ROI anual (%)")
        df_roi = pd.DataFrame([
            {"Escenario": e.nombre, "ROI anual (%)": round(e.roi_anual, 2)}
            for e in esc_todos
        ])
        fig_roi = px.bar(
            df_roi, x="ROI anual (%)", y="Escenario", orientation="h",
            color="Escenario", color_discrete_map=COLORES_ESCENARIO, text_auto=True,
        )
        fig_roi.add_vline(x=0, line_dash="dash", line_color="#7f8c8d")
        fig_roi.update_layout(showlegend=False, height=200,
                              margin=dict(t=10, b=10), xaxis_title="ROI anual (%)")
        fig_roi.update_traces(texttemplate="%{x:.1f}%", textposition="outside")
        st.plotly_chart(fig_roi, use_container_width=True)

        # ── Capital vs. Margen ────────────────────────────────────────────────
        st.markdown("#### Capital inmovilizado vs. Margen neto")
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
            df_sc,
            x="Capital inmovilizado (USD)", y="Margen neto (USD)",
            color="Escenario", size="Días", size_max=45,
            color_discrete_map=COLORES_ESCENARIO, text="Escenario",
        )
        fig_sc.add_hline(y=0, line_dash="dash", line_color="#e74c3c")
        fig_sc.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10))
        fig_sc.update_traces(textposition="top center")
        st.plotly_chart(fig_sc, use_container_width=True)

        # ── Pérdida por mortalidad ────────────────────────────────────────────
        st.markdown("#### Pérdida por mortalidad (USD)")
        df_pm = pd.DataFrame([
            {"Escenario": e.nombre, "Pérdida (USD)": round(e.perdida_mortalidad, 0)}
            for e in esc_todos
        ])
        fig_pm = px.bar(
            df_pm, x="Escenario", y="Pérdida (USD)",
            color="Escenario", color_discrete_map=COLORES_ESCENARIO,
            text_auto=True,
        )
        fig_pm.update_layout(showlegend=False, height=220, margin=dict(t=10, b=10))
        fig_pm.update_traces(texttemplate="%{y:$,.0f}", textposition="outside")
        st.plotly_chart(fig_pm, use_container_width=True)
