import unittest

from inventarios.config import DATOS_ENUNCIADO
from inventarios.modelo import calcular_plan


class TestModelo(unittest.TestCase):
    def test_balance_y_colchon(self):
        d = DATOS_ENUNCIADO
        compras, guardado, _ = calcular_plan(0.12, d)
        for p in d.productos:
            tenia = 0
            for i in range(3):
                self.assertAlmostEqual(guardado[p][i], tenia + compras[p][i] - d.demanda[p][i], delta=1)
                tenia = guardado[p][i]
            self.assertAlmostEqual(guardado[p][0], 0.12 * d.demanda[p][1], delta=1)
            self.assertEqual(guardado[p][2], 0)

    def test_bodega_muy_pequena_no_tiene_plan(self):
        d = DATOS_ENUNCIADO.copia()
        d.capacidad_bodega = 50
        with self.assertRaises(ValueError):
            calcular_plan(0.30, d)


if __name__ == "__main__":
    unittest.main()
