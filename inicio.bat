@echo off
title Planificacion Multiperiodo - Analisis Basico
cls
echo.
echo  ==================================================
echo  Planificacion Multiperiodo de Inventarios
echo  Analisis Basico
echo  ==================================================
echo.
echo  Verificando entorno y ejecucion de analisis basico...
echo.
python -c "from inventarios.config import DATOS_ENUNCIADO; from inventarios.modelo import calcular_plan; from inventarios.simulacion import promedio_de_costos; plan, g, c = calcular_plan(0.12, DATOS_ENUNCIADO); g_r, f_r = promedio_de_costos('rigida', 0, DATOS_ENUNCIADO); g_o, f_o = promedio_de_costos('optimizada', 0.12, DATOS_ENUNCIADO); ahorro = (1-(g_o+f_o)/(g_r+f_r))*100
print('Mejor colchon: 12%')
print('Ahorro: ', ahorro, '%')
echo.
echo  Analisis basico completado exitosamente.
echo.
pause > nul