import unittest
from unittest.mock import patch, mock_open

# Importamos solo el lector
from lector_datos_beneficios import leer

class TestLectorDatosBeneficios(unittest.TestCase):

    def test_01_lector_con_turnos_y_tolerancia(self):
        mock_data = """
        Tolerancia: 15
        Pacientes
        1, 30, 50.0
        2, 45, 100.0
        Combis
        C1 : 2, 10.0
        Matriz
        0, 1, 5.0
        1, 0, 5.0
        """
        
        with patch('builtins.open', mock_open(read_data=mock_data)):
            p, t, b, tol, c, caps, coefs, dists = leer("dummy.txt")

        self.assertEqual(tol, 15)
        self.assertEqual(p, [1, 2])
        self.assertEqual(t, {1: 30, 2: 45})
        self.assertEqual(b, {1: 50.0, 2: 100.0})
        self.assertEqual(c, ['C1'])
        self.assertEqual(caps, {'C1': 2})
        self.assertEqual(coefs, {'C1': 10.0})
        self.assertEqual(dists[0, 1], 5.0)

if __name__ == '__main__':
    unittest.main()