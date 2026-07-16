import os
import sys
from typing import Dict, List

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root)

from Salud.utils_salud import Paciente, TipoCombi

def generar_rutas_iniciales(pacientes: List[Paciente], centro: Paciente, flota: Dict[str, TipoCombi], distancias: dict, incomp, pac_dict) -> List[dict]:
    rutas = []
    
    generar_rutas_directas(pacientes, centro, flota, distancias, rutas)
    generar_rutas_golosas(pacientes, centro, flota, distancias, rutas, incomp, pac_dict)
    
    rutas_unicas = filtrar_rutas_unicas(rutas)
            
    return rutas_unicas

def filtrar_rutas_unicas(rutas):
    rutas_unicas = []
    vistos = set()
    for r in rutas:
        clave = (r["tipo_combi"], tuple(r["camino"]))
        if clave not in vistos:
            vistos.add(clave)
            rutas_unicas.append(r)
    return rutas_unicas

def generar_rutas_directas(pacientes, centro, flota, distancias, rutas):
    for tipo_k in flota.keys():
        for p in pacientes:
            tiempo_llegada = distancias.get((centro.id, p.id), 0)
            if llega_a_tiempo(p, tiempo_llegada):
                rutas.append(generar_ruta_a_paciente(centro, flota, tipo_k, p))

def generar_rutas_golosas(pacientes, centro, flota, distancias, rutas, incomp, pac_dict):
    for tipo_k, combi_info in flota.items():
        priorizar_beneficio(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict)
        priorizar_distancia(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict)
        priorizar_coeficiente(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict)

def priorizar_beneficio(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict):
    pacientes_disponibles = pacientes.copy()
    capacidad = combi_info.cant_asientos
    costo = combi_info.costo_operacion
    
    while pacientes_disponibles:
        p_ordenados = sorted(pacientes_disponibles, key=lambda p: p.beneficio, reverse=True)
        ruta_obtenida = generar_ruta_golosa(centro, distancias, p_ordenados, capacidad, incomp, pac_dict)
                
        if not ruta_obtenida:
            break
            
        rutas.append({
            "tipo_combi": tipo_k,
            "pacientes_ids": ruta_obtenida,
            "camino": [centro.id] + ruta_obtenida + [centro.id],
            "rentabilidad": sum(p.beneficio for p in pacientes if p.id in ruta_obtenida) - costo
        })
        
        pacientes_disponibles = [p for p in pacientes_disponibles if p.id not in ruta_obtenida]

def priorizar_distancia(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict):
    pacientes_disponibles = pacientes.copy()
    capacidad = combi_info.cant_asientos
    costo = combi_info.costo_operacion
    
    while pacientes_disponibles:
        p_ordenados = sorted(pacientes_disponibles, key=lambda p: distancias.get((centro.id, p.id), 9999))
        ruta_obtenida = generar_ruta_golosa(centro, distancias, p_ordenados, capacidad, incomp, pac_dict)
                
        if not ruta_obtenida:
            break
            
        rutas.append({
            "tipo_combi": tipo_k,
            "pacientes_ids": ruta_obtenida,
            "camino": [centro.id] + ruta_obtenida + [centro.id],
            "rentabilidad": sum(p.beneficio for p in pacientes if p.id in ruta_obtenida) - costo
        })
        
        pacientes_disponibles = [p for p in pacientes_disponibles if p.id not in ruta_obtenida]

def priorizar_coeficiente(pacientes, centro, distancias, rutas, tipo_k, combi_info, incomp, pac_dict):
    pacientes_disponibles = pacientes.copy()
    capacidad = combi_info.cant_asientos
    costo = combi_info.costo_operacion
    
    def ratio(p):
        dist = distancias.get((centro.id, p.id), 1.0)
        return p.beneficio / dist

    while pacientes_disponibles:
        p_ordenados = sorted(pacientes_disponibles, key=ratio, reverse=True)
        ruta_obtenida = generar_ruta_golosa(centro, distancias, p_ordenados, capacidad, incomp, pac_dict)
                
        if not ruta_obtenida:
            break
            
        rutas.append({
            "tipo_combi": tipo_k,
            "pacientes_ids": ruta_obtenida,
            "camino": [centro.id] + ruta_obtenida + [centro.id],
            "rentabilidad": sum(p.beneficio for p in pacientes if p.id in ruta_obtenida) - costo
        })
        
        pacientes_disponibles = [p for p in pacientes_disponibles if p.id not in ruta_obtenida]


def generar_ruta_golosa(centro, distancias, p_ordenados, capacidad, incomp, pac_dict):
    ruta_actual = []
    carga_actual = 0
    tiempo_actual = 0
    posicion_actual = centro.id
    
    for p in p_ordenados:
        dist = distancias.get((posicion_actual, p.id), 0)
        if (carga_actual < capacidad and llega_a_tiempo(p, tiempo_actual + dist)
            and es_compatible(p.id, ruta_actual, incomp, pac_dict)):
            ruta_actual.append(p.id)
            tiempo_actual = max(p.ih_inicio, tiempo_actual + dist)
            posicion_actual = p.id
            carga_actual += 1

    return ruta_actual

def llega_a_tiempo(p, tiempo_llegada):
    return tiempo_llegada <= p.ih_fin

def es_compatible(nuevo_paciente_id, pacientes_en_ruta, incomp, pac_dict):
    nuevo_paciente = pac_dict[nuevo_paciente_id]
    for p_id in pacientes_en_ruta:
        p_existente = pac_dict[p_id]
        if (nuevo_paciente.categoria, p_existente.categoria) in incomp or \
           (p_existente.categoria, nuevo_paciente.categoria) in incomp:
            return False
    return True

def generar_ruta_a_paciente(centro, flota, tipo_k, p):
    nueva_ruta = {
                "tipo_combi": tipo_k,
                "pacientes_ids": [p.id],
                "camino": [centro.id, p.id, centro.id],
                "rentabilidad": p.beneficio - flota[tipo_k].costo_operacion
            }
    
    return nueva_ruta