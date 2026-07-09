import sys
import unittest
import os
import shutil
from SaludCG import SaludCG

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root)

from Salud.utils_salud import parsear_salida

class TestModeloSaludCG(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.crear_carpetas_temporales()

    @classmethod
    def crear_carpetas_temporales(cls):
        os.makedirs("./IN", exist_ok=True)
        os.makedirs("./OUT_model2", exist_ok=True)  

    @classmethod
    def tearDownClass(cls):
        cls.borrar_carpetas_temporales()

    @classmethod
    def borrar_carpetas_temporales(cls):
        archivos_a_borrar = (["test_optimo", "test_cap", "test_incomp", "test_perdida", "test_beneficio_negativo", "test_cantidad_supera_calidad",
                               "test_calidad_supera_cantidad", "test_combi_mayor_costo_mayor_beneficio", "test_combi_menor_costo_mayor_beneficio",
                               "test_paciente_lejano_mejor_beneficio", "test_paciente_lejano_no_da_mejor_beneficio", "test_dos_combis_pueden_buscar_paciente_lejano",
                               "test_paciente_inalcanzable", "test_orden_ventanas", "test_incomp_multi_combi", "test_propagacion_espera",
                                "test_dos_combis_con_uno_de_capacidad"])
        for archivo in archivos_a_borrar:
            ruta = f"./IN/{archivo}_pacientes.in"
            if os.path.exists(ruta):
                os.remove(ruta)
            ruta = f"./IN/{archivo}_flota.in"
            if os.path.exists(ruta):
                os.remove(ruta)
            ruta = f"./IN/{archivo}_incompatibilidades.in"
            if os.path.exists(ruta):
                os.remove(ruta)
            ruta = f"./OUT_model2/{archivo}.out"  
            if os.path.exists(ruta):
                os.remove(ruta)

    def crear_instancia(self, nombre, pacientes, flota, incompatibilidades):
        with open(f"./IN/{nombre}_pacientes.in", "w", encoding='utf-8') as f:
            f.write("0, 0.0, 0.0\n")
            for p in pacientes:
                f.write(f"{p[0]}, {p[1]}, {p[2]}, {p[3]}, {p[4]}, {p[5]}, {p[6]}\n")
                
        with open(f"./IN/{nombre}_flota.in", "w", encoding='utf-8') as f:
            for c in flota:
                f.write(f"{c[0]}, {c[1]}, {c[2]}, {c[3]}\n")
                
        with open(f"./IN/{nombre}_incompatibilidades.in", "w", encoding='utf-8') as f:
            for inc in incompatibilidades:
                f.write(f"{inc[0]}, {inc[1]}\n")

    def leer_resultado(self, nombre):
        ruta = f"./OUT_model2/{nombre}.out" 
        self.assertTrue(os.path.exists(ruta), f"El archivo {ruta} no se generó.")
        with open(ruta, "r") as f:
            contenido = f.read()
            
        contenido_adaptado = contenido.replace("->", " -> ")
        return parsear_salida(contenido_adaptado)

    # ==========================================
    # TESTS DE COMPORTAMIENTO CG
    # ==========================================

    def test_01_solucion_optima_simple(self):
        self.crear_instancia(
            "test_optimo",
            pacientes=[
                ["1", 0.0, 10.0, 5, 50, "Común", 100],
                ["2", 0.0, 20.0, 10, 60, "Común", 100]
            ],
            flota=[["Combi_A", 1, 2, 50]],
            incompatibilidades=[]
        )
        
        exito = SaludCG("test_optimo", threshold=10.0)
        self.assertTrue(exito, "El modelo debería ejecutarse sin errores.")
        
        beneficio, rutas, no_atendidos = self.leer_resultado("test_optimo")
        self.assertEqual(beneficio, 150.0, "El beneficio no es el óptimo matemático.")
        self.assertEqual(len(no_atendidos), 0, "No debería quedar nadie sin atender.")

    def test_02_restriccion_capacidad_estricta(self):
        self.crear_instancia(
            "test_cap",
            pacientes=[
                ["1", 0.0, 10.0, 5, 50, "Común", 100],
                ["2", 0.0, 20.0, 10, 60, "Común", 200]
            ],
            flota=[["Combi_A", 1, 1, 50]],
            incompatibilidades=[]
        )
        
        SaludCG("test_cap", threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado("test_cap")
        
        self.assertEqual(beneficio, 150.0)
        self.assertIn(1, no_atendidos, "El paciente 1 (menor beneficio) debería quedar afuera.")
        self.assertEqual(len(rutas[0][1]), 3, "La ruta debe ser [0, 2, 0]")

    def test_03_eleccion_por_incompatibilidad(self):
        self.crear_instancia(
            "test_incomp",
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Inmunodeprimido", 100],
                ["2", 0.0, 20.0, 0, 100, "Infeccioso", 300]
            ],
            flota=[["Combi_Grande", 1, 5, 50]],
            incompatibilidades=[["Inmunodeprimido", "Infeccioso"]]
        )
        
        SaludCG("test_incomp", threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado("test_incomp")
        
        self.assertEqual(beneficio, 250.0)
        self.assertIn(1, no_atendidos, "El paciente incompatible de menor valor debe ser excluido.")

    def test_04_no_despachar_si_hay_perdida(self):
        self.crear_instancia(
            "test_perdida",
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 50]
            ],
            flota=[["Combi_Cara", 1, 5, 1000]],
            incompatibilidades=[]
        )
        
        SaludCG("test_perdida", threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado("test_perdida")
        
        self.assertEqual(beneficio, 0.0, "El beneficio óptimo es 0 (no despachar).")
        self.assertEqual(len(rutas), 0, "No se debería usar ninguna ruta.")
        self.assertIn(1, no_atendidos, "El paciente no debe ser atendido.")
    
    def test_05_no_buscar_beneficio_negativo(self):
        nombre_test = "test_beneficio_negativo"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 20],
                ["2", 0.0, 10.0, 0, 100, "Común", -5]
            ],
            flota=[["Combi_A", 1, 5, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 10, "El beneficio óptimo es 0 (no buscar al paciente 2).")
        self.assertEqual(len(rutas[0][1]), 3, "Debería ser la ruta 0 -> 1 -> 0.")
        self.assertIn(2, no_atendidos, "El paciente 2 no debe ser atendido.")
    
    def test_06_elegir_cantidad_si_supera_calidad(self):
        nombre_test = "test_cantidad_supera_calidad"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 20],
                ["2", 0.0, 10.0, 0, 100, "Común", 10],
                ["3", 0.0, 10.0, 0, 100, "Covid-19", 29]
            ],
            flota=[["Combi_A", 1, 2, 10]],
            incompatibilidades=[["Común", "Covid-19"]]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 20, "El beneficio óptimo es 20 (Buscar a los pacientes 1 y 2).")
        self.assertEqual(len(rutas[0][1]), 4, "Debería ser una ruta del estilo 0 -> 1 -> 2 -> 0.")
        self.assertIn(3, no_atendidos, "El paciente 3 no debe ser atendido.")

    def test_07_elegir_calidad_si_supera_cantidad(self):
        nombre_test = "test_calidad_supera_cantidad"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 20],
                ["2", 0.0, 10.0, 0, 100, "Común", 10],
                ["3", 0.0, 10.0, 0, 100, "Covid-19", 31]
            ],
            flota=[["Combi_A", 1, 2, 10]],
            incompatibilidades=[["Común", "Covid-19"]]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 21, "El beneficio óptimo es 21 (Buscar al paciente 3).")
        self.assertEqual(len(rutas[0][1]), 3, "Debería ser una ruta del estilo 0 -> 3 -> 0.")
        self.assertIn(1, no_atendidos, "El paciente 1 no debe ser atendido.")
        self.assertIn(2, no_atendidos, "El paciente 2 no debe ser atendido.")
    
    def test_08_elegir_combi_de_mayor_costo_si_da_mejor_beneficio(self):
        nombre_test = "test_combi_mayor_costo_mayor_beneficio"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 20],
                ["2", 0.0, 10.0, 0, 100, "Común", 20],
            ],
            flota=[["Combi_A", 1, 1, 10], ["Combi_B", 1, 2, 20]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 20, "El beneficio óptimo es 20 (Usar combi_b y buscar ambos pacientes).")
        self.assertEqual(len(rutas[0][1]), 4, "Debería ser una ruta del estilo 0 -> 1 -> 2 -> 0.")
        self.assertEqual(no_atendidos, [])

    def test_09_elegir_combi_de_menor_costo_si_da_mejor_beneficio(self):
        nombre_test = "test_combi_menor_costo_mayor_beneficio"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 100, "Común", 20],
                ["2", 0.0, 10.0, 0, 100, "Común", 20],
            ],
            flota=[["Combi_A", 1, 1, 10], ["Combi_B", 1, 2, 31]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 10, "El beneficio óptimo es 10 (Usar combi_a y buscar a uno de los pacientes).")
        self.assertEqual(len(rutas[0][1]), 3, "Debería ser una ruta del estilo 0 -> 1/2 -> 0.")
        self.assertTrue(1 in no_atendidos or 2 in no_atendidos, "Uno de los dos pacientes no debe ser atendido.")
    
    def test_10_elige_paciente_lejano_si_da_mejor_beneficio(self):
        nombre_test = "test_paciente_lejano_mejor_beneficio"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 10, "Común", 20],
                ["2", 0.0, 20.0, 0, 20, "Común", 20],   
                ["3", 0.0, -30.0, 0, 30, "Común", 41]
            ],
            flota=[["Combi_A", 1, 3, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 31, "El beneficio óptimo es 31 (Buscar paciente 3).")
        self.assertEqual(len(rutas[0][1]), 3, "Debería ser una ruta del estilo 0 -> 3 -> 0.")
        self.assertTrue(1 in no_atendidos and 2 in no_atendidos, "Los pacientes 1 y 2 no deben ser atendidos.")
    
    def test_11_no_elige_paciente_lejano_si_los_cercanos_dan_mejor_beneficio(self):
        nombre_test = "test_paciente_lejano_no_da_mejor_beneficio"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 10, "Común", 20],
                ["2", 0.0, 20.0, 0, 20, "Común", 20],   
                ["3", 0.0, -30.0, 0, 30, "Común", 39]
            ],
            flota=[["Combi_A", 1, 3, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 30, "El beneficio óptimo es 30 (Buscar pacientes 1 y 2).")
        self.assertEqual(len(rutas[0][1]), 4, "Debería ser una ruta del estilo 0 -> 1 -> 2 -> 0.")
        self.assertIn(3, no_atendidos, "El paciente 3 no debe ser atendido.")
    
    def test_12_con_dos_combis_se_puede_buscar_paciente_lejano(self):
        nombre_test = "test_dos_combis_pueden_buscar_paciente_lejano"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 10, "Común", 20],
                ["2", 0.0, 20.0, 0, 20, "Común", 20],   
                ["3", 0.0, -30.0, 0, 30, "Común", 39]
            ],
            flota=[["Combi_A", 2, 3, 10], ["Combi_B", 1, 3, 20]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 59, "El beneficio óptimo es 59 (Buscar pacientes 1, 2 y 3 usando ambas combis).")
        self.assertEqual(len(rutas), 2, "Deberían haber dos rutas, una de cada combi")
        self.assertEqual([], no_atendidos, "Deberían quedar todos los pacientes atendidos.")
    
    def test_13_paciente_inalcanzable(self):
        nombre_test = "test_paciente_inalcanzable"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 9, "Común", 1000],
            ],
            flota=[["Combi_A", 1, 1, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 0, "El beneficio óptimo es 0.")
        self.assertEqual(len(rutas), 0, "No deberían haber rutas, ya que no hay forma de llegar a tiempo")
        self.assertIn(1, no_atendidos, "El paciente 1 no debe ser atendido.")

    def test_14_orden_alterado_por_ventanas_de_tiempo(self):
        nombre_test = "test_orden_ventanas"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 30, 40, "Común", 100], 
                ["2", 0.0, 20.0, 20, 21, "Común", 100], 
            ],
            flota=[["Combi_A", 1, 2, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 190.0, "Debería atender a ambos (200 - 10).")
        self.assertEqual(rutas[0][1], [0, 2, 1, 0], "El modelo no alteró el orden físico para cumplir las ventanas de tiempo.")

    def test_15_incompatibilidad_resuelta_con_multiples_combis(self):
        nombre_test = "test_incomp_multi_combi"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 10.0, 0, 50, "Infeccioso", 100],
                ["2", 0.0, -10.0, 0, 50, "Inmunodeprimido", 100],
            ],
            flota=[["Combi_A", 2, 2, 10]],
            incompatibilidades=[["Infeccioso", "Inmunodeprimido"]]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 180.0, "El beneficio óptimo es 180.")
        self.assertEqual(len(rutas), 2, "Debería haber utilizado las 2 combis para aislar a los pacientes.")
        self.assertEqual(no_atendidos, [], "Nadie debería quedar sin atender.")

    def test_16_propagacion_de_espera_afecta_al_siguiente(self):
        nombre_test = "test_propagacion_espera"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", -100.0, 0.0, 100, 110, "Común", 100], 
                ["2", 100.0, 0.0, 200, 210, "Común", 150],  
            ],
            flota=[["Combi_A", 1, 5, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 140.0, "El beneficio óptimo es 140 (atender solo a P2).")
        self.assertEqual(rutas[0][1], [0, 2, 0], "Solo debió ir a buscar a P2.")
        self.assertIn(1, no_atendidos, "El paciente 1 debió quedar afuera porque el tiempo de espera arruinaba la ruta.")
    
    def test_17_dos_combis_con_uno_de_capacidad(self):
        nombre_test = "test_dos_combis_con_uno_de_capacidad"
        self.crear_instancia(
            nombre_test,
            pacientes=[
                ["1", 0.0, 20.0, 0, 100, "Común", 100], 
                ["2", 0.0, 10.0, 0, 100, "Común", 150],  
            ],
            flota=[["Combi_A", 1, 1, 10], ["Combi_B", 1, 1, 10]],
            incompatibilidades=[]
        )
        
        SaludCG(nombre_test, threshold=10.0)
        beneficio, rutas, no_atendidos = self.leer_resultado(nombre_test)
        
        self.assertEqual(beneficio, 230.0, "El beneficio óptimo es 230.")
        self.assertEqual(len(rutas), 2, "Deberían haber 2 rutas, una por cada combi")
        self.assertEqual([], no_atendidos, "Todos los pacientes deberían quedar atendidos.")

if __name__ == '__main__':
    unittest.main(verbosity=2)