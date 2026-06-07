# Maximum Flow Problem Solver

Solver para problemas de flujo máximo en redes dirigidas usando programación lineal con **PySCIPOpt**.

## Tabla de Contenidos

1. [Aspectos Técnicos](#aspectos-técnicos)
2. [Modelos Matemáticos](#modelos-matemáticos)

---

## Aspectos Técnicos

### Descripción

Este proyecto implementa un solver eficiente para resolver problemas de flujo máximo en redes dirigidas y problemas de ruteo de vehículos. El solver soporta múltiples configuraciones:
- **Flujo máximo clásico**: Una fuente y un destino
- **Múltiples fuentes y destinos**: Generalización que convierte el problema a su forma clásica
- **Variante de centros y pacientes (VRP)**: Modelo especializado para problemas de distribución con restricciones de capacidad
- **VRPTW (VRP con Ventanas de Tiempo)**: Extensión anterior que agrega restricciones temporales
- **VRP con Categorías Incompatibles**: Extensión que incorpora restricciones de compatibilidad entre categorías de pacientes

### Requisitos

- Python 3.7+
- PySCIPOpt 6.0+

### Instalación de Dependencias

```bash
pip install pyscipopt
```

### Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `main.py` | Script principal que contiene toda la lógica del solver |
| `input_file.txt` | Archivo de ejemplo para el modelo básico (una fuente, un destino) |
| `multi_st.txt` | Archivo de ejemplo para múltiples fuentes y destinos |
| `input_combis_pacientes.txt` | Archivo de ejemplo para modelo VRP básico |
| `input_combis_pacientes_tiempo.txt` | Archivo de ejemplo para modelo VRPTW |
| `input_combis_pacientes_categorias.txt` | Archivo de ejemplo para modelo VRP con categorías |
| `combis_pacientes_modelo.py` | Solver para VRP (ruteo de pacientes) |
| `combis_pacientes_modelo_tiempo.py` | Solver para VRPTW (ruteo con ventanas de tiempo) |
| `combis_pacientes_modelo_categorias.py` | Solver para VRP con restricciones de categorías incompatibles |
| `input_categorias_incompatibles.txt` | Pares de categorías incompatibles para el modelo con categorías |
| `test_vrp_categorias.py` | Suite de tests (18 tests) para validar el modelo con categorías |
| `requirements.txt` | Dependencias del proyecto |
| `README.md` | Este archivo |
| `main.tex` | Documento LaTeX con todas las formulaciones matemáticas |

### Estructura del Archivo de Entrada

#### Formato General

```
<número_de_nodos>
<nombres_nodos>
<nodo(s)_origen>
<nodo(s)_destino>
<número_de_aristas>
<nodo1> <nodo2> <capacidad>
<nodo1> <nodo2> <capacidad>
...
```

**Notas:**
- Los nombres de nodos no pueden ser `__SRC__` ni `__SNK__` (reservados internamente)
- Las fuentes y destinos pueden ser múltiples (separados por espacios)
- Las aristas son dirigidas: cada arista va de `nodo1` a `nodo2`

#### Ejemplo: Flujo Máximo Clásico (`input_file.txt`)

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

Este ejemplo define una red con:
- 4 nodos: S (origen), A, B, T (destino)
- 5 aristas dirigidas con sus capacidades máximas

#### Ejemplo: Múltiples Fuentes y Destinos (`multi_st.txt`)

```
5
S1 S2 M T1 T2
S1 S2
T1 T2
4
S1 M 5
S2 M 5
M T1 3
M T2 3
```

Este ejemplo define:
- 2 nodos origen (S1, S2) y 2 nodos destino (T1, T2)
- El nodo M actúa como punto de distribución intermedio

### Ejecución

```bash
# Flujo máximo clásico
python main.py input_file.txt

# Múltiples fuentes y destinos
python main.py multi_st.txt

# Modelos de ruteo de pacientes
python combis_pacientes_modelo.py input_combis_pacientes.txt
python combis_pacientes_modelo_tiempo.py input_combis_pacientes_tiempo.txt

# Modelo VRP con restricciones de categorías incompatibles
python combis_pacientes_modelo_categorias.py

# Tests para modelo con categorías
python -m unittest test_vrp_categorias -v
```

### Salida del Programa

El programa muestra:
- **Estado de la solución**: OPTIMAL o FEASIBLE
- **Valor del flujo máximo**: Valor total en unidades
- **Distribución del flujo**: Flujo por cada arista de la red

Ejemplo:
```
Status: OPTIMAL
Maximum Flow Value: 6.0 units

Flow distribution by channels:
  S1_M ---> 5.000000 units
  S2_M ---> 1.000000 units
  M_T1 ---> 3.000000 units
  M_T2 ---> 3.000000 units
```

---

## Modelos Matemáticos

### a) Modelo de Maximización (Una Fuente, Un Destino)

#### Descripción del Problema

Dado un grafo dirigido con un nodo origen (source), un nodo destino (sink) y aristas dirigidas con capacidades máximas, encontrar el flujo máximo que puede transportarse desde el origen al destino respetando las restricciones de capacidad.

#### Variables de Decisión

- $x_{u,v} \geq 0$: Flujo en la arista dirigida $(u, v)$, restringido a $0 \leq x_{u,v} \leq \text{cap}(u,v)$
- $F \geq 0$: Flujo total desde origen a destino

#### Función Objetivo

$$\text{Maximizar} \quad F$$

#### Restricciones

1. **Conservación de flujo en origen:**
   $$\sum_{(s, v)} x_{s,v} = F$$

2. **Conservación de flujo en destino:**
   $$\sum_{(u, t)} x_{u,t} = F$$

3. **Conservación de flujo en nodos intermedios:**
   $$\sum_{(u, i)} x_{u,i} = \sum_{(i, v)} x_{i,v} \quad \forall i \notin \{s, t\}$$

4. **Restricciones de capacidad:**
   $$0 \leq x_{u,v} \leq \text{cap}(u,v) \quad \forall (u,v) \in E$$

---

### b) Modelo de Múltiples Fuentes y Destinos

#### Descripción del Problema

Generalización del problema anterior donde existen múltiples nodos origen ($S = \{s_1, s_2, \ldots, s_k\}$) y múltiples nodos destino ($T = \{t_1, t_2, \ldots, t_m\}$). El objetivo es maximizar el flujo total desde cualquier origen a cualquier destino.

#### Reducción a Forma Clásica

Este problema se resuelve mediante la introducción de:
- **Super-source** $\sigma$: conectado a todas las fuentes con capacidad infinita
- **Super-sink** $\tau$: conectado desde todos los destinos con capacidad infinita

#### Variables de Decisión

- $x_{u,v}$: Flujo en cada arista (incluyendo aristas del super-source y super-sink)
- $F$: Flujo total que emerge de la super-source

#### Función Objetivo

$$\text{Maximizar} \quad F$$

#### Restricciones Extendidas

1. **Balance en super-source:**
   $$\sum_{s \in S} x_{\sigma,s} = F$$

2. **Balance en super-sink:**
   $$\sum_{t \in T} x_{t,\tau} = F$$

3. **Conservación en todos los nodos intermedios:**
   $$\sum_{(u, v)} x_{u,v} = \sum_{(v, w)} x_{v,w} \quad \forall v \in V$$

4. **Capacidades originales en aristas de red:**
   $$x_{u,v} \leq \text{cap}(u,v) \quad \forall (u,v) \in E$$

#### Ejemplo Resuelto

Para `multi_st.txt`:
- Super-source conecta a S1 y S2
- Super-sink recibe desde T1 y T2
- Flujo máximo = 6 unidades: min(cap(s1→m) + cap(s2→m), cap(m→t1) + cap(m→t2)) = min(10, 6) = 6

---

### c) Modelo de Centros y Pacientes (VRP)

#### Descripción del Problema

Optimizar el ruteo de un conjunto de vehículos (combis) para visitar a pacientes, minimizando el costo total (tiempo o distancia), sujeto a restricciones de capacidad y opcionalmente ventanas de tiempo.

#### Variables de Decisión

- $x_{i,j,k} \in \{0,1\}$: Indica si la combi $k$ viaja de nodo $i$ a nodo $j$
- $u_{i,k} \in [1, n]$: Variable auxiliar MTZ (Miller-Tucker-Zemlin) para prevenir subtours
- $T_{i,k} \geq 0$: Hora de llegada de la combi $k$ al nodo $i$ (solo en VRPTW)

#### Función Objetivo

$$\text{Minimizar} \quad \sum_{i,j,k} d_{i,j} \cdot x_{i,j,k}$$

donde $d_{i,j}$ es la distancia o tiempo entre nodos.

#### Restricciones

1. **Cada paciente es visitado exactamente una vez:**
   $$\sum_{i,k} x_{i,j,k} = 1 \quad \forall j \in \text{Pacientes}$$

2. **Conservación de flujo (continuidad de rutas):**
   $$\sum_{i} x_{i,p,k} = \sum_{j} x_{p,j,k} \quad \forall p, k$$

3. **Restricción de capacidad:**
   $$\sum_{j=1}^{n} x_{i,j,k} \leq \text{capacidad}_k \quad \forall k$$

4. **Eliminación de subtours (MTZ):**
   $$u_{i,k} - u_{j,k} + n \cdot x_{i,j,k} \leq n - 1 \quad \forall i,j,k$$

5. **Ventanas de tiempo (VRPTW):**
   $$\text{inicio}_i \leq T_{i,k} \leq \text{fin}_i \quad \forall i,k$$
   $$T_{j,k} \geq T_{i,k} + d_{i,j} - M(1 - x_{i,j,k}) \quad \forall i,j,k$$

---

### d) Modelo de Ruteo de Vehículos con Restricciones de Categorías

#### Descripción del Problema

Extensión del modelo VRPTW donde cada paciente pertenece a exactamente una categoría. Existe un conjunto de pares de categorías incompatibles, lo que significa que una misma combi no puede transportar pacientes de ambas categorías simultáneamente. El problema incluye dos tipos de incompatibilidad:

- **Incompatibilidad no reflexiva** $(c_1, c_2)$ con $c_1 \ne c_2$: Dos categorías distintas que no pueden estar juntas en la misma combi
- **Incompatibilidad reflexiva** $(c, c)$: Una categoría que puede tener máximo 1 paciente por combi

#### Variables de Decisión

- $x_{i,j,k} \in \{0,1\}$: Indica si la combi $k$ viaja del nodo $i$ al nodo $j$
- $z_{i,k} \in \{0,1\}$: Indica si la combi $k$ atiende al paciente $i$ (define $z_{i,k} = \sum_{j \ne i} x_{j,i,k}$)
- $T_{i,k} \geq 0$: Hora de llegada de la combi $k$ al nodo $i$
- $y_{c,k} \in \{0,1\}$: Indica si la combi $k$ atiende a algún paciente de la categoría $c$

#### Función Objetivo

$$\text{Minimizar} \quad \sum_{i,j,k} d_{i,j} \cdot x_{i,j,k}$$

#### Restricciones Principales

1. **Visita única:** Cada paciente es visitado exactamente una vez
2. **Conservación de flujo:** Continuidad de rutas
3. **Capacidad:** Límite de pacientes por combi
4. **Subtours:** Eliminación usando MTZ
5. **Definición de atención:** $z_{i,k} = \sum_{j \ne i} x_{j,i,k}$
6. **Tiempo de propagación:** Relación temporal entre viajes consecutivos
7. **Ventanas de tiempo:** Restricciones sobre llegada a cada paciente
8. **Definición de categoría:** $y_{c,k} \geq \sum_{i: \text{cat}_i = c} z_{i,k}$
9. **Incompatibilidad no reflexiva:** Para $(c_1, c_2)$ con $c_1 \ne c_2$:
   $$y_{c_1,k} + y_{c_2,k} \leq 1 \quad \forall k$$
10. **Incompatibilidad reflexiva:** Para $(c, c)$:
    $$\sum_{i: \text{cat}_i = c} z_{i,k} \leq 1 \quad \forall k$$

#### Ejemplo y Validación

Para el conjunto de datos de ejemplo:
- **5 pacientes** en 3 categorías: PAMI (2), Contagiosos (1), Mentales (2)
- **3 combis** con capacidades: 2, 3, 2
- **3 incompatibilidades**: Contagiosos↔Mentales, Contagiosos↔PAMI, Contagiosos↔Contagiosos (reflexiva)

**Resultado óptimo:** 163 minutos de distancia total

**Validación de restricciones:**
- Combi_A: PAMI + Mentales ✓ (compatible)
- Combi_B: Contagiosos (único) ✓ (reflexiva respetada)
- Combi_C: PAMI + Mentales ✓ (compatible)
- Todos los turnos respetados ✓
- Máximo 1 Contagioso por combi ✓

---



- El optimizador utiliza **SCIP** (Solving Constraint Integer Programs) como backend
- Las soluciones se redondean a 6 decimales para legibilidad
- Se ignoran flujos menores a 1e-6 (considerados cero numérico)
- Para el problema de múltiples fuentes/destinos, la capacidad de super-source/super-sink se establece como la suma de capacidades salientes totales (Big-M)
- El tiempo de ejecución es generalmente muy rápido (< 1 segundo) para instancias pequeñas y medianas