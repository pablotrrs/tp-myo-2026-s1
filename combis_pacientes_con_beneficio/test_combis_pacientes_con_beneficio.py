import unittest
import io
from unittest.mock import patch, mock_open
from contextlib import redirect_stdout

from combis_pacientes_con_beneficio import resolver

class TestOrienteeringVRP(unittest.TestCase):

    def test_01_restriccion_capacidad_y_maximizacion(self):
        """
        Escenario: Hay 2 pacientes, pero la combi tiene capacidad para 1 solo.
        El modelo DEBE elegir al paciente que otorga mayor beneficio.
        """
        pacientes = [1, 2]
        beneficios = {1: 10.0, 2: 500.0} # El paciente 2 es mucho más valioso
        combis = ['C1']
        capacidades = {'C1': 1} # Capacidad limitada a 1
        coeficientes = {'C1': 0.0}
        distancias = {(0,1): 10, (1,0): 10, (0,2): 10, (2,0): 10, (1,2): 10, (2,1): 10}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, beneficios, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("SOLUCIÓN ÓPTIMA ENCONTRADA", output)
        self.assertIn("Pacientes recogidos: [2]", output)
        self.assertNotIn("Pacientes recogidos: [1]", output)

    def test_02_seleccion_mejor_combi(self):
        """
        Escenario: 1 paciente, 2 combis disponibles. 
        Ambas tienen capacidad, pero una tiene un coeficiente mucho más alto.
        El modelo DEBE elegir la combi con mejor coeficiente.
        """
        pacientes = [1]
        beneficios = {1: 100.0}
        combis = ['Combi_Mala', 'Combi_Buena']
        capacidades = {'Combi_Mala': 5, 'Combi_Buena': 5}
        coeficientes = {'Combi_Mala': 10.0, 'Combi_Buena': 1000.0}
        distancias = {(0,1): 10, (1,0): 10}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, beneficios, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Combi seleccionada: Combi_Buena", output)
        self.assertNotIn("Combi seleccionada: Combi_Mala", output)

    def test_03_penalizacion_distancia_desempate(self):
        """
        Escenario: 2 pacientes con EXACTAMENTE EL MISMO beneficio. Capacidad para 1.
        El modelo DEBE elegir al paciente que está más cerca para minimizar la ruta,
        gracias al factor de penalización de distancia en la función objetivo.
        """
        pacientes = [1, 2]
        beneficios = {1: 100.0, 2: 100.0}
        combis = ['C1']
        capacidades = {'C1': 1}
        coeficientes = {'C1': 0.0}
        
        # El paciente 1 está a distancia 5. El paciente 2 está a distancia 500.
        distancias = {
            (0,1): 5, (1,0): 5, 
            (0,2): 500, (2,0): 500,
            (1,2): 10, (2,1): 10
        }

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, beneficios, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        # Al estar más cerca, la "penalización" de la F.O. del P1 es menor, por lo que su valor neto es mayor.
        self.assertIn("Pacientes recogidos: [1]", output)
        self.assertNotIn("Pacientes recogidos: [2]", output)

if __name__ == '__main__':
    unittest.main()