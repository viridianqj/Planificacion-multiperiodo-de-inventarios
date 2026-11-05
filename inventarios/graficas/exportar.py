"""Crea las gráficas fuera de la ventana (para guardarlas como PNG)."""

from matplotlib.figure import Figure

from inventarios.graficas.dibujo import dibujar_comparacion, dibujar_costos, dibujar_inventario, dibujar_plan

def figuras_para_exportar(res, datos, plan, tema):
    """Crea las 4 gráficas con el tema pedido. plan = (colchon, compras, guardado, costo)."""
    colchon, pc, pg, _ = plan
    pedidas = [
        ("costos_vs_colchon", (9, 5.2), lambda f: dibujar_costos(f, res, tema)),
        ("plan_de_compras", (11, 4.6), lambda f: dibujar_plan(f, datos, pc, pg, colchon, tema)),
        ("comparacion", (8, 5.2), lambda f: dibujar_comparacion(f, res, tema)),
        ("inventario", (8, 5.2), lambda f: dibujar_inventario(f, datos, pg, tema)),
    ]
    figuras = {}
    for nombre, tam, dibujar in pedidas:
        fig = Figure(figsize=tam, facecolor=tema["fondo"])
        fig.set_layout_engine("constrained")
        dibujar(fig)
        figuras[nombre] = fig
    return figuras
