"""
Clase Ruta para representar una secuencia de pacientes visitados por una combi.
"""

class Ruta:
    """Representa una ruta de pacientes visitados por una combi."""
    
    def __init__(self, pacientes=None, distancias=None, id_ruta=None, turnos=None, tolerancia=0):
        """
        Inicializa una ruta.
        
        Args:
            pacientes: Lista de IDs de pacientes en la ruta
            distancias: Diccionario con distancias entre nodos
            id_ruta: Identificador único de la ruta
            turnos: Diccionario {paciente_id: hora_turno} para ventanas de tiempo
            tolerancia: Margen de tolerancia antes del turno
        """
        if isinstance(pacientes, Ruta):
            # Constructor copia
            self.pacientes = pacientes.pacientes.copy()
            self.costo = pacientes.costo
            self.id_ruta = pacientes.id_ruta
            self.distancias = pacientes.distancias
            self.turnos = pacientes.turnos
            self.tolerancia = pacientes.tolerancia
        else:
            self.turnos = turnos or {}
            self.tolerancia = tolerancia
            self.distancias = distancias or {}
            self.id_ruta = id_ruta
            # Ordenar por turno si hay información de turnos; si no, por ID
            if pacientes:
                if self.turnos:
                    self.pacientes = sorted(pacientes, key=lambda p: (self.turnos.get(p, 0), p))
                else:
                    self.pacientes = sorted(pacientes)
            else:
                self.pacientes = []
            self.costo = self._calcular_costo()
    
    def _calcular_costo(self):
        """Calcula el costo total de la ruta (distancia recorrida)."""
        if len(self.pacientes) == 0:
            return 0
        
        # Ruta: Depósito (0) -> Pacientes -> Depósito (0)
        costo_total = 0
        nodo_actual = 0
        
        for paciente in self.pacientes:
            if (nodo_actual, paciente) in self.distancias:
                costo_total += self.distancias[nodo_actual, paciente]
                nodo_actual = paciente
        
        # Regreso al depósito
        if (nodo_actual, 0) in self.distancias:
            costo_total += self.distancias[nodo_actual, 0]
        
        return costo_total
    
    def es_factible(self):
        """
        Verifica si la ruta respeta las ventanas de tiempo.
        El vehículo puede esperar si llega antes de la ventana.
        Sin datos de turnos, toda ruta se considera factible.
        """
        if not self.turnos or not self.pacientes:
            return True
        
        T_actual = 0
        nodo_actual = 0
        for p in self.pacientes:  # ya están ordenados por turno
            if (nodo_actual, p) not in self.distancias:
                return False
            T_llegada = T_actual + self.distancias[nodo_actual, p]
            T_servicio = max(T_llegada, self.turnos[p] - self.tolerancia)
            if T_servicio > self.turnos[p]:  # llega tarde: infactible
                return False
            T_actual = T_servicio
            nodo_actual = p
        return True
    
    def __repr__(self):
        pacientes_str = ", ".join(str(p) for p in self.pacientes)
        return f"Ruta({self.id_ruta} (costo={self.costo:.1f}): [0 -> {pacientes_str} -> 0])"
    
    def __hash__(self):
        return hash(tuple(self.pacientes))
    
    def __eq__(self, other):
        if not isinstance(other, Ruta):
            return False
        return self.pacientes == other.pacientes
    
    def __iter__(self):
        return iter(self.pacientes)
    
    def copy(self):
        """Crea una copia de la ruta."""
        return Ruta(self.pacientes.copy(), self.distancias, self.id_ruta, self.turnos, self.tolerancia)
    
    def append(self, paciente):
        """Agrega un paciente a la ruta."""
        if paciente not in self.pacientes:
            self.pacientes.append(paciente)
            if self.turnos:
                self.pacientes.sort(key=lambda p: (self.turnos.get(p, 0), p))
            else:
                self.pacientes.sort()
            self.costo = self._calcular_costo()
        return self
    
    def contains_all(self, other_ruta):
        """Verifica si esta ruta contiene todos los pacientes de otra."""
        return all(p in self.pacientes for p in other_ruta.pacientes)


class Rutas:
    """Gestiona un conjunto de rutas."""
    
    def __init__(self, lista_pacientes, distancias, capacidad_combi, turnos=None, tolerancia=0):
        """
        Inicializa el conjunto de rutas.
        
        Args:
            lista_pacientes: Lista de IDs de pacientes
            distancias: Diccionario con distancias entre nodos
            capacidad_combi: Capacidad máxima de una combi
            turnos: Diccionario {paciente_id: hora_turno} para ventanas de tiempo
            tolerancia: Margen de tolerancia antes del turno
        """
        self.lista_pacientes = sorted(lista_pacientes)
        self.distancias = distancias
        self.capacidad_combi = capacidad_combi
        self.turnos = turnos or {}
        self.tolerancia = tolerancia
        self.rutas = self._generar_rutas_iniciales()
        print(f"Rutas iniciales generadas: {len(self.rutas)}")
    
    def _generar_rutas_iniciales(self):
        """
        Genera SOLO rutas individuales (un paciente por ruta).
        
        Este es el enfoque minimalista para Column Generation:
        comenzamos con un pool muy pequeño de rutas y las generamos iterativamente.
        """
        rutas = []
        contador = 0
        
        # Generar una ruta individual para CADA paciente
        for paciente in self.lista_pacientes:
            ruta = Ruta(
                [paciente],
                self.distancias,
                id_ruta=contador,
                turnos=self.turnos,
                tolerancia=self.tolerancia
            )
            # Verificar factibilidad (ventanas de tiempo, etc.)
            if ruta.es_factible():
                rutas.append(ruta)
                contador += 1
        
        return rutas
    
    def agregar_ruta(self, pacientes):
        """Agrega una nueva ruta al conjunto."""
        if pacientes:  # Solo agregar si no está vacía
            ruta_nueva = Ruta(pacientes, self.distancias, id_ruta=len(self.rutas),
                              turnos=self.turnos, tolerancia=self.tolerancia)
            # Verificar que no existe ya
            if ruta_nueva not in self.rutas:
                self.rutas.append(ruta_nueva)
                return True
        return False
