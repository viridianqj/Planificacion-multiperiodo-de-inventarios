"""Temas de color: oscuro (ventana), claro (PNG) y blanco y negro (impresión)."""

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
