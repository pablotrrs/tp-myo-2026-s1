"""
Subproblema de Generación de Columnas (Pricing Problem):
Genera nuevas rutas rentables usando los duales del problema maestro.

El subproblema es un problema de knapsack constrained donde buscamos maximizar
el costo reducido: c - y*a, donde:
  - c = beneficio de la ruta (negativo del costo, porque minimizamos)
  - y* = duales del problema maestro (precio de cada paciente)
  - a = vector de incidencia (qué pacientes están en la ruta)
"""

from pyscipopt import Model, quicksum
from ruta import Ruta
from itertools import combinations
import heapq

class SubproblemaGeneracionColumnas:
    """Genera nuevas rutas usando duales del problema maestro."""
    
    def __init__(self, lista_pacientes, distancias, capacidad_combi, duales, turnos=None, tolerancia=0):
        """
        Inicializa el subproblema.
        
        Args:
            lista_pacientes: Lista de IDs de pacientes
            distancias: Diccionario con distancias entre nodos
            capacidad_combi: Capacidad máxima de una combi
            duales: Diccionario con valores duales {paciente_id: valor_dual}
            turnos: Diccionario {paciente_id: hora_turno} para ventanas de tiempo
            tolerancia: Margen de tolerancia antes del turno
        """
        self.lista_pacientes = sorted(lista_pacientes)
        self.distancias = distancias
        self.capacidad_combi = capacidad_combi
        self.duales = duales or {}
        self.turnos = turnos or {}
        self.tolerancia = tolerancia
    
    def _calcular_costo_ruta(self, pacientes):
        """Calcula el costo total de una ruta (visitando en orden de turno)."""
        if not pacientes:
            return 0
        
        # Ordenar por turno si hay información
        if self.turnos:
            pacientes_ordenados = sorted(pacientes, key=lambda p: (self.turnos.get(p, 0), p))
        else:
            pacientes_ordenados = sorted(pacientes)
        
        costo = 0
        nodo_actual = 0
        
        for paciente in pacientes_ordenados:
            if (nodo_actual, paciente) in self.distancias:
                costo += self.distancias[nodo_actual, paciente]
                nodo_actual = paciente
        
        if (nodo_actual, 0) in self.distancias:
            costo += self.distancias[nodo_actual, 0]
        
        return costo
    
    def _es_ruta_factible(self, pacientes):
        """
        Verifica si la ruta respeta las ventanas de tiempo.
        El vehículo puede esperar si llega antes de la ventana.
        """
        if not self.turnos:
            return True
        
        pacientes_ordenados = sorted(pacientes, key=lambda p: (self.turnos.get(p, 0), p))
        T_actual = 0
        nodo_actual = 0
        for p in pacientes_ordenados:
            if (nodo_actual, p) not in self.distancias:
                return False
            T_llegada = T_actual + self.distancias[nodo_actual, p]
            T_servicio = max(T_llegada, self.turnos[p] - self.tolerancia)
            if T_servicio > self.turnos[p]:
                return False
            T_actual = T_servicio
            nodo_actual = p
        return True
    
    def _calcular_costo_reducido(self, pacientes):
        """
        Calcula el costo reducido de una ruta.
        
        Costo reducido = suma(duales_pacientes) - costo_ruta
        
        Si es > 0, la ruta es rentable (mejora la solución porque reduce el objetivo).
        Cuando una ruta tiene costo_reducido negativo, agregarla a la base MEJORA el objetivo.
        """
        costo_ruta = self._calcular_costo_ruta(pacientes)
        suma_duales = sum(self.duales.get(p, 0) for p in pacientes)
        
        # Costo reducido: suma_duales - costo_ruta
        # Si es > 0: la ruta es rentable (mejora el objetivo cuando se agrega)
        costo_reducido = suma_duales - costo_ruta
        
        return costo_reducido
    
    def generar_nueva_ruta_enumeracion(self):
        """
        Genera nuevas rutas enumerando todas las combinaciones factibles.
        
        Returns:
            (ruta_optima, costo_reducido_optimo)
            Si no hay ruta rentable, retorna (None, <= 0)
        """
        mejor_ruta = None
        mejor_costo_reducido = 0  # Criterio de parada: si <= 0, no hay mejora
        
        # Enumerar todas las combinaciones de pacientes que caben en la capacidad
        for r in range(1, self.capacidad_combi + 1):
            for pacientes in combinations(self.lista_pacientes, r):
                if not self._es_ruta_factible(list(pacientes)):
                    continue  # saltar rutas infactibles por ventanas de tiempo
                costo_reducido = self._calcular_costo_reducido(list(pacientes))
                
                if costo_reducido > mejor_costo_reducido:
                    mejor_costo_reducido = costo_reducido
                    mejor_ruta = list(pacientes)
        
        if mejor_ruta and mejor_costo_reducido > 1e-6:
            ruta = Ruta(mejor_ruta, self.distancias, turnos=self.turnos, tolerancia=self.tolerancia)
            return ruta, mejor_costo_reducido
        
        return None, mejor_costo_reducido
    
    def generar_nueva_ruta_pgm_lineal(self):
        """
        Genera nuevas rutas usando programación lineal.
        
        Modelo:
            max sum(c_p * x_p) - costo_ruta
            s.a. sum(x_p) <= capacidad
                 x_p in {0, 1}
        
        donde c_p = -duales[p] (negado porque minimizamos en el original)
        
        Returns:
            (ruta_optima, costo_reducido_optimo)
        """
        model = Model("Subproblema_VRP")
        
        # Variables: x_p = 1 si el paciente p está en la ruta
        x = {}
        for p in self.lista_pacientes:
            x[p] = model.addVar(vtype="B", name=f"x_{p}")
        
        # Variable para el costo de la ruta (linealizado mediante BigM)
        # En realidad, calculamos el costo como una función del conjunto de pacientes
        # Para simplificar, usaremos enumeración en el post-procesamiento
        
        # Objetivo: maximizar suma de duales (que es equivalente a minimizar costo reducido)
        model.setObjective(
            quicksum(self.duales.get(p, 0) * x[p] for p in self.lista_pacientes),
            "maximize"
        )
        
        # Restricción: capacidad
        model.addCons(
            quicksum(x[p] for p in self.lista_pacientes) <= self.capacidad_combi
        )
        
        model.optimize()
        
        # Extraer la solución
        if model.getStatus() == "optimal":
            pacientes_en_ruta = [p for p in self.lista_pacientes if model.getVal(x[p]) > 0.5]
            
            if pacientes_en_ruta:
                costo_reducido = self._calcular_costo_reducido(pacientes_en_ruta)
                
                if costo_reducido > 1e-6:
                    ruta = Ruta(pacientes_en_ruta, self.distancias)
                    return ruta, costo_reducido
        
        return None, 0
    
    def generar_nueva_ruta(self, metodo="enumeracion"):
        """
        Genera una nueva ruta rentable.
        
        Args:
            metodo: "enumeracion" o "pgm_lineal"
            
        Returns:
            (ruta_optima, costo_reducido_optimo)
        """
        if metodo == "enumeracion":
            return self.generar_nueva_ruta_enumeracion()
        elif metodo == "pgm_lineal":
            return self.generar_nueva_ruta_pgm_lineal()
        else:
            raise ValueError(f"Método desconocido: {metodo}")
