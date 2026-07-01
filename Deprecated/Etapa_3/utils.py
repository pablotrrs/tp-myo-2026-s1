"""
Funciones auxiliares para el algoritmo de generación de columnas.
"""

import os

def directorio(ruta_relativa="."):
    """Obtiene la ruta del directorio del script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta_relativa)

def leer_datos_vrp(nombre_archivo):
    """
    Lee los datos del problema VRP desde un archivo.
    
    Formato esperado:
    - Tolerancia: XX
    - Pacientes: ID, Turno, (opcionales: Beneficio, Categoría)
    - Combis: Nombre : Capacidad
    - Matriz: Origen, Destino, Distancia
    
    Returns:
        Tupla (pacientes, turnos, combis, capacidades, distancias)
    """
    pacientes = []
    turnos = {}
    combis = []
    capacidades = {}
    distancias = {}
    tolerancia = 0
    
    try:
        with open(nombre_archivo, 'r') as f:
            lineas = f.readlines()
    except FileNotFoundError:
        print(f"Error: Archivo {nombre_archivo} no encontrado.")
        return None, None, None, None, None
    
    seccion = ""
    for linea_original in lineas:
        linea = linea_original.strip()
        if not linea:
            continue
        
        # Detectar configuraciones y secciones
        if "Tolerancia:" in linea:
            tolerancia = int(linea.split(':')[1].strip())
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
        
        # Ignorar comentarios
        if linea.startswith("#"):
            continue
        
        # Limpiar posibles comentarios al final de la línea
        linea = linea.split('#')[0].strip()
        if not linea:
            continue
        
        # Leer datos según la sección activa
        try:
            if seccion == "P":
                partes = [p.strip() for p in linea.split(',')]
                id_paciente = int(partes[0])
                pacientes.append(id_paciente)
                turnos[id_paciente] = int(partes[1])
            elif seccion == "C":
                nombre, cap = linea.split(':')
                combis.append(nombre.strip())
                capacidades[nombre.strip()] = int(cap.strip())
            elif seccion == "M":
                orig, dest, costo = linea.split(',')
                distancias[int(orig.strip()), int(dest.strip())] = float(costo.strip())
        except (ValueError, IndexError) as e:
            print(f"Error al procesar línea: {linea} - {e}")
            continue
    
    return pacientes, turnos, tolerancia, combis, capacidades, distancias

def imprimir_rutas(rutas, titulo="Rutas"):
    """Imprime un conjunto de rutas."""
    print(f"\n{'='*70}")
    print(f"{titulo}")
    print(f"{'='*70}")
    for ruta in rutas:
        print(f"  {ruta}")
    print(f"{'='*70}\n")

def imprimir_solucion_maestro(uso_rutas, rutas, pacientes_visitados, distancia_total):
    """Imprime la solución del problema maestro."""
    print(f"\n{'='*70}")
    print(f"SOLUCIÓN DEL PROBLEMA MAESTRO")
    print(f"{'='*70}")
    print(f"Distancia total: {distancia_total:.2f}")
    print(f"Pacientes cubiertos: {len(pacientes_visitados)} / {len(rutas[0].pacientes) if rutas else 0}")
    print(f"\nRutas seleccionadas:")
    for idx, ruta in enumerate(rutas):
        if uso_rutas.get(ruta.id_ruta, 0) > 0.5:
            print(f"  Ruta {ruta.id_ruta}: {ruta}")
    print(f"{'='*70}\n")

def guardar_resultados(iteracion, duales, mejor_costo_reducido, nueva_ruta):
    """Guarda información de cada iteración."""
    print(f"\nIteración {iteracion}:")
    print(f"  Duales del problema maestro: {duales}")
    print(f"  Mejor costo reducido encontrado: {mejor_costo_reducido:.4f}")
    if nueva_ruta:
        print(f"  Nueva ruta generada: {nueva_ruta}")
    else:
        print(f"  No se generó nueva ruta (criterio de parada alcanzado)")
