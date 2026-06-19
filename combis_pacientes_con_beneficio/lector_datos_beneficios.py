def leer(nombre_archivo):
    pacientes = []
    turnos = {}
    beneficios = {}
    combis = []
    capacidades = {}
    coeficientes = {}
    distancias = {}
    tolerancia = 0
    
    with open(nombre_archivo, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
        
    seccion = ""
    for linea_original in lineas:
        linea = linea_original.strip()
        if not linea: 
            continue
            
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
            
        if linea.startswith("#"):
            continue
            
        linea = linea.split('#')[0].strip()
            
        if seccion == "P":
            # Formato esperado: ID_Paciente, Turno, Beneficio
            partes = linea.split(',')
            id_paciente = int(partes[0].strip())
            pacientes.append(id_paciente)
            turnos[id_paciente] = int(partes[1].strip())
            beneficios[id_paciente] = float(partes[2].strip())
            
        elif seccion == "C":
            # Formato esperado: Nombre_Combi : Capacidad, Coeficiente
            nombre, datos = linea.split(':')
            nombre = nombre.strip()
            cap, coef = datos.split(',')
            combis.append(nombre)
            capacidades[nombre] = int(cap.strip())
            coeficientes[nombre] = float(coef.strip())
            
        elif seccion == "M":
            # Formato esperado: Origen, Destino, Distancia/Costo
            orig, dest, costo = linea.split(',')
            distancias[int(orig.strip()), int(dest.strip())] = float(costo.strip())
            
    return pacientes, turnos, beneficios, tolerancia, combis, capacidades, coeficientes, distancias