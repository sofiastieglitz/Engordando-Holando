from modules.economics.models import CostosVariables, ResultadoEscenario


def _n_vendidos(n: int, mortalidad: float) -> int:
    return max(int(n * (1 - mortalidad)), 0)


def calcular_destete(p: dict) -> ResultadoEscenario:
    """Escenario A: venta del ternero al destete sin engorde adicional."""
    an = p["animal_params"]
    co = p["commercial_params"]
    fe = p["feed_params"]

    n    = an["n_terneros"]
    mort = an["A"]["mortalidad"]   # decimal
    nv   = _n_vendidos(n, mort)
    dias = an["A"]["dias"]

    costos = CostosVariables(
        compra       = n  * an["peso_inicial"]       * co["precio_compra"],
        # A (Cría) ya no expone costo_alim_dia: el modelo bioeconómico
        # vive en las page_*. Mantengo 0 para no romper Comparador legacy.
        alimentacion = 0.0,
        sanidad      = n  * an["A"]["sanidad"],
        flete_entrada= 0.0,
        flete_salida = nv * co["A"]["flete_salida"],
        amortizacion = 0.0,
        mano_obra    = an["A"]["mo_mes"] / 30.0       * dias,
        otros        = n  * co["A"]["otros"],
    )
    return ResultadoEscenario(
        nombre             = "A — Venta al destete",
        n_cabezas          = n,
        n_vendidos         = nv,
        mortalidad         = mort,
        ca                 = 0.0,
        dias               = dias,
        peso_entrada       = an["peso_inicial"],
        peso_salida        = an["peso_inicial"],
        precio_venta_usd_kg= co["A"]["precio_venta"],
        costos             = costos,
        costo_fijo         = 0.0,
        tasa_interes_anual = co["tasa_interes"],
    )


def calcular_recria(p: dict) -> ResultadoEscenario:
    """Escenario B: recría desde destete hasta peso de venta intermedio."""
    an = p["animal_params"]
    co = p["commercial_params"]
    fe = p["feed_params"]

    n    = an["n_terneros"]
    mort = an["B"]["mortalidad"]
    nv   = _n_vendidos(n, mort)
    gdp  = max(an["B"]["gdp"], 0.01)
    aumento = max(an["B"]["peso_salida"] - an["peso_inicial"], 1.0)
    dias = max(int(aumento / gdp), 1)

    ca            = an["B"]["ca"]
    costo_alim_dia = ca * gdp * fe["B"]["precio_alimento"]

    costos = CostosVariables(
        compra       = n  * an["peso_inicial"]   * co["precio_compra"],
        alimentacion = n  * costo_alim_dia        * dias,
        sanidad      = n  * an["B"]["sanidad"],
        flete_entrada= n  * co["B"]["flete_entrada"],
        flete_salida = nv * co["B"]["flete_salida"],
        amortizacion = 0.0,
        mano_obra    = an["B"]["mo_mes"] / 30.0   * dias,
        otros        = n  * co["B"]["otros"],
    )
    return ResultadoEscenario(
        nombre             = "B — Venta recriado",
        n_cabezas          = n,
        n_vendidos         = nv,
        mortalidad         = mort,
        ca                 = ca,
        dias               = dias,
        peso_entrada       = an["peso_inicial"],
        peso_salida        = an["B"]["peso_salida"],
        precio_venta_usd_kg= co["B"]["precio_venta"],
        costos             = costos,
        costo_fijo         = 0.0,
        tasa_interes_anual = co["tasa_interes"],
    )


def calcular_terminado(p: dict) -> ResultadoEscenario:
    """Escenario C: ciclo completo hasta peso de faena en feedlot."""
    an    = p["animal_params"]
    co    = p["commercial_params"]
    fe    = p["feed_params"]
    infra = p["infra_params"]

    n    = an["n_terneros"]
    mort = an["C"]["mortalidad"]
    nv   = _n_vendidos(n, mort)
    gdp  = max(an["C"]["gdp"], 0.01)
    aumento = max(an["C"]["peso_final"] - an["peso_inicial"], 1.0)
    dias = max(int(aumento / gdp), 1)

    ca            = an["C"]["ca"]
    costo_alim_dia = ca * gdp * fe["C"]["precio_alimento"]

    costos = CostosVariables(
        compra       = n  * an["peso_inicial"]    * co["precio_compra"],
        alimentacion = n  * costo_alim_dia          * dias,
        sanidad      = n  * an["C"]["sanidad"],
        flete_entrada= n  * co["C"]["flete_entrada"],
        flete_salida = nv * co["C"]["flete_salida"],
        amortizacion = n  * infra["C"]["amortizacion"],
        mano_obra    = an["C"]["mo_mes"] / 30.0     * dias,
        otros        = n  * co["C"]["otros"],
    )
    return ResultadoEscenario(
        nombre             = "C — Venta terminado",
        n_cabezas          = n,
        n_vendidos         = nv,
        mortalidad         = mort,
        ca                 = ca,
        dias               = dias,
        peso_entrada       = an["peso_inicial"],
        peso_salida        = an["C"]["peso_final"],
        precio_venta_usd_kg= co["C"]["precio_venta"],
        costos             = costos,
        costo_fijo         = 0.0,
        tasa_interes_anual = co["tasa_interes"],
    )
