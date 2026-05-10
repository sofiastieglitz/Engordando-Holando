from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from modules.pages.ui import page_header, section, kpi_card
from modules.economics.scenarios import calcular_terminado

if TYPE_CHECKING:
    from modules.economics.comparador import Comparador


def _run_simulation(
    params: dict,
    n_sim: int,
    cv_precio: float,
    cv_mort: float,
    cv_gdp: float,
    cv_alimento: float,
) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    an_c = params["animal_params"]["C"]
    co_c = params["commercial_params"]["C"]
    fe_c = params["feed_params"]["C"]

    base_precio = co_c["precio_venta"]
    base_mort   = an_c["mortalidad"]      # decimal
    base_gdp    = an_c["gdp"]
    base_alim   = fe_c["precio_alimento"]
    base_ca     = an_c["ca"]

    rows = []
    for _ in range(n_sim):
        new_precio = max(0.10, rng.normal(base_precio, base_precio * cv_precio / 100))
        new_mort   = float(np.clip(
            rng.normal(base_mort, max(base_mort * cv_mort / 100, 0.002)), 0.0, 0.50
        ))
        new_gdp    = max(0.10, rng.normal(base_gdp,   base_gdp   * cv_gdp    / 100))
        new_alim   = max(0.01, rng.normal(base_alim,  base_alim  * cv_alimento / 100))
        new_ca     = max(2.0,  rng.normal(base_ca,    base_ca    * 0.05))

        p = {
            **params,
            "animal_params": {
                **params["animal_params"],
                "C": {**an_c, "mortalidad": new_mort, "gdp": new_gdp, "ca": new_ca},
            },
            "commercial_params": {
                **params["commercial_params"],
                "C": {**co_c, "precio_venta": new_precio},
            },
            "feed_params": {
                **params["feed_params"],
                "C": {**fe_c, "precio_alimento": new_alim},
            },
        }

        e = calcular_terminado(p)
        rows.append({
            "margen_neto":    e.margen_neto,
            "roi_anual":      e.roi_anual,
            "precio_venta":   new_precio,
            "mortalidad_pct": new_mort * 100,
            "gdp":            new_gdp,
        })
    return pd.DataFrame(rows)


def render_content(params: dict, comp: "Comparador") -> None:
    """Monte Carlo content without page header — embeddable in other pages."""
    e_base = comp.terminado

    # ── Simulation controls ───────────────────────────────────────────────────
    section("Parámetros de la simulación")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        n_sim = int(st.select_slider("N° simulaciones", [500, 1_000, 2_000, 5_000],
                                     value=1_000, key="mc_n"))
    with c2:
        cv_precio   = st.slider("CV precio venta (%)",   2, 30, 10, 1, key="mc_cv_p")
    with c3:
        cv_mort     = st.slider("CV mortalidad (%)",     10, 100, 50, 10, key="mc_cv_m")
    with c4:
        cv_gdp      = st.slider("CV GDP (%)",             2, 20, 8,  1, key="mc_cv_g")
    with c5:
        cv_alimento = st.slider("CV precio alimento (%)", 2, 30, 12, 1, key="mc_cv_a")

    df = _run_simulation(params, n_sim, cv_precio, cv_mort, cv_gdp, cv_alimento)

    # ── Distribution KPIs ─────────────────────────────────────────────────────
    st.divider()
    section("Distribución del Margen Neto (USD)")
    p10, p25, p50, p75, p90 = np.percentile(df["margen_neto"], [10, 25, 50, 75, 90])
    prob_pos = float((df["margen_neto"] > 0).mean() * 100)

    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_card(k1, "📉", f"USD {p10:,.0f}",  "P10 — Escenario Pesimista", "rose",
             value_size="medium")
    kpi_card(k2, "📊", f"USD {p50:,.0f}",  "P50 — Mediana", "blue",
             delta=f"base: USD {e_base.margen_neto:,.0f}", delta_type="off", value_size="medium")
    kpi_card(k3, "📈", f"USD {p90:,.0f}",  "P90 — Escenario Optimista", "green",
             value_size="medium")
    kpi_card(k4, "✅", f"{prob_pos:.1f}%",  "Prob. Margen Positivo", "teal",
             delta=f"{int(prob_pos/100*n_sim):,}/{n_sim:,} simulaciones", delta_type="off", value_size="medium")
    kpi_card(k5, "〰️", f"USD {df['margen_neto'].std():,.0f}", "Desvío Estándar",
             "amber", value_size="medium")

    st.divider()

    # ── Distribution histogram ────────────────────────────────────────────────
    section("Distribución de frecuencias — Margen Neto")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=df["margen_neto"], nbinsx=60,
        marker_color="#2d9cdb", marker_opacity=0.75,
        name="Simulaciones",
    ))
    for pval, label, color in [
        (0,              "Breakeven",          "#e74c3c"),
        (p50,            f"P50 {p50:,.0f}",    "#1a6b3c"),
        (e_base.margen_neto, f"Base {e_base.margen_neto:,.0f}", "#f5a623"),
    ]:
        fig_hist.add_vline(x=pval, line_dash="dash", line_color=color, line_width=1.5,
                           annotation_text=f"USD {label}", annotation_position="top right")
    fig_hist.update_layout(
        height=360, margin=dict(t=20, b=20),
        xaxis_title="Margen Neto (USD)", yaxis_title="Frecuencia",
        plot_bgcolor="rgba(248,249,252,1)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # ── Scatter + ROI histogram ───────────────────────────────────────────────
    section("Sensibilidad al precio de venta — Margen Neto vs. mortalidad simulada")
    left, right = st.columns(2)

    with left:
        sample = df.sample(min(600, len(df)), random_state=1)
        fig_sc = px.scatter(
            sample, x="precio_venta", y="margen_neto",
            color="mortalidad_pct",
            color_continuous_scale="RdYlGn_r", opacity=0.55,
            labels={"precio_venta": "Precio venta (USD/kg)",
                    "margen_neto": "Margen neto (USD)",
                    "mortalidad_pct": "Mort. (%)"},
        )
        fig_sc.add_hline(y=0, line_dash="dash", line_color="#e74c3c")
        fig_sc.update_layout(
            height=320, margin=dict(t=10, b=10),
            plot_bgcolor="rgba(248,249,252,1)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with right:
        fig_roi = go.Figure(go.Histogram(
            x=df["roi_anual"], nbinsx=50,
            marker_color="#1a6b3c", marker_opacity=0.75,
        ))
        fig_roi.add_vline(x=0, line_dash="dot", line_color="#e74c3c")
        fig_roi.add_vline(x=e_base.roi_anual, line_dash="dash", line_color="#f5a623",
                          annotation_text=f"Base {e_base.roi_anual:.1f}%",
                          annotation_position="top right")
        fig_roi.update_layout(
            height=320, margin=dict(t=10, b=10),
            xaxis_title="ROI anual (%)", yaxis_title="Frecuencia",
            plot_bgcolor="rgba(248,249,252,1)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_roi, use_container_width=True)

    st.divider()

    # ── Percentile table ──────────────────────────────────────────────────────
    section("Tabla de percentiles")
    pct_rows = []
    for p in [5, 10, 25, 50, 75, 90, 95]:
        pct_rows.append({
            "Percentil":        f"P{p}",
            "Margen Neto (USD)": round(float(np.percentile(df["margen_neto"], p)), 0),
            "ROI anual (%)":     round(float(np.percentile(df["roi_anual"],   p)), 1),
        })
    st.dataframe(
        pd.DataFrame(pct_rows).style.format({
            "Margen Neto (USD)": "${:,.0f}",
            "ROI anual (%)":     "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


def render(params: dict, comp: "Comparador") -> None:
    page_header(
        "Simulación Monte Carlo",
        "Distribución estocástica del Margen Neto — Escenario C (Feedlot)",
    )
    render_content(params, comp)
