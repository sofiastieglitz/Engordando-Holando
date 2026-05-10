import pandas as pd

from modules.economics.models import ResultadoEscenario
from modules.economics.scenarios import calcular_destete, calcular_recria, calcular_terminado


class Comparador:
    def __init__(self, params: dict) -> None:
        self.destete = calcular_destete(params)
        self.recria = calcular_recria(params)
        self.terminado = calcular_terminado(params)
        self._todos: list[ResultadoEscenario] = [self.destete, self.recria, self.terminado]

    # ── Selección ─────────────────────────────────────────────────────────────

    def mejor_escenario(self) -> ResultadoEscenario:
        return max(self._todos, key=lambda e: e.margen_neto)

    def mejor_roi_anual(self) -> ResultadoEscenario:
        return max(self._todos, key=lambda e: e.roi_anual)

    # ── Tablas ────────────────────────────────────────────────────────────────

    def tabla_resumen(self) -> pd.DataFrame:
        return pd.DataFrame([e.summary_dict() for e in self._todos])

    def tabla_comparacion(self) -> pd.DataFrame:
        """Tabla pivoteada: indicadores como filas, escenarios como columnas."""
        df = self.tabla_resumen().set_index("Escenario").T
        df.index.name = "Indicador"
        return df.reset_index()

    def tabla_costos(self) -> pd.DataFrame:
        rows = []
        for e in self._todos:
            d = {"Escenario": e.nombre, **e.costos.as_dict(), "TOTAL": e.costo_variable_total}
            rows.append(d)
        return pd.DataFrame(rows)

    def tabla_costos_larga(self) -> pd.DataFrame:
        rows = []
        for e in self._todos:
            for cat, val in e.costos.as_dict().items():
                rows.append({"Escenario": e.nombre, "Categoría": cat, "USD": val})
        return pd.DataFrame(rows)

    def tabla_margenes(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "Escenario": e.nombre,
                "Ingreso bruto (USD)": round(e.ingreso_bruto, 0),
                "Costo variable (USD)": round(e.costo_variable_total, 0),
                "Margen bruto (USD)": round(e.margen_bruto, 0),
                "Margen neto (USD)": round(e.margen_neto, 0),
                "ROI (%)": round(e.roi, 1),
                "ROI anual (%)": round(e.roi_anual, 1),
                "Capital inmovilizado (USD)": round(e.capital_inmovilizado, 0),
                "Margen/cab (USD)": round(e.margen_por_cab, 0),
            }
            for e in self._todos
        ])
