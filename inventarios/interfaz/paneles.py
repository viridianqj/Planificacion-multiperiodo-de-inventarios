"""Encabezado y panel izquierdo con los parámetros."""

import tkinter as tk

from inventarios.config import COLCHON_MAX
from inventarios.config import DATOS_ENUNCIADO
from inventarios.config import N_SIMULACIONES
from inventarios.config import PASO_COLCHON
from inventarios.config import SEMILLA
from inventarios.config import VARIACION
from inventarios.interfaz.colores import C


class PanelesMixin:
    """Encabezado y panel izquierdo con los parámetros."""

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
