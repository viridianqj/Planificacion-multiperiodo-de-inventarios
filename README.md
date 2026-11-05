# Planificador de Inventarios

Investigación de Operaciones · Ejercicio 3: planificación multiperíodo de inventarios
(4 productos, 3 meses) con programación lineal (PuLP) y simulación de la demanda (±20%).

## Instalación

```
pip install -r requirements.txt
```

## Uso

```
python main.py             # abre la interfaz
python main.py --consola   # modo texto (guarda salidas/grafica_costos.png)
python -m unittest         # pruebas
```

## Estructura

```
proyecto_inventarios/
├── main.py                  Punto de entrada
├── requirements.txt
├── inventarios/
│   ├── config.py            Datos del problema y valores por defecto
│   ├── modelo.py            Parte 1: plan de compras con PuLP
│   ├── simulacion.py        Parte 2: simulación Monte Carlo de la demanda
│   ├── analisis.py          Pasos A, B y C (mejor colchón, plan y comparación)
│   ├── informe.py           Texto del informe y filas del plan (CSV)
│   ├── utilidades.py        Formato de dinero
│   ├── consola.py           Modo texto
│   ├── graficas/
│   │   ├── temas.py         Temas: oscuro, claro y blanco y negro
│   │   ├── dibujo.py        Las cuatro gráficas
│   │   └── exportar.py      Exportar gráficas a PNG
│   └── interfaz/
│       ├── colores.py       Paleta de la ventana
│       ├── widgets.py       Deslizador propio
│       ├── estilos.py       Fuentes, botones, campos
│       ├── paneles.py       Encabezado y panel de parámetros
│       ├── pestanas.py      Tarjetas y pestañas
│       ├── ejecucion.py     Cálculo en segundo plano y resultados
│       ├── interacciones.py Plan manual, mouse, exportar, restablecer
│       └── ventana.py       Ventana principal (App)
├── tests/                   Pruebas unitarias
└── salidas/                 Gráficas y archivos generados
```

## Notas

- Compatible con PuLP 3 y PuLP 4. En PuLP 4 el solver es HiGHS (`highspy`).
- La semilla aleatoria es fija (2026): los resultados son reproducibles.
