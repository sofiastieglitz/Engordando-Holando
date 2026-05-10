from dataclasses import dataclass


@dataclass
class CostosVariables:
    compra: float = 0.0
    alimentacion: float = 0.0
    sanidad: float = 0.0
    flete_entrada: float = 0.0
    flete_salida: float = 0.0
    amortizacion: float = 0.0
    mano_obra: float = 0.0
    otros: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.compra + self.alimentacion + self.sanidad
            + self.flete_entrada + self.flete_salida
            + self.amortizacion + self.mano_obra + self.otros
        )

    def as_dict(self) -> dict:
        return {
            "Compra": self.compra,
            "Alimentación": self.alimentacion,
            "Sanidad": self.sanidad,
            "Flete entrada": self.flete_entrada,
            "Flete salida": self.flete_salida,
            "Amortización": self.amortizacion,
            "Mano de obra": self.mano_obra,
            "Otros": self.otros,
        }


@dataclass
class ResultadoEscenario:
    nombre: str
    n_cabezas: int          # animales que entran al sistema
    n_vendidos: int         # animales que llegan a venta (tras mortalidad)
    mortalidad: float       # tasa decimal (ej. 0.03 = 3 %)
    ca: float               # conversión alimenticia kg MS / kg PV (0 si no aplica)
    dias: int
    peso_entrada: float
    peso_salida: float
    precio_venta_usd_kg: float
    costos: CostosVariables
    costo_fijo: float
    tasa_interes_anual: float   # decimal

    # ── Ingresos ─────────────────────────────────────────────────────────────

    @property
    def ingreso_bruto(self) -> float:
        return self.n_vendidos * self.peso_salida * self.precio_venta_usd_kg

    # ── Costos ───────────────────────────────────────────────────────────────

    @property
    def costo_variable_total(self) -> float:
        return self.costos.total

    @property
    def perdida_mortalidad(self) -> float:
        """Costo atribuible a los animales que no llegan a venta."""
        n_muertos = self.n_cabezas - self.n_vendidos
        if self.n_cabezas == 0 or n_muertos <= 0:
            return 0.0
        # Compra y alimentación se incurren en todos; flete salida solo en vendidos
        base = self.costos.compra + self.costos.alimentacion + self.costos.sanidad
        return base * (n_muertos / self.n_cabezas)

    # ── Márgenes ─────────────────────────────────────────────────────────────

    @property
    def margen_bruto(self) -> float:
        return self.ingreso_bruto - self.costo_variable_total

    @property
    def margen_neto(self) -> float:
        return self.margen_bruto - self.costo_fijo

    # ── Productividad ─────────────────────────────────────────────────────────

    @property
    def kg_ganados_total(self) -> float:
        """Sólo los animales vendidos aportan kg comercializables."""
        return float(max(self.n_vendidos * (self.peso_salida - self.peso_entrada), 0.0))

    @property
    def gdp_efectiva(self) -> float:
        return (self.peso_salida - self.peso_entrada) / max(self.dias, 1)

    @property
    def costo_alim_dia_derivado(self) -> float:
        """USD/cab/día de alimentación real (total / n_cabezas / días)."""
        return self.costos.alimentacion / max(self.n_cabezas * self.dias, 1)

    # ── Capital inmovilizado ──────────────────────────────────────────────────

    @property
    def capital_inmovilizado(self) -> float:
        """Promedio del capital comprometido: (inversión inicial + total) / 2."""
        return (self.costos.compra + self.costo_variable_total) / 2

    @property
    def costo_oportunidad(self) -> float:
        """Costo de oportunidad del capital en el período."""
        return self.capital_inmovilizado * self.tasa_interes_anual * (self.dias / 365)

    # ── ROI ──────────────────────────────────────────────────────────────────

    @property
    def roi(self) -> float:
        cap = self.capital_inmovilizado
        return (self.margen_neto / cap * 100) if cap > 0 else 0.0

    @property
    def roi_anual(self) -> float:
        return (self.roi * 365 / self.dias) if self.dias > 0 else 0.0

    # ── Ratios por unidad ────────────────────────────────────────────────────

    @property
    def margen_por_cab(self) -> float:
        return self.margen_neto / self.n_cabezas if self.n_cabezas > 0 else 0.0

    @property
    def margen_por_kg_ganado(self) -> float:
        kg = self.kg_ganados_total
        return self.margen_neto / kg if kg > 0.0 else 0.0

    @property
    def costo_por_kg_ganado(self) -> float:
        kg = self.kg_ganados_total
        return self.costo_variable_total / kg if kg > 0.0 else 0.0

    # ── Serialización ────────────────────────────────────────────────────────

    def summary_dict(self) -> dict:
        return {
            "Escenario": self.nombre,
            "Días": self.dias,
            "N° entrados": self.n_cabezas,
            "N° vendidos": self.n_vendidos,
            "Mortalidad (%)": round(self.mortalidad * 100, 1),
            "Peso entrada (kg)": self.peso_entrada,
            "Peso salida (kg)": self.peso_salida,
            "GDP (kg/día)": round(self.gdp_efectiva, 3),
            "CA (kg MS/kg PV)": round(self.ca, 2),
            "Alim. (USD/cab/día)": round(self.costo_alim_dia_derivado, 3),
            "Precio venta (USD/kg)": self.precio_venta_usd_kg,
            "Ingreso bruto (USD)": round(self.ingreso_bruto, 0),
            "Costo variable (USD)": round(self.costo_variable_total, 0),
            "Pérdida mortalidad (USD)": round(self.perdida_mortalidad, 0),
            "Margen bruto (USD)": round(self.margen_bruto, 0),
            "Margen neto (USD)": round(self.margen_neto, 0),
            "ROI (%)": round(self.roi, 1),
            "ROI anual (%)": round(self.roi_anual, 1),
            "Capital inmovilizado (USD)": round(self.capital_inmovilizado, 0),
            "Costo oportunidad (USD)": round(self.costo_oportunidad, 0),
            "Margen/cabeza (USD)": round(self.margen_por_cab, 0),
            "Margen/kg ganado (USD)": round(self.margen_por_kg_ganado, 2),
            "Costo/kg ganado (USD)": round(self.costo_por_kg_ganado, 2),
        }
