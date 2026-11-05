"""Texto del informe (consola y pestaña Resumen) y tabla del plan para exportar."""

from inventarios.utilidades import usd

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
