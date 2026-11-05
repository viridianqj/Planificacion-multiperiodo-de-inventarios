"""Tarjetas con números clave y las seis pestañas."""

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk

from inventarios.config import DATOS_ENUNCIADO
from inventarios.graficas.dibujo import dibujar_vacio
from inventarios.graficas.temas import TEMA_OSCURO
from inventarios.interfaz.colores import C
from inventarios.interfaz.widgets import Deslizador


class PestanasMixin:
    """Tarjetas con números clave y las seis pestañas."""

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
