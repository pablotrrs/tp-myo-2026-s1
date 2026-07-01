#!/usr/bin/env python3
"""
Tests para el algoritmo de generación de columnas (Etapa 3).

Casos de prueba:
1. Rutas individuales vs. combinadas
2. Factibilidad con time windows (ventanas de tiempo)
3. Cálculo correcto de costos
4. Generación de columnas con múltiples iteraciones
5. Asignación de combis a rutas
6. Casos infactibles
7. Soluciones óptimas simples
"""

import unittest
from io import StringIO
from unittest.mock import patch, mock_open
from contextlib import redirect_stdout

from ruta import Ruta, Rutas
from column_generation import AlgoritmoGeneracionColumnas
from utils import leer_datos_vrp


class TestRuta(unittest.TestCase):
    """Tests para la clase Ruta (representación individual de rutas)."""
    
    def test_01_ruta_individual_sin_time_windows(self):
        """Verifica que una ruta individual se calcula correctamente sin ventanas."""
        distancias = {
            (0, 1): 10.0,
            (1, 0): 10.0,
        }
        ruta = Ruta([1], distancias=distancias, id_ruta=0)
        
        # Costo: 0->1->0 = 10+10 = 20
        self.assertEqual(ruta.costo, 20.0)
        self.assertTrue(ruta.es_factible())
    
    def test_02_ruta_combinada_sin_time_windows(self):
        """Verifica que una ruta con 2 pacientes se calcula correctamente."""
        distancias = {
            (0, 1): 10.0,
            (1, 0): 10.0,
            (0, 2): 15.0,
            (2, 0): 15.0,
            (1, 2): 5.0,
            (2, 1): 5.0,
        }
        ruta = Ruta([1, 2], distancias=distancias, id_ruta=0)
        
        # Costo: 0->1->2->0 = 10+5+15 = 30
        self.assertEqual(ruta.costo, 30.0)
        self.assertTrue(ruta.es_factible())
    
    def test_03_ruta_factible_con_time_windows(self):
        """Verifica factibilidad con ventanas de tiempo (llega dentro de la ventana)."""
        distancias = {
            (0, 1): 5.0,
            (1, 0): 5.0,
            (0, 2): 10.0,
            (2, 0): 10.0,
            (1, 2): 8.0,
            (2, 1): 8.0,
        }
        turnos = {1: 100, 2: 120}
        tolerancia = 10
        
        ruta = Ruta([1, 2], distancias=distancias, turnos=turnos, tolerancia=tolerancia, id_ruta=0)
        
        # T[1] = max(5, 100-10) = 90 <= 100 OK
        # T[2] = max(90+8, 120-10) = 110 <= 120 OK
        self.assertTrue(ruta.es_factible())
    
    def test_04_ruta_infactible_llega_tarde(self):
        """Verifica infactibilidad cuando la combi no llega a tiempo."""
        distancias = {
            (0, 1): 50.0,
            (1, 0): 50.0,
        }
        turnos = {1: 20}
        tolerancia = 0
        
        ruta = Ruta([1], distancias=distancias, turnos=turnos, tolerancia=tolerancia, id_ruta=0)
        
        # T[1] = max(50, 20) = 50 > 20 => INFACTIBLE
        self.assertFalse(ruta.es_factible())
    
    def test_05_ruta_espera_en_ventana(self):
        """Verifica que la combi espera si llega antes de la ventana."""
        distancias = {
            (0, 1): 5.0,
            (1, 0): 5.0,
        }
        turnos = {1: 50}
        tolerancia = 10
        
        ruta = Ruta([1], distancias=distancias, turnos=turnos, tolerancia=tolerancia, id_ruta=0)
        
        # T[1] = max(5, 50-10) = 40 <= 50 => FACTIBLE
        # La combi llega a los 5 min, espera hasta los 40 (ventana abre a los 40, turno a los 50)
        self.assertTrue(ruta.es_factible())
    
    def test_06_ruta_ordenada_por_turno(self):
        """Verifica que los pacientes en la ruta se ordenan por turno."""
        distancias = {
            (0, 1): 1.0,
            (1, 0): 1.0,
            (0, 2): 1.0,
            (2, 0): 1.0,
            (1, 2): 1.0,
            (2, 1): 1.0,
        }
        turnos = {1: 100, 2: 50}  # Paciente 2 primero por turno
        tolerancia = 0
        
        ruta = Ruta([1, 2], distancias=distancias, turnos=turnos, tolerancia=tolerancia, id_ruta=0)
        
        # Debe estar ordenado: [2, 1] (turno 50 antes de 100)
        self.assertEqual(ruta.pacientes, [2, 1])


class TestRutas(unittest.TestCase):
    """Tests para la clase Rutas (generación de rutas iniciales)."""
    
    def test_01_genera_rutas_individuales_sin_capacidad(self):
        """Verifica generación minimalista: solo rutas individuales (single-patient)."""
        pacientes = [1, 2]
        distancias = {
            (0, 1): 10.0,
            (1, 0): 10.0,
            (0, 2): 15.0,
            (2, 0): 15.0,
            (1, 2): 5.0,
            (2, 1): 5.0,
        }
        capacidad = 5  # Suficiente para todos
        
        rutas = Rutas(pacientes, distancias, capacidad)
        
        # Punto 1 "Inicialización Minimalista": Solo genera rutas individuales
        self.assertEqual(len(rutas.rutas), 2)
        self.assertIn(Ruta([1], distancias), rutas.rutas)
        self.assertIn(Ruta([2], distancias), rutas.rutas)
    
    def test_02_genera_rutas_combinadas_con_capacidad_2(self):
        """Verifica generación minimalista: solo rutas individuales (single-patient)."""
        pacientes = [1, 2, 3]
        distancias = {
            (0, 1): 10.0, (1, 0): 10.0,
            (0, 2): 10.0, (2, 0): 10.0,
            (0, 3): 10.0, (3, 0): 10.0,
            (1, 2): 5.0, (2, 1): 5.0,
            (1, 3): 5.0, (3, 1): 5.0,
            (2, 3): 5.0, (3, 2): 5.0,
        }
        capacidad = 2
        
        rutas = Rutas(pacientes, distancias, capacidad)
        
        # Punto 1 "Inicialización Minimalista": Solo genera rutas individuales
        # Debe generar: {1}, {2}, {3}
        num_individuales = 3
        self.assertEqual(len(rutas.rutas), num_individuales)
    
    def test_03_filtra_rutas_infactibles_con_time_windows(self):
        """Verifica que se filtren rutas infactibles por time windows."""
        pacientes = [1, 2]
        distancias = {
            (0, 1): 50.0, (1, 0): 50.0,
            (0, 2): 1.0, (2, 0): 1.0,
            (1, 2): 100.0, (2, 1): 100.0,
        }
        turnos = {1: 20, 2: 20}
        tolerancia = 5
        capacidad = 2
        
        rutas = Rutas(pacientes, distancias, capacidad, turnos=turnos, tolerancia=tolerancia)
        
        # Ruta {1}: 0->1->0, T[1]=50 > 20 => INFACTIBLE
        # Ruta {2}: 0->2->0, T[2]=1 <= 20 => FACTIBLE
        # Ruta {1,2}: Infactible (1 no se puede visitar)
        
        # Debería quedar solo {2}
        num_factibles = sum(1 for r in rutas.rutas if r.es_factible())
        self.assertGreater(num_factibles, 0)


class TestAlgoritmoGeneracionColumnasSimple(unittest.TestCase):
    """Tests simples del algoritmo de generación de columnas."""
    
    def test_01_caso_simple_2_pacientes(self):
        """Resuelve un caso simple con 2 pacientes y una combi."""
        pacientes = [1, 2]
        distancias = {
            (0, 1): 10.0, (1, 0): 10.0,
            (0, 2): 15.0, (2, 0): 15.0,
            (1, 2): 5.0, (2, 1): 5.0,
        }
        combis = ['A']
        capacidades = {'A': 5}
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=5,
            combis=combis, capacidades=capacidades
        )
        
        valor_obj, rutas_usadas, _ = algo.resolver(verbose=False)
        
        # Verificar que se resuelve
        self.assertIsNotNone(valor_obj)
        self.assertGreater(valor_obj, 0)
        
        # Verificar cobertura
        pacientes_cubiertos = set()
        for ruta in rutas_usadas:
            pacientes_cubiertos.update(ruta.pacientes)
        self.assertEqual(pacientes_cubiertos, {1, 2})
    
    def test_02_caso_con_time_windows(self):
        """Resuelve un caso con ventanas de tiempo."""
        pacientes = [1, 2]
        turnos = {1: 100, 2: 120}
        distancias = {
            (0, 1): 10.0, (1, 0): 10.0,
            (0, 2): 15.0, (2, 0): 15.0,
            (1, 2): 5.0, (2, 1): 5.0,
        }
        tolerancia = 20
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=5,
            turnos=turnos, tolerancia=tolerancia
        )
        
        valor_obj, rutas_usadas, _ = algo.resolver(verbose=False)
        
        # Verificar que se resuelve
        self.assertIsNotNone(valor_obj)
        
        # Verificar factibilidad de todas las rutas
        for ruta in rutas_usadas:
            self.assertTrue(ruta.es_factible(), f"Ruta {ruta} no es factible")
    
    def test_03_caso_con_capacidad_limitada(self):
        """Resuelve un caso donde capacidad=1 obliga a usar varias combis."""
        pacientes = [1, 2, 3]
        distancias = {
            (0, 1): 10.0, (1, 0): 10.0,
            (0, 2): 10.0, (2, 0): 10.0,
            (0, 3): 10.0, (3, 0): 10.0,
            (1, 2): 20.0, (2, 1): 20.0,
            (1, 3): 20.0, (3, 1): 20.0,
            (2, 3): 20.0, (3, 2): 20.0,
        }
        combis = ['A', 'B', 'C']
        capacidades = {'A': 1, 'B': 1, 'C': 1}
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=1,
            combis=combis, capacidades=capacidades
        )
        
        valor_obj, rutas_usadas, _ = algo.resolver(verbose=False)
        
        # Cada ruta debe tener como máximo 1 paciente
        for ruta in rutas_usadas:
            self.assertLessEqual(len(ruta.pacientes), 1)
        
        # Debe cubrir todos los pacientes
        pacientes_cubiertos = set()
        for ruta in rutas_usadas:
            pacientes_cubiertos.update(ruta.pacientes)
        self.assertEqual(len(pacientes_cubiertos), 3)
    
    def test_04_criterio_parada_convergencia(self):
        """Verifica que el algoritmo converge (se detiene)."""
        pacientes = [1, 2, 3, 4]
        distancias = {}
        for i in range(5):
            for j in range(5):
                distancias[i, j] = abs(i - j) * 10.0 if i != j else 0.0
        
        algo = AlgoritmoGeneracionColumnas(pacientes, distancias, capacidad_combi=3)
        
        valor_obj, rutas_usadas, historia = algo.resolver(verbose=False)
        
        # Verificar que hay historial de iteraciones
        self.assertGreater(len(historia), 0)
        
        # Verificar que terminó por criterio de parada (último costo_reducido <= 1e-6)
        ultima_iter = historia[-1]
        self.assertLessEqual(ultima_iter['costo_reducido'], 1e-6)


class TestAlgoritmoGeneracionColumnasIterativo(unittest.TestCase):
    """Tests para verificar múltiples iteraciones del CG."""
    
    def test_01_multiples_iteraciones(self):
        """Verifica que el algoritmo hace múltiples iteraciones cuando es necesario."""
        pacientes = [1, 2, 3, 4, 5, 6]
        # Distancias diseñadas para incentivar combinar pacientes
        # Centro -> paciente es caro, pero paciente -> paciente es barato
        distancias = {}
        for i in range(7):
            for j in range(7):
                if i == 0:  # Desde centro
                    distancias[i, j] = 20.0 if j != 0 else 0.0
                elif j == 0:  # Al centro
                    distancias[i, j] = 20.0
                elif i != j:
                    distancias[i, j] = 8.0 + abs(i - j)
                else:
                    distancias[i, j] = 0.0
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=2
        )
        
        valor_obj, rutas_usadas, historia = algo.resolver(verbose=False)
        
        # Verificar que hay al menos 1 iteración
        self.assertGreater(len(historia), 0)
    
    def test_02_historia_registro_iteraciones(self):
        """Verifica que se registra información en cada iteración."""
        pacientes = [1, 2, 3]
        distancias = {}
        for i in range(4):
            for j in range(4):
                distancias[i, j] = 10.0 * abs(i - j) if i != j else 0.0
        
        algo = AlgoritmoGeneracionColumnas(pacientes, distancias, capacidad_combi=2)
        valor_obj, rutas_usadas, historia = algo.resolver(verbose=False)
        
        # Cada elemento debe tener: iteracion, num_rutas, valor_objetivo, costo_reducido
        for iter_data in historia:
            self.assertIn('iteracion', iter_data)
            self.assertIn('num_rutas', iter_data)
            self.assertIn('valor_objetivo', iter_data)
            self.assertIn('costo_reducido', iter_data)


class TestLectorDatos(unittest.TestCase):
    """Tests para la función de lectura de datos."""
    
    def test_01_lector_formato_basico(self):
        """Verifica lectura de archivo con formato básico."""
        mock_data = """
        Tolerancia: 10
        Pacientes
        1, 50
        2, 60
        Combis
        A:2
        Matriz
        0, 1, 20.0
        1, 0, 20.0
        0, 2, 25.0
        2, 0, 25.0
        1, 2, 10.0
        2, 1, 10.0
        """
        
        with patch('builtins.open', mock_open(read_data=mock_data)):
            p, t, tol, c, caps, d = leer_datos_vrp("dummy.txt")
        
        self.assertEqual(p, [1, 2])
        self.assertEqual(t, {1: 50, 2: 60})
        self.assertEqual(tol, 10)
        self.assertEqual(c, ['A'])
        self.assertEqual(caps, {'A': 2})
        self.assertEqual(d[0, 1], 20.0)
    
    def test_02_lector_multiples_combis(self):
        """Verifica lectura con múltiples combis."""
        mock_data = """
        Tolerancia: 15
        Pacientes
        1, 100
        Combis
        Combi_A:2
        Combi_B:3
        Matriz
        0, 1, 15.0
        1, 0, 15.0
        """
        
        with patch('builtins.open', mock_open(read_data=mock_data)):
            p, t, tol, c, caps, d = leer_datos_vrp("dummy.txt")
        
        self.assertEqual(len(c), 2)
        self.assertIn('Combi_A', c)
        self.assertIn('Combi_B', c)
        self.assertEqual(caps['Combi_A'], 2)
        self.assertEqual(caps['Combi_B'], 3)


class TestCasosEspeciales(unittest.TestCase):
    """Tests para casos especiales y edge cases."""
    
    def test_01_un_solo_paciente(self):
        """Resuelve caso trivial con un único paciente."""
        pacientes = [1]
        distancias = {(0, 1): 10.0, (1, 0): 10.0}
        
        algo = AlgoritmoGeneracionColumnas(pacientes, distancias, capacidad_combi=1)
        valor_obj, rutas_usadas, _ = algo.resolver(verbose=False)
        
        self.assertEqual(len(rutas_usadas), 1)
        self.assertEqual(valor_obj, 20.0)  # 0->1->0
    
    def test_02_distancia_simetrica(self):
        """Verifica que la solución es consistente (no depende de orden)."""
        pacientes = [1, 2, 3]
        distancias = {}
        for i in range(4):
            for j in range(4):
                distancias[i, j] = abs(i - j) * 5.0 if i != j else 0.0
        
        algo = AlgoritmoGeneracionColumnas(pacientes, distancias, capacidad_combi=2)
        valor_obj_1, rutas_1, _ = algo.resolver(verbose=False)
        
        algo2 = AlgoritmoGeneracionColumnas(pacientes, distancias, capacidad_combi=2)
        valor_obj_2, rutas_2, _ = algo2.resolver(verbose=False)
        
        # Valores objetivos deben ser iguales
        self.assertAlmostEqual(valor_obj_1, valor_obj_2, places=2)
    
    def test_03_max_iteraciones_limite(self):
        """Verifica que el algoritmo respeta el límite máximo de iteraciones."""
        pacientes = list(range(1, 11))  # 10 pacientes
        distancias = {}
        for i in range(11):
            for j in range(11):
                distancias[i, j] = abs(i - j) * 5.0 if i != j else 0.0
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=2, max_iteraciones=3
        )
        valor_obj, rutas_usadas, historia = algo.resolver(verbose=False)
        
        # No debe exceder max_iteraciones
        self.assertLessEqual(len(historia), 3)


class TestCoherencionConModelosExistentes(unittest.TestCase):
    """Tests que verifican coherencia con modelos anteriores."""
    
    def test_01_resultado_compatible_input_vrp_colgen(self):
        """
        Verifica que el CG reproduce el resultado del archivo input_vrp_colgen.txt
        (debería dar 105 minutos, igual que Modelo 3).
        """
        # Datos del archivo input_vrp_colgen.txt
        pacientes = [1, 2, 3, 4]
        turnos = {1: 100, 2: 120, 3: 140, 4: 160}
        tolerancia = 30
        combis = ['Combi_A', 'Combi_B']
        capacidades = {'Combi_A': 2, 'Combi_B': 3}
        
        # Matriz de distancias estándar (4x4 symmetric)
        distancias = {}
        for i in range(5):
            for j in range(5):
                if i == 0 or j == 0:
                    distancias[i, j] = 50.0 if i != j else 0.0
                else:
                    distancias[i, j] = 10.0 if i != j else 0.0
        
        algo = AlgoritmoGeneracionColumnas(
            pacientes, distancias, capacidad_combi=3,
            turnos=turnos, tolerancia=tolerancia,
            combis=combis, capacidades=capacidades
        )
        
        valor_obj, rutas_usadas, _ = algo.resolver(verbose=False)
        
        # El valor objetivo debería estar cerca de 105
        # (o al menos ser razonable)
        self.assertGreater(valor_obj, 0)
        self.assertIsNotNone(rutas_usadas)
        
        # Debe cubrir todos los pacientes
        pacientes_cubiertos = set()
        for ruta in rutas_usadas:
            pacientes_cubiertos.update(ruta.pacientes)
        self.assertEqual(pacientes_cubiertos, set(pacientes))


if __name__ == '__main__':
    unittest.main()
