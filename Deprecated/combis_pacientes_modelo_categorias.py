from pyscipopt import Model, quicksum

def leer_datos_vrp_categorias(archivo_pacientes, archivo_incompatibles):
    pacientes = []
    turnos = {}
    categorias_pacientes = {}
    combis = []
    capacidades = {}
    distancias = {}
    tolerancia = 0
    incompatibles = []
    
    # Leer archivo de pacientes con categorías
    with open(archivo_pacientes, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
        
    seccion = ""
    for linea_original in lineas:
        linea = linea_original.strip()
        if not linea: 
            continue
            
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
            
        if linea.startswith("#"):
            continue
            
        linea = linea.split('#')[0].strip()
            
        if seccion == "P":
            partes = linea.split(',')
            id_paciente = int(partes[0].strip())
            pacientes.append(id_paciente)
            turnos[id_paciente] = int(partes[1].strip())
            categorias_pacientes[id_paciente] = partes[2].strip()
        elif seccion == "C":
            nombre, cap = linea.split(':')
            combis.append(nombre)
            capacidades[nombre] = int(cap)
        elif seccion == "M":
            orig, dest, costo = linea.split(',')
            distancias[int(orig), int(dest)] = float(costo)
    
    # Leer archivo de categorías incompatibles
    with open(archivo_incompatibles, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
    
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        cat1, cat2 = linea.split(',')
        incompatibles.append((cat1.strip(), cat2.strip()))
            
    return pacientes, turnos, categorias_pacientes, tolerancia, combis, capacidades, distancias, incompatibles

def resolver_vrp_con_categorias(pacientes, turnos, categorias_pacientes, tolerancia, combis, capacidades, distancias, incompatibles):
    model = Model("VRPTW_Categorias_UNGS")
    nodos = [0] + pacientes
    M = 10000
    
    # Obtener todas las categorías únicas
    categorias = set(categorias_pacientes.values())
    
    # Crear diccionario de pacientes por categoría
    pacientes_por_categoria = {}
    for cat in categorias:
        pacientes_por_categoria[cat] = [p for p in pacientes if categorias_pacientes[p] == cat]
    
    # --- VARIABLES ---
    x = {}
    for i in nodos:
        for j in nodos:
            if i != j and (i,j) in distancias:
                for k in combis:
                    x[i, j, k] = model.addVar(vtype="B", name=f"x_{i}_{j}_{k}")

    T = {}
    for i in nodos:
        for k in combis:
            T[i, k] = model.addVar(vtype="C", lb=0, name=f"T_{i}_{k}")
    
    # Variable y[c,k] = 1 si la combi k atiende a algún paciente de la categoría c
    y = {}
    for c in categorias:
        for k in combis:
            y[c, k] = model.addVar(vtype="B", name=f"y_{c}_{k}")

    # --- FUNCIÓN OBJETIVO ---
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

    # --- RESTRICCIONES TEMPORALES ---
    
    # 5. Propagación del Tiempo
    for k in combis:
        for i in nodos:
            for j in nodos:
                if i != j and (i,j) in distancias and j != 0:
                    model.addCons(T[j, k] >= T[i, k] + distancias[i, j] - M * (1 - x[i, j, k]))

    # 6. Ventanas de Tiempo de los Pacientes
    for k in combis:
        for p in pacientes:
            z_pk = quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias)
            model.addCons(T[p, k] >= (turnos[p] - tolerancia) * z_pk)
            model.addCons(T[p, k] <= turnos[p] * z_pk + M * (1 - z_pk))

    # --- RESTRICCIONES DE CATEGORÍAS ---
    
    # 7. Definir y[c,k]: si la combi k atiende algún paciente de categoría c
    for c in categorias:
        for k in combis:
            for p in pacientes_por_categoria[c]:
                z_pk = quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias)
                # Si la combi k atiende al paciente p, entonces debe tener la categoría c
                model.addCons(y[c, k] >= z_pk)

    # 8. Restricción de categorías incompatibles (reflexivas y no reflexivas)
    for cat1, cat2 in incompatibles:
        for k in combis:
            if cat1 == cat2:
                # Incompatibilidad reflexiva: máximo 1 paciente de esa categoría por combi
                suma_pacientes = quicksum(
                    quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias)
                    for p in pacientes_por_categoria.get(cat1, [])
                )
                model.addCons(suma_pacientes <= 1)
            else:
                # Incompatibilidad entre categorías distintas: no pueden estar ambas
                model.addCons(y[cat1, k] + y[cat2, k] <= 1)

    # --- EJECUCIÓN ---
    model.optimize()
    
    if model.getStatus() == "optimal":
        print(f"\nSOLUCIÓN ÓPTIMA ENCONTRADA")
        print(f"Costo Total de Tránsito: {model.getObjVal()} minutos")
        print(f"\nCategorías: {', '.join(sorted(categorias))}")
        print(f"Pares Incompatibles: {incompatibles}\n")
        
        for k in combis:
            rutas = [(i, j) for i in nodos for j in nodos if i != j and (i,j) in distancias and model.getVal(x[i, j, k]) > 0.5]
            if rutas:
                print(f"\n--- {k} ---")
                categorias_en_combi = [c for c in categorias if model.getVal(y[c, k]) > 0.5]
                print(f"Categorías transportadas: {categorias_en_combi}")
                for i, j in rutas:
                    print(f"  Viaje: Nodo {i} -> Nodo {j} (Costo tramo: {distancias[i,j]})")
                print("  Cronograma de atención:")
                tiempos = [(n, model.getVal(T[n, k])) for n in nodos if sum(model.getVal(x[i, n, k]) for i in nodos if i != n and (i,n) in distancias) > 0.5]
                tiempos.sort(key=lambda item: item[1])
                for n, t in tiempos:
                    if n != 0:
                        cat = categorias_pacientes[n]
                        print(f"    Paciente {n} (Categoría: {cat}): Recogido a los {t:.1f} minutos (Turno: {turnos[n]}, Ventana: {turnos[n]-tolerancia} a {turnos[n]})")
    else:
        print("\nNo se encontró solución factible.")
        print("Posibles razones:")
        print("- Incompatibilidad de categorías imposible de resolver")
        print("- Ventanas de tiempo incompatibles con capacidades")
        print("- Distancias insuficientes para cumplir plazos")

if __name__ == "__main__":
    p, t, cat, tol, c, caps, dists, incomp = leer_datos_vrp_categorias(
        "input_combis_pacientes_categorias.txt",
        "input_categorias_incompatibles.txt"
    )
    resolver_vrp_con_categorias(p, t, cat, tol, c, caps, dists, incomp)
