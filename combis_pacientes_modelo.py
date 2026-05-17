from pyscipopt import Model, quicksum

def leer_datos_vrp(nombre_archivo):
    """
    Lee archivo de entrada para VRP con ventanas temporales.
    
    Retorna:
    - pacientes: lista de IDs de pacientes
    - combis: lista de nombres de combis
    - capacidades: dict con capacidad de cada combi
    - tiempos_cita: dict con tiempo de cita de cada paciente
    - tolerancia: tiempo de tolerancia (en minutos)
    - distancias: dict con distancias entre nodos
    """
    pacientes = []
    combis = []
    capacidades = {}
    tiempos_cita = {}
    distancias = {}
    tolerancia = 0
    
    with open(nombre_archivo, 'r') as f:
        lineas = f.readlines()
        
    seccion = ""
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            if "Tolerancia" in linea:
                seccion = "T"
            elif "Pacientes" in linea:
                seccion = "P"
            elif "Combis" in linea:
                seccion = "C"
            elif "Matriz" in linea:
                seccion = "M"
            continue
            
        if seccion == "T":
            tolerancia = int(linea)
        elif seccion == "P":
            partes = [p.strip() for p in linea.split(',')]
            paciente_id = int(partes[0])
            tiempo = int(partes[1])
            pacientes.append(paciente_id)
            tiempos_cita[paciente_id] = tiempo
        elif seccion == "C":
            nombre, cap = linea.split(':')
            combis.append(nombre.strip())
            capacidades[nombre.strip()] = int(cap)
        elif seccion == "M":
            partes = [p.strip() for p in linea.split(',')]
            orig, dest, costo = int(partes[0]), int(partes[1]), float(partes[2])
            distancias[orig, dest] = costo
            
    return pacientes, combis, capacidades, tiempos_cita, tolerancia, distancias


def resolver_vrp_ventanas(pacientes, combis, capacidades, tiempos_cita, tolerancia, distancias):
    """
    Resuelve VRP con ventanas de tiempo.
    
    Variables:
    - x[i,j,k]: flujo binario (1 si arco i->j usado en combi k)
    - arrivo[i,k]: tiempo de arrivo al paciente i con combi k
    
    Restricciones:
    1. Cada paciente visitado exactamente una vez
    2. Capacidad de combis
    3. Flujo (conservación)
    4. Ventana temporal: t_i - τ ≤ arrivo[i,k] ≤ t_i
    5. Continuidad temporal
    6. MTZ (subtour elimination)
    """
    model = Model("VRP_Ventanas_Temporales")
    nodos = [0] + pacientes  # 0 es el Centro
    N = len(pacientes)
    
    # Variables de ruteo
    x = {}
    for i in nodos:
        for j in nodos:
            if i != j:
                for k in combis:
                    x[i, j, k] = model.addVar(vtype="B", name=f"x_{i}_{j}_{k}")
    
    # Variables de tiempo (continuas)
    arrivo = {}
    for i in pacientes:
        for k in combis:
            # Tiempo de arrivo al paciente i con combi k
            arrivo[i, k] = model.addVar(vtype="C", lb=0, ub=10000, name=f"arrivo_{i}_{k}")
    
    # Variable de tiempo en centro para cada combi (partida)
    partida = {}
    for k in combis:
        partida[k] = model.addVar(vtype="C", lb=0, ub=10000, name=f"partida_{k}")
    
    # Variables MTZ para evitar subtours
    u = {}
    for i in pacientes:
        for k in combis:
            u[i, k] = model.addVar(vtype="C", lb=1, ub=N, name=f"u_{i}_{k}")
    
    # ===== FUNCIÓN OBJETIVO =====
    model.setObjective(
        quicksum(distancias[i, j] * x[i, j, k] 
                 for i in nodos for j in nodos if (i,j) in distancias for k in combis),
        "minimize"
    )
    
    # ===== RESTRICCIONES =====
    
    # Restricción 1: Cada paciente visitado exactamente una vez
    for j in pacientes:
        model.addCons(
            quicksum(x[i, j, k] for i in nodos if i != j for k in combis) == 1,
            name=f"visit_once_{j}"
        )
    
    # Restricción 2: Capacidad de combis
    for k in combis:
        model.addCons(
            quicksum(x[i, j, k] for i in nodos for j in pacientes if i != j) <= capacidades[k],
            name=f"capacity_{k}"
        )
    
    # Restricción 3: Flujo (conservación)
    for k in combis:
        for p in pacientes:
            model.addCons(
                quicksum(x[i, p, k] for i in nodos if i != p) == 
                quicksum(x[p, j, k] for j in nodos if j != p),
                name=f"flow_{p}_{k}"
            )
    
    # Restricción 4: Salida y regreso al Centro
    for k in combis:
        model.addCons(
            quicksum(x[0, j, k] for j in pacientes) == 
            quicksum(x[i, 0, k] for i in pacientes),
            name=f"return_center_{k}"
        )
    
    # Restricción 5: Ventanas temporales [t_i - τ, t_i]
    for i in pacientes:
        for k in combis:
            t_i = tiempos_cita[i]
            lower_bound = t_i - tolerancia
            
            # Si paciente i es visitado por combi k
            # arrivo[i,k] debe estar en [t_i - τ, t_i]
            # Usamos big-M: si no se visita, arrivo no tiene restricción
            M = 10000
            
            # arrivo[i,k] >= (t_i - τ) - M*(1 - sum(arcos hacia i))
            model.addCons(
                arrivo[i, k] >= lower_bound - M * (1 - quicksum(x[j, i, k] for j in nodos if j != i)),
                name=f"time_lower_{i}_{k}"
            )
            
            # arrivo[i,k] <= t_i + M*(1 - sum(arcos hacia i))
            model.addCons(
                arrivo[i, k] <= t_i + M * (1 - quicksum(x[j, i, k] for j in nodos if j != i)),
                name=f"time_upper_{i}_{k}"
            )
    
    # Restricción 6: Continuidad temporal
    for k in combis:
        for i in nodos:
            for j in pacientes:
                if i != j and (i, j) in distancias:
                    if i == 0:
                        # Desde centro: tiempo_llegada[j] >= partida[k] + distancia[0,j]
                        model.addCons(
                            arrivo[j, k] >= partida[k] + distancias[i, j] - 10000 * (1 - x[i, j, k]),
                            name=f"temporal_{i}_{j}_{k}"
                        )
                    else:
                        # Entre pacientes: tiempo_llegada[j] >= tiempo_llegada[i] + distancia[i,j]
                        model.addCons(
                            arrivo[j, k] >= arrivo[i, k] + distancias[i, j] - 10000 * (1 - x[i, j, k]),
                            name=f"temporal_{i}_{j}_{k}"
                        )
    
    # Restricción 7: MTZ (eliminación de subtours)
    for k in combis:
        for i in pacientes:
            for j in pacientes:
                if i != j and (i, j) in distancias:
                    model.addCons(
                        u[i, k] - u[j, k] + N * x[i, j, k] <= N - 1,
                        name=f"mtz_{i}_{j}_{k}"
                    )
    
    # ===== OPTIMIZACIÓN =====
    model.optimize()
    
    # ===== IMPRESIÓN DE RESULTADOS =====
    if model.getStatus() == "optimal":
        print(f"\n{'='*70}")
        print(f"SOLUCIÓN ÓPTIMA ENCONTRADA")
        print(f"{'='*70}")
        print(f"Costo total de transporte: {model.getObjVal():.2f} unidades")
        print(f"{'='*70}\n")
        
        for k in combis:
            print(f"Ruta de {k}:")
            ruta_actual = 0  # Centro
            tiempo_actual = 0
            pacientes_recogidos = []
            costo_ruta = 0
            visited_edges = set()
            max_iterations = len(nodos) + 2
            iterations = 0
            
            # Construir la ruta
            while ruta_actual != 0 or not pacientes_recogidos:
                iterations += 1
                if iterations > max_iterations:
                    print(f"  WARNING: Route reconstruction exceeded max iterations")
                    break
                
                found_next = False
                for j in nodos:
                    if j != ruta_actual and model.getVal(x[ruta_actual, j, k]) > 0.5:
                        edge = (ruta_actual, j)
                        if edge in visited_edges:
                            continue
                        visited_edges.add(edge)
                        found_next = True
                        costo_ruta += distancias.get((ruta_actual, j), 0)
                        
                        if j == 0:
                            print(f"  → Retorno al Centro")
                        else:
                            tiempo_arr = model.getVal(arrivo[j, k])
                            ventana_inf = tiempos_cita[j] - tolerancia
                            ventana_sup = tiempos_cita[j]
                            pacientes_recogidos.append(j)
                            print(f"  → Paciente {j}: arrivo={tiempo_arr:.1f}min, ventana=[{ventana_inf}, {ventana_sup}]")
                        
                        ruta_actual = j
                        break
                
                if not found_next:
                    if ruta_actual != 0:
                        print(f"  WARNING: Route ended prematurely at node {ruta_actual}")
                    break
            
            if pacientes_recogidos:
                print(f"  Pacientes: {pacientes_recogidos}, Costo parcial: {costo_ruta:.2f}")
            print()
    else:
        print(f"No se encontró solución óptima. Estado: {model.getStatus()}")


# --- EJECUCIÓN ---
if __name__ == "__main__":
    p, c, caps, t_citas, tau, dists = leer_datos_vrp("input_combis_pacientes.txt")
    resolver_vrp_ventanas(p, c, caps, t_citas, tau, dists)
