"""Punto de entrada.

    python main.py             abre la interfaz
    python main.py --consola   modo texto
"""
import sys


def main():
    if "--consola" in sys.argv:
        from inventarios.consola import modo_consola
        return modo_consola()
    try:
        __import__("tkinter")
    except ImportError:
        print("No encontré Tkinter, así que no puedo abrir la ventana. Corro en modo consola.\n")
        from inventarios.consola import modo_consola
        return modo_consola()
    from inventarios.interfaz import iniciar
    iniciar()


if __name__ == "__main__":
    main()
