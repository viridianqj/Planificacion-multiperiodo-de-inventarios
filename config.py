"""
CONFIGURACIÓN DEL PROBLEMA DE INVENTARIO MULTIPERIODO
Datos y parámetros del ejercicio de planificación de inventarios.
"""

# Productos y períodos
productos = ["p1", "p2", "p3", "p4"]
meses = [1, 2, 3]

# Demanda esperada por producto y mes
demanda = {
    "p1": [200, 300, 250],
    "p2": [150, 200, 180],
    "p3": [400, 500, 450],
    "p4": [100, 120, 110],
}

# Costos en dólares por unidad
costo_compra = {"p1": 50, "p2": 80, "p3": 30, "p4": 100}   # costo de compra
costo_guardar = {"p1": 5, "p2": 8, "p3": 3, "p4": 10}      # costo de guardar 1 unidad 1 mes
penalizacion = {"p1": 25, "p2": 40, "p3": 15, "p4": 50}    # penalización por falta

# Capacidad de la bodega (máximo de unidades guardadas por mes, todos los productos)
capacidad_bodega = 800