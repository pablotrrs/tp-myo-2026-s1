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
        self.duales_pacientes = {}
    
    def construir_modelo(self, relajado=True):
        """Construye el modelo de programación lineal del problema maestro."""
        self.model = Model("Problema_Maestro_VRP")
        
        # Variables: y_r = 1 si la ruta r es usada, 0 sino
        self.variables_ruta = {}
        vtype = "C" if relajado else "B"  # Continuo si es relajado, Binario si es entero
        for ruta in self.rutas:
            self.variables_ruta[ruta.id_ruta] = self.model.addVar(
                vtype=vtype, lb=0, ub=1, name=f"y_{ruta.id_ruta}"
            )
        
        # Función objetivo: minimizar distancia total
        self.model.setObjective(
            quicksum(
                ruta.costo * self.variables_ruta[ruta.id_ruta]
                for ruta in self.rutas
            ),
            "minimize"
        )
        
        # Restricciones: cada paciente debe ser cubierto por al menos una ruta
        self.restricciones_cobertura = {}
        for paciente in self.lista_pacientes:
            rutas_que_cubren = [ruta for ruta in self.rutas if paciente in ruta.pacientes]
            
            if rutas_que_cubren:
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
    
    def resolver(self, relajado=True):
        """
        Resuelve el problema maestro.
        
        Args:
            relajado: Si True, resuelve la relajación lineal; si False, solución entera
            
        Returns:
            (status, valor_objetivo, uso_rutas, duales)
        """
        if self.model is None:
            self.construir_modelo(relajado=relajado)
        
        self.model.optimize()
        
        status = self.model.getStatus()
        
        if status == "optimal":
            valor_objetivo = self.model.getObjVal()
            
            # Extraer solución
            uso_rutas = {}
            for ruta in self.rutas:
                valor = self.model.getVal(self.variables_ruta[ruta.id_ruta])
                if valor > 1e-6:
                    uso_rutas[ruta.id_ruta] = valor
            
            # Extraer duales de las restricciones de cobertura
            self.duales_pacientes = {}
            for paciente, restriccion in self.restricciones_cobertura.items():
                try:
                    dual = self.model.getDualsolLinear(restriccion)
                    self.duales_pacientes[paciente] = dual
                except:
                    # Si no hay dual disponible, usar valor por defecto
                    self.duales_pacientes[paciente] = 0.0
            
            return status, valor_objetivo, uso_rutas, self.duales_pacientes
        else:
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
