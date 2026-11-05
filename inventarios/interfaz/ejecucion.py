"""Ejecución del análisis en un hilo y pintado de resultados."""

import queue
import threading

from tkinter import messagebox

from inventarios.analisis import analizar
from inventarios.config import DATOS_ENUNCIADO
from inventarios.config import Datos
from inventarios.graficas.dibujo import dibujar_comparacion
from inventarios.graficas.dibujo import dibujar_costos
from inventarios.graficas.dibujo import dibujar_inventario
from inventarios.graficas.dibujo import dibujar_plan
from inventarios.graficas.temas import TEMA_OSCURO
from inventarios.informe import construir_informe
from inventarios.utilidades import usd


class EjecucionMixin:
    """Ejecución del análisis en un hilo y pintado de resultados."""

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
