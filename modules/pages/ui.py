"""Shared UI primitives for all page modules."""
from __future__ import annotations
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from modules.economics.models import ResultadoEscenario

_SCENARIO_META: dict[str, tuple[str, str, str, str]] = {
    "A — Venta al destete": ("amber", "bd-amber", "🟡", "Venta al destete"),
    "B — Venta recriado":   ("blue",  "bd-blue",  "🔵", "Venta recriado"),
    "C — Venta terminado":  ("green", "bd-green", "🟢", "Venta terminado"),
}


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<p class="ap-page-title">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="ap-page-sub">{subtitle}</p>', unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<p class="ap-section">{label}</p>', unsafe_allow_html=True)


def placeholder(name: str, description: str = "") -> None:
    desc = description or "Este módulo está en desarrollo y estará disponible próximamente."
    st.markdown(
        f"""<div class="ap-ph">
            <div class="ap-ph-icon">🚧</div>
            <div class="ap-ph-title">{name}</div>
            <div class="ap-ph-text">{desc}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def kpi_card(
    col,
    icon: str,
    value: str,
    label: str,
    accent: str = "blue",
    delta: str | None = None,
    delta_type: str = "off",
    badge: str | None = None,
    badge_class: str = "bd-blue",
    sub_pairs: list[tuple[str, str]] | None = None,
    value_size: str = "large",
) -> None:
    badge_html = f'<div class="kpi-badge {badge_class}">{badge}</div>' if badge else ""
    val_cls = "kpi-value" if value_size == "large" else "kpi-value-md"
    delta_html = f'<div class="kpi-delta-{delta_type}">{delta}</div>' if delta else ""
    sub_html = ""
    if sub_pairs:
        items = "".join(
            f'<div><div class="kpi-sub-v">{v}</div>'
            f'<div class="kpi-sub-l">{lbl}</div></div>'
            for v, lbl in sub_pairs
        )
        sub_html = f'<div class="kpi-hr"></div><div class="kpi-sub">{items}</div>'
    col.markdown(
        f"""<div class="kpi-card ac-{accent}">
            {badge_html}
            <span class="kpi-icon">{icon}</span>
            <div class="{val_cls}">{value}</div>
            <div class="kpi-label">{label}</div>
            {delta_html}
            {sub_html}
        </div>""",
        unsafe_allow_html=True,
    )


def scenario_card(col, e: "ResultadoEscenario") -> None:
    accent, badge_cls, emoji, short = _SCENARIO_META.get(
        e.nombre, ("blue", "bd-blue", "•", e.nombre)
    )
    kpi_card(
        col=col, icon="💰",
        value=f"USD {e.margen_neto:,.0f}",
        label="Margen Neto",
        accent=accent,
        badge=f"{emoji} {short}",
        badge_class=badge_cls,
        sub_pairs=[
            (f"USD {e.margen_bruto:,.0f}", "Margen Bruto"),
            (f"{e.roi_anual:.1f}%",         "ROI Anual"),
            (f"USD {e.margen_por_cab:,.0f}", "Margen / cab"),
            (f"{e.dias}d",                   "Días ciclo"),
        ],
    )


def flujo_strip(e: "ResultadoEscenario") -> None:
    cap_rot = e.margen_neto / max(e.capital_inmovilizado, 1) * 100
    cards = [
        ("💵", f"USD {e.ingreso_bruto:,.0f}",         "Ingreso Bruto",        "flujo-pos"),
        None,
        ("💸", f"–USD {e.costo_variable_total:,.0f}", "Costos Variables",     "flujo-neg"),
        None,
        ("📊", f"USD {e.margen_bruto:,.0f}",           "Margen Bruto",         "flujo-neu"),
        None,
        ("🎯", f"USD {e.margen_neto:,.0f}",            "Margen Neto",          "flujo-neu"),
        None,
        ("🏦", f"USD {e.capital_inmovilizado:,.0f}",   "Capital Inmovilizado", ""),
        None,
        ("🔄", f"{cap_rot:.1f}%",                      "Retorno s/Capital",    "flujo-pos"),
    ]
    parts: list[str] = []
    for item in cards:
        if item is None:
            parts.append('<div class="flujo-arrow">›</div>')
        else:
            icon, val, lbl, cls = item
            parts.append(
                f'<div class="flujo-card">'
                f'<div class="flujo-icon">{icon}</div>'
                f'<div class="flujo-v {cls}">{val}</div>'
                f'<div class="flujo-l">{lbl}</div>'
                f'</div>'
            )
    st.markdown(
        f'<div class="flujo-wrap">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )
