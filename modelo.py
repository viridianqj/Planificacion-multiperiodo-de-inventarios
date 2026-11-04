"""
MODELO DE PROGRAMACIÓN LINEAL PARA INVENTARIOS
Calcula el plan de compras óptimo usando PuLP given un nivel de colchón de seguridad.
"""

import pulp
from config import productos, meses, costo_compra, costo_guardar, penalizacion, capacidad_bodega, demanda


def calcular_plan(colchon):
    """
    Calcula el plan de compras más barato usando Programación Lineal.

    Recibe el 'colchon' (por ejemplo 0.12 = guardar 12% extra de lo que
    se venderá el mes siguiente) y devuelve el plan de compras más barato.

    Returns:
        tuple: (plan_compras, plan_guardado, costo_total)
    """

    # Creamos el problema: queremos MINIMIZAR el costo total
    problema = pulp.LpProblem("Inventarios", pulp.LpMinimize)

    # Las tres cantidades que el programa va a decidir (nunca negativas):
    compras = {}  # unidades que compro del producto p en el mes m
    guardado = {}  # unidades que me sobran al final del mes
    faltante = {}  # unidades que me faltaron
    for p in productos:
        for m in meses:
            compras[p, m] = pulp.LpVariable(f"compra_{p}_{m}", lowBound=0)
            guardado[p, m] = pulp.LpVariable(f"guardado_{p}_{m}", lowBound=0)
            faltante[p, m] = pulp.LpVariable(f"faltante_{p}_{m}", lowBound=0)

    # ---- LO QUE QUEREMOS MINIMIZAR: el costo total ----
    # Un faltante cuesta (compra + penalización) porque hay que comprar
    # esa unidad de urgencia y además pagar la penalización.
    costo_total = 0
    for p in productos:
        for m in meses:
            costo_total += costo_compra[p] * compras[p, m]
            costo_total += costo_guardar[p] * guardado[p, m]
            costo_total += (costo_compra[p] + penalizacion[p]) * faltante[p, m]
    problema += costo_total

    # ---- REGLA 1: la ecuación de balance (como una cuenta de ahorros) ----
    #   guardado al cierre = lo que tenía + lo que compré
    #                        - lo que pidieron + lo que faltó
    for p in productos:
        for m in meses:
            if m == 1:
                lo_que_tenia = 0  # al inicio no hay inventario
            else:
                lo_que_tenia = guardado[p, m - 1]  # lo que sobró el mes anterior
            pedido = demanda[p][m - 1]
            problema += guardado[p, m] == lo_que_tenia + compras[p, m] - pedido + faltante[p, m]

    # ---- REGLA 2: el colchón de seguridad ----
    # (en el mes 3 no hace falta: ya no hay mes siguiente)
    for p in productos:
        for m in [1, 2]:
            demanda_mes_siguiente = demanda[p][m]
            problema += guardado[p, m] >= colchon * demanda_mes_siguiente

    # ---- REGLA 3: la bodega tiene límite ----
    for m in meses:
        total_guardado = 0
        for p in productos:
            total_guardado += guardado[p, m]
        problema += total_guardado <= capacidad_bodega

    # Le pedimos al solver que encuentre la mejor respuesta
    problema.solve(pulp.PULP_CBC_CMD(msg=0))

    # Guardamos los resultados en tablas
    plan_compras = {}
    plan_guardado = {}
    for p in productos:
        plan_compras[p] = [round(compras[p, m].value()) for m in meses]
        plan_guardado[p] = [round(guardado[p, m].value()) for m in meses]

    return plan_compras, plan_guardado, pulp.value(problema.objective)