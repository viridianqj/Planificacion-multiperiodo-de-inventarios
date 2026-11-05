"""PARTE 2: simulación de la demanda al azar (método de Monte Carlo)."""

import random

from inventarios.config import N_SIMULACIONES, VARIACION

def simular_un_escenario(politica, colchon, datos, variacion=VARIACION):
    """
    Simula los 3 meses UNA vez, con demanda al azar entre -variación y +variación.
    politica = "rigida" -> compra siempre exactamente lo esperado (la forma actual)
    politica = "optimizada" -> compra lo necesario para tener el colchón
    Devuelve (costo de guardar, costo de faltantes).
    """
    costo_de_guardar = 0
    costo_de_faltantes = 0
    ultimo_mes = datos.meses[-1]

    for p in datos.productos:
        sobrante = 0   # lo que tengo en bodega al empezar el mes
        for m in datos.meses:
            esperado = datos.demanda[p][m - 1]

            # La demanda REAL: cambia al azar hacia arriba o hacia abajo
            cambio = random.uniform(-variacion, variacion)
            real = esperado * (1 + cambio)

            # ¿Cuánto compro este mes?
            if politica == "rigida":
                compro = esperado   # siempre lo esperado
            else:
                if m < ultimo_mes:
                    quiero_al_cierre = colchon * datos.demanda[p][m]  # colchón
                else:
                    quiero_al_cierre = 0
                # compro lo que falta para cubrir lo esperado + el colchón,
                # descontando lo que ya tengo
                compro = max(esperado + quiero_al_cierre - sobrante, 0)

            tengo = sobrante + compro

            if tengo >= real:
                sobrante = tengo - real   # me sobró producto
                faltante = 0
            else:
                sobrante = 0
                faltante = real - tengo   # me faltó producto

            costo_de_guardar += datos.costo_guardar[p] * sobrante
            costo_de_faltantes += datos.penalizacion[p] * faltante

    return costo_de_guardar, costo_de_faltantes


def promedio_de_costos(politica, colchon, datos, n_sim=N_SIMULACIONES, variacion=VARIACION):
    """Repite la simulación muchas veces y devuelve el promedio."""
    suma_guardar = 0
    suma_faltantes = 0
    for _ in range(n_sim):
        guardar, faltantes = simular_un_escenario(politica, colchon, datos, variacion)
        suma_guardar += guardar
        suma_faltantes += faltantes
    return suma_guardar / n_sim, suma_faltantes / n_sim
