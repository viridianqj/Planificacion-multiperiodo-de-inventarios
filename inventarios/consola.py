"""Modo texto: imprime los pasos A, B y C y guarda la gráfica principal en `salidas/`."""
from pathlib import Path

from matplotlib.figure import Figure

from inventarios.analisis import analizar
from inventarios.config import DATOS_ENUNCIADO, N_SIMULACIONES, VARIACION
from inventarios.graficas.dibujo import dibujar_costos
from inventarios.graficas.temas import TEMA_CLARO
from inventarios.informe import construir_informe

RAIZ = Path(__file__).resolve().parents[1]


def modo_consola():
    datos = DATOS_ENUNCIADO.copia()
    print("Calculando... (puede tardar unos segundos)\n")
    try:
        res = analizar(datos)
    except (RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        return
    for _, linea in construir_informe(res, datos, N_SIMULACIONES, VARIACION):
        print(linea)
    fig = Figure(figsize=(9, 5.2))
    fig.set_layout_engine("constrained")
    dibujar_costos(fig, res, TEMA_CLARO)
    carpeta = RAIZ / "salidas"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / "grafica_costos.png"
    fig.savefig(ruta, dpi=170, facecolor=fig.get_facecolor())
    print(f"\nGráfica guardada en: {ruta}")
