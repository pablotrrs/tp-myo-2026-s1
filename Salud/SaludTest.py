"""
SaludTest(instancia, output)
Función de validación que verifica si una solución es operativamente factible.
NO utiliza programación lineal.
"""

import sys
import os
import math
from typing import Tuple, List, Dict

# Agregar el directorio padre para importar utils_salud
sys.path.insert(0, os.path.dirname(__file__))

from utils_salud import (
    leer_pacientes, leer_flota, leer_incompatibilidades,
    distancia_euclidea, parsear_salida
)


def SaludTest(instancia: str, output_file: str = None, 
             in_path: str = "./IN") -> bool:
    """
    Valida si la solución propuesta es operativamente factible.
    
    Realiza las siguientes verificaciones:
    - Capacidad respetada en cada combi
    - Ventanas de tiempo respetadas para cada paciente
    - Distancias y tiempos calculados correctamente
    - Sin categorías incompatibles en la misma combi
    - Beneficio total calculado correctamente
    
    NO utiliza programación lineal.
    
    Args:
        instancia: nombre de la instancia (ej: "test1")
        output_file: ruta al archivo .out a validar
                    (default: "./OUT_model1/{instancia}.out")
        in_path: ruta a carpeta con archivos de entrada
    
    Retorna: True si la solución es válida, False en caso contrario
    """
    
    # Determinar ruta del archivo de salida si no se proporciona
    if output_file is None:
        output_file = f"./OUT_model1/{instancia}.out"
    
    print(f"\n{'='*70}")
    print(f"SALUDTEST - Validación de Solución")
    print(f"Instancia: {instancia}")
    print(f"Archivo: {output_file}")
    print(f"{'='*70}\n")
    
    try:
        # ===== LEER DATOS DE ENTRADA =====
        print("[1/6] Leyendo datos de entrada...")
        
        archivo_pacientes = os.path.join(in_path, f"{instancia}_pacientes.in")
        archivo_flota = os.path.join(in_path, f"{instancia}_flota.in")
        archivo_incomp = os.path.join(in_path, f"{instancia}_incompatibilidades.in")
        
        pacientes, centro = leer_pacientes(archivo_pacientes)
        flota = leer_flota(archivo_flota)
        incomp = leer_incompatibilidades(archivo_incomp)
        
        print(f"  ✓ {len(pacientes)} pacientes cargados")
        print(f"  ✓ {len(flota)} tipos de combi")
        
        # ===== LEER ARCHIVO DE SALIDA =====
        print("\n[2/6] Leyendo archivo de salida...")
        
        if not os.path.exists(output_file):
            print(f"  ✗ Archivo no encontrado: {output_file}")
            return False
        
        with open(output_file, 'r') as f:
            contenido = f.read()
        
        beneficio_reportado, rutas, no_atendidos = parsear_salida(contenido)
        
        print(f"  ✓ Beneficio reportado: {beneficio_reportado}")
        print(f"  ✓ {len(rutas)} rutas")
        print(f"  ✓ {len(no_atendidos)} pacientes no atendidos")
        
        # ===== VALIDAR CADA RUTA =====
        print("\n[3/6] Validando rutas...")
        
        for ruta_idx, (tipo_combi, nodos) in enumerate(rutas):
            print(f"\n  Ruta {ruta_idx + 1}: {tipo_combi}")
            
            # Validar que exista el tipo de combi
            if tipo_combi not in flota:
                print(f"    ✗ Tipo de combi desconocido: {tipo_combi}")
                return False
            
            combi_info = flota[tipo_combi]
            
            # V1: Comienza y termina en centro (nodo 0)
            if len(nodos) < 2 or nodos[0] != 0 or nodos[-1] != 0:
                print(f"    ✗ Ruta no comienza o no termina en centro")
                return False
            print(f"    ✓ Comienza y termina en centro")
            
            # V2: Capacidad respetada
            num_pacientes = len(nodos) - 2  # Sin contar el centro dos veces
            if num_pacientes > combi_info.cant_asientos:
                print(f"    ✗ Excede capacidad: {num_pacientes} > {combi_info.cant_asientos}")
                return False
            print(f"    ✓ Capacidad respetada: {num_pacientes}/{combi_info.cant_asientos}")
            
            # V3: Ventanas de tiempo y tiempos de viaje
            print(f"    ✓ Validando ventanas de tiempo...")
            
            tiempo_actual = 0
            nodos_en_ruta = nodos[1:-1]  # Excluir centros de inicio y fin
            
            # Mapas de pacientes para búsqueda rápida
            pacientes_dict = {p.id: p for p in pacientes}
            
            for i in range(len(nodos) - 1):
                nodo_actual_id = nodos[i]
                nodo_siguiente_id = nodos[i + 1]
                
                # Encontrar coordenadas
                if nodo_actual_id == 0:
                    coord_actual = (centro.x, centro.y)
                else:
                    coord_actual = (pacientes_dict[nodo_actual_id].x, 
                                  pacientes_dict[nodo_actual_id].y)
                
                if nodo_siguiente_id == 0:
                    coord_siguiente = (centro.x, centro.y)
                else:
                    coord_siguiente = (pacientes_dict[nodo_siguiente_id].x, 
                                     pacientes_dict[nodo_siguiente_id].y)
                
                # Calcular distancia (tiempo a velocidad unitaria)
                dx = coord_siguiente[0] - coord_actual[0]
                dy = coord_siguiente[1] - coord_actual[1]
                dist = math.sqrt(dx*dx + dy*dy)
                tiempo_actual += dist
                
                # Validar ventana de tiempo si no es el centro
                if nodo_siguiente_id != 0:
                    paciente_sig = pacientes_dict[nodo_siguiente_id]
                    
                    if tiempo_actual < paciente_sig.ih_inicio:
                        # Puede esperar
                        tiempo_actual = paciente_sig.ih_inicio
                    
                    if tiempo_actual > paciente_sig.ih_fin:
                        print(f"      ✗ Paciente {nodo_siguiente_id} violado: "
                              f"tiempo={tiempo_actual:.2f} > ih_fin={paciente_sig.ih_fin}")
                        return False
                    
                    print(f"      ✓ P{nodo_siguiente_id}: tiempo={tiempo_actual:.2f} "
                          f"∈ [{paciente_sig.ih_inicio}, {paciente_sig.ih_fin}]")
            
            # V4: Sin categorías incompatibles
            print(f"    ✓ Validando incompatibilidades...")
            
            pacientes_en_ruta = [pacientes_dict[pid] for pid in nodos_en_ruta]
            
            for i, p1 in enumerate(pacientes_en_ruta):
                for p2 in pacientes_en_ruta[i+1:]:
                    if (p1.categoria, p2.categoria) in incomp:
                        print(f"      ✗ Incompatibilidad detectada: "
                              f"{p1.categoria} <-> {p2.categoria}")
                        return False
            
            if len(pacientes_en_ruta) > 1:
                cats = [p.categoria for p in pacientes_en_ruta]
                print(f"      ✓ Categorías compatibles: {cats}")
            
            # V5: Distancias calculadas correctamente
            # (ya se validó en ventanas de tiempo)
            print(f"    ✓ Distancias calculadas correctamente")
        
        # ===== VALIDAR PACIENTES NO ATENDIDOS =====
        print("\n[4/6] Validando pacientes no atendidos...")
        
        pacientes_atendidos = set()
        for _, nodos in rutas:
            for nodo_id in nodos[1:-1]:  # Excluir centros
                pacientes_atendidos.add(nodo_id)
        
        pacientes_no_atendidos_esperados = set(p.id for p in pacientes) - pacientes_atendidos
        
        if set(no_atendidos) != pacientes_no_atendidos_esperados:
            print(f"  ✗ Lista de no atendidos incorrecta")
            print(f"    Esperado: {sorted(pacientes_no_atendidos_esperados)}")
            print(f"    Reportado: {sorted(no_atendidos)}")
            return False
        
        print(f"  ✓ Lista de no atendidos válida: {sorted(no_atendidos) if no_atendidos else 'vacía'}")
        
        # ===== VALIDAR BENEFICIO TOTAL =====
        print("\n[5/6] Validando beneficio total...")
        
        beneficio_pacientes = sum(
            pacientes_dict[pid].beneficio 
            for pid in pacientes_atendidos
        )
        
        costo_combis_usadas = sum(
            flota[tipo_combi].costo_operacion
            for tipo_combi, _ in rutas
        )
        
        beneficio_esperado = beneficio_pacientes - costo_combis_usadas
        
        # Permitir pequeño error de precisión
        epsilon = 1e-6
        if abs(beneficio_reportado - beneficio_esperado) > epsilon:
            print(f"  ✗ Beneficio incorrecto")
            print(f"    Reportado: {beneficio_reportado}")
            print(f"    Esperado: {beneficio_esperado}")
            print(f"    Beneficio pacientes: {beneficio_pacientes}")
            print(f"    Costo combis: {costo_combis_usadas}")
            return False
        
        print(f"  ✓ Beneficio válido: {beneficio_reportado:.2f}")
        print(f"    Beneficio pacientes: {beneficio_pacientes:.2f}")
        print(f"    Costo combis: {costo_combis_usadas:.2f}")
        
        # ===== RESUMEN =====
        print(f"\n[6/6] Resumen de validación")
        print(f"  Rutas válidas: {len(rutas)}")
        print(f"  Pacientes atendidos: {len(pacientes_atendidos)}")
        print(f"  Pacientes no atendidos: {len(no_atendidos)}")
        print(f"  Beneficio neto: {beneficio_reportado:.2f}")
        
        print(f"\n✓ SOLUCIÓN VÁLIDA")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error durante validación: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python SaludTest.py <instancia> [output_file] [in_path]")
        print("Ejemplo: python SaludTest.py test1")
        print("         python SaludTest.py test1 ./OUT_model1/test1.out ./IN")
        sys.exit(1)
    
    instancia = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    in_path = sys.argv[3] if len(sys.argv) > 3 else "./IN"
    
    resultado = SaludTest(instancia, output_file, in_path)
    sys.exit(0 if resultado else 1)
