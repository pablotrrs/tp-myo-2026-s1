"""
Estrategia 1: Salud(instancia, umbral)
Resuelve el problema mediante un modelo compacto MILP.
"""

import sys
import os
import signal
import time
from typing import Tuple, List, Dict

# Agregar el directorio padre para importar utils_salud
sys.path.insert(0, os.path.dirname(__file__))

from pyscipopt import Model, quicksum, SCIP_PARAMSETTING
from utils_salud import (
    Paciente, TipoCombi,
    leer_pacientes, leer_flota, leer_incompatibilidades,
    distancia_euclidea, validar_entrada, generar_matriz_distancias,
    generar_salida
)


def construir_modelo_milp(pacientes: List[Paciente], centro: Paciente,
                         flota: Dict[str, TipoCombi],
                         incomp: set) -> Tuple[Model, dict]:
    """
    Construye el modelo MILP para el problema Salud.
    
    Retorna: (modelo, variables_dict)
    """
    
    modelo = Model("Salud")
    
    # Obtener parámetros
    nodos = [centro] + pacientes
    tipos_combi = list(flota.keys())
    distancias = generar_matriz_distancias(pacientes, centro)
    
    # Crear lista de todas las combis (instancias) disponibles
    combis_disponibles = []
    combi_id = 0
    combi_to_tipo = {}  # Mapeo de ID de combi a tipo
    for tipo_k in tipos_combi:
        for _ in range(flota[tipo_k].cant_disponible):
            combis_disponibles.append(combi_id)
            combi_to_tipo[combi_id] = tipo_k
            combi_id += 1
    
    # Big-M
    M = 10000
    
    # ===== VARIABLES =====
    
    # x[i,j,k] ∈ {0,1}: viajar de nodo i a nodo j con combi k (instancia)
    x = {}
    for i in nodos:
        for j in nodos:
            if i.id != j.id and (i.id, j.id) in distancias:
                for k in combis_disponibles:
                    x[i.id, j.id, k] = modelo.addVar(
                        vtype="B", 
                        name=f"x_{i.id}_{j.id}_{k}"
                    )
    
    # z[p,k] ∈ {0,1}: paciente p atendido por combi k (instancia)
    z = {}
    for p in pacientes:
        for k in combis_disponibles:
            z[p.id, k] = modelo.addVar(
                vtype="B",
                name=f"z_{p.id}_{k}"
            )
    
    # a[p] ∈ {0,1}: paciente p es atendido (selección)
    a = {}
    for p in pacientes:
        a[p.id] = modelo.addVar(vtype="B", name=f"a_{p.id}")
    
    # u[k] ∈ {0,1}: combi k es utilizada
    u = {}
    for k in combis_disponibles:
        u[k] = modelo.addVar(vtype="B", name=f"u_{k}")
    
    # T[i,k] ≥ 0: tiempo de llegada al nodo i con combi k (instancia)
    T = {}
    for i in nodos:
        for k in combis_disponibles:
            T[i.id, k] = modelo.addVar(
                vtype="C", lb=0, ub=M,
                name=f"T_{i.id}_{k}"
            )
    
    # ===== FUNCIÓN OBJETIVO =====
    # max: Σ(beneficio[p] * a[p]) - Σ(costo[tipo(k)] * u[k])
    
    beneficio_pacientes = quicksum(
        p.beneficio * a[p.id] for p in pacientes
    )
    costo_combis = quicksum(
        flota[combi_to_tipo[k]].costo_operacion * u[k] for k in combis_disponibles
    )
    
    modelo.setObjective(beneficio_pacientes - costo_combis, "maximize")
    
    # ===== RESTRICCIONES =====
    
    # RC1: Cobertura - cada paciente atendido por una sola combi (o ninguna)
    for p in pacientes:
        modelo.addCons(
            quicksum(z[p.id, k] for k in combis_disponibles) == a[p.id],
            name=f"cobertura_{p.id}"
        )
    
    # RC2: Flujo en nodos - si entra, debe salir
    for k in combis_disponibles:
        for p in pacientes:
            entrada = quicksum(
                x[i.id, p.id, k] for i in nodos
                if i.id != p.id and (i.id, p.id) in distancias
            )
            salida = quicksum(
                x[p.id, j.id, k] for j in nodos
                if p.id != j.id and (p.id, j.id) in distancias
            )
            modelo.addCons(entrada == salida, name=f"flujo_{p.id}_{k}")
    
    # RC3: Salida y regreso del centro
    for k in combis_disponibles:
        salida_centro = quicksum(
            x[centro.id, j.id, k] for j in pacientes
            if (centro.id, j.id) in distancias
        )
        regreso_centro = quicksum(
            x[i.id, centro.id, k] for i in pacientes
            if (i.id, centro.id) in distancias
        )
        modelo.addCons(salida_centro == u[k], name=f"salida_{k}")
        modelo.addCons(regreso_centro == u[k], name=f"regreso_{k}")
    
    # RC4: Capacidad por combi
    for k in combis_disponibles:
        tipo_k = combi_to_tipo[k]
        modelo.addCons(
            quicksum(z[p.id, k] for p in pacientes)
            <= flota[tipo_k].cant_asientos * u[k],
            name=f"capacidad_{k}"
        )
    
    # RC5: Ventanas de tiempo
    for k in combis_disponibles:
        # T[0,k] = 0: el viaje comienza en t=0 desde el centro médico
        modelo.addCons(T[centro.id, k] == 0, name=f"t_inicio_{k}")

        # Propagación del tiempo
        for i in nodos:
            for j in nodos:
                if i.id != j.id and (i.id, j.id) in distancias:
                    if j.id != centro.id:  # No es el centro
                        dist = distancias[i.id, j.id]
                        modelo.addCons(
                            T[j.id, k] >= T[i.id, k] + dist 
                            - M * (1 - x[i.id, j.id, k]),
                            name=f"tiempo_prop_{i.id}_{j.id}_{k}"
                        )
        
        # Ventanas de tiempo de pacientes
        for p in pacientes:
            # T[p,k] >= ih_inicio * z[p,k]
            modelo.addCons(
                T[p.id, k] >= p.ih_inicio * z[p.id, k],
                name=f"tw_inicio_{p.id}_{k}"
            )
            # T[p,k] <= ih_fin * z[p,k] + M * (1 - z[p,k])
            modelo.addCons(
                T[p.id, k] <= p.ih_fin * z[p.id, k] + M * (1 - z[p.id, k]),
                name=f"tw_fin_{p.id}_{k}"
            )
    
    # RC6: Incompatibilidades de categorías
    for k in combis_disponibles:
        for i, p1 in enumerate(pacientes):
            for p2 in pacientes[i+1:]:
                if (p1.categoria, p2.categoria) in incomp:
                    modelo.addCons(
                        z[p1.id, k] + z[p2.id, k] <= 1,
                        name=f"incomp_{p1.id}_{p2.id}_{k}"
                    )
    
    # ===== CONECTAR z CON x =====
    # z[p,k] = entrada al nodo p: entrar al vértice es equivalente a atender al paciente.
    # Se usa igualdad (no <=) para cerrar ambas implicaciones:
    #   si la combi entra, recoge; si recoge, entró.
    # La sumatoria incluye el nodo 0 (centro) para capturar arcos directos centro→paciente.
    for k in combis_disponibles:
        for p in pacientes:
            entrada = quicksum(
                x[i.id, p.id, k] for i in nodos
                if i.id != p.id and (i.id, p.id) in distancias
            )
            modelo.addCons(z[p.id, k] == entrada, name=f"z_conn_{p.id}_{k}")
    
    variables_dict = {
        'x': x, 'z': z, 'a': a, 'u': u, 'T': T,
        'nodos': nodos, 'pacientes': pacientes, 'centro': centro,
        'combis_disponibles': combis_disponibles, 'combi_to_tipo': combi_to_tipo,
        'flota': flota, 'distancias': distancias
    }
    
    return modelo, variables_dict


def extraer_solucion(modelo: Model, vars_dict: dict) -> Tuple[float, List, List]:
    """
    Extrae la solución del modelo resuelto.
    
    Retorna: (beneficio, rutas, no_atendidos)
    donde rutas = [(tipo_combi, [ids_pacientes]), ...]
    """
    
    if modelo.getStatus() != "optimal":
        # Intentar obtener solución factible del problema
        pass
    
    x = vars_dict['x']
    z = vars_dict['z']
    a = vars_dict['a']
    u = vars_dict['u']
    nodos = vars_dict['nodos']
    pacientes = vars_dict['pacientes']
    centro = vars_dict['centro']
    combis_disponibles = vars_dict['combis_disponibles']
    combi_to_tipo = vars_dict['combi_to_tipo']
    
    # Extraer rutas
    rutas = []
    
    # Para cada combi utilizada, extraer su ruta
    for k in combis_disponibles:
        if modelo.getVal(u[k]) > 0.5:
            tipo_k = combi_to_tipo[k]
            
            # Encontrar pacientes atendidos por esta combi
            pacientes_combi = []
            for p in pacientes:
                if modelo.getVal(z[p.id, k]) > 0.5:
                    pacientes_combi.append(p.id)
            
            if pacientes_combi:
                # Ordenar pacientes según la secuencia de viaje
                ruta_ordenada = ordenar_ruta(
                    centro, pacientes_combi, x, k, modelo, nodos
                )
                rutas.append((tipo_k, ruta_ordenada))
    
    # Pacientes no atendidos
    no_atendidos = [
        p.id for p in pacientes
        if modelo.getVal(a[p.id]) < 0.5
    ]
    
    # Beneficio
    beneficio = modelo.getObjVal()
    
    return beneficio, rutas, no_atendidos


def ordenar_ruta(centro: Paciente, pacientes_ids: List[int], x: dict, k: int,
                modelo: Model, nodos: List[Paciente]) -> List[int]:
    """
    Ordena los pacientes en una ruta según la secuencia de viaje (x variables).
    
    Retorna: [0, p1, p2, ..., 0]
    """
    
    # Construir grafo de aristas usadas para esta combi k
    aristas = {}
    for i in nodos:
        for j in nodos:
            if i.id != j.id and (i.id, j.id, k) in x:
                val = modelo.getVal(x[i.id, j.id, k])
                if val is not None and val > 0.5:
                    aristas[i.id] = j.id
    
    # Reconstruir la ruta desde el centro
    ruta = [centro.id]
    nodo_actual = centro.id
    visited = set([centro.id])
    
    while nodo_actual in aristas:
        proximo = aristas[nodo_actual]
        if proximo == centro.id and len(ruta) > 1:
            # Retorno al centro
            ruta.append(proximo)
            break
        if proximo in visited:
            # Ciclo detectado, salir
            break
        ruta.append(proximo)
        visited.add(proximo)
        nodo_actual = proximo
    
    # Asegurar que termina en centro
    if len(ruta) == 0 or ruta[-1] != centro.id:
        ruta.append(centro.id)
    
    # Si la ruta no incluye todos los pacientes, hay error
    ruta_pacientes = set(ruta[1:-1])
    pacientes_esperados = set(pacientes_ids)
    
    if ruta_pacientes != pacientes_esperados:
        # Fallback: ordenar pacientes manualmente
        ruta = [centro.id] + sorted(pacientes_ids) + [centro.id]
    
    return ruta


def Salud(instancia: str, threshold: float,
          out_path: str = "./OUT_modelo1", in_path: str = "./IN") -> bool:
    """
    Estrategia 1: Modelo compacto MILP.
    
    Resuelve el problema de logística médica mediante un modelo MILP compacto.
    
    Args:
        instancia: nombre de la instancia (sin extensión, ej: "test1")
        threshold: tiempo máximo de ejecución en segundos
        out_path: carpeta donde escribir {instancia}.out
        in_path: carpeta con los archivos {instancia}_*.in

    Retorna: True si se completó, False en caso contrario

    Rutas por defecto:
    - Entrada: ./IN/{instancia}_*.in
    - Salida: ./OUT_modelo1/{instancia}.out

    El umbral es global: se cuenta desde el inicio de la función, de modo que la
    lectura de datos y el armado del modelo se descuentan del presupuesto que se
    le entrega al solver.
    """

    start_time = time.time()

    print(f"\n{'='*70}")
    print(f"SALUD - Modelo Compacto MILP")
    print(f"Instancia: {instancia}, Threshold: {threshold}s")
    print(f"{'='*70}\n")
    
    try:
        # ===== LEER DATOS =====
        archivo_pacientes = os.path.join(in_path, f"{instancia}_pacientes.in")
        archivo_flota = os.path.join(in_path, f"{instancia}_flota.in")
        archivo_incomp = os.path.join(in_path, f"{instancia}_incompatibilidades.in")
        
        print("[1/4] Leyendo datos...")
        pacientes, centro = leer_pacientes(archivo_pacientes)
        flota = leer_flota(archivo_flota)
        incomp = leer_incompatibilidades(archivo_incomp)
        
        print(f"  [OK] {len(pacientes)} pacientes")
        print(f"  [OK] {len(flota)} tipos de combi")
        print(f"  [OK] Centro médico en ({centro.x}, {centro.y})")
        
        # Validar
        validar_entrada(pacientes, flota, incomp)
        
        # ===== CONSTRUIR MODELO =====
        print("\n[2/4] Construyendo modelo MILP...")
        modelo, vars_dict = construir_modelo_milp(pacientes, centro, flota, incomp)
        
        print(f"  [OK] Variables: {modelo.getNVars()}")
        print(f"  [OK] Restricciones: {modelo.getNConss()}")

        # El enunciado pide el tamaño del MODELO INICIAL, por lo que estas
        # métricas se emiten antes de optimizar: después de optimize() SCIP
        # informa el modelo ya transformado por el presolve, que es más chico.
        print(f"[METRIC] n_vars={modelo.getNVars()}")
        print(f"[METRIC] n_conss={modelo.getNConss()}")

        # ===== CONFIGURAR TIMEOUT =====
        # Se le entrega al solver solo el tiempo que queda del umbral global,
        # descontando lo que ya consumieron la lectura y el armado del modelo.
        # Se reserva un margen para extraer la solución y escribir el .out.
        reserva_salida = min(5.0, max(1.0, 0.02 * threshold))
        elapsed = time.time() - start_time
        tiempo_solver = max(1.0, threshold - elapsed - reserva_salida)

        print(f"\n[3/4] Resolviendo (umbral global: {threshold}s, "
              f"ya usados: {elapsed:.1f}s, para el solver: {tiempo_solver:.1f}s)...")
        modelo.setParam("limits/time", tiempo_solver)
        modelo.setParam("display/verblevel", 0)  # Silenciar SCIP
        
        # ===== RESOLVER =====
        modelo.optimize()

        print(f"[METRIC] dual_bound={modelo.getDualbound()}")

        # ===== EXTRAER SOLUCIÓN =====
        print(f"\n[4/4] Extrayendo solución...")
        beneficio, rutas, no_atendidos = extraer_solucion(modelo, vars_dict)
        
        print(f"  [OK] Beneficio: {beneficio:.2f}")
        print(f"  [OK] Rutas: {len(rutas)}")
        print(f"  [OK] Pacientes no atendidos: {len(no_atendidos)}")
        
        # ===== GENERAR OUTPUT =====
        salida_contenido = generar_salida(beneficio, rutas, no_atendidos)
        
        # Guardar a archivo
        os.makedirs(out_path, exist_ok=True)
        archivo_salida = os.path.join(out_path, f"{instancia}.out")
        
        with open(archivo_salida, 'w') as f:
            f.write(salida_contenido)
        
        print(f"\n[OK] Salida guardada en: {archivo_salida}")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python Salud.py <instancia> <threshold> [out_path] [in_path]")
        print("Ejemplo: python Salud.py test1 30")
        sys.exit(1)

    instancia = sys.argv[1]
    threshold = float(sys.argv[2])
    out_path = sys.argv[3] if len(sys.argv) > 3 else "./OUT_modelo1"
    in_path = sys.argv[4] if len(sys.argv) > 4 else "./IN"

    Salud(instancia, threshold, out_path, in_path)
