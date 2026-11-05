"""Ventana principal: junta las piezas de la interfaz."""

import queue
import sys
import tkinter as tk

from inventarios.interfaz.colores import C
from inventarios.interfaz.ejecucion import EjecucionMixin
from inventarios.interfaz.estilos import EstilosMixin
from inventarios.interfaz.interacciones import InteraccionesMixin
from inventarios.interfaz.paneles import PanelesMixin
from inventarios.interfaz.pestanas import PestanasMixin


class App(EstilosMixin, PanelesMixin, PestanasMixin, EjecucionMixin, InteraccionesMixin, tk.Tk):
    """Ventana del planificador de inventarios."""

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


def iniciar():
    """Abre la ventana del planificador."""
    if sys.platform == "win32":      # evita que la ventana se vea borrosa en pantallas con zoom
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()
