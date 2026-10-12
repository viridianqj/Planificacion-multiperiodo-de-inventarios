"""
INVENTARIOS PARA 4 PRODUCTOS DURANTE 3 MESES 

Idea: cada mes hay que decidir cuántas unidades comprar de cada producto.
  - Si compras de menos  -> te quedas sin producto y pagas una penalización.
  - Si compras de más    -> te sobra y pagas por guardarlo.

El programa hace dos cosas:
  PARTE 1: usa PuLP para calcular el plan de compras más barato.
  PARTE 2: prueba muchos "colchones" de seguridad y escoge el mejor,
           simulando miles de meses con demanda al azar (±20%).

Para instalar PuLP:  pip install pulp
"""

import random
import pulp

# =====================================================================
# 0. LOS DATOS DEL PROBLEMA
# =====================================================================

productos = ["p1", "p2", "p3", "p4"]
meses = [1, 2, 3]

# Cuántas unidades se espera vender cada mes de cada producto
demanda = {
    "p1": [200, 300, 250],
    "p2": [150, 200, 180],
    "p3": [400, 500, 450],
    "p4": [100, 120, 110],
}

# Costos en dólares por unidad
costo_compra = {"p1": 50, "p2": 80, "p3": 30, "p4": 100}   # lo que cuesta comprar
costo_guardar = {"p1": 5, "p2": 8, "p3": 3, "p4": 10}      # guardar 1 unidad 1 mes
penalizacion = {"p1": 25, "p2": 40, "p3": 15, "p4": 50}    # extra si falta 1 unidad

capacidad_bodega = 800   # máximo de unidades guardadas por mes (todos los productos)


# =====================================================================
# PARTE 1: EL PLAN DE COMPRAS CON PuLP
# =====================================================================
# Recibe el "colchon" (por ejemplo 0.12 = guardar 12% extra de lo que
# se venderá el mes siguiente) y devuelve el plan de compras más barato.

def calcular_plan(colchon):

    # Creamos el problema: queremos MINIMIZAR el costo total
    problema = pulp.LpProblem("Inventarios", pulp.LpMinimize)

    # Las tres cantidades que el programa va a decidir (nunca negativas):
    compras = {} #  unidades que compro del producto p en el mes m
    guardado = {} # unidades que me sobran al final del mes
    faltante = {} # unidades que me faltaron
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


# =====================================================================
# PARTE 2: PROBAR COLCHONES CON MUCHOS MESES SIMULADOS
# =====================================================================

random.seed(2026)   # para que siempre salgan los mismos números
CANTIDAD_SIMULACIONES = 5000


def simular_un_escenario(politica, colchon):
    """
    Simula los 3 meses UNA vez, con demanda al azar entre -20% y +20%.
    politica = "rigida" -> compra siempre exactamente lo esperado (la forma actual)
    politica = "optimizada" -> compra lo necesario para tener el colchón
    Devuelve (costo de guardar, costo de faltantes).
    """
    costo_de_guardar = 0
    costo_de_faltantes = 0

    for p in productos:
        sobrante = 0   # lo que tengo en bodega al empezar el mes
        for m in meses:
            esperado = demanda[p][m - 1]

            # La demanda REAL: cambia al azar hasta 20% hacia arriba o abajo
            variacion = random.uniform(-0.20, 0.20)
            real = esperado * (1 + variacion)

            # ¿Cuánto compro este mes?
            if politica == "rigida":
                compro = esperado   # siempre lo esperado
            else:
                if m < 3:
                    quiero_al_cierre = colchon * demanda[p][m]  # colchón
                else:
                    quiero_al_cierre = 0
                # compro lo que falta para cubrir lo esperado + el colchón,
                # descontando lo que ya tengo
                compro = max(esperado + quiero_al_cierre - sobrante, 0)

            tengo = sobrante + compro

            if tengo >= real:
                sobrante = tengo - real # me sobró producto
                faltante = 0
            else:
                sobrante = 0
                faltante = real - tengo  # me faltó producto

            costo_de_guardar += costo_guardar[p] * sobrante
            costo_de_faltantes += penalizacion[p] * faltante

    return costo_de_guardar, costo_de_faltantes


def promedio_de_costos(politica, colchon):
    """Repite la simulación muchas veces y devuelve el promedio."""
    suma_guardar = 0
    suma_faltantes = 0
    for i in range(CANTIDAD_SIMULACIONES):
        guardar, faltantes = simular_un_escenario(politica, colchon)
        suma_guardar += guardar
        suma_faltantes += faltantes
    return suma_guardar / CANTIDAD_SIMULACIONES, suma_faltantes / CANTIDAD_SIMULACIONES


# =====================================================================
# PROGRAMA PRINCIPAL
# =====================================================================

if __name__ == "__main__":

    # ---- Paso A: probar colchones de 0% a 30% ----
    print("PASO A: probando colchones (costo promedio de guardar + faltantes)")
    print("-" * 55)

    mejor_colchon = None
    menor_costo = None

    colchon = 0.0
    while colchon <= 0.301:
        guardar, faltantes = promedio_de_costos("optimizada", colchon)
        total = guardar + faltantes
        print(f"Colchón {colchon*100:4.0f}%  ->  ${total:,.0f}")

        if menor_costo is None or total < menor_costo:
            menor_costo = total
            mejor_colchon = colchon
        colchon += 0.02

    print(f"\nEl mejor colchón es {mejor_colchon*100:.0f}% (costo ${menor_costo:,.0f})\n")

    # ---- Paso B: el plan de compras con ese colchón ----
    plan_compras, plan_guardado, costo = calcular_plan(round(mejor_colchon, 2))

    print("PASO B: plan de compras (unidades por mes: mes1, mes2, mes3)")
    print("-" * 55)
    for p in productos:
        print(f"{p}: comprar {plan_compras[p]}   guardar al cierre {plan_guardado[p]}")
    print(f"Costo del plan sin variación de demanda: ${costo:,.0f}\n")

    # ---- Paso C: comparar contra la forma actual ----
    print("PASO C: comparación contra la forma actual (demanda ±20%)")
    print("-" * 55)
    g_r, f_r = promedio_de_costos("rigida", 0)
    g_o, f_o = promedio_de_costos("optimizada", mejor_colchon)

    print(f"Forma actual : guardar ${g_r:,.0f} + faltantes ${f_r:,.0f} = ${g_r+f_r:,.0f}")
    print(f"Optimizada   : guardar ${g_o:,.0f} + faltantes ${f_o:,.0f} = ${g_o+f_o:,.0f}")
    ahorro = (1 - (g_o + f_o) / (g_r + f_r)) * 100
    print(f"Reducción de sobrecostos: {ahorro:.1f}%")
