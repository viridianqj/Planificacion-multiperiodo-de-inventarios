"""Widgets propios de la ventana."""

import tkinter as tk

from inventarios.interfaz.colores import C


class Deslizador(tk.Canvas):
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
