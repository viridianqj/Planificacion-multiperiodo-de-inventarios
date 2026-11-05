"""PARTE 1: el plan de compras más barato, con programación lineal (PuLP)."""

import pulp

def crear_variable(problema, nombre):
    """
    Crea una variable que nunca puede ser negativa.
    PuLP 4.x las crea desde el problema (problema.add_variable);
    PuLP 3.x y anteriores usan pulp.LpVariable. Así el código sirve con las dos.
    """
    if hasattr(problema, "add_variable"):
        return problema.add_variable(nombre, lowBound=0)
    return pulp.LpVariable(nombre, lowBound=0)


def crear_solver():
    """
    El solver es el programa que resuelve las ecuaciones.
    PuLP 3.x y anteriores traen CBC incluido; PuLP 4.x usa HiGHS (pip install highspy).
    """
    if hasattr(pulp, "PULP_CBC_CMD"):
        return pulp.PULP_CBC_CMD(msg=0)
    return pulp.HiGHS(msg=False)


def calcular_plan(colchon, datos):
    """
    Recibe el "colchon" (por ejemplo 0.12 = guardar 12% extra de lo que
    se venderá el mes siguiente) y devuelve el plan de compras más barato.
    """
    productos, meses = datos.productos, datos.meses

    # Creamos el problema: queremos MINIMIZAR el costo total
    problema = pulp.LpProblem("Inventarios", pulp.LpMinimize)

    # Las tres cantidades que el programa va a decidir (nunca negativas):
    compras = {}     # unidades que compro del producto p en el mes m
    guardado = {}    # unidades que me sobran al final del mes
    faltante = {}    # unidades que me faltaron
    for p in productos:
        for m in meses:
            compras[p, m] = crear_variable(problema, f"compra_{p}_{m}")
            guardado[p, m] = crear_variable(problema, f"guardado_{p}_{m}")
            faltante[p, m] = crear_variable(problema, f"faltante_{p}_{m}")

    # ---- LO QUE QUEREMOS MINIMIZAR: el costo total ----
    # Un faltante cuesta (compra + penalización) porque hay que comprar
    # esa unidad de urgencia y además pagar la penalización.
    costo_total = 0
    for p in productos:
        for m in meses:
            costo_total += datos.costo_compra[p] * compras[p, m]
            costo_total += datos.costo_guardar[p] * guardado[p, m]
            costo_total += (datos.costo_compra[p] + datos.penalizacion[p]) * faltante[p, m]
    problema += costo_total

    # ---- REGLA 1: la ecuación de balance (como una cuenta de ahorros) ----
    #   guardado al cierre = lo que tenía + lo que compré
    #                        - lo que pidieron + lo que faltó
    for p in productos:
        for m in meses:
            if m == meses[0]:
                lo_que_tenia = 0                     # al inicio no hay inventario
            else:
                lo_que_tenia = guardado[p, m - 1]    # lo que sobró el mes anterior
            pedido = datos.demanda[p][m - 1]
            problema += guardado[p, m] == lo_que_tenia + compras[p, m] - pedido + faltante[p, m]

    # ---- REGLA 2: el colchón de seguridad ----
    # (en el último mes no hace falta: ya no hay mes siguiente)
    for p in productos:
        for m in meses[:-1]:
            demanda_mes_siguiente = datos.demanda[p][m]
            problema += guardado[p, m] >= colchon * demanda_mes_siguiente

    # ---- REGLA 3: la bodega tiene límite ----
    for m in meses:
        total_guardado = 0
        for p in productos:
            total_guardado += guardado[p, m]
        problema += total_guardado <= datos.capacidad_bodega

    # Le pedimos al solver que encuentre la mejor respuesta
    try:
        resultado = problema.solve(crear_solver())
    except pulp.PulpSolverError as error:
        raise RuntimeError("PuLP no encontró un solver. Instálalo con:  pip install highspy") from error

    # PuLP 4.x devuelve un objeto con .status; PuLP 3.x devuelve el número directamente (1 = óptimo)
    estado = getattr(resultado, "status", resultado)
    if estado != 1:
        raise ValueError(
            f"No hay plan posible con colchón {colchon*100:.0f}% y bodega de "
            f"{datos.capacidad_bodega:,.0f} unidades. Sube la capacidad o baja el colchón."
        )

    # Guardamos los resultados en tablas
    plan_compras = {}
    plan_guardado = {}
    for p in productos:
        plan_compras[p] = [round(compras[p, m].value()) for m in meses]
        plan_guardado[p] = [round(guardado[p, m].value()) for m in meses]

    return plan_compras, plan_guardado, pulp.value(problema.objective)
