# Solver Modular de Programación Lineal

Solver unificado para problemas de **Flujo Máximo** y **Enrutamiento de Vehículos con Ventanas de Tiempo (VRP-TW)** usando programación lineal con **PySCIPOpt**.

## Descripción General

Este proyecto implementa solvers para dos problemas clásicos de optimización:

1. **Maximum Flow (Flujo Máximo)**: Encuentra el flujo máximo en redes dirigidas con múltiples orígenes y destinos
2. **VRP with Time Windows (Enrutamiento con Ventanas de Tiempo)**: Asigna pacientes a vehículos respetando capacidades y ventanas de tiempo

Ambos utilizan el enfoque de programación lineal entera mixta (MIP) para garantizar soluciones óptimas.

## Requisitos

- Python 3.7+
- PySCIPOpt >= 6.0

### Instalación de dependencias

```bash
pip install -r requirements.txt
```

O instalar directamente:

```bash
pip install pyscipopt networkx matplotlib
```

## Archivos del Proyecto

```
├── main.py                      # Solver unificado (máximo flujo + VRP-TW)
├── combis_pacientes_modelo.py   # Módulo VRP-TW (invocado desde main.py)
├── graph_visualizer.py          # Visualizador de grafos
├── input_combis_pacientes.txt   # Ejemplo 1: VRP-TW (4 pacientes)
├── input_combis_pacientes_2.txt # Ejemplo 2: VRP-TW (6 pacientes)
├── input_file.txt               # Ejemplo: Maximum Flow (alternativo)
├── requirements.txt             # Dependencias
└── README.md                    # Este archivo
```

---

# Problema 1: Maximum Flow (Flujo Máximo)

## Descripción

Dado un grafo dirigido con:
- Múltiples nodos origen (sources) y destino (sinks)
- Aristas dirigidas con capacidades máximas
- Nodo **centro** como punto de distribución

El objetivo es encontrar el flujo máximo total que puede transportarse desde todos los orígenes hacia todos los destinos respetando capacidades.

### Formulación Matemática

**Variables:**
- $x_{u,v}$: flujo en la arista (u, v)
- $F$: flujo total desde fuentes a sumideros

**Función Objetivo:**
$$\text{Maximizar } F$$

**Restricciones:**

1. **Conservación de masa en super-source:**
   $$\sum_{(S^*, v)} x_{S^*,v} = F$$

2. **Conservación de masa en super-sink:**
   $$\sum_{(u, T^*)} x_{u,T^*} = F$$

3. **Conservación en nodos intermedios:**
   $$\sum_{(u, nodo)} x_{u,nodo} = \sum_{(nodo, v)} x_{nodo,v}$$

4. **Capacidades:**
   $$0 \leq x_{u,v} \leq \text{cap}(u,v)$$

## Formato de Entrada

```
<número_de_nodos>
<nombres_nodos>
<número_de_orígenes>
<nodo_origen_1> <nodo_origen_2> ...
<número_de_destinos>
<nodo_destino_1> <nodo_destino_2> ...
<número_de_aristas>
<origen> <destino> <capacidad>
...
```

### Ejemplo: `multi_st.txt`

```
5
S1 S2 M T1 T2
2
S1 S2
2
T1 T2
4
S1 M 10
S2 M 8
M T1 12
M T2 9
```

## Uso

```bash
python main.py maxflow input_file.txt
```

## Salida Esperada

```
======================================================================
MAXIMUM FLOW SOLUTION
======================================================================
Status: OPTIMAL
Maximum Flow Value: 17.0 units

Flow by edge:
  S1 → M: 10.0
  S2 → M: 8.0
  M → T1: 12.0
  M → T2: 9.0

Total: 17.0 units
======================================================================
```

---

# Problema 2: Vehicle Routing Problem with Time Windows (VRP-TW)

## Descripción

Se debe asignar **n pacientes** a **k vehículos** para recoger/entregar servicios, minimizando el costo de transporte total, respetando:

- **Capacidades** de vehículos
- **Ventanas de tiempo** para cada paciente [t_i - τ, t_i]
- **Salida y retorno** desde centro de atención (depósito)

El costo del tiempo de espera es CERO; solo se penaliza la distancia viajada.

### Formulación Matemática

**Variables:**
- $x_{i,j,k} \in \{0,1\}$: si vehículo k viaja de nodo i a nodo j
- $arrival_{i,k}$: tiempo de arribo del vehículo k al paciente i
- $departure_k$: hora de salida del vehículo k desde el depósito
- $u_{i,k}$: variables MTZ para eliminación de subtours

**Función Objetivo:**
$$\text{Minimizar } \sum_{i,j,k} d_{i,j} \cdot x_{i,j,k}$$

**Restricciones Principales:**

1. **Cobertura de pacientes:**
   $$\sum_{k} \sum_{i} x_{i,j,k} = 1 \quad \forall j \in \text{pacientes}$$

2. **Capacidad:**
   $$\sum_{j \in \text{pacientes}} x_{i,j,k} \leq \text{cap}_k \quad \forall k, i$$

3. **Conservación de flujo:**
   $$\sum_{i} x_{i,j,k} = \sum_{l} x_{j,l,k} \quad \forall j,k$$

4. **Ventanas de tiempo:**
   $$t_i - \tau \leq arrival_{i,k} \leq t_i \quad \forall i,k$$

5. **Continuidad temporal:**
   $$arrival_{i,k} + t_{i,j} \leq arrival_{j,k} + M(1 - x_{i,j,k})$$

6. **Eliminación de subtours (MTZ):**
   $$u_{i,k} - u_{j,k} + n \cdot x_{i,j,k} \leq n-1$$

## Formato de Entrada

```
# Tolerancia temporal global (minutos)
<tolerancia_tau>

# Pacientes: id, tiempo_cita
<id_paciente> , <tiempo_cita>
...

# Vehículos: Nombre:Capacidad
<nombre_vehiculo>:<capacidad>
...

# Matriz de distancias: origen, destino, costo
<nodo_origen> , <nodo_destino> , <costo>
...
```

### Ejemplo 1: `input_combis_pacientes.txt` (4 pacientes)

```
30

1, 60
2, 90
3, 120
4, 150

Combi_A:2
Combi_B:3

0, 1, 10
0, 2, 15
0, 3, 20
0, 4, 25
1, 2, 5
1, 3, 25
1, 4, 30
2, 3, 10
2, 4, 20
3, 4, 5
```

**Interpretación:**
- Tolerancia: 30 min → Paciente 1 (cita 60) tiene ventana [30, 60]
- 2 combis: Combi_A (cap. 2), Combi_B (cap. 3)
- Matriz simétrica: viaje centro↔P1 cuesta 10 min

### Ejemplo 2: `input_combis_pacientes_2.txt` (6 pacientes)

Similar pero con 6 pacientes y 3 vehículos.

## Uso

```bash
python main.py vrptw input_combis_pacientes.txt
```

## Salida Esperada

```
======================================================================
VRP WITH TIME WINDOWS SOLUTION
======================================================================
Status: OPTIMAL
Total Transport Cost: 75.00 units

Route for Combi_A:
  → Patient 1: arrival=30.0min, window=[30, 60]
  → Return to Depot
  Patients visited: [1], Route cost: 20.00

Route for Combi_B:
  → Patient 2: arrival=60.0min, window=[60, 90]
  → Patient 3: arrival=90.0min, window=[90, 120]
  → Patient 4: arrival=120.0min, window=[120, 150]
  → Return to Depot
  Patients visited: [2, 3, 4], Route cost: 55.00

======================================================================
```

---

## Herramienta: Visualizador de Grafos

### Descripción

Script para generar visualizaciones en red de instancias de VRP-TW, mostrando:
- Nodos (centro y pacientes con ventanas de tiempo)
- Aristas dirigidas con costos
- Posicionamiento basado en distancias

### Uso

```bash
# Generar grafo con nombre por defecto
python graph_visualizer.py input_combis_pacientes.txt

# Generar grafo con nombre personalizado
python graph_visualizer.py input_combis_pacientes_2.txt mi_grafo.png
```

**Salida:** Imagen PNG con el grafo visualizado (ej: `grafo_pacientes.png`)

---

## Funciones Principales

### `main.py`

#### Maximum Flow (funciones propias)

- `read_input(filename)`: Parsea input de máximo flujo
- `create_model(data)`: Construye modelo MIP
- `solve_model(model, variables)`: Resuelve modelo
- `print_solution(is_optimal, obj_value, solution)`: Imprime solución
- `main_maxflow(input_file)`: Orquesta resolución de máximo flujo

#### VRP-TW (delegado a combis_pacientes_modelo.py)

- `main_vrptw(input_file)`: Orquesta resolución de VRP-TW
  - Invoca: `leer_datos_vrp()` y `resolver_vrp_ventanas()` desde combis_pacientes_modelo.py

### `combis_pacientes_modelo.py`

- `leer_datos_vrp(nombre_archivo)`: Parsea input VRP-TW
- `resolver_vrp_ventanas(...)`: Crea modelo y resuelve VRP-TW

### `graph_visualizer.py`

- `parse_input_file(filename)`: Extrae datos del archivo de entrada
- `create_graph_visualization(input_file, output_file)`: Genera visualización

---

## Ejemplos de Ejecución

### 1. Máximo Flujo

```bash
$ python main.py maxflow input_file.txt

Reading input from: input_file.txt
Network: 4 nodes, 5 edges
Source: S, Sink: T

Creating optimization model...
Solving model...

======================================================================
MAXIMUM FLOW SOLUTION
======================================================================
Status: OPTIMAL
Maximum Flow Value: 4.0 units

Flow distribution by channels:
  A_B ---> 1.000000 units
  A_T ---> 1.000000 units
  B_T ---> 3.000000 units
  S_A ---> 2.000000 units
  S_B ---> 2.000000 units
======================================================================
```

### 2. VRP con Ventanas de Tiempo

```bash
$ python main.py vrptw input_combis_pacientes.txt

Loading: input_combis_pacientes.txt
Patients: [1, 2, 3, 4]
Vehicles: ['Combi_A', 'Combi_B']
Tolerance (minutes): 30

[SCIP solver output...]

Status: OPTIMAL
Total Transport Cost: 75.00 units
...
```

### 3. Visualización de Grafo

```bash
$ python graph_visualizer.py input_combis_pacientes_2.txt

✓ Grafo generado exitosamente: grafo_pacientes.png
  - Nodos: 7 (1 centro + 6 pacientes)
  - Aristas: 21
  - Tolerancia temporal: 45 minutos
```

---

## Notas Técnicas

- **Solver Backend:** SCIP (via PySCIPOpt)
- **Tipos de Variables:** Binary (B), Continuous (C), Integer (I)
- **Big-M Parameter:** M = 10000 para restricciones de ventanas de tiempo
- **MTZ Variables:** Utilizadas para eliminación eficiente de subtours
- **Precision:** Soluciones redondeadas a 6 decimales

## Puntos Importantes

### Para VRP-TW

1. **Tiempos de espera:** NO tienen costo (solo distancia se minimiza)
2. **Ventanas rígidas:** Un vehículo NO puede llegar después del límite superior
3. **Salida desde depósito:** Todos los vehículos salen en t=0
4. **Tolerancia:** Parámetro global τ que define ventanas como [t_i - τ, t_i]

### Para Maximum Flow

1. **Super-nodes:** S* y T* técnica para multi-source/sink
2. **Simetría:** Aristas bidireccionales automáticamente equilibradas
3. **Flujo conservativo:** Ley de Kirchhoff garantizada en todo nodo