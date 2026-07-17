import sys
import os
import time
from typing import Tuple, List, Dict

from utils_saludCG import generar_rutas_iniciales

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root)

from pyscipopt import Model, quicksum
from Salud.utils_salud import (
    Paciente, TipoCombi,
    leer_pacientes, leer_flota, leer_incompatibilidades,
    generar_matriz_distancias, generar_salida
)


def construir_subproblema_base(tipo_k: str, combi_info: TipoCombi, pacientes: List[Paciente], 
                               centro: Paciente, distancias: dict, incomp: set, M: float) -> Tuple[Model, dict, dict]:
    """Construye un subproblema MILP base para un tipo de combi específico."""
    modelo_pricing = Model(f"Pricing_{tipo_k}")
    modelo_pricing.setParam("display/verblevel", 0)
    
    nodos = [centro] + pacientes
    
    # Variables de flujo de aristas
    x = {}
    for i in nodos:
        for j in nodos:
            if i.id != j.id and (i.id, j.id) in distancias:
                x[i.id, j.id] = modelo_pricing.addVar(vtype="B", name=f"x_{i.id}_{j.id}")
    
    # Variables de atención de pacientes
    z = {}
    for p in pacientes:
        z[p.id] = modelo_pricing.addVar(vtype="B", name=f"z_{p.id}")
    
    # Variables de tiempo
    T = {}
    for i in nodos:
        T[i.id] = modelo_pricing.addVar(vtype="C", lb=0, ub=M, name=f"T_{i.id}")

    # RC: Capacidad máxima de asientos
    modelo_pricing.addCons(quicksum(z[p.id] for p in pacientes) <= combi_info.cant_asientos)

    # RC: Vinculación fuerte y flujo estricto (Entrada == z == Salida)
    for p in pacientes:
        entrada = quicksum(x[i.id, p.id] for i in nodos if i.id != p.id and (i.id, p.id) in distancias)
        salida = quicksum(x[p.id, j.id] for j in nodos if p.id != j.id and (p.id, j.id) in distancias)
        modelo_pricing.addCons(entrada == z[p.id])
        modelo_pricing.addCons(salida == z[p.id])

    # RC: Salida y regreso del centro (como máximo 1 viaje por vehículo utilizado)
    usada = quicksum(x[centro.id, j.id] for j in pacientes if (centro.id, j.id) in distancias)
    regreso = quicksum(x[i.id, centro.id] for i in pacientes if (i.id, centro.id) in distancias)
    modelo_pricing.addCons(usada <= 1)
    modelo_pricing.addCons(regreso == usada)
    
    # Si la combi sale a operar, por lo menos debe visitar 1 paciente
    modelo_pricing.addCons(quicksum(z[p.id] for p in pacientes) >= usada)

    # RC: Ventanas de tiempo y Subtours (Subtour elimination / MTZ)
    for i in nodos:
        for j in nodos:
            if i.id != j.id and (i.id, j.id) in distancias and j.id != centro.id:
                dist = distancias[i.id, j.id]
                modelo_pricing.addCons(T[j.id] >= T[i.id] + dist - M * (1 - x[i.id, j.id]))

    for p in pacientes:
        modelo_pricing.addCons(T[p.id] >= p.ih_inicio * z[p.id])
        modelo_pricing.addCons(T[p.id] <= p.ih_fin * z[p.id] + M * (1 - z[p.id]))

    # RC: Incompatibilidades por bioseguridad
    for i_idx, p1 in enumerate(pacientes):
        for p2 in pacientes[i_idx+1:]:
            if (p1.categoria, p2.categoria) in incomp:
                modelo_pricing.addCons(z[p1.id] + z[p2.id] <= 1)

    return modelo_pricing, x, z


def resolver_pricing(modelo_pricing: Model, x: dict, z: dict, tipo_k: str, combi_info: TipoCombi, 
                     pacientes: List[Paciente], centro: Paciente, distancias: dict, pac_dict: dict, 
                     dual_pi: dict, dual_mu: float, time_limit: float) -> Tuple[bool, dict, float]:
    """Resuelve el problema de pricing actualizando los costos reducidos a partir de los duales."""
    modelo_pricing.freeTransform()
    
    # Maximizar Ganancia Reducida: Sum (Beneficio_p - pi_p) * z_p
    obj_expr = quicksum((pac_dict[p.id].beneficio - dual_pi.get(p.id, 0.0)) * z[p.id] for p in pacientes)
    modelo_pricing.setObjective(obj_expr, "maximize")
    
    modelo_pricing.setParam("limits/time", time_limit)
    modelo_pricing.optimize()

    status = modelo_pricing.getStatus()
    if status in ["optimal", "timelimit", "gaplimit"] and len(modelo_pricing.getSols()) > 0:
        obj_val = modelo_pricing.getObjVal()
        ganancia_reducida = obj_val - combi_info.costo_operacion - dual_mu
        
        # Si la columna tiene una ganancia reducida positiva/atractiva
        if ganancia_reducida > 1e-4:
            pacientes_ids = [p.id for p in pacientes if modelo_pricing.getVal(z[p.id]) > 0.5]
            beneficio_ruta = sum(pac_dict[pid].beneficio for pid in pacientes_ids)
            
            nodos = [centro] + pacientes
            aristas = {}
            for i in nodos:
                for j in nodos:
                    if i.id != j.id and (i.id, j.id) in distancias:
                        if modelo_pricing.getVal(x[i.id, j.id]) > 0.5:
                            aristas[i.id] = j.id
            
            # Reconstrucción estructurada del camino secuencial
            camino = [centro.id]
            actual = centro.id
            while actual in aristas:
                proximo = aristas[actual]
                camino.append(proximo)
                if proximo == centro.id: 
                    break
                actual = proximo
            
            rentabilidad = beneficio_ruta - combi_info.costo_operacion
            
            # Representación estructurada de la nueva columna (Ruta)
            nueva_ruta = {
                "tipo_combi": tipo_k,
                "pacientes_ids": pacientes_ids,
                "camino": camino,
                "rentabilidad": rentabilidad
            }
            return True, nueva_ruta, ganancia_reducida
            
    return False, None, 0.0


def SaludCG(instancia: str, threshold: float) -> bool:
    """
    Estrategia 2: Modelo mediante Generación de Columnas.
    """
    start_time = time.time()
    in_path = "./IN"
    out_path = "./OUT_model2"
    
    print(f"\n{'='*70}")
    print(f"SALUD CG - Generación de Columnas (Estructurado)")
    print(f"Instancia: {instancia}, Threshold: {threshold}s")
    print(f"{'='*70}\n")
    
    try:
        # ===== LEER DATOS =====
        archivo_pacientes = os.path.join(in_path, f"{instancia}_pacientes.in")
        archivo_flota = os.path.join(in_path, f"{instancia}_flota.in")
        archivo_incomp = os.path.join(in_path, f"{instancia}_incompatibilidades.in")
        
        pacientes, centro = leer_pacientes(archivo_pacientes)
        flota = leer_flota(archivo_flota)
        incomp = leer_incompatibilidades(archivo_incomp)
        distancias = generar_matriz_distancias(pacientes, centro)
        
        pac_dict = {p.id: p for p in pacientes}
        M = 10000
        
        # Inicializar los modelos matemáticos de Pricing de forma estructurada
        submodelos = {}
        for tipo_k, combi_info in flota.items():
            submodelos[tipo_k] = construir_subproblema_base(tipo_k, combi_info, pacientes, centro, distancias, incomp, M)
        
        # Pool dinámico de columnas (rutas iniciales vacías, CG generará las necesarias)
        pool_rutas = generar_rutas_iniciales(pacientes, centro, flota, distancias, incomp, pac_dict)
        
        # ===== BUCLE PRINCIPAL DE GENERACIÓN DE COLUMNAS =====
        iteracion = 0
        iteraciones_sin_mejora = 0  # Contador robusto para convergencia LP
        while True:
            elapsed = time.time() - start_time
            if elapsed > threshold * 0.8:  # Resguardo de tiempo para el Maestro Entero Final
                break
                
            iteracion += 1
            maestro_rl = Model("Maestro_Relaxed")
            maestro_rl.setParam("display/verblevel", 0)
            maestro_rl.setParam("presolving/maxrounds", 0) 
            
            # Variables de selección continuas [0, 1]
            y = {}
            for idx, r in enumerate(pool_rutas):
                y[idx] = maestro_rl.addVar(vtype="C", lb=0, name=f"y_{idx}")
                
            # FO del maestro: Maximize rentabilidad total del pool
            maestro_rl.setObjective(quicksum(r["rentabilidad"] * y[idx] for idx, r in enumerate(pool_rutas)), "maximize")
            
            # Restricción Maestro: Cada paciente atendido como máximo 1 vez
            cons_pacientes = {}
            for p in pacientes:
                rutas_con_p = [idx for idx, r in enumerate(pool_rutas) if p.id in r["pacientes_ids"]]
                cons_pacientes[p.id] = maestro_rl.addCons(quicksum(y[idx] for idx in rutas_con_p) <= 1)
                
            # Restricción Maestro: No superar la cantidad de vehículos disponibles de la flota
            cons_flota = {}
            for tipo_k, combi_info in flota.items():
                rutas_tipo = [idx for idx, r in enumerate(pool_rutas) if r["tipo_combi"] == tipo_k]
                cons_flota[tipo_k] = maestro_rl.addCons(quicksum(y[idx] for idx in rutas_tipo) <= combi_info.cant_disponible)
                
            maestro_rl.optimize()
            
            # Extracción estructurada de los valores duales (precios sombra)
            # IMPORTANTE: No truncar duales a 0 artificialmente. Según la teoría CG,
            # los duales contienen información crítica para el pricing correcto.
            # Solo si son significativamente negativos (ruido numérico), truncar.
            dual_pi = {}
            for p in pacientes:
                try:
                    raw_dual = maestro_rl.getDualsolLinear(cons_pacientes[p.id])
                    if raw_dual < -1e-6:  # Detectar valores significativamente negativos
                        print(f"[DEBUG] Dual negativo para paciente {p.id}: {raw_dual:.2e}")
                    dual_pi[p.id] = max(0.0, raw_dual)
                except:
                    dual_pi[p.id] = 0.0
                
            dual_mu = {}
            for tipo_k in flota.keys():
                try:
                    raw_dual = maestro_rl.getDualsolLinear(cons_flota[tipo_k])
                    if raw_dual < -1e-6:  # Detectar valores significativamente negativos
                        print(f"[DEBUG] Dual negativo para tipo {tipo_k}: {raw_dual:.2e}")
                    dual_mu[tipo_k] = max(0.0, raw_dual)
                except:
                    dual_mu[tipo_k] = 0.0

            # Resolver el pricing por cada tipo de combi de la flota
            rutas_agregadas = 0
            for tipo_k, combi_info in flota.items():
                encontrada, nueva_ruta, gr = resolver_pricing(
                    submodelos[tipo_k][0], submodelos[tipo_k][1], submodelos[tipo_k][2],
                    tipo_k, combi_info, pacientes, centro, distancias, pac_dict, 
                    dual_pi, dual_mu.get(tipo_k, 0.0), 10.0
                )
                if encontrada:
                    # Comprobar que el pricing no haya devuelto una ruta idéntica
                    ya_existe = any(r["camino"] == nueva_ruta["camino"] and r["tipo_combi"] == nueva_ruta["tipo_combi"] for r in pool_rutas)
                    
                    if not ya_existe:
                        pool_rutas.append(nueva_ruta)
                        rutas_agregadas += 1

            # Criterio robusto de convergencia LP: requiere 2+ iteraciones sin mejora
            # (más conservador que parar en la primera iteración sin columnas)
            if rutas_agregadas == 0:
                iteraciones_sin_mejora += 1
                if iteraciones_sin_mejora >= 2:
                    print(f"[DEBUG] Convergencia LP alcanzada: {iteraciones_sin_mejora} iteraciones sin nuevas columnas")
                    break
            else:
                iteraciones_sin_mejora = 0

        # =======================================================
        # RESOLUCIÓN ENTERA FINAL (Restricción del pool a binarias)
        # =======================================================
        tiempo_restante = threshold - (time.time() - start_time)
        maestro_ip = Model("Maestro_Integer")
        maestro_ip.setParam("display/verblevel", 0)
        maestro_ip.setParam("limits/time", max(5.0, tiempo_restante))
        
        y_int = {}
        for idx, r in enumerate(pool_rutas):
            y_int[idx] = maestro_ip.addVar(vtype="B", name=f"y_{idx}")
            
        maestro_ip.setObjective(quicksum(r["rentabilidad"] * y_int[idx] for idx, r in enumerate(pool_rutas)), "maximize")
        
        for p in pacientes:
            rutas_con_p = [idx for idx, r in enumerate(pool_rutas) if p.id in r["pacientes_ids"]]
            maestro_ip.addCons(quicksum(y_int[idx] for idx in rutas_con_p) <= 1)
            
        for tipo_k, combi_info in flota.items():
            rutas_tipo = [idx for idx, r in enumerate(pool_rutas) if r["tipo_combi"] == tipo_k]
            maestro_ip.addCons(quicksum(y_int[idx] for idx in rutas_tipo) <= combi_info.cant_disponible)
            
        maestro_ip.optimize()
        
        beneficio_total = 0.0
        rutas_finales = []
        pacientes_atendidos = set()
        
        if len(maestro_ip.getSols()) > 0:
            beneficio_total = maestro_ip.getObjVal()
            for idx, r in enumerate(pool_rutas):
                if maestro_ip.getVal(y_int[idx]) > 0.5:
                    rutas_finales.append((r["tipo_combi"], r["camino"]))
                    pacientes_atendidos.update(r["pacientes_ids"])
                    
        no_atendidos = [p.id for p in pacientes if p.id not in pacientes_atendidos]
        
        print(f"DEBUG: Pacientes atendidos: {len(pacientes_atendidos)}")
        print(f"DEBUG: Rutas elegidas: {len(rutas_finales)}")
        for r in rutas_finales:
            print(f"Ruta: {r[1]}")

        # ===== GENERAR ARCHIVO DE SALIDA FORMATO ESTRICTO =====
        salida_contenido = generar_salida(beneficio_total, rutas_finales, no_atendidos)
        
        os.makedirs(out_path, exist_ok=True)
        archivo_salida = os.path.join(out_path, f"{instancia}.out")
        
        with open(archivo_salida, 'w') as f:
            f.write(salida_contenido)
            
        print(f"[OK] Output generado exitosamente: {archivo_salida}")
        print(f"[OK] Beneficio Neto Final Obtenido: {beneficio_total:.2f}")
        return True
        
    except Exception as e:
        print(f"\n✗ Error crítico en la ejecución de la estrategia: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python SaludCG.py <instancia> <threshold>")
        sys.exit(1)
    
    instancia_param = sys.argv[1]
    threshold_param = float(sys.argv[2])
    SaludCG(instancia_param, threshold_param)