"""
Estrategia 3: SaludChallenger(instancia, umbral)
Resuelve el problema aplicando Branch & Price: generación de columnas en cada nodo
del árbol, con inicialización golosa, eliminación de columnas sin uso y warm-start.
"""

import sys
import os
import time
import heapq
import itertools
import math
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root)

from pyscipopt import Model, quicksum, SCIP_PARAMSETTING
from Salud.utils_salud import (
    Paciente, TipoCombi,
    leer_pacientes, leer_flota, leer_incompatibilidades,
    generar_matriz_distancias, generar_salida
)

EPS_RC = 1e-4      # ganancia reducida mínima para agregar una columna
EPS_INT = 1e-5     # tolerancia de integralidad
EPS_OBJ = 1e-6     # tolerancia para poda por cota
K_SIN_USO = 25     # resoluciones consecutivas sin uso antes de eliminar una columna
MAX_NODOS = 500    # resguardo contra árboles patológicos


@dataclass(order=True)
class Nodo:
    """Nodo del árbol de Branch & Price (heap best-first por cota del padre)."""
    prioridad: float        # -cota_LP del padre: heapq saca primero la mejor cota
    orden: int              # desempate estable
    juntos: FrozenSet[Tuple[int, int]] = field(compare=False, default=frozenset())
    separados: FrozenSet[Tuple[int, int]] = field(compare=False, default=frozenset())
    requeridos: FrozenSet[int] = field(compare=False, default=frozenset())
    prohibidos: FrozenSet[int] = field(compare=False, default=frozenset())
    flota_lb: dict = field(compare=False, default_factory=dict)
    flota_ub: dict = field(compare=False, default_factory=dict)
    profundidad: int = field(compare=False, default=0)


def columna_compatible(ruta: dict, nodo: Nodo) -> bool:
    """Una columna es válida en un nodo si respeta todas sus decisiones de ramificación."""
    s = set(ruta["pacientes_ids"])
    if s & set(nodo.prohibidos):
        return False
    for (a, b) in nodo.juntos:
        if (a in s) != (b in s):
            return False
    for (a, b) in nodo.separados:
        if a in s and b in s:
            return False
    return True


def nueva_columna(tipo: str, orden_pacientes: List[Paciente], centro: Paciente,
                  info: TipoCombi) -> dict:
    beneficio = sum(p.beneficio for p in orden_pacientes)
    return {
        "tipo_combi": tipo,
        "pacientes_ids": [p.id for p in orden_pacientes],
        "camino": [centro.id] + [p.id for p in orden_pacientes] + [centro.id],
        "rentabilidad": beneficio - info.costo_operacion,
        "sin_uso": 0,
        "eliminada": False,
    }


def generar_columnas_iniciales(pacientes: List[Paciente], centro: Paciente,
                               flota: Dict[str, TipoCombi], distancias: dict,
                               incomp: set) -> List[dict]:
    """Inicialización eficiente: singletons factibles + rutas golosas por tipo."""
    columnas = []

    def alcanzable(p: Paciente) -> bool:
        return max(distancias[(centro.id, p.id)], p.ih_inicio) <= p.ih_fin

    # 1) Singletons factibles para cada tipo (garantizan flexibilidad al maestro)
    for tipo, info in flota.items():
        for p in pacientes:
            if alcanzable(p):
                columnas.append(nueva_columna(tipo, [p], centro, info))

    # 2) Heurística golosa: rutas multi-paciente por tipo de combi
    for tipo, info in flota.items():
        pendientes = [p for p in pacientes if alcanzable(p)]
        pendientes.sort(key=lambda p: -p.beneficio)
        while pendientes:
            ruta = []
            t = 0.0
            actual = centro.id
            while len(ruta) < info.cant_asientos:
                mejor, mejor_t, mejor_score = None, None, None
                for p in pendientes:
                    if p in ruta:
                        continue
                    if any((p.categoria, q.categoria) in incomp for q in ruta):
                        continue
                    llegada = max(t + distancias[(actual, p.id)], p.ih_inicio)
                    if llegada > p.ih_fin:
                        continue
                    score = p.beneficio - distancias[(actual, p.id)]
                    if mejor is None or score > mejor_score:
                        mejor, mejor_t, mejor_score = p, llegada, score
                if mejor is None:
                    break
                ruta.append(mejor)
                t = mejor_t
                actual = mejor.id
            if not ruta:
                break
            if len(ruta) > 1:  # los singletons ya fueron agregados
                columnas.append(nueva_columna(tipo, ruta, centro, info))
            for p in ruta:
                pendientes.remove(p)

    return columnas


def construir_pricing(tipo_k: str, combi_info: TipoCombi, pacientes: List[Paciente],
                      centro: Paciente, distancias: dict, incomp: set, M: float,
                      nodo: Nodo) -> Tuple[Model, dict, dict]:
    """Subproblema de pricing para un tipo de combi, con las decisiones del nodo."""
    mp = Model(f"Pricing_{tipo_k}")
    mp.setParam("display/verblevel", 0)

    nodos = [centro] + pacientes
    n = len(pacientes)

    x = {}
    for i in nodos:
        for j in nodos:
            if i.id != j.id and (i.id, j.id) in distancias:
                x[i.id, j.id] = mp.addVar(vtype="B", name=f"x_{i.id}_{j.id}")

    z = {p.id: mp.addVar(vtype="B", name=f"z_{p.id}") for p in pacientes}
    T = {i.id: mp.addVar(vtype="C", lb=0, ub=M, name=f"T_{i.id}") for i in nodos}
    # Variable de orden (MTZ) para eliminar ciclos entre pacientes a distancia 0
    u = {p.id: mp.addVar(vtype="C", lb=0, ub=n, name=f"u_{p.id}") for p in pacientes}

    mp.addCons(quicksum(z.values()) <= combi_info.cant_asientos)

    for p in pacientes:
        entrada = quicksum(x[i.id, p.id] for i in nodos if (i.id, p.id) in x)
        salida = quicksum(x[p.id, j.id] for j in nodos if (p.id, j.id) in x)
        mp.addCons(entrada == z[p.id])
        mp.addCons(salida == z[p.id])

    usada = quicksum(x[centro.id, j.id] for j in pacientes if (centro.id, j.id) in x)
    regreso = quicksum(x[i.id, centro.id] for i in pacientes if (i.id, centro.id) in x)
    mp.addCons(usada <= 1)
    mp.addCons(regreso == usada)
    # Nadie puede ser atendido si la combi no sale del centro (evita rutas fantasma)
    for p in pacientes:
        mp.addCons(z[p.id] <= usada)

    # Ventanas de tiempo (permiten espera) y orden MTZ anti-subtours
    for i in nodos:
        for j in nodos:
            if (i.id, j.id) in x and j.id != centro.id:
                dist = distancias[i.id, j.id]
                mp.addCons(T[j.id] >= T[i.id] + dist - M * (1 - x[i.id, j.id]))
                if i.id != centro.id:
                    mp.addCons(u[j.id] >= u[i.id] + 1 - n * (1 - x[i.id, j.id]))

    for p in pacientes:
        mp.addCons(T[p.id] >= p.ih_inicio * z[p.id])
        mp.addCons(T[p.id] <= p.ih_fin * z[p.id] + M * (1 - z[p.id]))

    # Incompatibilidades de bioseguridad
    for i_idx, p1 in enumerate(pacientes):
        for p2 in pacientes[i_idx + 1:]:
            if (p1.categoria, p2.categoria) in incomp:
                mp.addCons(z[p1.id] + z[p2.id] <= 1)

    # Decisiones de ramificación del nodo
    for (a, b) in nodo.juntos:
        mp.addCons(z[a] == z[b])
    for (a, b) in nodo.separados:
        mp.addCons(z[a] + z[b] <= 1)
    for pid in nodo.prohibidos:
        mp.addCons(z[pid] == 0)

    return mp, x, z


def resolver_pricing(mp: Model, x: dict, z: dict, tipo_k: str, combi_info: TipoCombi,
                     pacientes: List[Paciente], centro: Paciente, pac_dict: dict,
                     dual_pi: dict, dual_mu: float,
                     time_limit: float) -> Tuple[bool, Optional[dict], float]:
    """Resuelve el pricing con los duales actuales; devuelve una columna atractiva si existe."""
    mp.freeTransform()
    obj_expr = quicksum((pac_dict[p.id].beneficio - dual_pi.get(p.id, 0.0)) * z[p.id]
                        for p in pacientes)
    mp.setObjective(obj_expr, "maximize")
    mp.setParam("limits/time", time_limit)
    mp.optimize()

    status = mp.getStatus()
    if status in ["optimal", "timelimit", "gaplimit"] and len(mp.getSols()) > 0:
        ganancia_reducida = mp.getObjVal() - combi_info.costo_operacion - dual_mu
        if ganancia_reducida > EPS_RC:
            aristas = {}
            for (i, j), var in x.items():
                if mp.getVal(var) > 0.5:
                    aristas[i] = j

            camino = [centro.id]
            actual = centro.id
            while actual in aristas:
                proximo = aristas[actual]
                camino.append(proximo)
                if proximo == centro.id:
                    break
                actual = proximo

            pacientes_ids = [nid for nid in camino if nid != centro.id]
            if not pacientes_ids:
                return False, None, 0.0

            beneficio = sum(pac_dict[pid].beneficio for pid in pacientes_ids)
            col = {
                "tipo_combi": tipo_k,
                "pacientes_ids": pacientes_ids,
                "camino": camino,
                "rentabilidad": beneficio - combi_info.costo_operacion,
                "sin_uso": 0,
                "eliminada": False,
            }
            return True, col, ganancia_reducida

    return False, None, 0.0


def resolver_maestro_lp(pool: List[dict], activos: List[int], pacientes: List[Paciente],
                        flota: Dict[str, TipoCombi], nodo: Nodo, PEN: float):
    """Relajación LP del maestro restringido en el nodo. Devuelve obj, y, duales y uso de artificiales."""
    m = Model("Maestro_LP")
    m.setParam("display/verblevel", 0)
    # Sin presolve, heurísticas ni propagación: si SCIP reduce el problema,
    # los duales de las restricciones originales se pierden o quedan corruptos
    m.setPresolve(SCIP_PARAMSETTING.OFF)
    m.setHeuristics(SCIP_PARAMSETTING.OFF)
    m.disablePropagation()

    y = {idx: m.addVar(vtype="C", lb=0, name=f"y_{idx}") for idx in activos}
    artificiales = []

    obj = quicksum(pool[idx]["rentabilidad"] * y[idx] for idx in activos)

    cons_pac = {}
    for p in pacientes:
        if p.id in nodo.prohibidos:
            continue
        rutas_con_p = [idx for idx in activos if p.id in pool[idx]["pacientes_ids"]]
        expr = quicksum(y[idx] for idx in rutas_con_p)
        if p.id in nodo.requeridos:
            # Variable artificial penalizada: mantiene el LP factible y con duales definidos
            s = m.addVar(vtype="C", lb=0, ub=1, name=f"s_{p.id}")
            artificiales.append(s)
            cons_pac[p.id] = m.addCons(expr + s == 1)
        else:
            cons_pac[p.id] = m.addCons(expr <= 1)

    cons_ub = {}
    cons_lb = {}
    for tipo, info in flota.items():
        rutas_tipo = [idx for idx in activos if pool[idx]["tipo_combi"] == tipo]
        expr = quicksum(y[idx] for idx in rutas_tipo)
        ub = nodo.flota_ub.get(tipo, info.cant_disponible)
        cons_ub[tipo] = m.addCons(expr <= ub)
        lb = nodo.flota_lb.get(tipo, 0)
        if lb > 0:
            s = m.addVar(vtype="C", lb=0, ub=lb, name=f"sf_{tipo}")
            artificiales.append(s)
            cons_lb[tipo] = m.addCons(expr + s >= lb)

    m.setObjective(obj - PEN * quicksum(artificiales), "maximize")
    m.optimize()

    if m.getStatus() != "optimal":
        return None

    yvals = {idx: m.getVal(var) for idx, var in y.items()}

    # En problemas de maximización SCIP devuelve los duales de su problema
    # interno de minimización: hay que negarlos para obtener los duales reales
    dual_pi = {}
    for pid, cons in cons_pac.items():
        try:
            dual_pi[pid] = -m.getDualsolLinear(cons)
        except Exception:
            dual_pi[pid] = 0.0

    dual_mu = {}
    for tipo in flota:
        val = 0.0
        try:
            val += -m.getDualsolLinear(cons_ub[tipo])
        except Exception:
            pass
        if tipo in cons_lb:
            try:
                val += -m.getDualsolLinear(cons_lb[tipo])
            except Exception:
                pass
        dual_mu[tipo] = val

    uso_artificial = sum(m.getVal(s) for s in artificiales) > 1e-6
    return m.getObjVal(), yvals, dual_pi, dual_mu, uso_artificial


def cg_en_nodo(nodo: Nodo, pool: List[dict], existentes: set, pacientes: List[Paciente],
               centro: Paciente, flota: Dict[str, TipoCombi], distancias: dict,
               incomp: set, pac_dict: dict, M: float, PEN: float, deadline: float,
               stats: dict, protegidas: set):
    """Generación de columnas hasta convergencia LP dentro de un nodo del árbol.

    Devuelve (obj, yvals, uso_artificial, convergio) o None si el nodo debe podarse.
    """
    pricing = {tipo: construir_pricing(tipo, info, pacientes, centro, distancias,
                                       incomp, M, nodo)
               for tipo, info in flota.items()}
    ultimo = None
    while True:
        restante = deadline - time.time()
        if restante <= 0:
            if ultimo is None:
                return None
            obj, yvals, art = ultimo
            return obj, yvals, art, False

        activos = [idx for idx, r in enumerate(pool)
                   if not r["eliminada"] and columna_compatible(r, nodo)]
        res = resolver_maestro_lp(pool, activos, pacientes, flota, nodo, PEN)
        if res is None:
            return None
        obj, yvals, dual_pi, dual_mu, art = res
        stats["iter_cg"] += 1
        ultimo = (obj, yvals, art)

        # Eliminación de columnas: K resoluciones consecutivas sin uso
        for idx in activos:
            r = pool[idx]
            if yvals.get(idx, 0.0) > EPS_INT:
                r["sin_uso"] = 0
            else:
                r["sin_uso"] += 1
                if r["sin_uso"] >= K_SIN_USO and idx not in protegidas:
                    r["eliminada"] = True
                    stats["cols_eliminadas"] += 1

        agregadas = 0
        for tipo, info in flota.items():
            mp, x, z = pricing[tipo]
            ok, col, _ = resolver_pricing(
                mp, x, z, tipo, info, pacientes, centro, pac_dict,
                dual_pi, dual_mu.get(tipo, 0.0), min(10.0, max(1.0, restante))
            )
            if ok:
                clave = (tipo, tuple(col["camino"]))
                if clave not in existentes:
                    pool.append(col)
                    existentes.add(clave)
                    stats["cols_generadas"] += 1
                    agregadas += 1
                else:
                    # La columna ya está en el pool: si fue eliminada hay que
                    # revivirla, o la cota LP del nodo quedaría subestimada
                    for r in pool:
                        if (r["eliminada"] and r["tipo_combi"] == tipo
                                and tuple(r["camino"]) == clave[1]):
                            r["eliminada"] = False
                            r["sin_uso"] = 0
                            agregadas += 1
                            break

        if agregadas == 0:
            return obj, yvals, art, True


def elegir_ramificacion(pool: List[dict], yvals: dict, pacientes: List[Paciente],
                        flota: Dict[str, TipoCombi]):
    """Selecciona la decisión de ramificación para una solución LP fraccionaria."""
    # 1) Ryan-Foster: par de pacientes con valor "juntos" fraccionario
    juntos_val = {}
    for idx, v in yvals.items():
        if v <= EPS_INT:
            continue
        ids = sorted(pool[idx]["pacientes_ids"])
        for par in itertools.combinations(ids, 2):
            juntos_val[par] = juntos_val.get(par, 0.0) + v

    mejor_par, mejor_dist = None, None
    for par, val in juntos_val.items():
        if abs(val - round(val)) > EPS_INT:
            d = abs(val - 0.5)
            if mejor_par is None or d < mejor_dist:
                mejor_par, mejor_dist = par, d
    if mejor_par is not None:
        return ("par", mejor_par)

    # 2) Atención fraccionaria de un paciente
    a_val = {p.id: 0.0 for p in pacientes}
    for idx, v in yvals.items():
        for pid in pool[idx]["pacientes_ids"]:
            a_val[pid] += v

    mejor_p, mejor_dist = None, None
    for pid, val in a_val.items():
        if abs(val - round(val)) > EPS_INT:
            d = abs(val - 0.5)
            if mejor_p is None or d < mejor_dist:
                mejor_p, mejor_dist = pid, d
    if mejor_p is not None:
        return ("paciente", mejor_p)

    # 3) Cantidad fraccionaria de vehículos por tipo
    for tipo in flota:
        cnt = sum(v for idx, v in yvals.items() if pool[idx]["tipo_combi"] == tipo)
        if abs(cnt - round(cnt)) > EPS_INT:
            return ("flota", (tipo, cnt))

    return None


def redondear_grupos_identicos(pool: List[dict], yvals: dict):
    """Caso borde: fraccionalidad repartida entre columnas equivalentes
    (mismo conjunto de pacientes y mismo tipo). Elige un representante por grupo."""
    grupos = {}
    for idx, v in yvals.items():
        if v <= EPS_INT:
            continue
        clave = (pool[idx]["tipo_combi"], frozenset(pool[idx]["pacientes_ids"]))
        grupos.setdefault(clave, []).append((idx, v))

    elegidos = []
    for clave, lista in grupos.items():
        total = sum(v for _, v in lista)
        if abs(total - round(total)) > 1e-4:
            return None
        if round(total) >= 1:
            elegidos.append(max(lista, key=lambda t: t[1])[0])
    return elegidos


def resolver_maestro_entero(pool: List[dict], pacientes: List[Paciente],
                            flota: Dict[str, TipoCombi], time_limit: float):
    """Maestro entero sobre el pool actual (heurística de incumbente / warm-start)."""
    activos = [idx for idx, r in enumerate(pool) if not r["eliminada"]]
    if not activos:
        return None, []

    m = Model("Maestro_IP")
    m.setParam("display/verblevel", 0)
    m.setParam("limits/time", max(2.0, time_limit))

    y = {idx: m.addVar(vtype="B", name=f"y_{idx}") for idx in activos}
    m.setObjective(quicksum(pool[idx]["rentabilidad"] * y[idx] for idx in activos),
                   "maximize")

    for p in pacientes:
        rutas_con_p = [idx for idx in activos if p.id in pool[idx]["pacientes_ids"]]
        if rutas_con_p:
            m.addCons(quicksum(y[idx] for idx in rutas_con_p) <= 1)

    for tipo, info in flota.items():
        rutas_tipo = [idx for idx in activos if pool[idx]["tipo_combi"] == tipo]
        if rutas_tipo:
            m.addCons(quicksum(y[idx] for idx in rutas_tipo) <= info.cant_disponible)

    m.optimize()

    if len(m.getSols()) == 0:
        return None, []
    elegidos = [idx for idx in activos if m.getVal(y[idx]) > 0.5]
    return sum(pool[idx]["rentabilidad"] for idx in elegidos), elegidos


def SaludChallenger(instancia: str, threshold: float) -> bool:
    """
    Estrategia 3: Branch & Price con inicialización golosa, eliminación de
    columnas y warm-start del incumbente.
    """
    start_time = time.time()
    deadline = start_time + threshold
    in_path = "./IN"
    out_path = "./OUT_model3"

    print(f"\n{'='*70}")
    print(f"SALUD CHALLENGER - Branch & Price")
    print(f"Instancia: {instancia}, Threshold: {threshold}s")
    print(f"{'='*70}\n")

    try:
        # ===== LEER DATOS =====
        pacientes, centro = leer_pacientes(os.path.join(in_path, f"{instancia}_pacientes.in"))
        flota = leer_flota(os.path.join(in_path, f"{instancia}_flota.in"))
        incomp = leer_incompatibilidades(os.path.join(in_path, f"{instancia}_incompatibilidades.in"))
        distancias = generar_matriz_distancias(pacientes, centro)

        pac_dict = {p.id: p for p in pacientes}
        M = 10000
        PEN = sum(abs(p.beneficio) for p in pacientes) + \
            sum(t.costo_operacion for t in flota.values()) + 1000.0

        stats = {"nodos": 0, "iter_cg": 0, "cols_generadas": 0, "cols_eliminadas": 0}

        # ===== INICIALIZACIÓN EFICIENTE DE COLUMNAS =====
        pool = []
        existentes = set()
        for col in generar_columnas_iniciales(pacientes, centro, flota, distancias, incomp):
            clave = (col["tipo_combi"], tuple(col["camino"]))
            if clave not in existentes:
                pool.append(col)
                existentes.add(clave)
        stats["cols_generadas"] = len(pool)
        print(f"[INIT] Columnas iniciales generadas: {len(pool)}")

        # ===== WARM-START: incumbente inicial con el maestro entero heurístico =====
        # "No operar" siempre es factible: incumbente base Z = 0
        incumbente_val = 0.0
        incumbente_rutas: List[int] = []
        val_ws, rutas_ws = resolver_maestro_entero(pool, pacientes, flota,
                                                   min(5.0, threshold * 0.1))
        if val_ws is not None and val_ws > incumbente_val + EPS_OBJ:
            incumbente_val, incumbente_rutas = val_ws, rutas_ws
        print(f"[WARM-START] Incumbente inicial: {incumbente_val:.2f}")

        # ===== BRANCH & PRICE =====
        reserva_final = min(10.0, max(3.0, 0.15 * threshold))
        heap = [Nodo(prioridad=-math.inf, orden=0)]
        contador = 1
        optimo_probado = False
        sin_tiempo = False
        cota_dual_raiz = None

        while heap:
            if time.time() > deadline - reserva_final:
                sin_tiempo = True
                break
            if stats["nodos"] >= MAX_NODOS:
                break

            nodo = heapq.heappop(heap)
            cota_padre = -nodo.prioridad
            if nodo.profundidad > 0 and cota_padre <= incumbente_val + EPS_OBJ:
                continue  # poda por cota heredada

            stats["nodos"] += 1
            res = cg_en_nodo(nodo, pool, existentes, pacientes, centro, flota,
                             distancias, incomp, pac_dict, M, PEN,
                             deadline - reserva_final, stats, set(incumbente_rutas))
            if res is None:
                continue  # nodo infactible o sin tiempo para arrancar
            obj, yvals, uso_artificial, convergio = res

            if nodo.profundidad == 0 and convergio:
                cota_dual_raiz = obj

            if not convergio:
                sin_tiempo = True
                break
            if uso_artificial:
                continue  # las decisiones de ramificación son infactibles: podar
            if obj <= incumbente_val + EPS_OBJ:
                continue  # poda por cota LP

            fraccionarias = {idx: v for idx, v in yvals.items()
                             if EPS_INT < v < 1 - EPS_INT}
            if not fraccionarias:
                elegidos = [idx for idx, v in yvals.items() if v > 0.5]
                val = sum(pool[idx]["rentabilidad"] for idx in elegidos)
                if val > incumbente_val + EPS_OBJ:
                    incumbente_val, incumbente_rutas = val, elegidos
                    print(f"[B&P] Nuevo incumbente entero: {incumbente_val:.2f} "
                          f"(nodo {stats['nodos']})")
                continue

            decision = elegir_ramificacion(pool, yvals, pacientes, flota)
            if decision is None:
                # Fraccionalidad repartida entre columnas equivalentes: redondear
                elegidos = redondear_grupos_identicos(pool, yvals)
                if elegidos is not None:
                    val = sum(pool[idx]["rentabilidad"] for idx in elegidos)
                    if val > incumbente_val + EPS_OBJ:
                        incumbente_val, incumbente_rutas = val, elegidos
                        print(f"[B&P] Incumbente por redondeo de grupos: {incumbente_val:.2f}")
                continue

            tipo_dec, dato = decision
            if tipo_dec == "par":
                (a, b) = dato
                hijos = [
                    Nodo(prioridad=-obj, orden=contador,
                         juntos=nodo.juntos | {(a, b)}, separados=nodo.separados,
                         requeridos=nodo.requeridos, prohibidos=nodo.prohibidos,
                         flota_lb=dict(nodo.flota_lb), flota_ub=dict(nodo.flota_ub),
                         profundidad=nodo.profundidad + 1),
                    Nodo(prioridad=-obj, orden=contador + 1,
                         juntos=nodo.juntos, separados=nodo.separados | {(a, b)},
                         requeridos=nodo.requeridos, prohibidos=nodo.prohibidos,
                         flota_lb=dict(nodo.flota_lb), flota_ub=dict(nodo.flota_ub),
                         profundidad=nodo.profundidad + 1),
                ]
            elif tipo_dec == "paciente":
                pid = dato
                hijos = [
                    Nodo(prioridad=-obj, orden=contador,
                         juntos=nodo.juntos, separados=nodo.separados,
                         requeridos=nodo.requeridos | {pid}, prohibidos=nodo.prohibidos,
                         flota_lb=dict(nodo.flota_lb), flota_ub=dict(nodo.flota_ub),
                         profundidad=nodo.profundidad + 1),
                    Nodo(prioridad=-obj, orden=contador + 1,
                         juntos=nodo.juntos, separados=nodo.separados,
                         requeridos=nodo.requeridos, prohibidos=nodo.prohibidos | {pid},
                         flota_lb=dict(nodo.flota_lb), flota_ub=dict(nodo.flota_ub),
                         profundidad=nodo.profundidad + 1),
                ]
            else:  # "flota"
                tipo_combi, cnt = dato
                ub_hijo = dict(nodo.flota_ub)
                ub_hijo[tipo_combi] = math.floor(cnt)
                lb_hijo = dict(nodo.flota_lb)
                lb_hijo[tipo_combi] = math.ceil(cnt)
                hijos = [
                    Nodo(prioridad=-obj, orden=contador,
                         juntos=nodo.juntos, separados=nodo.separados,
                         requeridos=nodo.requeridos, prohibidos=nodo.prohibidos,
                         flota_lb=dict(nodo.flota_lb), flota_ub=ub_hijo,
                         profundidad=nodo.profundidad + 1),
                    Nodo(prioridad=-obj, orden=contador + 1,
                         juntos=nodo.juntos, separados=nodo.separados,
                         requeridos=nodo.requeridos, prohibidos=nodo.prohibidos,
                         flota_lb=lb_hijo, flota_ub=dict(nodo.flota_ub),
                         profundidad=nodo.profundidad + 1),
                ]
            contador += 2
            for h in hijos:
                heapq.heappush(heap, h)

        if not heap and not sin_tiempo and stats["nodos"] < MAX_NODOS:
            optimo_probado = True

        # ===== REFUERZO FINAL: maestro entero sobre todo el pool =====
        tiempo_restante = deadline - time.time()
        val_ip, rutas_ip = resolver_maestro_entero(pool, pacientes, flota, tiempo_restante)
        if val_ip is not None and val_ip > incumbente_val + EPS_OBJ:
            incumbente_val, incumbente_rutas = val_ip, rutas_ip

        # ===== RESULTADO =====
        rutas_finales = [(pool[idx]["tipo_combi"], pool[idx]["camino"])
                         for idx in incumbente_rutas]
        atendidos = set()
        for idx in incumbente_rutas:
            atendidos.update(pool[idx]["pacientes_ids"])
        no_atendidos = [p.id for p in pacientes if p.id not in atendidos]

        print(f"\n[STATS] Nodos explorados: {stats['nodos']}")
        if cota_dual_raiz is not None:
            print(f"[STATS] Cota dual (LP raíz): {cota_dual_raiz:.2f}")
        print(f"[STATS] Tiempo total: {time.time() - start_time:.2f}s")
        print(f"[STATS] Iteraciones de CG: {stats['iter_cg']}")
        print(f"[STATS] Columnas generadas: {stats['cols_generadas']}")
        print(f"[STATS] Columnas eliminadas: {stats['cols_eliminadas']}")
        print(f"[STATS] Óptimo probado: {'Sí' if optimo_probado else 'No (límite de tiempo/nodos)'}")
        print(f"[STATS] Pacientes atendidos: {len(atendidos)}")

        print(f"[METRIC] n_vars={stats['cols_generadas']}")
        print(f"[METRIC] n_conss={len(pacientes) + len(flota)}")
        print(f"[METRIC] n_vars_last_master={sum(1 for r in pool if not r.get('eliminada', False))}")
        print(f"[METRIC] dual_bound={cota_dual_raiz if cota_dual_raiz is not None else 'N/A'}")


        for tipo_combi, camino in rutas_finales:
            print(f"Ruta ({tipo_combi}): {camino}")

        salida_contenido = generar_salida(incumbente_val, rutas_finales, no_atendidos)

        os.makedirs(out_path, exist_ok=True)
        archivo_salida = os.path.join(out_path, f"{instancia}.out")
        with open(archivo_salida, 'w') as f:
            f.write(salida_contenido)

        print(f"\n[OK] Output generado exitosamente: {archivo_salida}")
        print(f"[OK] Beneficio Neto Final Obtenido: {incumbente_val:.2f}")
        return True

    except Exception as e:
        print(f"\n[ERROR] Error crítico en la ejecución de la estrategia: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python SaludChallenger.py <instancia> <threshold>")
        sys.exit(1)

    SaludChallenger(sys.argv[1], float(sys.argv[2]))
