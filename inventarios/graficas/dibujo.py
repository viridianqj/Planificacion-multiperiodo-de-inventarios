"""Funciones que dibujan cada gráfica sobre una Figure de matplotlib."""

import math

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from inventarios.utilidades import usd

def _estilo_ejes(ax, t):
    ax.set_facecolor(t["fondo"])
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(t["grid"])
    ax.tick_params(colors=t["texto2"], labelsize=9, length=3, color=t["grid"])
    ax.yaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)


def _relleno(t, i):
    """Cómo se rellena la barra número i (color en pantalla, trama en blanco y negro)."""
    if t["bn"]:
        return dict(facecolor=t["grises"][i % 4], hatch=t["tramas"][i % 4], edgecolor=t["texto"], linewidth=0.9)
    return dict(facecolor=t["serie"][i % len(t["serie"])], edgecolor=t["fondo"], linewidth=1.5)


def _estilo_demanda(t):
    if t["bn"]:
        return dict(facecolor="#ffffff", edgecolor=t["texto"], linewidth=1.0)
    return dict(facecolor=t["demanda"], edgecolor=t["fondo"], linewidth=1.5)


def _chip(t):
    return dict(boxstyle="round,pad=0.3", fc=t["fondo"], ec=t["grid"], lw=0.8)


def _titulo(ax, texto, t):
    ax.set_title(texto, loc="left", color=t["texto"], fontsize=13, fontweight="bold", pad=14)


def dibujar_vacio(fig, t, mensaje):
    fig.clear()
    fig.set_facecolor(t["fondo"])
    fig.text(0.5, 0.5, mensaje, ha="center", va="center", color=t["texto2"], fontsize=12)


def dibujar_costos(fig, res, t):
    """LA GRÁFICA QUE PIDE EL ENUNCIADO: costo de almacenamiento vs. faltantes."""
    fig.clear()
    fig.set_facecolor(t["fondo"])
    ax = fig.add_subplot(111)
    _estilo_ejes(ax, t)
    x = [c * 100 for c in res.colchones]

    ax.plot(x, res.costos_guardar, label="Almacenamiento", **t["lineas"]["guardar"])
    ax.plot(x, res.costos_faltantes, label="Faltantes", **t["lineas"]["faltantes"])
    ax.plot(x, res.costos_totales, label="Total", **t["lineas"]["total"])

    xm = res.mejor_colchon * 100
    ax.axvline(xm, color=t["texto2"], lw=1, ls=":", zorder=1)
    ax.scatter([xm], [res.menor_costo], s=120, color=t["texto"], edgecolor=t["fondo"],
               linewidth=2, zorder=6)
    ax.annotate(f"Mínimo: colchón {xm:.0f}%\n{usd(res.menor_costo)} por escenario",
                xy=(xm, res.menor_costo), xytext=(22, -52), textcoords="offset points",
                fontsize=9, color=t["texto"], bbox=_chip(t),
                arrowprops=dict(arrowstyle="-", color=t["texto2"], lw=1))

    _titulo(ax, "Almacenamiento vs. faltantes", t)
    ax.set_xlabel("Colchón de seguridad (% de la demanda esperada del mes siguiente)",
                  color=t["texto2"], fontsize=9.5)
    ax.set_ylabel("Costo promedio por escenario (USD)", color=t["texto2"], fontsize=9.5)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: usd(v)))
    if len(x) <= 16:
        ax.set_xticks(x)
    ax.set_ylim(0, max(res.costos_totales + res.costos_faltantes + res.costos_guardar) * 1.12)
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.01), ncol=3, frameon=False,
              labelcolor=t["texto2"], fontsize=9.5, handlelength=2.2)


def dibujar_comparacion(fig, res, t):
    """Forma actual vs. optimizada: barras apiladas (guardar + faltantes)."""
    fig.clear()
    fig.set_facecolor(t["fondo"])
    ax = fig.add_subplot(111)
    _estilo_ejes(ax, t)
    x = [0, 1]
    guardar = [res.rigida[0], res.optimizada[0]]
    faltan = [res.rigida[1], res.optimizada[1]]
    totales = [guardar[0] + faltan[0], guardar[1] + faltan[1]]
    ancho = 0.4
    ymax = max(totales) * 1.28 if max(totales) > 0 else 1

    ax.bar(x, guardar, ancho, label="Almacenamiento", **_relleno(t, 0))
    ax.bar(x, faltan, ancho, bottom=guardar, label="Faltantes", **_relleno(t, 1))
    for k in x:
        if guardar[k] > ymax * 0.08:
            ax.text(k, guardar[k] / 2, usd(guardar[k]), ha="center", va="center", fontsize=9,
                    color=t["texto"], bbox=_chip(t))
        if faltan[k] > ymax * 0.08:
            ax.text(k, guardar[k] + faltan[k] / 2, usd(faltan[k]), ha="center", va="center",
                    fontsize=9, color=t["texto"], bbox=_chip(t))
        ax.text(k, totales[k] + ymax * 0.015, usd(totales[k]), ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=t["texto"])

    ax.text(0.5, ymax * 0.93, f"Reducción de sobrecostos: {res.ahorro:.1f}%", ha="center", va="center",
            fontsize=12, fontweight="bold", color=t["texto"], bbox=_chip(t))
    ax.set_xticks(x)
    ax.set_xticklabels(["Forma actual\n(compra rígida)", f"Optimizada\n(colchón {res.mejor_colchon*100:.0f}%)"],
                       color=t["texto"], fontsize=10)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: usd(v)))
    ax.set_ylabel("Costo promedio por escenario (USD)", color=t["texto2"], fontsize=9.5)
    _titulo(ax, "Forma actual vs. plan optimizado", t)
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.01), ncol=2, frameon=False,
              labelcolor=t["texto2"], fontsize=9.5)


def dibujar_plan(fig, datos, plan_compras, plan_guardado, colchon, t):
    """Un mini-gráfico por producto: demanda, compra y lo que queda guardado."""
    fig.clear()
    fig.set_facecolor(t["fondo"])
    n = len(datos.productos)
    columnas = min(n, 4)
    filas = math.ceil(n / columnas)
    ejes = fig.subplots(filas, columnas, squeeze=False)
    x = list(range(len(datos.meses)))
    ancho = 0.36
    for i, p in enumerate(datos.productos):
        ax = ejes[i // columnas][i % columnas]
        _estilo_ejes(ax, t)
        dem, com, gua = datos.demanda[p], plan_compras[p], plan_guardado[p]
        ax.bar([k - ancho / 2 for k in x], dem, ancho, **_estilo_demanda(t))
        ax.bar([k + ancho / 2 for k in x], com, ancho, **_relleno(t, i))
        ax.plot(x, gua, color=t["texto"], lw=1.8, marker="o", ms=6,
                markeredgecolor=t["fondo"], markeredgewidth=1.2, zorder=5)
        for k, v in enumerate(com):
            ax.text(k + ancho / 2, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8, color=t["texto"])
        ax.set_title(p.upper(), loc="left", color=t["texto"], fontsize=11, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Mes {m}" for m in datos.meses], fontsize=8)
        ax.set_ylim(0, max(max(dem), max(com), max(gua), 1) * 1.2)
    for j in range(n, filas * columnas):
        ejes[j // columnas][j % columnas].set_visible(False)
    fig.suptitle(f"Plan de compras por producto (colchón {colchon*100:.0f}%)", x=0.01, ha="left",
                 color=t["texto"], fontsize=13, fontweight="bold")
    if t["bn"]:
        compra_key = Patch(facecolor=t["grises"][1], hatch=t["tramas"][0], edgecolor=t["texto"], label="Compra")
    else:
        compra_key = Patch(facecolor=t["serie"][0], label="Compra (cada producto tiene su color)")
    asas = [Patch(label="Demanda esperada", **_estilo_demanda(t)), compra_key,
            Line2D([], [], color=t["texto"], lw=1.8, marker="o", ms=6, label="Guardado al cierre")]
    fig.legend(handles=asas, loc="outside lower center", ncol=3, frameon=False,
               labelcolor=t["texto2"], fontsize=9)


def dibujar_inventario(fig, datos, plan_guardado, t):
    """Cuánto se guarda al cierre de cada mes (apilado por producto) frente al límite de la bodega."""
    fig.clear()
    fig.set_facecolor(t["fondo"])
    ax = fig.add_subplot(111)
    _estilo_ejes(ax, t)
    x = list(range(len(datos.meses)))
    base = [0] * len(x)
    for i, p in enumerate(datos.productos):
        valores = plan_guardado[p]
        ax.bar(x, valores, 0.4, bottom=base, label=p.upper(), **_relleno(t, i))
        base = [b + v for b, v in zip(base, valores)]
    cap = datos.capacidad_bodega
    tope = max(cap, max(base)) * 1.22
    for k in x:
        ax.text(k, base[k] + tope * 0.012, f"{base[k]:,.0f} u.", ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=t["texto"])
    ax.axhline(cap, color=t["texto"], lw=1.4, ls="--", zorder=4)
    uso = max(base) / cap * 100 if cap else 0
    ax.text(len(x) - 0.55, cap + tope * 0.012,
            f"Capacidad de la bodega: {cap:,.0f}  (uso máximo: {uso:.0f}%)", ha="right",
            va="bottom", fontsize=9, color=t["texto2"])
    ax.set_xticks(x)
    ax.set_xticklabels([f"Mes {m}" for m in datos.meses], color=t["texto"], fontsize=10)
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.set_ylim(0, tope)
    ax.set_ylabel("Unidades guardadas al cierre", color=t["texto2"], fontsize=9.5)
    _titulo(ax, "Inventario al cierre de cada mes", t)
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.01), ncol=len(datos.productos), frameon=False,
              labelcolor=t["texto2"], fontsize=9.5)
