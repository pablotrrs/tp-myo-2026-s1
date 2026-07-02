# Estrategia 1: Salud - Modelo Compacto MILP

## Descripción General

Implementa la **primera estrategia** del trabajo práctico: resolver el problema de logística médica mediante un **modelo compacto de Programación Lineal Entera Mixta (MILP)** usando PySCIPOpt.

## Archivos Principales

### `Salud.py`
Implementación del modelo MILP compacto.

**Función principal:**
```python
def Salud(instancia: str, threshold: float) -> bool
```

Parámetros:
- `instancia`: nombre de la instancia sin extensión (ej: "test1")
- `threshold`: tiempo máximo de ejecución en segundos

Rutas estándar:
- **Entrada**: `./IN/{instancia}_*.in`
- **Salida**: `./OUT_model1/{instancia}.out`

Retorna: `True` si se completó exitosamente, `False` en caso contrario

### `SaludTest.py`
Función de validación que verifica si una solución es operativamente factible.

**Función principal:**
```python
def SaludTest(instancia: str, output_file: str = None, in_path: str = "./IN") -> bool
```

Parámetros:
- `instancia`: nombre de la instancia
- `output_file`: ruta al archivo `.out` (default: `./OUT_model1/{instancia}.out`)
- `in_path`: ruta a carpeta con archivos de entrada (default: `./IN`)

**Validaciones (SIN programación lineal):**
1. ✓ Comienza y termina en centro (nodo 0)
2. ✓ Respeta capacidad de cada combi
3. ✓ Respeta ventanas de tiempo [ih_inicio, ih_fin]
4. ✓ Distancias y tiempos calculados correctamente
5. ✓ Sin categorías médicas incompatibles
6. ✓ Beneficio neto calculado correctamente

Retorna: `True` si la solución es válida, `False` en caso contrario

### `utils_salud.py`
Utilidades compartidas para todas las estrategias.

**Clases:**
- `Paciente`: id, x, y, ih_inicio, ih_fin, categoria, beneficio
- `TipoCombi`: nombre, cant_disponible, cant_asientos, costo_operacion

**Funciones de parseo:**
- `leer_pacientes(archivo)` → (pacientes[], centro)
- `leer_flota(archivo)` → {tipo_combi: TipoCombi}
- `leer_incompatibilidades(archivo)` → set de pares incompatibles
- `distancia_euclidea(p1, p2)` → float
- `generar_salida(beneficio, rutas, no_atendidos)` → string con formato requerido

## Formato de Entrada

Tres archivos de texto por instancia (ej: "test1"):

### `test1_pacientes.in`
```
# id,x,y,ih_inicio,ih_fin,categoria,beneficio
0,40.0,50.0
1,25.0,85.0,100,300,Inmunodeprimido,180
2,22.0,75.0,100,300,Sanitario,210
```

Nota: `id=0` es el centro médico (sin ventanas de tiempo ni beneficio)

### `test1_flota.in`
```
# tipo_combi,cant_disponible,cant_asientos,costo_operacion
Combi_Chica,5,12,150
Combi_Mediana,2,20,250
```

### `test1_incompatibilidades.in`
```
# categoria1,categoria2
Inmunodeprimido,Infeccioso
Infeccioso,Pediatrico
```

Líneas vacías se ignoran automáticamente.

## Formato de Salida

Archivo de texto: `./OUT_model1/{instancia}.out`

```
Z = 540.0
Combi_Chica: [0 -> 1 -> 3 -> 0]
Combi_Mediana: [0 -> 2 -> 0]
No_Atendidos: 4, 5
```

Formato exacto:
- Línea 1: `Z = {valor_beneficio_neto}`
- Líneas 2+: `{tipo_combi}: [{ruta_ordenada}]`
- Última línea: `No_Atendidos: {lista_o_vacío}`

## Uso

### Resolver una instancia
```bash
python Salud/Salud.py <instancia> <threshold>

# Ejemplo: 30 segundos de timeout
python Salud/Salud.py test1 30
```

### Validar una solución
```bash
python Salud/SaludTest.py <instancia> [output_file] [in_path]

# Ejemplo: validar con rutas estándar
python Salud/SaludTest.py test1

# Ejemplo: validar con ruta explícita
python Salud/SaludTest.py test1 ./OUT_model1/test1.out ./IN
```

### Resolver y validar
```bash
python validate_salud.py <instancia> <threshold>

# Ejemplo: ejecuta Salud() + SaludTest()
python validate_salud.py test1 30
```

### Desde código Python
```python
from Salud.Salud import Salud
from Salud.SaludTest import SaludTest

# Resolver
Salud("test1", 30.0)

# Validar
SaludTest("test1")
```

## Modelo Matemático

### Conjuntos
- `P`: conjunto de pacientes (sin incluir centro)
- `K`: conjunto de combis (instancias individuales)
- `T`: tipos de combis
- `V = {0} ∪ P`: nodos (centro + pacientes)

### Variables de Decisión
- `x[i,j,k]` ∈ {0,1}: arista de i a j con combi k
- `z[p,k]` ∈ {0,1}: paciente p atendido por combi k
- `a[p]` ∈ {0,1}: paciente p es atendido (por cualquier combi)
- `u[k]` ∈ {0,1}: combi k utilizada
- `T[i,k]` ≥ 0: tiempo de llegada al nodo i con combi k

### Función Objetivo
```
max: Σ(beneficio[p] × a[p]) - Σ(costo[tipo(k)] × u[k])
```

### Restricciones Principales
1. **Cobertura**: Cada paciente atendido por máximo una combi
2. **Flujo**: Balance de entrada/salida en nodos
3. **Centro**: Salida y regreso obligatorios en centro
4. **Capacidad**: Respeto de asientos por combi
5. **Ventanas de tiempo**: Respeto de intervalos horarios
6. **Incompatibilidades**: Categorías incompatibles no comparten combi

## Test Instances

Incluidas en `./IN/`:

| Instancia | Pacientes | Combis | Incomp. | Beneficio | Validación |
|-----------|-----------|--------|---------|-----------|-----------|
| test1     | 3         | 2      | 0       | 390.0     | ✓ Válida  |
| test2     | 5         | 3      | 2       | 640.0     | ✓ Válida  |
| test3     | 7         | 3      | 3       | 1110.0    | ✓ Válida  |

## Notas Técnicas

- **Solver**: PySCIPOpt (SCIP)
- **Timeout seguro**: `model.setParam("limits/time", threshold)`
- **Big-M**: 10000 (para ventanas de tiempo)
- **Distancia**: Euclidea desde coordenadas
- **Velocidad**: 1 unidad de distancia por unidad de tiempo
- **Múltiples combis**: Cada instancia tiene ID único para distintas asignaciones
- **Beneficio neto**: Σ(beneficio_pacientes_atendidos) - Σ(costo_combis_utilizadas)

## Limitaciones

- Modelo compacto (no descomposición)
- Sin cortes ni preprocesamiento avanzado
- Mejor para instancias pequeñas/medianas (< 50 pacientes)
- Para instancias grandes, considerar Column Generation (Estrategia 2)

## Próximos Pasos

1. **SaludCG** - Column Generation
2. **SaludChallenger** - Branch & Price + mejoras
3. **evaluador.py** - Evaluación comparativa
4. **Informe** - Documentación completa
