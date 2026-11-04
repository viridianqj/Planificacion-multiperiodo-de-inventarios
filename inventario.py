"no se olviden de importar las librerias muchachios jajajaja"
import copy
import csv
import math
import os
import queue
import random
import sys
import threading
from dataclasses import dataclass

import pulp
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import font as tkfont
    from tkinter import ttk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:      # Python sin Tkinter (pasa en algunos Linux)
    tk = None


# =====================================================================
# 0. LOS DATOS DEL PROBLEMA
# =====================================================================

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

# Valores por defecto del análisis
N_SIMULACIONES = 5000     # meses simulados por cada colchón
VARIACION = 0.20          # la demanda real cambia hasta ±20%
COLCHON_MAX = 0.30        # se prueban colchones de 0% hasta 30%
PASO_COLCHON = 0.02       # ... de 2% en 2%
SEMILLA = 2026            # para que siempre salgan los mismos números


def usd(valor):
    return f"${valor:,.0f}"


# =====================================================================
# PARTE 1: EL PLAN DE COMPRAS CON PuLP
# =====================================================================

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


# =====================================================================
# PARTE 2: PROBAR COLCHONES CON MUCHOS MESES SIMULADOS
# =====================================================================

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


@dataclass
class Resultado:
    colchones: list
    costos_guardar: list
    costos_faltantes: list
    costos_totales: list
    mejor_colchon: float
    menor_costo: float
    plan_compras: dict
    plan_guardado: dict
    costo_plan: float
    rigida: tuple          # (guardar, faltantes) de la forma actual
    optimizada: tuple      # (guardar, faltantes) con el mejor colchón
    ahorro: float          # % de reducción de sobrecostos


def analizar(datos, n_sim=N_SIMULACIONES, variacion=VARIACION, colchon_max=COLCHON_MAX,
             paso=PASO_COLCHON, semilla=SEMILLA, progreso=None):
    """
    Hace todo el análisis: Paso A (barrido de colchones), Paso B (plan con PuLP)
    y Paso C (comparación contra la forma actual).
    `progreso` es una función opcional que recibe un número de 0 a 1.
    """
    random.seed(semilla)

    pasos = int(round(colchon_max / paso))
    total_etapas = pasos + 3
    hechas = 0

    def avanzar():
        nonlocal hechas
        hechas += 1
        if progreso:
            progreso(hechas / total_etapas)

    # ---- Paso A: probar colchones de 0% hasta el máximo ----
    colchones, c_guardar, c_faltantes, c_totales = [], [], [], []
    mejor_colchon = None
    menor_costo = None
    for i in range(pasos + 1):
        colchon = round(i * paso, 4)
        guardar, faltantes = promedio_de_costos("optimizada", colchon, datos, n_sim, variacion)
        total = guardar + faltantes
        colchones.append(colchon)
        c_guardar.append(guardar)
        c_faltantes.append(faltantes)
        c_totales.append(total)
        if menor_costo is None or total < menor_costo:
            menor_costo = total
            mejor_colchon = colchon
        avanzar()

    # ---- Paso B: el plan de compras con ese colchón ----
    plan_compras, plan_guardado, costo_plan = calcular_plan(mejor_colchon, datos)

    # ---- Paso C: comparar contra la forma actual (con una simulación nueva) ----
    g_r, f_r = promedio_de_costos("rigida", 0, datos, n_sim, variacion)
    avanzar()
    g_o, f_o = promedio_de_costos("optimizada", mejor_colchon, datos, n_sim, variacion)
    avanzar()
    if g_r + f_r > 0:
        ahorro = (1 - (g_o + f_o) / (g_r + f_r)) * 100
    else:
        ahorro = 0.0

    return Resultado(colchones, c_guardar, c_faltantes, c_totales, mejor_colchon, menor_costo,
                     plan_compras, plan_guardado, costo_plan, (g_r, f_r), (g_o, f_o), ahorro)


def plan_a_filas(datos, plan_compras, plan_guardado):
    """Una fila por producto y mes: (producto, mes, demanda, compra, guardado)."""
    filas = []
    for p in datos.productos:
        for i, m in enumerate(datos.meses):
            filas.append((p, m, datos.demanda[p][i], plan_compras[p][i], plan_guardado[p][i]))
    return filas


def construir_informe(res, datos, n_sim, variacion):
    """El mismo texto de la consola, como lista de (estilo, linea). Lo usan la consola y la pestaña Resumen."""
    L = []
    L.append(("h", "PASO A: probando colchones (costo promedio de guardar + faltantes)"))
    L.append(("dim", "-" * 62))
    for c, t in zip(res.colchones, res.costos_totales):
        marca = "   <-- el mejor" if c == res.mejor_colchon else ""
        L.append(("ok" if marca else "n", f"Colchón {c*100:4.0f}%  ->  {usd(t)}{marca}"))
    L.append(("n", ""))
    L.append(("ok", f"El mejor colchón es {res.mejor_colchon*100:.0f}% (costo {usd(res.menor_costo)})"))
    L.append(("n", ""))

    meses_txt = ", ".join(f"mes{m}" for m in datos.meses)
    L.append(("h", f"PASO B: plan de compras (unidades por mes: {meses_txt})"))
    L.append(("dim", "-" * 62))
    for p in datos.productos:
        L.append(("n", f"{p}: comprar {res.plan_compras[p]}   guardar al cierre {res.plan_guardado[p]}"))
    L.append(("n", f"Costo del plan sin variación de demanda: {usd(res.costo_plan)}"))
    L.append(("n", ""))

    L.append(("h", f"PASO C: comparación contra la forma actual (demanda ±{variacion*100:.0f}%, {n_sim:,} simulaciones)"))
    L.append(("dim", "-" * 62))
    g_r, f_r = res.rigida
    g_o, f_o = res.optimizada
    L.append(("n", f"Forma actual : guardar {usd(g_r)} + faltantes {usd(f_r)} = {usd(g_r + f_r)}"))
    L.append(("n", f"Optimizada   : guardar {usd(g_o)} + faltantes {usd(f_o)} = {usd(g_o + f_o)}"))
    L.append(("ok", f"Reducción de sobrecostos: {res.ahorro:.1f}%"))
    L.append(("n", ""))

    L.append(("h", "RESPUESTAS A LAS PREGUNTAS DEL EJERCICIO"))
    L.append(("dim", "-" * 62))
    L.append(("n", f"1) El plan óptimo es el del paso B: colchón de {res.mejor_colchon*100:.0f}% "
                   f"({usd(res.costo_plan)} en total, compras incluidas)."))
    L.append(("n", f"2) Sincronizar compras, almacén y faltantes baja los sobrecostos {res.ahorro:.1f}% "
                   f"frente a comprar justo lo esperado cada mes."))
    return L


# =====================================================================
# PARTE 3: LAS GRÁFICAS
# =====================================================================
# Cada función dibuja sobre una Figure que ya existe. Reciben un "tema"
# (colores) para poder usar las mismas gráficas en la ventana (oscuro),
# en reportes (claro) y en documentos impresos (blanco y negro).

TEMA_OSCURO = {
    "bn": False, "fondo": "#131f38", "texto": "#f0efec", "texto2": "#9fb0cc", "grid": "#24365c",
    "serie": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
    "demanda": "#41537a",
    "lineas": {
        "guardar": dict(color="#3987e5", lw=2, marker="o", ms=7, markeredgecolor="#131f38", markeredgewidth=1.5),
        "faltantes": dict(color="#d95926", lw=2, marker="o", ms=7, markeredgecolor="#131f38", markeredgewidth=1.5),
        "total": dict(color="#f0efec", lw=2.6, marker="o", ms=7, markeredgecolor="#131f38", markeredgewidth=1.5),
    },
}

TEMA_CLARO = {
    "bn": False, "fondo": "#fcfcfb", "texto": "#0b0b0b", "texto2": "#52514e", "grid": "#e4e3df",
    "serie": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "demanda": "#cfcdc6",
    "lineas": {
        "guardar": dict(color="#2a78d6", lw=2, marker="o", ms=7, markeredgecolor="#fcfcfb", markeredgewidth=1.5),
        "faltantes": dict(color="#eb6834", lw=2, marker="o", ms=7, markeredgecolor="#fcfcfb", markeredgewidth=1.5),
        "total": dict(color="#0b0b0b", lw=2.6, marker="o", ms=7, markeredgecolor="#fcfcfb", markeredgewidth=1.5),
    },
}

TEMA_BN = {   # blanco y negro: se distingue por tramas y tipos de línea, no por color
    "bn": True, "fondo": "#ffffff", "texto": "#000000", "texto2": "#333333", "grid": "#d9d9d9",
    "grises": ["#f2f2f2", "#cfcfcf", "#9c9c9c", "#6e6e6e"],
    "tramas": ["///", "...", "xxx", "\\\\\\"],
    "demanda": "#ffffff",
    "lineas": {
        "guardar": dict(color="#555555", lw=1.8, ls="-", marker="o", ms=6, markeredgecolor="#000000"),
        "faltantes": dict(color="#000000", lw=1.8, ls="--", marker="s", ms=6, markeredgecolor="#000000"),
        "total": dict(color="#000000", lw=3.2, ls="-", marker="^", ms=7, markeredgecolor="#000000"),
    },
}


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


# =====================================================================
# PARTE 4: LA INTERFAZ
# =====================================================================

C = {
    "fondo": "#0b1220", "header": "#0f1b33", "tarjeta": "#131f38", "tarjeta2": "#1a2a4a",
    "borde": "#24365c", "texto": "#f0efec", "texto2": "#9fb0cc", "acento": "#3987e5",
    "acento_claro": "#6da7ec", "verde": "#199e70", "naranja": "#d95926", "rojo": "#e66767",
    "tinta": "#06152b",
}

_Lienzo = tk.Canvas if tk else object
_Ventana = tk.Tk if tk else object


class Deslizador(_Lienzo):
    """Barra deslizante propia: pista fina, parte llena de color y una bolita."""

    def __init__(self, padre, desde, hasta, variable, comando=None, fondo=None):
        fondo = fondo or C["tarjeta"]
        super().__init__(padre, height=26, bg=fondo, highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self.desde, self.hasta, self.var, self.comando, self.fondo = desde, hasta, variable, comando, fondo
        self.bind("<Configure>", lambda e: self._dibujar())
        self.bind("<Button-1>", self._mover)
        self.bind("<B1-Motion>", self._mover)
        self.bind("<Left>", lambda e: self._fijar(self.var.get() - 1))
        self.bind("<Right>", lambda e: self._fijar(self.var.get() + 1))
        self.var.trace_add("write", lambda *a: self._dibujar())

    def _x(self, valor):
        ancho = max(self.winfo_width() - 20, 1)
        return 10 + (valor - self.desde) / (self.hasta - self.desde) * ancho

    def _dibujar(self):
        self.delete("all")
        y, x0 = 13, 10
        x1 = max(self.winfo_width() - 10, x0 + 1)
        xv = self._x(self.var.get())
        self.create_line(x0, y, x1, y, width=4, fill=C["borde"], capstyle="round")
        self.create_line(x0, y, xv, y, width=4, fill=C["acento"], capstyle="round")
        self.create_oval(xv - 8, y - 8, xv + 8, y + 8, fill=C["acento_claro"], outline=self.fondo, width=3)

    def _mover(self, evento):
        self.focus_set()
        valor = self.desde + (evento.x - 10) / max(self.winfo_width() - 20, 1) * (self.hasta - self.desde)
        self._fijar(round(valor))

    def _fijar(self, valor):
        valor = int(min(max(valor, self.desde), self.hasta))
        if valor != self.var.get():
            self.var.set(valor)
            if self.comando:
                self.comando(valor)


class App(_Ventana):
    PAGINAS = ["Costos vs. colchón", "Plan de compras", "Comparación", "Inventario", "Datos", "Resumen"]

    def __init__(self):
        super().__init__()
        self.title("Planificador de Inventarios · Investigación de Operaciones")
        self.configure(bg=C["fondo"])
        self._fuentes()
        self._estilo_ttk()
        ancho = 1320
        alto = min(840, self.winfo_screenheight() - 90)
        x = max((self.winfo_screenwidth() - ancho) // 2, 0)
        y = max((self.winfo_screenheight() - alto) // 2 - 20, 0)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(1120, 640)

        self.res = None
        self.datos_usados = None
        self.plan = None            # (colchon, compras, guardado, costo) que se muestra en las pestañas del plan
        self.cola = queue.Queue()
        self.ocupado = False
        self._hover = None
        self._job_plan = None
        self._valores_kpi = {}

        self._crear_variables()
        self._crear_encabezado()
        cuerpo = tk.Frame(self, bg=C["fondo"])
        cuerpo.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        self._crear_lateral(cuerpo)
        self._crear_principal(cuerpo)
        self._mostrar("Costos vs. colchón")

        self.bind("<Control-Return>", lambda e: self.ejecutar())
        self.bind("<F5>", lambda e: self.ejecutar())
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(350, self.ejecutar)

    # ------------------------------------------------------------ estilos
    def _fuentes(self):
        familias = set(tkfont.families())
        self.f = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans", "Arial")
                       if f in familias), "TkDefaultFont")
        self.fm = next((f for f in ("Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")
                        if f in familias), "TkFixedFont")

    def _estilo_ttk(self):
        e = ttk.Style(self)
        e.theme_use("clam")
        e.configure("Treeview", background=C["tarjeta2"], fieldbackground=C["tarjeta2"],
                    foreground=C["texto"], rowheight=28, borderwidth=0, font=(self.f, 10))
        e.map("Treeview", background=[("selected", C["borde"])], foreground=[("selected", C["texto"])])
        e.configure("Treeview.Heading", background=C["borde"], foreground=C["texto"], relief="flat",
                    font=(self.f, 9, "bold"), padding=(6, 7), borderwidth=0)
        e.map("Treeview.Heading", background=[("active", C["borde"])])
        e.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # ------------------------------------------------------------ piezas reutilizables
    def _etiqueta(self, padre, texto, tam=10, negrita=False, color=None, fondo=None, **kw):
        return tk.Label(padre, text=texto, font=(self.f, tam, "bold" if negrita else "normal"),
                        fg=color or C["texto"], bg=fondo or padre["bg"], **kw)

    def _titulo_seccion(self, padre, texto):
        self._etiqueta(padre, texto, 8, True, C["texto2"]).pack(anchor="w", padx=18, pady=(16, 4))

    def _boton(self, padre, texto, comando, principal=False):
        fondo = C["acento"] if principal else C["tarjeta2"]
        encima = C["acento_claro"] if principal else C["borde"]
        b = tk.Button(padre, text=texto, command=comando, font=(self.f, 11 if principal else 10, "bold"),
                      fg=C["tinta"] if principal else C["texto"], bg=fondo, activebackground=encima,
                      activeforeground=C["tinta"] if principal else C["texto"],
                      disabledforeground="#6b7fa3", relief="flat", bd=0, cursor="hand2",
                      padx=14, pady=10 if principal else 8)
        b.bind("<Enter>", lambda e: b.config(bg=encima) if b["state"] == "normal" else None)
        b.bind("<Leave>", lambda e: b.config(bg=fondo))
        return b

    def _campo(self, padre, **kw):
        return dict(font=(self.f, 11), bg=C["tarjeta2"], fg=C["texto"], insertbackground=C["texto"],
                    relief="flat", highlightthickness=1, highlightbackground=C["borde"],
                    highlightcolor=C["acento"], **kw)

    def _fila_slider(self, padre, texto, var, desde, hasta, formato):
        caja = tk.Frame(padre, bg=C["tarjeta"])
        caja.pack(fill="x", padx=18, pady=(8, 0))
        fila = tk.Frame(caja, bg=C["tarjeta"])
        fila.pack(fill="x")
        self._etiqueta(fila, texto, 10, False, C["texto"]).pack(side="left")
        valor = self._etiqueta(fila, formato(var.get()), 10, True, C["acento_claro"])
        valor.pack(side="right")
        Deslizador(caja, desde, hasta, var,
                   comando=lambda v: valor.config(text=formato(v))).pack(fill="x", pady=(2, 0))
        var.trace_add("write", lambda *a: valor.config(text=formato(var.get())))

    def _spin(self, padre, texto, var, desde, hasta, paso):
        self._etiqueta(padre, texto, 10, False, C["texto"]).pack(anchor="w")
        tk.Spinbox(padre, from_=desde, to=hasta, increment=paso, textvariable=var, width=6,
                   buttonbackground=C["borde"], **self._campo(padre)).pack(fill="x", pady=(3, 0), ipady=4)

    def _fila_spin(self, padre, texto, var, desde, hasta, paso):
        caja = tk.Frame(padre, bg=C["tarjeta"])
        caja.pack(fill="x", padx=18, pady=(10, 0))
        self._spin(caja, texto, var, desde, hasta, paso)

    def _fila_segmentada(self, padre, texto, var, opciones):
        caja = tk.Frame(padre, bg=C["tarjeta"])
        caja.pack(fill="x", padx=18, pady=(10, 0))
        self._etiqueta(caja, texto, 10, False, C["texto"]).pack(anchor="w")
        fila = tk.Frame(caja, bg=C["tarjeta2"])
        fila.pack(fill="x", pady=(3, 0))
        botones = []

        def pintar(*_):
            for valor, b in botones:
                activo = var.get() == valor
                b.config(fg=C["tinta"] if activo else C["texto2"])

        for valor in opciones:
            b = tk.Radiobutton(fila, text=f"{valor}%", value=valor, variable=var, indicatoron=False,
                               bg=C["tarjeta2"], fg=C["texto2"], selectcolor=C["acento"],
                               activebackground=C["borde"], activeforeground=C["texto"], relief="flat",
                               bd=0, padx=10, pady=6, font=(self.f, 10, "bold"), highlightthickness=0,
                               cursor="hand2", command=pintar)
            b.pack(side="left", expand=True, fill="x")
            botones.append((valor, b))
        var.trace_add("write", pintar)
        pintar()

    # ------------------------------------------------------------ variables y encabezado
    def _crear_variables(self):
        self.v_var = tk.IntVar(value=int(VARIACION * 100))
        self.v_sims = tk.StringVar(value=str(N_SIMULACIONES))
        self.v_cmax = tk.IntVar(value=int(COLCHON_MAX * 100))
        self.v_paso = tk.IntVar(value=int(PASO_COLCHON * 100))
        self.v_cap = tk.StringVar(value=str(DATOS_ENUNCIADO.capacidad_bodega))
        self.v_semilla = tk.StringVar(value=str(SEMILLA))
        self.v_colchon_plan = tk.IntVar(value=12)
        self.v_estado = tk.StringVar(value="Iniciando…")
        self.entradas = {}

    def _crear_encabezado(self):
        enc = tk.Frame(self, bg=C["header"])
        enc.pack(fill="x")
        barra = tk.Canvas(enc, height=4, bg=C["header"], highlightthickness=0, bd=0)
        barra.pack(fill="x")

        def degradado(_=None):
            barra.delete("all")
            ancho = max(barra.winfo_width(), 1)
            segmentos = 120
            a, b = (0x39, 0x87, 0xE5), (0x19, 0x9E, 0x70)
            for i in range(segmentos):
                f = i / (segmentos - 1)
                col = "#%02x%02x%02x" % tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))
                barra.create_rectangle(i * ancho / segmentos, 0, (i + 1) * ancho / segmentos + 1, 4,
                                       fill=col, outline=col)
        barra.bind("<Configure>", degradado)

        interior = tk.Frame(enc, bg=C["header"])
        interior.pack(fill="x", padx=24, pady=14)
        izq = tk.Frame(interior, bg=C["header"])
        izq.pack(side="left")
        self._etiqueta(izq, "Planificador de Inventarios", 20, True).pack(anchor="w")
        self._etiqueta(izq, "Programación lineal con PuLP  ·  Simulación Monte Carlo de la demanda  ·  "
                            "4 productos × 3 meses", 10, False, C["texto2"]).pack(anchor="w")
        self.pastilla = tk.Label(interior, textvariable=self.v_estado, font=(self.f, 10, "bold"),
                                 fg=C["tinta"], bg=C["acento"], padx=14, pady=5)
        self.pastilla.pack(side="right")

    def _estado(self, texto, tipo="listo"):
        self.v_estado.set(texto)
        self.pastilla.config(bg={"listo": C["verde"], "trabajando": C["acento_claro"],
                                 "error": C["rojo"]}[tipo])

    # ------------------------------------------------------------ panel izquierdo
    def _crear_lateral(self, padre):
        lat = tk.Frame(padre, bg=C["tarjeta"], width=300, highlightthickness=1, highlightbackground=C["borde"])
        lat.grid(row=0, column=0, sticky="ns", padx=(0, 16), pady=(16, 0))
        lat.pack_propagate(False)

        # Los botones se empacan primero para que, en pantallas bajitas, siempre se vean
        inferior = tk.Frame(lat, bg=C["tarjeta"])
        inferior.pack(side="bottom", fill="x", padx=18, pady=(0, 18))

        self._titulo_seccion(lat, "PARÁMETROS DEL ANÁLISIS")
        self._fila_slider(lat, "Variación de la demanda", self.v_var, 0, 40, lambda v: f"± {v}%")
        self._fila_spin(lat, "Simulaciones por colchón", self.v_sims, 500, 50000, 500)
        self._fila_slider(lat, "Colchón máximo a probar", self.v_cmax, 5, 50, lambda v: f"{v}%")
        self._fila_segmentada(lat, "Paso entre colchones", self.v_paso, [1, 2, 5])
        dos = tk.Frame(lat, bg=C["tarjeta"])
        dos.pack(fill="x", padx=18, pady=(10, 0))
        dos.columnconfigure((0, 1), weight=1, uniform="dos")
        izq = tk.Frame(dos, bg=C["tarjeta"])
        izq.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        der = tk.Frame(dos, bg=C["tarjeta"])
        der.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._spin(izq, "Bodega (unid.)", self.v_cap, 100, 5000, 50)
        self._etiqueta(der, "Semilla aleatoria", 10, False, C["texto"]).pack(anchor="w")
        tk.Entry(der, textvariable=self.v_semilla, width=6, **self._campo(der)).pack(fill="x", pady=(3, 0), ipady=5)
        self._etiqueta(lat, "El colchón es el inventario extra que se deja guardado al cierre de cada mes, "
                            "como % de la demanda esperada del mes siguiente. El programa prueba varios y "
                            "elige el más barato.", 9, False, C["texto2"], justify="left",
                       wraplength=262).pack(anchor="w", padx=18, pady=(16, 0))

        self.progreso = tk.Canvas(inferior, height=6, bg=C["tarjeta2"], highlightthickness=0, bd=0)
        self.progreso.pack(fill="x", pady=(0, 12))
        self.btn_run = self._boton(inferior, "▶  Ejecutar análisis", self.ejecutar, principal=True)
        self.btn_run.pack(fill="x")
        self._boton(inferior, "Guardar gráficas (PNG)", self._exportar_png).pack(fill="x", pady=(8, 0))
        self._boton(inferior, "Exportar plan (CSV)", self._exportar_csv).pack(fill="x", pady=(8, 0))
        self._boton(inferior, "Restablecer valores", self._restablecer).pack(fill="x", pady=(8, 0))

    def _progreso(self, fraccion):
        self.progreso.delete("all")
        ancho = max(self.progreso.winfo_width(), 1)
        self.progreso.create_rectangle(0, 0, ancho * fraccion, 6, fill=C["acento"], outline=C["acento"])

    # ------------------------------------------------------------ panel principal
    def _crear_principal(self, padre):
        prin = tk.Frame(padre, bg=C["fondo"])
        prin.grid(row=0, column=1, sticky="nsew", pady=(16, 0))
        prin.columnconfigure(0, weight=1)
        prin.rowconfigure(2, weight=1)

        # ---- las 5 tarjetas con los números clave ----
        kpis = tk.Frame(prin, bg=C["fondo"])
        kpis.grid(row=0, column=0, sticky="ew")
        definicion = [("mejor", "MEJOR COLCHÓN", C["acento"]), ("optimo", "COSTO PROMEDIO ÓPTIMO", C["acento"]),
                      ("actual", "FORMA ACTUAL", C["acento"]), ("ahorro", "REDUCCIÓN DE SOBRECOSTOS", C["verde"]),
                      ("plan", "COSTO DEL PLAN (LP)", C["acento"])]
        self.kpi_valor, self.kpi_sub = {}, {}
        for i, (clave, titulo, color) in enumerate(definicion):
            kpis.columnconfigure(i, weight=1, uniform="kpi")
            tarj = tk.Frame(kpis, bg=C["tarjeta"], highlightthickness=1, highlightbackground=C["borde"])
            tarj.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            tk.Frame(tarj, bg=color, height=3).pack(fill="x")
            self._etiqueta(tarj, titulo, 8, True, C["texto2"]).pack(anchor="w", padx=14, pady=(10, 0))
            self.kpi_valor[clave] = self._etiqueta(tarj, "—", 22, True, C["texto"])
            self.kpi_valor[clave].pack(anchor="w", padx=14)
            self.kpi_sub[clave] = self._etiqueta(tarj, " ", 9, False, C["texto2"])
            self.kpi_sub[clave].pack(anchor="w", padx=14, pady=(0, 10))

        # ---- pestañas ----
        self.barra_tabs = tk.Frame(prin, bg=C["fondo"])
        self.barra_tabs.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        self.contenedor = tk.Frame(prin, bg=C["tarjeta"], highlightthickness=1, highlightbackground=C["borde"])
        self.contenedor.grid(row=2, column=0, sticky="nsew")
        self.contenedor.rowconfigure(0, weight=1)
        self.contenedor.columnconfigure(0, weight=1)
        self.paginas, self.tabs = {}, {}
        for nombre in self.PAGINAS:
            marco = tk.Frame(self.contenedor, bg=C["tarjeta"])
            marco.grid(row=0, column=0, sticky="nsew")
            self.paginas[nombre] = marco
            tab = tk.Label(self.barra_tabs, text=nombre, font=(self.f, 10, "bold"), padx=16, pady=8,
                           cursor="hand2", bg=C["fondo"], fg=C["texto2"])
            tab.pack(side="left")
            tab.bind("<Button-1>", lambda e, n=nombre: self._mostrar(n))
            self.tabs[nombre] = tab

        self._pagina_costos()
        self._pagina_plan()
        self._pagina_comparacion()
        self._pagina_inventario()
        self._pagina_datos()
        self._pagina_resumen()

    def _mostrar(self, nombre):
        self.paginas[nombre].tkraise()
        for n, tab in self.tabs.items():
            activo = n == nombre
            tab.config(bg=C["tarjeta"] if activo else C["fondo"], fg=C["acento_claro"] if activo else C["texto2"])
        for lienzo in (getattr(self, "c_costos", None), getattr(self, "c_plan", None),
                       getattr(self, "c_comp", None), getattr(self, "c_inv", None)):
            if lienzo is not None:
                lienzo.draw_idle()

    def _nuevo_lienzo(self, marco, **pack):
        fig = Figure(figsize=(8, 4.5), dpi=100, facecolor=TEMA_OSCURO["fondo"])
        fig.set_layout_engine("constrained")
        lienzo = FigureCanvasTkAgg(fig, master=marco)
        lienzo.get_tk_widget().configure(bg=TEMA_OSCURO["fondo"], highlightthickness=0)
        lienzo.get_tk_widget().pack(fill="both", expand=True, **pack)
        dibujar_vacio(fig, TEMA_OSCURO, "Calculando…")
        return fig, lienzo

    def _pagina_costos(self):
        m = self.paginas["Costos vs. colchón"]
        self.fig_costos, self.c_costos = self._nuevo_lienzo(m, padx=10, pady=10)
        self.c_costos.mpl_connect("motion_notify_event", self._pasar_mouse)
        self.c_costos.mpl_connect("axes_leave_event", lambda e: self._quitar_hover())
        self._etiqueta(m, "Pasa el mouse sobre la gráfica para ver los costos de cada colchón.", 9, False,
                       C["texto2"]).pack(side="bottom", anchor="w", padx=16, pady=(0, 8))

    def _pagina_comparacion(self):
        m = self.paginas["Comparación"]
        self.fig_comp, self.c_comp = self._nuevo_lienzo(m, padx=10, pady=10)

    def _pagina_inventario(self):
        m = self.paginas["Inventario"]
        self.fig_inv, self.c_inv = self._nuevo_lienzo(m, padx=10, pady=10)

    def _pagina_plan(self):
        m = self.paginas["Plan de compras"]
        control = tk.Frame(m, bg=C["tarjeta"])
        control.pack(fill="x", padx=16, pady=(12, 6))
        self._etiqueta(control, "Colchón de seguridad del plan", 10, True).pack(side="left")
        self.lbl_colchon_plan = self._etiqueta(control, "12%", 12, True, C["acento_claro"])
        self.lbl_colchon_plan.pack(side="left", padx=(12, 12))
        Deslizador(control, 0, 40, self.v_colchon_plan, comando=self._mover_colchon_plan).pack(
            side="left", fill="x", expand=True)
        self._boton(control, "Usar el óptimo", self._usar_optimo).pack(side="left", padx=(14, 0))
        self.v_colchon_plan.trace_add("write", lambda *a: self.lbl_colchon_plan.config(
            text=f"{self.v_colchon_plan.get()}%"))

        columnas = ("producto", "c1", "c2", "c3", "g1", "g2", "g3")
        marco_tabla = tk.Frame(m, bg=C["tarjeta"])
        marco_tabla.pack(fill="x", padx=16, pady=(4, 0))
        self.tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings", height=5, selectmode="none")
        titulos = ["Producto", "Comprar mes 1", "Comprar mes 2", "Comprar mes 3",
                   "Inventario mes 1", "Inventario mes 2", "Inventario mes 3"]
        for col, titulo in zip(columnas, titulos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, anchor="center", width=130 if col != "producto" else 90, stretch=True)
        self.tabla.tag_configure("par", background=C["tarjeta2"])
        self.tabla.tag_configure("impar", background="#16243f")
        self.tabla.tag_configure("total", background=C["borde"], font=(self.f, 10, "bold"))
        self.tabla.pack(fill="x")
        self.fig_plan, self.c_plan = self._nuevo_lienzo(m, padx=10, pady=(8, 10))

    def _pagina_datos(self):
        m = self.paginas["Datos"]
        self._etiqueta(m, "Datos del problema", 14, True).grid(row=0, column=0, columnspan=8, sticky="w",
                                                              padx=24, pady=(20, 2))
        self._etiqueta(m, "Cambia cualquier número y pulsa «Ejecutar análisis». Demanda en unidades, costos en USD por unidad.",
                       10, False, C["texto2"]).grid(row=1, column=0, columnspan=8, sticky="w", padx=24, pady=(0, 16))
        cabeceras = ["Producto", "Demanda mes 1", "Demanda mes 2", "Demanda mes 3",
                     "Costo de compra", "Guardar 1 u. / mes", "Penalización faltante"]
        for j, h in enumerate(cabeceras):
            self._etiqueta(m, h, 9, True, C["texto2"]).grid(row=2, column=j, padx=8, pady=(0, 4))
        for i, p in enumerate(DATOS_ENUNCIADO.productos):
            self._etiqueta(m, p.upper(), 12, True, C["acento_claro"]).grid(row=3 + i, column=0, padx=8, pady=6)
            for j in range(6):
                var = tk.StringVar()
                self.entradas[i, j] = var
                tk.Entry(m, textvariable=var, width=14, justify="center", **self._campo(m)).grid(
                    row=3 + i, column=j + 1, padx=8, pady=6, ipady=6)
        self._cargar_datos_por_defecto()
        self._etiqueta(m, "La capacidad de la bodega y la variación de la demanda se cambian en el panel de la izquierda.",
                       9, False, C["texto2"]).grid(row=8, column=0, columnspan=8, sticky="w", padx=24, pady=(18, 0))

    def _cargar_datos_por_defecto(self):
        d = DATOS_ENUNCIADO
        for i, p in enumerate(d.productos):
            valores = [*d.demanda[p], d.costo_compra[p], d.costo_guardar[p], d.penalizacion[p]]
            for j, v in enumerate(valores):
                self.entradas[i, j].set(str(v))

    def _pagina_resumen(self):
        m = self.paginas["Resumen"]
        self.texto = tk.Text(m, bg=C["tarjeta"], fg=C["texto"], font=(self.fm, 10), relief="flat", bd=0,
                             padx=20, pady=16, wrap="none", highlightthickness=0, state="disabled",
                             cursor="arrow", spacing1=2)
        self.texto.pack(fill="both", expand=True)
        self.texto.tag_configure("h", foreground=C["acento_claro"], font=(self.fm, 10, "bold"), spacing1=6)
        self.texto.tag_configure("ok", foreground="#2fc79a", font=(self.fm, 10, "bold"))
        self.texto.tag_configure("dim", foreground=C["borde"])
        self.texto.tag_configure("n", foreground=C["texto"])

    # ------------------------------------------------------------ ejecutar el análisis
    def _leer_datos(self):
        base = DATOS_ENUNCIADO
        demanda, compra, guardar, penal = {}, {}, {}, {}
        for i, p in enumerate(base.productos):
            valores = []
            for j in range(6):
                texto = self.entradas[i, j].get().strip().replace(",", ".")
                try:
                    v = float(texto)
                except ValueError:
                    raise ValueError(f"En la pestaña «Datos», el valor «{texto}» de {p.upper()} no es un número.")
                if v < 0:
                    raise ValueError(f"En la pestaña «Datos», {p.upper()} tiene un número negativo.")
                valores.append(int(v) if v == int(v) else v)
            demanda[p] = valores[0:3]
            compra[p], guardar[p], penal[p] = valores[3:6]
        try:
            cap = float(self.v_cap.get().replace(",", "."))
        except ValueError:
            raise ValueError("La capacidad de la bodega no es un número.")
        if cap <= 0:
            raise ValueError("La capacidad de la bodega debe ser mayor que cero.")
        cap = int(cap) if cap == int(cap) else cap
        return Datos(list(base.productos), list(base.meses), demanda, compra, guardar, penal, cap)

    def ejecutar(self):
        if self.ocupado:
            return
        try:
            datos = self._leer_datos()
            n_sim = int(self.v_sims.get())
            semilla = int(self.v_semilla.get())
            if n_sim < 100:
                raise ValueError("Usa al menos 100 simulaciones por colchón.")
        except ValueError as error:
            messagebox.showerror("Revisa los datos", str(error))
            return
        params = dict(n_sim=n_sim, variacion=self.v_var.get() / 100, colchon_max=self.v_cmax.get() / 100,
                      paso=self.v_paso.get() / 100, semilla=semilla)
        self.ocupado = True
        self.btn_run.config(state="disabled", text="Calculando…")
        self._estado("Calculando…", "trabajando")
        self._progreso(0)
        threading.Thread(target=self._trabajo, args=(datos, params), daemon=True).start()
        self.after(60, self._revisar_cola)

    def _trabajo(self, datos, params):
        """Corre en otro hilo para que la ventana no se congele."""
        try:
            res = analizar(datos, progreso=lambda f: self.cola.put(("prog", f)), **params)
            self.cola.put(("ok", (datos, params, res)))
        except Exception as error:
            self.cola.put(("error", str(error)))

    def _revisar_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "prog":
                    self._progreso(dato)
                elif tipo == "ok":
                    self._terminar_ok(*dato)
                    return
                else:
                    self._terminar_error(dato)
                    return
        except queue.Empty:
            pass
        self.after(60, self._revisar_cola)

    def _terminar_error(self, mensaje):
        self.ocupado = False
        self.btn_run.config(state="normal", text="▶  Ejecutar análisis")
        self._progreso(0)
        self._estado("Error", "error")
        messagebox.showerror("No se pudo calcular", mensaje)

    def _terminar_ok(self, datos, params, res):
        self.ocupado = False
        self.btn_run.config(state="normal", text="▶  Ejecutar análisis")
        self._progreso(1)
        self.res, self.datos_usados, self.params = res, datos, params
        self.plan = (res.mejor_colchon, res.plan_compras, res.plan_guardado, res.costo_plan)
        self.v_colchon_plan.set(int(round(res.mejor_colchon * 100)))

        self._pintar_costos()
        dibujar_comparacion(self.fig_comp, res, TEMA_OSCURO)
        self.c_comp.draw_idle()
        self._pintar_plan()
        self._pintar_resumen()

        mejor = res.mejor_colchon * 100
        g_r, f_r = res.rigida
        g_o, f_o = res.optimizada
        self._animar("mejor", mejor, lambda v: f"{v:.0f}%", "de la demanda siguiente")
        self._animar("optimo", res.menor_costo, usd, "guardar + faltantes")
        self._animar("actual", g_r + f_r, usd, "compra rígida")
        self._animar("ahorro", res.ahorro, lambda v: f"{v:.1f}%", f"{usd(g_r + f_r)} → {usd(g_o + f_o)}")
        self._estado("Listo", "listo")

    # ------------------------------------------------------------ pintar resultados
    def _pintar_costos(self):
        dibujar_costos(self.fig_costos, self.res, TEMA_OSCURO)
        self._hover = None
        self.c_costos.draw_idle()

    def _pintar_plan(self):
        colchon, pc, pg, costo = self.plan
        datos = self.datos_usados
        self.tabla.delete(*self.tabla.get_children())
        for i, p in enumerate(datos.productos):
            self.tabla.insert("", "end", values=(p.upper(), *pc[p], *pg[p]), tags=("par" if i % 2 == 0 else "impar",))
        tot_c = [sum(pc[p][k] for p in datos.productos) for k in range(len(datos.meses))]
        tot_g = [sum(pg[p][k] for p in datos.productos) for k in range(len(datos.meses))]
        self.tabla.insert("", "end", values=("TOTAL", *tot_c, *tot_g), tags=("total",))
        dibujar_plan(self.fig_plan, datos, pc, pg, colchon, TEMA_OSCURO)
        self.c_plan.draw_idle()
        dibujar_inventario(self.fig_inv, datos, pg, TEMA_OSCURO)
        self.c_inv.draw_idle()
        self._animar("plan", costo, usd, f"colchón de {colchon*100:.0f}%")

    def _pintar_resumen(self):
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        for estilo, linea in construir_informe(self.res, self.datos_usados, self.params["n_sim"],
                                               self.params["variacion"]):
            self.texto.insert("end", linea + "\n", estilo)
        self.texto.config(state="disabled")

    def _animar(self, clave, destino, formato, subtitulo, pasos=18):
        inicio = self._valores_kpi.get(clave, 0)
        self._valores_kpi[clave] = destino
        self.kpi_sub[clave].config(text=subtitulo)

        def paso(k=0):
            f = 1 - (1 - (k + 1) / pasos) ** 3          # frena al llegar
            self.kpi_valor[clave].config(text=formato(inicio + (destino - inicio) * f))
            if k + 1 < pasos:
                self.after(16, paso, k + 1)
        paso()

    # ------------------------------------------------------------ plan con colchón manual
    def _mover_colchon_plan(self, _valor):
        if self._job_plan:
            self.after_cancel(self._job_plan)
        self._job_plan = self.after(220, self._recalcular_plan)

    def _recalcular_plan(self):
        self._job_plan = None
        if self.datos_usados is None:
            return
        colchon = self.v_colchon_plan.get() / 100
        try:
            pc, pg, costo = calcular_plan(colchon, self.datos_usados)
        except ValueError as error:
            self._estado("Plan imposible", "error")
            messagebox.showwarning("Ese colchón no cabe", str(error))
            return
        self.plan = (colchon, pc, pg, costo)
        self._estado("Listo", "listo")
        self._pintar_plan()

    def _usar_optimo(self):
        if self.res is not None:
            self.v_colchon_plan.set(int(round(self.res.mejor_colchon * 100)))
            self._recalcular_plan()

    # ------------------------------------------------------------ mouse sobre la gráfica principal
    def _pasar_mouse(self, evento):
        if self.res is None or not self.fig_costos.axes:
            return
        ax = self.fig_costos.axes[0]
        if evento.inaxes is not ax or evento.xdata is None:
            self._quitar_hover()
            return
        xs = [c * 100 for c in self.res.colchones]
        i = min(range(len(xs)), key=lambda k: abs(xs[k] - evento.xdata))
        if self._hover is None or self._hover["ax"] is not ax:
            linea = ax.axvline(xs[i], color=TEMA_OSCURO["texto2"], lw=1, alpha=0.8, zorder=2)
            caja = ax.text(0.985, 0.97, "", transform=ax.transAxes, ha="right", va="top", fontsize=9.5,
                           color=TEMA_OSCURO["texto"], linespacing=1.6, zorder=10,
                           bbox=dict(boxstyle="round,pad=0.6", fc=C["tarjeta2"], ec=C["borde"]))
            self._hover = {"ax": ax, "linea": linea, "caja": caja}
        h = self._hover
        h["linea"].set_xdata([xs[i], xs[i]])
        h["caja"].set_text(f"Colchón {xs[i]:.0f}%\nAlmacenamiento  {usd(self.res.costos_guardar[i])}\n"
                           f"Faltantes  {usd(self.res.costos_faltantes[i])}\n"
                           f"Total  {usd(self.res.costos_totales[i])}")
        h["linea"].set_visible(True)
        h["caja"].set_visible(True)
        self.c_costos.draw_idle()

    def _quitar_hover(self):
        if self._hover is not None:
            self._hover["linea"].set_visible(False)
            self._hover["caja"].set_visible(False)
            self.c_costos.draw_idle()

    # ------------------------------------------------------------ exportar y restablecer
    def _exportar_png(self):
        if self.res is None:
            return
        carpeta = filedialog.askdirectory(title="Carpeta donde guardar las gráficas")
        if not carpeta:
            return
        figuras = figuras_para_exportar(self.res, self.datos_usados, self.plan, TEMA_CLARO)
        for nombre, fig in figuras.items():
            fig.savefig(os.path.join(carpeta, f"grafica_{nombre}.png"), dpi=200, facecolor=fig.get_facecolor())
        messagebox.showinfo("Listo", f"Guardé {len(figuras)} gráficas en:\n{carpeta}")

    def _exportar_csv(self):
        if self.res is None:
            return
        ruta = filedialog.asksaveasfilename(title="Guardar plan de compras", defaultextension=".csv",
                                            initialfile="plan_de_compras.csv",
                                            filetypes=[("CSV (Excel)", "*.csv")])
        if not ruta:
            return
        _, pc, pg, _ = self.plan
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            w = csv.writer(archivo, delimiter=";")
            w.writerow(["Producto", "Mes", "Demanda esperada", "Compra", "Guardado al cierre"])
            w.writerows(plan_a_filas(self.datos_usados, pc, pg))
        messagebox.showinfo("Listo", f"Plan guardado en:\n{ruta}")

    def _restablecer(self):
        self.v_var.set(int(VARIACION * 100))
        self.v_sims.set(str(N_SIMULACIONES))
        self.v_cmax.set(int(COLCHON_MAX * 100))
        self.v_paso.set(int(PASO_COLCHON * 100))
        self.v_cap.set(str(DATOS_ENUNCIADO.capacidad_bodega))
        self.v_semilla.set(str(SEMILLA))
        self._cargar_datos_por_defecto()
        self._estado("Valores restablecidos", "trabajando")

    def _cerrar(self):
        self.quit()
        self.destroy()


# =====================================================================
# PROGRAMA PRINCIPAL
# =====================================================================

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
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grafica_costos.png")
    fig.savefig(ruta, dpi=170, facecolor=fig.get_facecolor())
    print(f"\nGráfica guardada en: {ruta}")


def main():
    if "--consola" in sys.argv:
        return modo_consola()
    if tk is None:
        print("No encontré Tkinter, así que no puedo abrir la ventana. Corro en modo consola.\n")
        return modo_consola()
    if sys.platform == "win32":      # evita que la ventana se vea borrosa en pantallas con zoom
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()