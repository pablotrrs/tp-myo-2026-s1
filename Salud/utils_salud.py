"""
Utilidades para el problema Salud de logística médica.
Incluye parsers para los archivos de entrada y funciones helper.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class Paciente:
    """Representa un paciente con sus datos."""
    id: int
    x: float
    y: float
    ih_inicio: int = None
    ih_fin: int = None
    categoria: str = None
    beneficio: float = None
    
    def es_centro(self) -> bool:
        """Verifica si es el centro (id=0)."""
        return self.id == 0


@dataclass
class TipoCombi:
    """Representa un tipo de combi disponible."""
    nombre: str
    cant_disponible: int
    cant_asientos: int
    costo_operacion: float


def distancia_euclidea(p1: Paciente, p2: Paciente) -> float:
    """Calcula la distancia euclidea entre dos puntos."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def leer_pacientes(archivo: str) -> Tuple[List[Paciente], Paciente]:
    """
    Lee el archivo de pacientes y centro médico.
    
    Formato:
    # id,x,y,ih_inicio,ih_fin,categoria,beneficio
    0,40.0,50.0
    1,25.0,85.0,120,240,Inmunodeprimido,180
    
    Retorna: (lista_pacientes, centro_medico)
    """
    pacientes = []
    centro = None
    
    with open(archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            # Saltar comentarios y líneas vacías
            if not linea or linea.startswith('#'):
                continue
            
            partes = [p.strip() for p in linea.split(',')]
            
            id_pac = int(partes[0])
            x = float(partes[1])
            y = float(partes[2])
            
            if id_pac == 0:
                # Es el centro médico
                centro = Paciente(id=0, x=x, y=y)
            else:
                # Es un paciente
                ih_inicio = int(partes[3])
                ih_fin = int(partes[4])
                categoria = partes[5]
                beneficio = float(partes[6])
                
                paciente = Paciente(
                    id=id_pac,
                    x=x,
                    y=y,
                    ih_inicio=ih_inicio,
                    ih_fin=ih_fin,
                    categoria=categoria,
                    beneficio=beneficio
                )
                pacientes.append(paciente)
    
    return pacientes, centro


def leer_flota(archivo: str) -> Dict[str, TipoCombi]:
    """
    Lee el archivo de flota heterogénea.
    
    Formato:
    # tipo_combi,cant_disponible,cant_asientos,costo_operacion
    Combi_Chica,5,12,150
    Combi_Mediana,5,20,250
    
    Retorna: dict {nombre_tipo: TipoCombi}
    """
    flota = {}
    
    with open(archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            
            partes = [p.strip() for p in linea.split(',')]
            
            nombre = partes[0]
            cant_disponible = int(partes[1])
            cant_asientos = int(partes[2])
            costo_operacion = float(partes[3])
            
            tipo_combi = TipoCombi(
                nombre=nombre,
                cant_disponible=cant_disponible,
                cant_asientos=cant_asientos,
                costo_operacion=costo_operacion
            )
            flota[nombre] = tipo_combi
    
    return flota


def leer_incompatibilidades(archivo: str) -> Set[Tuple[str, str]]:
    """
    Lee el archivo de incompatibilidades de categorías.
    
    Formato:
    # categoria1,categoria2
    Inmunodeprimido,Infeccioso
    Infeccioso,Pediatrico
    
    Retorna: set de pares (cat1, cat2) donde ambas direcciones están incluidas
    """
    incomp = set()
    
    with open(archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            
            cat1, cat2 = [p.strip() for p in linea.split(',')]
            
            # Agregar ambas direcciones (simétrico)
            incomp.add((cat1, cat2))
            incomp.add((cat2, cat1))
    
    return incomp


def validar_entrada(pacientes: List[Paciente], flota: Dict[str, TipoCombi], 
                   incomp: Set[Tuple[str, str]]) -> bool:
    """Valida que los datos de entrada sean consistentes."""
    
    # Verificar que todos los pacientes tengan datos
    for p in pacientes:
        assert p.id > 0, f"ID de paciente inválido: {p.id}"
        assert p.x is not None and p.y is not None, f"Coordenadas faltantes para paciente {p.id}"
        assert p.ih_inicio is not None and p.ih_fin is not None, \
            f"Ventanas de tiempo faltantes para paciente {p.id}"
        assert p.ih_inicio < p.ih_fin, \
            f"Ventana inválida para paciente {p.id}: {p.ih_inicio} >= {p.ih_fin}"
        assert p.categoria is not None, f"Categoría faltante para paciente {p.id}"
        assert p.beneficio is not None, f"Beneficio faltante para paciente {p.id}"
    
    # Verificar que la flota tenga combis
    assert len(flota) > 0, "La flota está vacía"
    
    for tipo_nombre, tipo_combi in flota.items():
        assert tipo_combi.cant_disponible > 0, \
            f"Combis disponibles inválido para {tipo_nombre}"
        assert tipo_combi.cant_asientos > 0, \
            f"Capacidad inválida para {tipo_nombre}"
    
    return True


def generar_matriz_distancias(pacientes: List[Paciente], centro: Paciente) -> Dict[Tuple[int, int], float]:
    """
    Genera una matriz de distancias euclídeas.
    
    Retorna: dict {(i, j): distancia}
    """
    nodos = [centro] + pacientes
    distancias = {}
    
    for i, p1 in enumerate(nodos):
        for j, p2 in enumerate(nodos):
            if i != j:
                dist = distancia_euclidea(p1, p2)
                distancias[(p1.id, p2.id)] = dist
    
    return distancias


def parsear_salida(contenido: str) -> Tuple[float, List[Tuple[str, List[int]]], List[int]]:
    """
    Parsea el contenido de un archivo .out generado.
    
    Retorna: (beneficio, rutas, no_atendidos)
    donde rutas = [(tipo_combi, [ids_pacientes]), ...]
    """
    lineas = contenido.strip().split('\n')
    beneficio = None
    rutas = []
    no_atendidos = []
    
    for linea in lineas:
        linea = linea.strip()
        
        if linea.startswith('Z = '):
            beneficio = float(linea.replace('Z = ', ''))
        
        elif ': [' in linea and ']' in linea:
            # Es una línea de ruta
            tipo_combi, ruta_str = linea.split(': ')
            tipo_combi = tipo_combi.strip()
            
            # Extraer IDs de la ruta [0 -> 1 -> 2 -> 0]
            ruta_str = ruta_str.replace('[', '').replace(']', '')
            ids_str = ruta_str.split(' -> ')
            ids = [int(x.strip()) for x in ids_str]
            
            rutas.append((tipo_combi, ids))
        
        elif linea.startswith('No_Atendidos: '):
            no_atendidos_str = linea.replace('No_Atendidos: ', '').strip()
            if no_atendidos_str:
                no_atendidos = [int(x.strip()) for x in no_atendidos_str.split(',')]
    
    return beneficio, rutas, no_atendidos


def generar_salida(beneficio: float, rutas: List[Tuple[str, List[int]]], 
                   no_atendidos: List[int]) -> str:
    """
    Genera el contenido del archivo .out en el formato especificado.
    
    Retorna: string con el contenido del archivo
    """
    lineas = []
    
    # Línea de beneficio
    lineas.append(f"Z = {beneficio:.1f}")
    
    # Líneas de rutas
    for tipo_combi, ids in rutas:
        ruta_str = ' -> '.join(str(id_) for id_ in ids)
        lineas.append(f"{tipo_combi}: [{ruta_str}]")
    
    # Línea de no atendidos
    if no_atendidos:
        no_atendidos_str = ', '.join(str(id_) for id_ in no_atendidos)
        lineas.append(f"No_Atendidos: {no_atendidos_str}")
    else:
        lineas.append("No_Atendidos: ")
    
    return '\n'.join(lineas) + '\n'
