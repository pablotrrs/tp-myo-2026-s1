from pyscipopt import Model, quicksum

def leer_datos_vrp(nombre_archivo):
    pacientes = []
    turnos = {}
    combis = []
    capacidades = {}
    distancias = {}
    tolerancia = 0
    
    with open(nombre_archivo, 'r') as f:
        lineas = f.readlines()
        
    seccion = ""
    for linea_original in lineas:
        linea = linea_original.strip()
        if not linea: 
            continue
            
        # 1. Detectar configuraciones y secciones ANTES de ignorar los '#'
        if "Tolerancia:" in linea:
            tolerancia = int(linea.split(':')[1])
            continue
        if "Pacientes" in linea: 
            seccion = "P"
            continue
        if "Combis" in linea: 
            seccion = "C"
            continue
        if "Matriz" in linea: 
            seccion = "M"
            continue
            
        # 2. Si la línea empieza con '#', es un comentario puro, lo saltamos
        if linea.startswith("#"):
            continue
            
        # 3. Limpiar posibles comentarios al final de los datos útiles
        linea = linea.split('#')[0].strip()
            
        # 4. Leer los datos según la sección activa
        if seccion == "P":
            partes = linea.split(',')
            id_paciente = int(partes[0].strip())
            pacientes.append(id_paciente)
            turnos[id_paciente] = int(partes[1].strip())
        elif seccion == "C":
            nombre, cap = linea.split(':')
            combis.append(nombre)
            capacidades[nombre] = int(cap)
        elif seccion == "M":
            orig, dest, costo = linea.split(',')
            distancias[int(orig), int(dest)] = float(costo)
            
    return pacientes, turnos, tolerancia, combis, capacidades, distancias

def resolver_vrp_con_tiempo(pacientes, turnos, tolerancia, combis, capacidades, distancias):
    model = Model("VRPTW_UNGS")
    nodos = [0] + pacientes # 0 es el Centro
    M = 10000 # Constante Big-M (Horizonte temporal máximo)
    
    # --- VARIABLES ---
    # x[i,j,k] = 1 si la combi k viaja de i a j
    x = {}
    for i in nodos:
        for j in nodos:
            if i != j and (i,j) in distancias:
                for k in combis:
                    x[i, j, k] = model.addVar(vtype="B", name=f"x_{i}_{j}_{k}")

    # T[i,k] = Tiempo en el que la combi k INICIA el servicio en el nodo i
    T = {}
    for i in nodos:
        for k in combis:
            T[i, k] = model.addVar(vtype="C", lb=0, name=f"T_{i}_{k}")

    # --- FUNCIÓN OBJETIVO ---
    # El costo sigue siendo estrictamente el tiempo de viaje en tránsito
    model.setObjective(
        quicksum(distancias[i, j] * x[i, j, k] 
                 for i in nodos for j in nodos if (i,j) in distancias for k in combis),
        "minimize"
    )

    # --- RESTRICCIONES ESTRUCTURALES ---
    # 1. Visita única
    for j in pacientes:
        model.addCons(quicksum(x[i, j, k] for i in nodos if i != j and (i,j) in distancias for k in combis) == 1)

    # 2. Conservación de flujo
    for k in combis:
        for p in pacientes:
            model.addCons(
                quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias) == 
                quicksum(x[p, j, k] for j in nodos if j != p and (p,j) in distancias)
            )

    # 3. Salida y Regreso al Centro
    for k in combis:
        model.addCons(quicksum(x[0, j, k] for j in pacientes if (0,j) in distancias) <= 1)
        model.addCons(
            quicksum(x[0, j, k] for j in pacientes if (0,j) in distancias) == 
            quicksum(x[i, 0, k] for i in pacientes if (i,0) in distancias)
        )

    # 4. Capacidad de las Combis
    for k in combis:
        model.addCons(
            quicksum(x[i, j, k] for i in pacientes for j in nodos if i != j and (i,j) in distancias) <= capacidades[k]
        )

    # --- RESTRICCIONES TEMPORALES (NUEVAS) ---
    
    # 5. Propagación del Tiempo (Corregida: Sin viajar al pasado)
    for k in combis:
        for i in nodos:
            for j in nodos:
                # Si viajamos de i a j, y j NO ES el centro de atención (0)
                if i != j and (i,j) in distancias and j != 0:
                    model.addCons(T[j, k] >= T[i, k] + distancias[i, j] - M * (1 - x[i, j, k]), 
                                  name=f"Propagacion_{i}_{j}_{k}")

    # 6. Ventanas de Tiempo de los Pacientes
    for k in combis:
        for p in pacientes:
            # Variable auxiliar que vale 1 si la combi k atiende al paciente p
            y_pk = quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias)
            
            # El tiempo de recogida no puede ser menor a (Turno - Tolerancia)
            model.addCons(T[p, k] >= (turnos[p] - tolerancia) * y_pk)
            
            # El tiempo de recogida no puede exceder la hora del Turno
            # (El término M * (1 - y_pk) desactiva la restricción si la combi k no va a p)
            model.addCons(T[p, k] <= turnos[p] * y_pk + M * (1 - y_pk))

    # --- EJECUCIÓN ---
    model.optimize()
    
    if model.getStatus() == "optimal":
        print(f"\nSOLUCIÓN ÓPTIMA ENCONTRADA")
        print(f"Costo Total de Tránsito: {model.getObjVal()} minutos")
        for k in combis:
            rutas = [(i, j) for i in nodos for j in nodos if i != j and (i,j) in distancias and model.getVal(x[i, j, k]) > 0.5]
            if rutas:
                print(f"\n--- {k} ---")
                for i, j in rutas:
                    print(f"  Viaje: Nodo {i} -> Nodo {j} (Costo tramo: {distancias[i,j]})")
                print("  Cronograma de atención:")
                # Ordenar los nodos visitados por tiempo para imprimirlos cronológicamente
                tiempos = [(n, model.getVal(T[n, k])) for n in nodos if sum(model.getVal(x[i, n, k]) for i in nodos if i != n and (i,n) in distancias) > 0.5]
                tiempos.sort(key=lambda item: item[1])
                for n, t in tiempos:
                    if n != 0:
                        print(f"    Paciente {n}: Recogido a los {t:.1f} minutos (Turno: {turnos[n]}, Ventana: {turnos[n]-tolerancia} a {turnos[n]})")
    else:
        print("\nNo se encontró solución factible. Es matemáticamente imposible cumplir con las ventanas de tiempo dadas las capacidades y distancias.")

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    p, t, tol, c, caps, dists = leer_datos_vrp("input_combis_pacientes_tiempo.txt")
    resolver_vrp_con_tiempo(p, t, tol, c, caps, dists)