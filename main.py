"""
PROGRAMA PRINCIPAL DE PLANIFICACIÓN MULTIPERIODO DE INVENTARIOS
Orquesta el cálculo del plan óptimo y la simulación de colchones de seguridad.
"""

import sys
import os

# Añadir el directorio actual al path para importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import productos, meses, costo_compra, costo_guardar, penalizacion, capacidad_bodega, demanda
from modelo import calcular_plan
from simulacion import promedio_de_costos


def main():
    """Función principal que ejecuta los tres pasos del análisis."""
    
    print("=" * 60)
    print("PLANIFICACIÓN MULTIPERIODO DE INVENTARIOS")
    print("=" * 60)
    
    # ---- Paso A: probar colchones de 0% a 30% ----
    print("\nPASO A: probando colchones (costo promedio de guardar + faltantes)")
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
    print("PASO B: plan de compras (unidades por mes: mes1, mes2, mes3)")
    print("-" * 55)
    plan_compras, plan_guardado, costo = calcular_plan(round(mejor_colchon, 2))
    
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


if __name__ == "__main__":
    main()