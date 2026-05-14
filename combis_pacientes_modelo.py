from pyscipopt import Model, quicksum

def leer_datos_vrp(nombre_archivo):
    pacientes = []
    combis = []
    capacidades = {}
    distancias = {}
    
    # Lectura del archivo siguiendo tu lineamiento anterior
    with open(nombre_archivo, 'r') as f:
        lineas = f.readlines()
        
    seccion = ""
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            if "Pacientes" in linea: seccion = "P"
            elif "Combis" in linea: seccion = "C"
            elif "Matriz" in linea: seccion = "M"
            continue
            
        if seccion == "P":
            pacientes = [int(p.strip()) for p in linea.split(',')]
        elif seccion == "C":
            nombre, cap = linea.split(':')
            combis.append(nombre)
            capacidades[nombre] = int(cap)
        elif seccion == "M":
            orig, dest, costo = linea.split(',')
            distancias[int(orig), int(dest)] = float(costo)
            
    return pacientes, combis, capacidades, distancias

def resolver_vrp(pacientes, combis, capacidades, distancias):
    model = Model("VRP_UNGS")
    nodos = [0] + pacientes # 0 es el Centro
    N = len(pacientes)
    
    # Variables: x[i,j,k] binaria
    x = {}
    for i in nodos:
        for j in nodos:
            if i != j:
                for k in combis:
                    x[i, j, k] = model.addVar(vtype="B", name=f"x_{i}_{j}_{k}")

    # Variables MTZ para evitar subtours
    u = {}
    for i in pacientes:
        for k in combis:
            u[i, k] = model.addVar(vtype="C", lb=1, ub=N, name=f"u_{i}_{k}")

    # Función Objetivo: Minimizar costo total
    model.setObjective(
        quicksum(distancias[i, j] * x[i, j, k] 
                 for i in nodos for j in nodos if (i,j) in distancias for k in combis),
        "minimize"
    )

    # Restricción 1: Cada paciente se visita una vez
    for j in pacientes:
        model.addCons(quicksum(x[i, j, k] for i in nodos if i != j for k in combis) == 1)

    # Restricción 2: Flujo (Entra = Sale)
    for k in combis:
        for p in pacientes:
            model.addCons(
                quicksum(x[i, p, k] for i in nodos if i != p) == 
                quicksum(x[p, j, k] for j in nodos if j != p)
            )

    # Restricción 3: Salida/Regreso al Centro
    for k in combis:
        model.addCons(quicksum(x[0, j, k] for j in pacientes) <= 1)
        model.addCons(
            quicksum(x[0, j, k] for j in pacientes) == 
            quicksum(x[i, 0, k] for i in pacientes)
        )

    # Restricción 4: Capacidad (d_i = 1)
    for k in combis:
        model.addCons(
            quicksum(x[i, j, k] for i in pacientes for j in nodos if i != j) <= capacidades[k]
        )

    # Restricción 5: MTZ Subtour Elimination
    for k in combis:
        for i in pacientes:
            for j in pacientes:
                if i != j:
                    # Si existe el arco entre i y j, forzar orden
                    if (i,j) in distancias:
                        model.addCons(u[i, k] - u[j, k] + N * x[i, j, k] <= N - 1)

    model.optimize()
    
    if model.getStatus() == "optimal":
        print(f"\nSOLUCIÓN ENCONTRADA - Costo: {model.getObjVal()}")
        for k in combis:
            print(f"Ruta {k}:")
            for i in nodos:
                for j in nodos:
                    if i != j and model.getVal(x[i, j, k]) > 0.5:
                        print(f"  {i} -> {j}")
    else:
        print("No se encontró solución óptima.")

# --- EJECUCIÓN ---
p, c, caps, dists = leer_datos_vrp("input_combis_pacientes.txt")
resolver_vrp(p, c, caps, dists)
