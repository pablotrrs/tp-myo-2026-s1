# Vehicle Routing Problem with Time Windows (VRPTW)

Solver para optimización de rutas de combis de pacientes usando programación lineal con **PySCIPOpt**.

## Descripción

Este proyecto implementa solvers para resolver problemas de ruteo de vehículos, específicamente para optimizar las rutas de combis que transportan pacientes desde un centro de origen hacia sus domicilios y de regreso.

### Problema Abordado

Optimizar el ruteo de un conjunto de combis que debe visitar a pacientes en diferentes ubicaciones, considerando:
- Capacidad máxima de pasajeros por combi
- Ubicación de cada paciente y distancia entre ellos
- Minimización del tiempo total de viaje

Se incluye también una variante con **ventanas de tiempo** donde cada paciente tiene un turno específico en el que debe ser atendido.

## Requisitos

- Python 3.7+
- PySCIPOpt

### Instalación de dependencias

```bash
pip install pyscipopt
```

## Uso

### Modelos Disponibles

#### 1. VRP Básico (`combis_pacientes_modelo.py`)
Resuelve el problema de ruteo sin restricciones de tiempo.

#### 2. VRPTW (`combis_pacientes_modelo_tiempo.py`)
Resuelve el problema de ruteo considerando ventanas de tiempo específicas para cada paciente.

### Estructura del archivo de entrada

Los archivos de entrada siguen este formato:

```
Tolerancia: <valor>

# Pacientes
# id,turno
<id_paciente>,<turno>
<id_paciente>,<turno>
...

# Combis
# nombre:capacidad
<nombre_combi>:<capacidad>
<nombre_combi>:<capacidad>
...

# Matriz de distancias
# origen,destino,distancia
<nodo_origen>,<nodo_destino>,<distancia>
<nodo_origen>,<nodo_destino>,<distancia>
...
```

**Nota:** El nodo `0` representa el centro de origen.

### Ejemplo de Entrada

Archivo `input_combis_pacientes_tiempo.txt`:
```
Tolerancia: 120

# Pacientes
# id,turno
1,1
2,1
3,2
4,2

# Combis
# nombre:capacidad
Combi_A:3
Combi_B:2

# Matriz de distancias
# origen,destino,distancia
0,1,10.5
0,2,12.0
1,3,8.5
1,4,15.0
...
```

### Ejecución

```bash
python combis_pacientes_modelo.py input_combis_pacientes.txt
python combis_pacientes_modelo_tiempo.py input_combis_pacientes_tiempo.txt
```

### Salida Esperada

El programa retorna:
- Estado de la solución (OPTIMAL o FEASIBLE)
- Costo total (tiempo de viaje minimizado)
- Asignación de rutas por cada combi
- Tiempo de llegada a cada paciente

## Archivos del Proyecto

- `combis_pacientes_modelo.py`: Solver para VRP básico
- `combis_pacientes_modelo_tiempo.py`: Solver para VRPTW (con ventanas de tiempo)
- `input_combis_pacientes.txt`: Archivo de ejemplo para modelo básico
- `input_combis_pacientes_tiempo.txt`: Archivo de ejemplo para modelo con tiempo
- `input_file.txt`: Datos adicionales
- `requirements.txt`: Dependencias del proyecto
- `LICENSE`: Licencia del proyecto
- `README.md`: Este archivo

## Modelo Matemático

### Variables de Decisión

- $x_{i,j,k} \in \{0,1\}$: Indica si la combi $k$ viaja de paciente $i$ a paciente $j$
- $u_{i,k} \in [1, N]$: Variable auxiliar para prevenir subtours (restricción MTZ)
- $T_{i,k} \geq 0$: Tiempo en que la combi $k$ llega al paciente $i$

### Función Objetivo

$$\text{Minimizar} \sum_{i,j,k} \text{distancia}_{i,j} \cdot x_{i,j,k}$$

### Restricciones Principales

1. **Visita única por paciente:**
   $$\sum_{i,k} x_{i,j,k} = 1 \quad \forall j \in \text{Pacientes}$$

2. **Conservación de flujo:**
   $$\sum_{i} x_{i,p,k} = \sum_{j} x_{p,j,k} \quad \forall p, k$$

3. **Capacidad de la combi:**
   $$\text{Pasajeros asignados a } k \leq \text{capacidad}_k$$

4. **Eliminación de subtours (restricción MTZ):**
   $$u_{i,k} - u_{j,k} + N \cdot x_{i,j,k} \leq N - 1$$

## Notas

- El optimizador utiliza SCIP como backend
- La tolerancia temporal permite cierta flexibilidad en las ventanas de tiempo
- El nodo 0 siempre representa el centro de origen y destino final
- Ambas combis deben retornar al centro después de completar sus rutas