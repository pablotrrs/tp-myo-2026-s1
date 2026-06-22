import unittest
import io
from unittest.mock import patch, mock_open
from contextlib import redirect_stdout

from combis_pacientes_con_beneficio import resolver

class TestOrienteeringVRPTW(unittest.TestCase):

    def test_01_paciente_gran_beneficio_pero_no_llega_a_tiempo_es_ignorado(self):
        pacientes = [1, 2]
        turnos = {1: 10, 2: 5}
        beneficios = {1: 10.0, 2: 5000.0} 
        tolerancia = 0
        combis = ['C1']
        capacidades = {'C1': 5} 
        coeficientes = {'C1': 0.0}
        distancias = {(0,1): 5, (1,0): 5, (0,2): 20, (2,0): 20, (1,2): 10, (2,1): 10}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Pacientes recogidos: [1]", output)
        
        linea_pacientes = output.split("Pacientes recogidos:")[1].split("\n")[0]
        self.assertNotIn("2", linea_pacientes)

    def test_02_en_problemas_de_capacidad_combi_elige_paciente_mayor_beneficio(self):
        pacientes = [1, 2]
        turnos = {1: 100, 2: 100}
        beneficios = {1: 10.0, 2: 500.0} 
        tolerancia = 10
        combis = ['C1']
        capacidades = {'C1': 1} 
        coeficientes = {'C1': 0.0}
        distancias = {(0,1): 10, (1,0): 10, (0,2): 10, (2,0): 10, (1,2): 10, (2,1): 10}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Pacientes recogidos: [2]", output)
        
        linea_pacientes = output.split("Pacientes recogidos:")[1].split("\n")[0]
        self.assertNotIn("1", linea_pacientes)

    def test_03_seleccion_mejor_combi(self):
        pacientes = [1]
        turnos = {1: 20}
        beneficios = {1: 100.0}
        tolerancia = 5
        combis = ['Combi_Comun', 'Combi_VIP']
        capacidades = {'Combi_Comun': 5, 'Combi_VIP': 2}
        coeficientes = {'Combi_Comun': 10.0, 'Combi_VIP': 1000.0}
        distancias = {(0,1): 10, (1,0): 10}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Combi seleccionada: Combi_VIP", output)
        self.assertNotIn("Combi seleccionada: Combi_Comun", output)

    def test_04_ninguno_puede_llegar_a_tiempo_da_infactible(self):
        pacientes = [1, 2, 3]
        turnos = {1: 20, 2: 20, 3: 20}
        beneficios = {1: 100.0, 2: 100.0, 3: 100.0}
        tolerancia = 1
        combis = ['A']
        capacidades = {'A': 1}
        coeficientes = {'A': 10.0}
        distancias = {(0,1): 100, (1,0): 100, (0,2): 100, (2,0): 100, (0,3): 100, (3,0): 100}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("No se encontró solución factible", output)
        self.assertNotIn("SOLUCIÓN ÓPTIMA ENCONTRADA", output)

    def test_05_combi_con_bajo_coeficiente_pero_mayor_capacidad_es_elegida_cuando_beneficio_es_alto(self):
        pacientes = [1, 2, 3]
        turnos = {1: 20, 2: 30, 3: 40}
        beneficios = {1: 100.0, 2: 50.0, 3: 20.0}
        tolerancia = 15
        combis = ['A', 'B']
        capacidades = {'A': 1, 'B': 3}
        coeficientes = {'A': 69.0, 'B': 0}
        distancias = {(0,1): 1, (1,0): 1, (0,2): 1, (2,0): 1, (0,3): 1, (3,0): 1, (1,2): 1, (2,1): 1, (1,3): 1, (3,1): 1, (2,3): 1, (3,2): 1}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Combi seleccionada: B", output)
        self.assertNotIn("Combi seleccionada: A", output)
    
    def test_06_combi_elige_el_menos_malo_cuando_tiene_pacientes_beneficio_negativo(self):
        pacientes = [1, 2, 3]
        turnos = {1: 20, 2: 30, 3: 40}
        beneficios = {1: -1.0, 2: -2.0, 3: -3.0}
        tolerancia = 15
        combis = ['A']
        capacidades = {'A': 1}
        coeficientes = {'A': 0}
        distancias = {(0,1): 1, (1,0): 1, (0,2): 1, (2,0): 1, (0,3): 1, (3,0): 1, (1,2): 1, (2,1): 1, (1,3): 1, (3,1): 1, (2,3): 1, (3,2): 1}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Pacientes recogidos: [1]", output)
        
        linea_pacientes = output.split("Pacientes recogidos:")[1].split("\n")[0]
        self.assertIn("1", linea_pacientes)

    def test_07_se_elige_correctamente_entre_combis_coeficiente_negativo(self):
        pacientes = [1, 2, 3]
        turnos = {1: 20, 2: 30, 3: 40}
        beneficios = {1: 100.0, 2: 50.0, 3: 20.0}
        tolerancia = 15
        combis = ['A', 'B']
        capacidades = {'A': 1, 'B': 1}
        coeficientes = {'A': -1.0, 'B': -1.1}
        distancias = {(0,1): 1, (1,0): 1, (0,2): 1, (2,0): 1, (0,3): 1, (3,0): 1, (1,2): 1, (2,1): 1, (1,3): 1, (3,1): 1, (2,3): 1, (3,2): 1}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Combi seleccionada: A", output)
        self.assertNotIn("Combi seleccionada: B", output)

    def test_08_combi_gran_coeficiente_puede_ganar_a_capacidad(self):
        pacientes = [1, 2, 3]
        turnos = {1: 20, 2: 30, 3: 40}
        beneficios = {1: 100.0, 2: 50.0, 3: 20.0}
        tolerancia = 15
        combis = ['A', 'B']
        capacidades = {'A': 1, 'B': 3}
        coeficientes = {'A': 71.0, 'B': 0}
        distancias = {(0,1): 1, (1,0): 1, (0,2): 1, (2,0): 1, (0,3): 1, (3,0): 1, (1,2): 1, (2,1): 1, (1,3): 1, (3,1): 1, (2,3): 1, (3,2): 1}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Combi seleccionada: A", output)
        self.assertNotIn("Combi seleccionada: B", output)

    def test_09_pacientes_alcanzables_individualmente_pero_mutuamente_excluyentes_por_distancia(self):
        pacientes = [1, 2]
        turnos = {1: 10, 2: 12}
        beneficios = {1: 100.0, 2: 300.0}
        tolerancia = 0
        combis = ['A']
        capacidades = {'A': 5}
        coeficientes = {'A': 0.0}
        distancias = {(0,1): 10, (1,0): 10, (0,2): 12, (2,0): 12, (1,2): 50, (2,1): 50}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Pacientes recogidos: [2]", output)
        linea_pacientes = output.split("Pacientes recogidos:")[1].split("\n")[0]
        self.assertNotIn("1", linea_pacientes)
    
    def test_10_combi_llega_temprano_y_espera_al_turno(self):
        pacientes = [1]
        turnos = {1: 50}
        beneficios = {1: 100.0}
        tolerancia = 5
        combis = ['A']
        capacidades = {'A': 1}
        coeficientes = {'A': 0.0}
        distancias = {(0,1): 1, (1,0): 1}

        f = io.StringIO()
        with redirect_stdout(f):
            resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias)
        output = f.getvalue()

        self.assertIn("Pacientes recogidos: [1]", output)
        
        self.assertNotIn("Recogido a los 1.0 min", output)
        self.assertIn("Recogido a los 45.0 min", output)

if __name__ == '__main__':
    unittest.main()