import unittest

from inventarios.analisis import analizar
from inventarios.config import DATOS_ENUNCIADO


class TestAnalisis(unittest.TestCase):
    def test_resultado_con_los_datos_del_enunciado(self):
        res = analizar(DATOS_ENUNCIADO.copia())
        self.assertEqual(round(res.mejor_colchon * 100), 12)
        self.assertEqual(round(res.menor_costo), 3309)
        self.assertEqual(round(res.costo_plan), 154713)
        self.assertAlmostEqual(res.ahorro, 19.3, delta=0.1)

    def test_es_reproducible(self):
        a = analizar(DATOS_ENUNCIADO.copia(), n_sim=300)
        b = analizar(DATOS_ENUNCIADO.copia(), n_sim=300)
        self.assertEqual(a.costos_totales, b.costos_totales)


if __name__ == "__main__":
    unittest.main()
