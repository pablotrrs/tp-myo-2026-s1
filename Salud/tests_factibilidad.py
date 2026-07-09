import unittest
import os
import shutil
from SaludTest import SaludTest

class TestFactibilidad(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.crear_carpetas_temporales()
        
        cls.crear_instancia_base()

    @classmethod
    def crear_carpetas_temporales(cls):
        os.makedirs("./IN_TEST", exist_ok=True)
        os.makedirs("./OUT_TEST", exist_ok=True)

    @classmethod
    def crear_instancia_base(cls):
        cls.escribir_pacientes([
            ["1", 0.0, 10.0, 5, 20, "Inmunodeprimido", 100],
            ["2", 0.0, 20.0, 15, 30, "Infeccioso", 150]
        ])
        
        cls.escribir_combis([["Combi_A", 2, 1, 50], ["Combi_B", 1, 5, 100]])
            
        cls.escribir_incompatibilidad("Inmunodeprimido", "Infeccioso")

    @classmethod
    def escribir_pacientes(cls, pacientes):
        with open("./IN_TEST/test_base_pacientes.in", "w") as f:
            f.write("0, 0.0, 0.0\n")
            for paciente in pacientes:
                f.write(f"{paciente[0]}, {paciente[1]}, {paciente[2]}, {paciente[3]}, {paciente[4]}, {paciente[5]}, {paciente[6]}\n")

    @classmethod
    def escribir_combis(cls, combis):
        with open("./IN_TEST/test_base_flota.in", "w") as f:
            for combi in combis:
                f.write(f"{combi[0]}, {combi[1]}, {combi[2]}, {combi[3]}\n")

    @classmethod
    def escribir_incompatibilidad(cls, primer_inc, segundo_inc):
        with open("./IN_TEST/test_base_incompatibilidades.in", "w") as f:
            f.write(f"{primer_inc}, {segundo_inc}\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree("./IN_TEST")
        shutil.rmtree("./OUT_TEST")

    def guardar_salida_mock(self, contenido, nombre_archivo="test_base.out"):
        ruta = f"./OUT_TEST/{nombre_archivo}"
        with open(ruta, "w") as f:
            f.write(contenido)
        return ruta

    # ==========================================
    # TESTS DE VALIDACIÓN
    # ==========================================

    def test_01_ruta_ideal_con_espera(self):
        salida = (
            "Z = 50.0\n"
            "Combi_A: [0 -> 1 -> 0]\n"
            "No_Atendidos: 2\n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertTrue(es_valido, "Debería ser válido: Respeta ventana, capacidad y beneficio.")

    def test_02_violacion_capacidad(self):
        salida = (
            "Z = 200.0\n"
            "Combi_A: [0 -> 1 -> 2 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: La Combi_A solo tiene 1 asiento.")

    def test_03_violacion_incompatibilidad(self):
        salida = (
            "Z = 150.0\n"
            "Combi_B: [0 -> 1 -> 2 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: Categorías incompatibles juntas.")

    def test_04_llegada_tarde_ventana_tiempo(self):
        with open("./IN_TEST/test_tarde_pacientes.in", "w") as f:
            f.write("0, 0.0, 0.0\n")
            f.write("1, 0.0, 50.0, 5, 10, Normal, 100\n") 
        with open("./IN_TEST/test_tarde_flota.in", "w") as f:
            f.write("Combi_A, 1, 5, 10\n")
        with open("./IN_TEST/test_tarde_incompatibilidades.in", "w") as f:
            f.write("\n")
            
        salida = (
            "Z = 90.0\n"
            "Combi_A: [0 -> 1 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida, "test_tarde.out")
        es_valido = SaludTest("test_tarde", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: Llega en T=50 pero la ventana cierra en T=10.")

    def test_05_el_paciente_fantasma(self):
        with open("./IN_TEST/test_fantasma_pacientes.in", "w") as f:
            f.write("0, 0.0, 0.0\n")
            f.write("1, 0.0, 10.0, 5, 20, Normal, 100\n")
            f.write("2, 0.0, 20.0, 15, 30, Normal, 150\n")
            
        with open("./IN_TEST/test_fantasma_flota.in", "w") as f:
            f.write("Combi_B, 1, 5, 100\n")
            
        with open("./IN_TEST/test_fantasma_incompatibilidades.in", "w") as f:
            f.write("\n") 

        salida = (
            "Z = 50.0\n"
            "Combi_B: [0 -> 1 -> 2 -> 0]\n"
            "No_Atendidos: 1\n"
        )
        ruta_out = self.guardar_salida_mock(salida, "test_fantasma.out")
        es_valido = SaludTest("test_fantasma", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: Incongruencia entre la ruta física y la lista de No Atendidos.")
    
    def test_06_ruta_no_termina_en_centro(self):
        salida = (
            "Z = 50.0\n"
            "Combi_A: [0 -> 1 -> 2]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: La ruta no termina en el centro (0).")
    
    def test_07_ruta_no_comienza_en_centro(self):
        salida = (
            "Z = 50.0\n"
            "Combi_A: [1 -> 2 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: La ruta no comienza en el centro (0).")

    def test_08_combi_inexistente(self):
        salida = (
            "Z = 50.0\n"
            "Combi_Inexistente: [0 -> 1 -> 0]\n"
            "No_Atendidos: 2\n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: 'Combi_Inexistente' no existe en la flota base.")

    def test_09_calculo_beneficio_erroneo(self):
        salida = (
            "Z = 51.0\n"
            "Combi_A: [0 -> 1 -> 0]\n"
            "No_Atendidos: 2\n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: El beneficio Z reportado es matemáticamente incorrecto.")

    def test_10_paciente_olvidado(self):
        salida = (
            "Z = 50.0\n"
            "Combi_A: [0 -> 1 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: Falta declarar el estado del paciente 2.")

    def test_11_multiples_rutas_correctas(self):
        with open("./IN_TEST/test_multi_pacientes.in", "w") as f:
            f.write("0, 0.0, 0.0\n")
            f.write("1, 0.0, 10.0, 5, 20, Normal, 100\n")
            f.write("2, 0.0, 20.0, 15, 20, Normal, 150\n")
            f.write("3, 0.0, 10.0, 5, 30, Normal, 100\n")
            
        with open("./IN_TEST/test_multi_flota.in", "w") as f:
            f.write("Combi_A, 2, 1, 50\n")
            f.write("Combi_B, 1, 5, 100\n")
            
        with open("./IN_TEST/test_multi_incompatibilidades.in", "w") as f:
            f.write("\n")

        salida = (
            "Z = 200.0\n"
            "Combi_A: [0 -> 1 -> 0]\n"
            "Combi_B: [0 -> 2 -> 3 -> 0]\n"
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida, "test_multi.out")
        es_valido = SaludTest("test_multi", ruta_out, "./IN_TEST")
        self.assertTrue(es_valido, "Debería ser válido: Rutas múltiples procesadas correctamente.")
    
    def test_12_paciente_inexistente(self):
        salida = (
            "Z = 50.0\n"
            "Combi_A: [0 -> 3 -> 0]\n" #El paciente 3 no existe
            "No_Atendidos: \n"
        )
        ruta_out = self.guardar_salida_mock(salida)
        es_valido = SaludTest("test_base", ruta_out, "./IN_TEST")
        self.assertFalse(es_valido, "Debería fallar: No existe el paciente 3 en la lista de pacientes.")


if __name__ == '__main__':
    unittest.main(verbosity=2)