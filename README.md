# Maximum Flow Problem Solver

Solver de problemas de flujo máximo en redes dirigidas usando programación lineal con **PySCIPOpt**.

## Descripción

Este proyecto implementa un solver para encontrar el flujo máximo en una red dirigida. Utiliza el enfoque de programación lineal para resolver el problema de manera óptima.

### Problema Abordado

Dado un grafo dirigido con:
- Un nodo origen (source)
- Un nodo destino (sink)
- Aristas dirigidas con capacidades máximas

El objetivo es encontrar el flujo máximo que puede transportarse desde el origen al destino respetando las restricciones de capacidad.

## Requisitos

- Python 3.7+
- PySCIPOpt

### Instalación de dependencias

```bash
pip install pyscipopt
```

## Uso

### Estructura del archivo de entrada

El archivo de entrada debe tener el siguiente formato:

```
<número_de_nodos>
<nombres_nodos>
<nodo_origen>
<nodo_destino>
<número_de_aristas>
<nodo1> <nodo2> <capacidad>
<nodo1> <nodo2> <capacidad>
...
```

### Ejemplo

Archivo `input_file.txt`:
```
4
S A B T
S
T
5
S A 3
S B 2
A B 1
A T 1
B T 3
```

Este ejemplo define una red con 4 nodos (S, A, B, T) donde:
- S es el origen
- T es el destino
- Hay 5 aristas dirigidas con sus respectivas capacidades

### Ejecución

```bash
python main.py input_file.txt
```

### Salida

El programa muestra:
- El estado de la solución (OPTIMAL o FEASIBLE)
- El valor del flujo máximo
- La distribución del flujo por cada canal (arista)

Ejemplo de salida:
```
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
  S_A ---> 2.000000 units
  S_B ---> 2.000000 units
  A_B ---> 1.000000 units
  A_T ---> 1.000000 units
  B_T ---> 3.000000 units
======================================================================
```

## Archivos del Proyecto

- `main.py`: Script principal que contiene toda la lógica del solver
- `input_file.txt`: Archivo de ejemplo con una instancia del problema
- `README.md`: Este archivo

## Funciones Principales

### `read_input(filename)`
Lee y parsea el archivo de entrada validando su formato.

### `create_model(data)`
Crea el modelo de programación lineal con:
- Variables de flujo para cada arista
- Variable de flujo total
- Restricciones de conservación de masa en cada nodo

### `solve_model(model, variables)`
Resuelve el modelo usando SCIP y extrae la solución.

### `print_solution(is_optimal, obj_value, solution)`
Imprime los resultados de forma legible.

## Modelo Matemático

**Variables:**
- $x_{u,v}$: flujo en la arista (u, v)
- $F$: flujo total desde origen a destino

**Función Objetivo:**
$$\text{Maximizar } F$$

**Restricciones:**

1. **Conservación de masa en origen:**
   $$\sum_{(origen, v)} x_{origen,v} - \sum_{(u, origen)} x_{u,origen} = F$$

2. **Conservación de masa en destino:**
   $$\sum_{(u, destino)} x_{u,destino} - \sum_{(destino, v)} x_{destino,v} = F$$

3. **Conservación de masa en nodos intermedios:**
   $$\sum_{(u, nodo)} x_{u,nodo} - \sum_{(nodo, v)} x_{nodo,v} = 0$$

4. **Restricciones de capacidad:**
   $$0 \leq x_{u,v} \leq \text{capacidad}(u,v)$$

## Notas

- El solver utiliza SCIP como optimizador backend
- Las soluciones se redondean a 6 decimales en la salida
- Se ignoran flujos menores a 1e-6 para evitar números muy pequeños

## Autor

Basado en el problema de flujo máximo (Maximum Flow Problem) de teoría de grafos y optimización.