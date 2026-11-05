"""Plan con colchón manual, mouse sobre la gráfica, exportar y restablecer."""

import csv
import os

from tkinter import filedialog
from tkinter import messagebox

from inventarios.config import COLCHON_MAX
from inventarios.config import DATOS_ENUNCIADO
from inventarios.config import N_SIMULACIONES
from inventarios.config import PASO_COLCHON
from inventarios.config import SEMILLA
from inventarios.config import VARIACION
from inventarios.graficas.exportar import figuras_para_exportar
from inventarios.graficas.temas import TEMA_CLARO
from inventarios.graficas.temas import TEMA_OSCURO
from inventarios.informe import plan_a_filas
from inventarios.interfaz.colores import C
from inventarios.modelo import calcular_plan
from inventarios.utilidades import usd


class InteraccionesMixin:
    """Plan con colchón manual, mouse sobre la gráfica, exportar y restablecer."""

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
