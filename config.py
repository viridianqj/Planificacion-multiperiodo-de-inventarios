"""
CONFIGURACIÓN DEL PROBLEMA DE INVENTARIO MULTIPERIODO
Datos y parámetros del ejercicio de planificación de inventarios.
"""

from dataclasses import dataclass


@dataclass
class Datos:
    productos: list
    meses: list
    demanda: dict          # unidades que se esperan vender cada mes
    costo_compra: dict     # USD por unidad comprada
    costo_guardar: dict    # USD por guardar 1 unidad 1 mes
    penalizacion: dict     # USD extra por cada unidad que falta
    capacidad_bodega: float  # máximo de unidades guardadas por mes (todos los productos)

    def copia(self):
        return copy.deepcopy(self)


DATOS_ENUNCIADO = Datos(
    productos=["p1", "p2", "p3", "p4"],
    meses=[1, 2, 3],
    demanda={
        "p1": [200, 300, 250],
        "p2": [150, 200, 180],
        "p3": [400, 500, 450],
        "p4": [100, 120, 110],
    },
    costo_compra={"p1": 50, "p2": 80, "p3": 30, "p4": 100},
    costo_guardar={"p1": 5, "p2": 8, "p3": 3, "p4": 10},
    penalizacion={"p1": 25, "p2": 40, "p3": 15, "p4": 50},
    capacidad_bodega=800,
)

# Variables de nivel de módulo para compatibilidad con imports directos
productos = ["p1", "p2", "p3", "p4"]
meses = [1, 2, 3]
costo_compra = {"p1": 50, "p2": 80, "p3": 30, "p4": 100}
costo_guardar = {"p1": 5, "p2": 8, "p3": 3, "p4": 10}
penalizacion = {"p1": 25, "p2": 40, "p3": 15, "p4": 50}
capacidad_bodega = 800
demanda = {
    "p1": [200, 300, 250],
    "p2": [150, 200, 180],
    "p3": [400, 500, 450],
    "p4": [100, 120, 110],
}


# Valores por defecto del análisis
N_SIMULACIONES = 5000     # meses simulados por cada colchón
VARIACION = 0.20          # la demanda real cambia hasta ±20%
COLCHON_MAX = 0.30        # se prueban colchones de 0% hasta 30%
PASO_COLCHON = 0.02       # ... de 2% en 2%
SEMILLA = 2026            # para que siempre salgan los mismos números


def usd(valor):
    return f"${valor:,.0f}"