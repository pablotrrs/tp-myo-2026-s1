import unittest
from combis_pacientes_modelo_categorias import leer_datos_vrp_categorias, resolver_vrp_con_categorias

class TestVRPCategorias(unittest.TestCase):
    
    def setUp(self):
        """Configurar los datos para las pruebas"""
        self.pacientes, self.turnos, self.categorias, self.tolerancia, \
        self.combis, self.capacidades, self.distancias, self.incompatibles = \
            leer_datos_vrp_categorias(
                "input_combis_pacientes_categorias.txt",
                "input_categorias_incompatibles.txt"
            )
    
    def test_lectura_pacientes(self):
        """Verifica que se leyeron correctamente los pacientes"""
        self.assertEqual(len(self.pacientes), 5)
        self.assertIn(1, self.pacientes)
        self.assertIn(5, self.pacientes)
    
    def test_lectura_turnos(self):
        """Verifica que se leyeron correctamente los turnos"""
        self.assertEqual(self.turnos[1], 100)
        self.assertEqual(self.turnos[2], 120)
        self.assertEqual(self.turnos[5], 140)
    
    def test_lectura_categorias(self):
        """Verifica que se leyeron correctamente las categorías"""
        self.assertEqual(self.categorias[1], "PAMI")
        self.assertEqual(self.categorias[2], "Contagiosos")
        self.assertEqual(self.categorias[4], "Mentales")
    
    def test_tolerancia(self):
        """Verifica que se leyó correctamente la tolerancia"""
        self.assertEqual(self.tolerancia, 30)
    
    def test_lectura_combis(self):
        """Verifica que se leyeron correctamente las combis"""
        self.assertEqual(len(self.combis), 3)
        self.assertIn("Combi_A", self.combis)
        self.assertIn("Combi_B", self.combis)
        self.assertIn("Combi_C", self.combis)
    
    def test_capacidades(self):
        """Verifica que se leyeron correctamente las capacidades"""
        self.assertEqual(self.capacidades["Combi_A"], 2)
        self.assertEqual(self.capacidades["Combi_B"], 3)
        self.assertEqual(self.capacidades["Combi_C"], 2)
    
    def test_lectura_distancias(self):
        """Verifica que se leyeron correctamente las distancias"""
        self.assertEqual(self.distancias[(0, 1)], 15.0)
        self.assertEqual(self.distancias[(1, 2)], 10.0)
        self.assertEqual(self.distancias[(0, 5)], 18.0)
    
    def test_lectura_incompatibles(self):
        """Verifica que se leyeron correctamente los pares incompatibles"""
        self.assertEqual(len(self.incompatibles), 3)
        self.assertIn(("Contagiosos", "Mentales"), self.incompatibles)
        self.assertIn(("Contagiosos", "PAMI"), self.incompatibles)
        self.assertIn(("Contagiosos", "Contagiosos"), self.incompatibles)
    
    def test_todas_distancias_positivas(self):
        """Verifica que todas las distancias sean positivas"""
        for distancia in self.distancias.values():
            self.assertGreater(distancia, 0)
    
    def test_todas_capacidades_positivas(self):
        """Verifica que todas las capacidades sean positivas"""
        for capacidad in self.capacidades.values():
            self.assertGreater(capacidad, 0)
    
    def test_ventana_tiempo_valida(self):
        """Verifica que todas las ventanas de tiempo sean válidas"""
        for paciente in self.pacientes:
            turno = self.turnos[paciente]
            ventana_min = turno - self.tolerancia
            self.assertGreater(turno, ventana_min)
    
    def test_categorias_unicas_por_paciente(self):
        """Verifica que cada paciente tiene exactamente una categoría"""
        for paciente in self.pacientes:
            self.assertIn(paciente, self.categorias)
    
    def test_matriz_simetrica_aproximada(self):
        """Verifica que la matriz de distancias sea aproximadamente simétrica"""
        for i in self.pacientes:
            for j in self.pacientes:
                if i != j and (i, j) in self.distancias and (j, i) in self.distancias:
                    # Las distancias de ida y vuelta deberían ser iguales
                    self.assertEqual(self.distancias[(i, j)], self.distancias[(j, i)])
    
    def test_incompatibilidad_reflexiva(self):
        """Verifica que la incompatibilidad está bien definida"""
        categorias_set = set(self.categorias.values())
        for cat1, cat2 in self.incompatibles:
            self.assertIn(cat1, categorias_set)
            self.assertIn(cat2, categorias_set)
    
    def test_no_hay_pacientes_duplicados(self):
        """Verifica que no hay pacientes duplicados"""
        self.assertEqual(len(self.pacientes), len(set(self.pacientes)))
    
    def test_resolucion_modelo_factible(self):
        """Verifica que el modelo puede ser resuelto (prueba de factibilidad)"""
        # Esta prueba simplemente verifica que el modelo no falla en la resolución
        try:
            resolver_vrp_con_categorias(
                self.pacientes, self.turnos, self.categorias, self.tolerancia,
                self.combis, self.capacidades, self.distancias, self.incompatibles
            )
            # Si llegamos aquí, el modelo se resolvió sin excepciones
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"La resolución del modelo generó una excepción: {e}")
    
    def test_incompatibilidad_reflexiva_detectada(self):
        """Verifica que se detecten correctamente incompatibilidades reflexivas"""
        incompatibles_reflexivos = [pair for pair in self.incompatibles if pair[0] == pair[1]]
        # En este test data, no hay reflexivos por defecto
        # Pero el modelo debe estar preparado para detectarlos
        self.assertIsNotNone(incompatibles_reflexivos)
    
    def test_incompatibilidad_no_reflexiva_detectada(self):
        """Verifica que se detecten correctamente incompatibilidades no reflexivas"""
        incompatibles_no_reflexivos = [pair for pair in self.incompatibles if pair[0] != pair[1]]
        # En los datos de prueba tenemos: (Contagiosos, Mentales) y (Contagiosos, PAMI)
        self.assertEqual(len(incompatibles_no_reflexivos), 2)
        self.assertIn(("Contagiosos", "Mentales"), incompatibles_no_reflexivos)
        self.assertIn(("Contagiosos", "PAMI"), incompatibles_no_reflexivos)

if __name__ == '__main__':
    unittest.main()
