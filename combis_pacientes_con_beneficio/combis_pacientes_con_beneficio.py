from pyscipopt import Model, quicksum

def resolver(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias):
    model = Model("Orienteering_VRPTW_UNGS")
    nodos = [0] + pacientes # 0 es el Centro
    N = len(pacientes)
    M = 10000 # Constante Big-M (Horizonte temporal)
    
    # --- VARIABLES ---
    x = combi_k_viaja_de_i_a_j(combis, distancias, model, nodos)
    z = paciente_p_recogido_por_combi_k(pacientes, combis, model)
    w = combi_k_es_elegida(combis, model)
    u = eliminacion_subtours(pacientes, model, N)
    T = inicializar_tiempos(nodos, combis, model)

    # --- FUNCIÓN OBJETIVO --- 
    maximizar_beneficio_combi_pacientes(pacientes, beneficios, combis, coeficientes, model, z, w)

    # --- RESTRICCIONES ESTRUCTURALES ---
    solo_una_combi(combis, model, w)

    for k in combis:
        combi_sale_una_vez(pacientes, distancias, model, x, w, k)
        combi_llega_a_centro(pacientes, distancias, model, x, w, k)
        combis_no_elegidas_tienen_capacidad_0(pacientes, capacidades, model, z, w, k)
        conservacion_flujo(distancias, model, nodos, x, z, k, pacientes)

    cada_paciente_es_recogido_por_a_lo_sumo_una_combi(pacientes, combis, model, z)
    no_debe_haber_subtours(pacientes, combis, distancias, model, N, x, u)

    # --- RESTRICCIONES TEMPORALES ---
    propagacion_del_tiempo(nodos, combis, distancias, model, M, x, T)
    respetar_ventanas_de_tiempo(pacientes, combis, turnos, tolerancia, model, M, z, T)

    # --- EJECUCIÓN ---
    ejecutar_modelo(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias, model, nodos, x, z, w, T)




# ==========================================
# MÉTODOS DE VARIABLES
# ==========================================

def combi_k_viaja_de_i_a_j(combis, distancias, model, nodos):
    x = {}
    for i in nodos:
        for j in nodos:
            if i != j and (i,j) in distancias:
                for k in combis:
                    x[i, j, k] = model.addVar(vtype="B", name=f"x_{i}_{j}_{k}")
    return x

def paciente_p_recogido_por_combi_k(pacientes, combis, model):
    z = {}
    for p in pacientes:
        for k in combis:
            z[p, k] = model.addVar(vtype="B", name=f"z_{p}_{k}")
    return z

def combi_k_es_elegida(combis, model):
    w = {}
    for k in combis:
        w[k] = model.addVar(vtype="B", name=f"w_{k}")
    return w

def eliminacion_subtours(pacientes, model, N):
    u = {}
    for i in pacientes:
        u[i] = model.addVar(vtype="C", lb=1, ub=N, name=f"u_{i}")
    return u

def inicializar_tiempos(nodos, combis, model):
    T = {}
    for i in nodos:
        for k in combis:
            T[i, k] = model.addVar(vtype="C", lb=0, name=f"T_{i}_{k}")
    return T


# ==========================================
# MÉTODOS DE RESTRICCIONES Y F.O.
# ==========================================

def maximizar_beneficio_combi_pacientes(pacientes, beneficios, combis, coeficientes, model, z, w):
    model.setObjective(
        quicksum(beneficios[p] * z[p, k] for p in pacientes for k in combis) +
        quicksum(coeficientes[k] * w[k] for k in combis),
        "maximize"
    )

def solo_una_combi(combis, model, w):
    model.addCons(quicksum(w[k] for k in combis) == 1, name="Una_Sola_Combi")

def combi_sale_una_vez(pacientes, distancias, model, x, w, k):
    model.addCons(quicksum(x[0, j, k] for j in pacientes if (0,j) in distancias) == w[k], name=f"Salida_Centro_{k}")

def combi_llega_a_centro(pacientes, distancias, model, x, w, k):
    model.addCons(quicksum(x[i, 0, k] for i in pacientes if (i,0) in distancias) == w[k], name=f"Regreso_Centro_{k}")

def combis_no_elegidas_tienen_capacidad_0(pacientes, capacidades, model, z, w, k):
    model.addCons(quicksum(z[p, k] for p in pacientes) <= capacidades[k] * w[k], name=f"Capacidad_{k}")

def conservacion_flujo(distancias, model, nodos, x, z, k, pacientes):
    for p in pacientes:
        model.addCons(quicksum(x[i, p, k] for i in nodos if i != p and (i,p) in distancias) == z[p, k], name=f"Entrada_{p}_{k}")
        model.addCons(quicksum(x[p, j, k] for j in nodos if j != p and (p,j) in distancias) == z[p, k], name=f"Salida_{p}_{k}")

def cada_paciente_es_recogido_por_a_lo_sumo_una_combi(pacientes, combis, model, z):
    for p in pacientes:
        model.addCons(quicksum(z[p, k] for k in combis) <= 1, name=f"Visita_Unica_{p}")

def no_debe_haber_subtours(pacientes, combis, distancias, model, N, x, u):
    for k in combis:
        for i in pacientes:
            for j in pacientes:
                if i != j and (i,j) in distancias:
                    model.addCons(u[i] - u[j] + N * x[i, j, k] <= N - 1, name=f"MTZ_{i}_{j}_{k}")

def propagacion_del_tiempo(nodos, combis, distancias, model, M, x, T):
    for k in combis:
        for i in nodos:
            for j in nodos:
                if i != j and (i,j) in distancias and j != 0:
                    model.addCons(T[j, k] >= T[i, k] + distancias[i, j] - M * (1 - x[i, j, k]), name=f"Prop_Tiempo_{i}_{j}_{k}")

def respetar_ventanas_de_tiempo(pacientes, combis, turnos, tolerancia, model, M, z, T):
    for k in combis:
        for p in pacientes:
            # Utilizamos z[p,k] directamente en lugar de sumar las entradas de x
            model.addCons(T[p, k] >= (turnos[p] - tolerancia) * z[p, k], name=f"Ventana_Min_{p}_{k}")
            model.addCons(T[p, k] <= turnos[p] * z[p, k] + M * (1 - z[p, k]), name=f"Ventana_Max_{p}_{k}")


# ==========================================
# MÉTODOS DE EJECUCIÓN Y OUTPUT
# ==========================================

def ejecutar_modelo(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias, model, nodos, x, z, w, T):
    model.optimize()
    
    if model.getStatus() == "optimal":
        imprimir_solucion_optima(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias, model, nodos, x, z, w, T)
    else:
        imprimir_aviso_no_hay_solucion()

def imprimir_solucion_optima(pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias, model, nodos, x, z, w, T):
    print(f"\n¡SOLUCIÓN ÓPTIMA ENCONTRADA!")
    beneficio_pacientes = sum(beneficios[p] for p in pacientes for k in combis if model.getVal(z[p, k]) > 0.5)
    combi_elegida = next(k for k in combis if model.getVal(w[k]) > 0.5)
    beneficio_combi = coeficientes[combi_elegida]
        
    print(f"Beneficio Total (Pacientes + Combi): {beneficio_pacientes + beneficio_combi}")
    print(f"Combi seleccionada: {combi_elegida} (Coeficiente: {beneficio_combi})")
        
    rutas = [(i, j) for i in nodos for j in nodos if i != j and (i,j) in distancias and model.getVal(x[i, j, combi_elegida]) > 0.5]
        
    print("\n--- RUTA Y CRONOGRAMA ---")
    for i, j in rutas:
        if j != 0:
            print(f"  Viaje: Nodo {i} -> Nodo {j} (Recoge paciente con Beneficio: {beneficios[j]})")
        else:
            print(f"  Viaje: Nodo {i} -> Nodo {j} (Regreso al Centro)")
            
    # Ordenamos y mostramos los tiempos
    tiempos = [(p, model.getVal(T[p, combi_elegida])) for p in pacientes if model.getVal(z[p, combi_elegida]) > 0.5]
    tiempos.sort(key=lambda item: item[1])
    
    print("\n--- DETALLE DE TIEMPOS ---")
    for p, t in tiempos:
        print(f"  Paciente {p}: Recogido a los {t:.1f} min (Turno: {turnos[p]}, Ventana: {turnos[p]-tolerancia} a {turnos[p]})")
            
    print(f"\nPacientes recogidos: {[p for p in pacientes if model.getVal(z[p, combi_elegida]) > 0.5]}")
    print(f"Capacidad utilizada: {sum(1 for p in pacientes if model.getVal(z[p, combi_elegida]) > 0.5)} / {capacidades[combi_elegida]}")

def imprimir_aviso_no_hay_solucion():
    print("No se encontró solución factible. Es posible que las ventanas de tiempo sean demasiado estrictas para alcanzar a los pacientes.")