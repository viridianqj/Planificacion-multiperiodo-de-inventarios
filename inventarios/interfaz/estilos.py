"""Fuentes, estilo de la tabla y piezas reutilizables (etiquetas, botones, campos)."""

import tkinter as tk

from tkinter import font as tkfont
from tkinter import ttk

from inventarios.interfaz.colores import C
from inventarios.interfaz.widgets import Deslizador


class EstilosMixin:
    """Fuentes, estilo de la tabla y piezas reutilizables (etiquetas, botones, campos)."""

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
