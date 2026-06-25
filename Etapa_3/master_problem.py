"""
Problema Maestro: Selecciona rutas óptimas para cubrir todos los pacientes.

El modelo maestro recibe un conjunto de rutas y determina cuál es la mejor
combinación de rutas para visitar todos los pacientes, minimizando la distancia total.
"""

from pyscipopt import Model, quicksum
from ruta import Ruta

class ProblemaMaestro:
    """Resuelve el problema maestro de selección de rutas."""
    
    def __init__(self, lista_pacientes, rutas, num_combis=None):
        """
        Inicializa el problema maestro.
        
        Args:
            lista_pacientes: Lista de IDs de pacientes a visitar
            rutas: Lista de objetos Ruta disponibles
            num_combis: Número de combis disponibles (restricción de factibilidad)
        """
        self.lista_pacientes = sorted(lista_pacientes)
        self.rutas = rutas
        self.num_combis = num_combis
        self.model = None
        self.variables_ruta = {}
        self.variables_artificiales = {}  # Variables artificiales para factibilidad
        self.duales_pacientes = {}
        # Penalidad para variables artificiales: debe ser grande pero no dominar los duales
        # Usamos valor intermedio que balance factibilidad con precios razonables
        self.BIG_M = 5000.0
    
    def construir_modelo(self, relajado=True, usar_artificiales=True):
        """
        Construye el modelo de programación lineal del problema maestro.
        
        Args:
            relajado: Si True, resuelve relajación lineal; si False, solución entera
            usar_artificiales: Si True, incluye variables artificiales (para factibilidad inicial)
                               Si False, no las incluye (evita duales inflados durante CG)
        
        Las variables artificiales garantizan factibilidad cuando usar_artificiales=True.
        """
        self.model = Model("Problema_Maestro_VRP")
        
        # Configurar SCIP para evitar que elimine restricciones antes de leer duales
        self.model.setParam("presolving/maxrounds", 0)  # Desactivar presolving
        self.model.setParam("presolving/donotmultaggr", 1)  # No agregar variables
        
        # Variables: y_r = 1 si la ruta r es usada, 0 sino
        self.variables_ruta = {}
        vtype = "C" if relajado else "B"  # Continuo si es relajado, Binario si es entero
        for ruta in self.rutas:
            self.variables_ruta[ruta.id_ruta] = self.model.addVar(
                vtype=vtype, lb=0, ub=1, name=f"y_{ruta.id_ruta}"
            )
        
        # Variables artificiales (solo si se especifica)
        self.variables_artificiales = {}
        if usar_artificiales:
            for paciente in self.lista_pacientes:
                self.variables_artificiales[paciente] = self.model.addVar(
                    vtype="C", lb=0, ub=1, name=f"s_{paciente}"
                )
        
        # Función objetivo: minimizar distancia + penalidad de variables artificiales (si se usan)
        obj_expr = quicksum(
            ruta.costo * self.variables_ruta[ruta.id_ruta]
            for ruta in self.rutas
        )
        if usar_artificiales:
            obj_expr += quicksum(
                self.BIG_M * self.variables_artificiales[paciente]
                for paciente in self.lista_pacientes
            )
        self.model.setObjective(obj_expr, "minimize")
        
        # Restricciones: cada paciente debe ser cubierto por al menos una ruta
        self.restricciones_cobertura = {}
        for paciente in self.lista_pacientes:
            rutas_que_cubren = [ruta for ruta in self.rutas if paciente in ruta.pacientes]
            
            if usar_artificiales:
                # Con variables artificiales: sum(y_r : p in r) + s_i >= 1
                restriccion = self.model.addCons(
                    quicksum(
                        self.variables_ruta[ruta.id_ruta]
                        for ruta in rutas_que_cubren
                    ) + self.variables_artificiales[paciente] >= 1,
                    name=f"Cobertura_Paciente_{paciente}"
                )
            else:
                # Sin variables artificiales: sum(y_r : p in r) >= 1 (puede ser infactible)
                restriccion = self.model.addCons(
                    quicksum(
                        self.variables_ruta[ruta.id_ruta]
                        for ruta in rutas_que_cubren
                    ) >= 1,
                    name=f"Cobertura_Paciente_{paciente}"
                )
            
            self.restricciones_cobertura[paciente] = restriccion
        
        # Restricción: Máximo número de combis disponibles
        # (cada ruta usada requiere una combi)
        if self.num_combis is not None:
            self.model.addCons(
                quicksum(self.variables_ruta[ruta.id_ruta] for ruta in self.rutas) <= self.num_combis,
                name="Max_Combis_Disponibles"
            )
    
    def resolver(self, relajado=True, usar_artificiales=True):
        """
        Resuelve el problema maestro.
        
        Args:
            relajado: Si True, resuelve la relajación lineal; si False, solución entera
            usar_artificiales: Si True, usa variables artificiales para factibilidad
            
        Returns:
            (status, valor_objetivo, uso_rutas, duales_pacientes)
            
        Los duales extraídos se usan en el subproblema para generar columnas.
        """
        if self.model is None:
            self.construir_modelo(relajado=relajado, usar_artificiales=usar_artificiales)
        
        self.model.optimize()
        
        status = self.model.getStatus()
        
        if status == "optimal":
            valor_objetivo = self.model.getObjVal()
            
            # Extraer solución: solo rutas con valor > tolerancia
            uso_rutas = {}
            for ruta in self.rutas:
                valor = self.model.getVal(self.variables_ruta[ruta.id_ruta])
                if valor > 1e-6:
                    uso_rutas[ruta.id_ruta] = valor
            
            # Verificar si se usaron variables artificiales (solo si existen)
            variables_artificiales_usadas = {}
            if usar_artificiales:
                for paciente in self.lista_pacientes:
                    if paciente in self.variables_artificiales:
                        val_artificial = self.model.getVal(self.variables_artificiales[paciente])
                        if val_artificial > 1e-6:
                            variables_artificiales_usadas[paciente] = val_artificial
            
            if variables_artificiales_usadas:
                print(f"[CG] Variables artificiales usadas en iteración: {variables_artificiales_usadas}")
            
            # Extraer duales de las restricciones de cobertura (muy importante para CG)
            self.duales_pacientes = {}
            for paciente, restriccion in self.restricciones_cobertura.items():
                try:
                    # El dual es el "precio sombra" del paciente
                    # Representa cuánto mejora la solución si se agrega una unidad de cobertura
                    dual = self.model.getDualsolLinear(restriccion)
                    self.duales_pacientes[paciente] = dual if dual is not None else 0.0
                except Exception:
                    # Si no se puede extraer el dual, usar 0.0 (sin perturbar la solución)
                    self.duales_pacientes[paciente] = 0.0
            
            return status, valor_objetivo, uso_rutas, self.duales_pacientes
        else:
            print(f"[Error] Problema maestro con status: {status}")
            return status, None, {}, {}
    
    def obtener_duales(self):
        """Retorna los duales de las restricciones de cobertura."""
        return self.duales_pacientes
    
    def obtener_solucion(self):
        """Retorna la solución actual (rutas usadas)."""
        if self.model is None:
            return {}
        
        uso_rutas = {}
        for ruta in self.rutas:
            valor = self.model.getVal(self.variables_ruta[ruta.id_ruta])
            if valor > 1e-6:
                uso_rutas[ruta.id_ruta] = valor
        
        return uso_rutas
    
    def obtener_valor_objetivo(self):
        """Retorna el valor objetivo actual."""
        if self.model is None:
            return None
        return self.model.getObjVal()
