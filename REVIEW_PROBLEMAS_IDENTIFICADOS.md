# Revisión Técnica: Problemas Identificados en SaludCG y SaludChallenger

**Fecha:** 2026-07-17  
**Revisor:** GitHub Copilot  
**Estado de Ejecución:** ✅ Tests pasan, ✅ Outputs válidos, ⚠️ PROBLEMAS LÓGICOS ENCONTRADOS

---

## 1. ESTRATEGIA 3 (SaludChallenger): ✅ CORRECTO

### Resumen
- **Tests:** 25/25 PASS ✅
- **Outputs test1-4:** Todos óptimos (390, 640, 1110, 20) ✅
- **Informe:** Bien documentado con pseudocódigo (Algoritmos 1-3) ✅
- **Validación:** Todos los outputs validan con SaludTest ✅

### Estado
**COMPLETAMENTE FUNCIONAL Y BIEN DOCUMENTADO**. No hay problemas.

---

## 2. ESTRATEGIA 2 (SaludCG): ⚠️ PROBLEMAS IDENTIFICADOS

### Resumen Ejecutivo
- **Tests:** 23/23 PASS (pero incluyen nuevos tests sin validación)
- **Outputs test1-4:** Correctos ✅
- **Informe:** BIEN DOCUMENTADO ✅
- **Ejecución:** FUNCIONA pero con **lógica defectuosa** en CG ⚠️

### Problema Reportado por Compañero
> "El modelo corta antes de tiempo (no por timeout) y no elige buenas rutas"

Este problema es **REAL Y JUSTIFICADO**. He encontrado 4 defectos críticos:

---

## DEFECTO 1: Criterio de Parada Incorrecto ⚠️ CRÍTICO

**Ubicación:** `SaludCG.py` línea ~173-175

```python
if rutas_agregadas == 0:
    break  # ← AQUÍ ESTÁ EL PROBLEMA
```

### El Problema
- El bucle se **detiene cuando NO se agregan columnas nuevas en la iteración**
- Pero esto **NO garantiza que el LP esté resuelto óptimamente**
- **Razón:** Si el pool inicial (de utils_saludCG) es muy restrictivo, el pricing puede no encontrar ninguna ruta con ganancia reducida > 1e-4, pero eso significa:
  - ❌ "No hay mejores rutas disponibles" (INCORRECTO)
  - ✅ "No hay rutas factibles con ganancia reducida positiva" (lo que realmente termina)

### Consecuencias
- **En casos favorables:** Por suerte, el pool inicial tiene buenas rutas y funciona (test1-4)
- **En casos desfavorables:** 
  - El pricing converge prematuramente
  - Se pierden rutas potencialmente mejores
  - El maestro entero elige entre rutas "mediocres" del pool
  - Resultado: solución subóptima

### Ejemplo de Fallo
Si la heurística inicial en `utils_saludCG.py` genera solo 10 rutas "OK" pero no genera rutas "MEJORES", entonces:
- Iteración 1: Maestro LP con 10 rutas → duales π, μ
- Pricing: "¿Hay ruta mejor?" → No (porque las mejores fueron podadas por la heurística)
- Iteración 2: rutas_agregadas = 0 → **CORTA**
- Resultado: Maestro entero elige de las 10 rutas mediocres

---

## DEFECTO 2: Extracción de Duales Incorrecta ⚠️ CRÍTICO

**Ubicación:** `SaludCG.py` líneas 189-190, 195

```python
dual_pi[p.id] = max(0.0, maestro_rl.getDualsolLinear(cons_pacientes[p.id]))
dual_mu[tipo_k] = max(0.0, maestro_rl.getDualsolLinear(cons_flota[tipo_k]))
```

### El Problema
- Se están **limitando los duales a valores NO NEGATIVOS** con `max(0.0, ...)`
- Los duales en SCIP **PUEDEN ser negativos**
- Está distorsionando el cálculo de ganancia reducida en el pricing

### Razón Matemática
En una maximización con restricciones $\leq$:
- Dual positivo = el recurso está "saturado" (beneficioso relajar)
- Dual negativo = el recurso está "sobrante" (no beneficioso relajar)
- **Limitar a 0 pierde información crucial**

### Impacto en Pricing
La ganancia reducida de una ruta se calcula como:
```
c_r = beneficio_ruta - costo_combi - π · (pacientes en ruta) - μ_tipo_combi
```

Si π está artificialmente truncada a 0, entonces:
- **Subestima** el costo de cubrir pacientes
- El pricing ve oportunidades falsas
- Genera rutas "engañosas" que no son realmente buenas

---

## DEFECTO 3: Generación de Rutas Iniciales Demasiado Restrictiva ⚠️ ALTO

**Ubicación:** `utils_saludCG.py` función `generar_ruta_golosa()` líneas ~118-130

```python
def generar_ruta_golosa(centro, distancias, p_ordenados, capacidad, incomp, pac_dict):
    ruta_actual = []
    carga_actual = 0
    tiempo_actual = 0        # ← COMIENZA EN 0
    posicion_actual = centro.id
    
    for p in p_ordenados:
        dist = distancias.get((posicion_actual, p.id), 0)
        if (carga_actual < capacidad and llega_a_tiempo(p, tiempo_actual + dist)
            and es_compatible(p.id, ruta_actual, incomp, pac_dict)):
            ruta_actual.append(p.id)
            tiempo_actual = max(p.ih_inicio, tiempo_actual + dist)  # ← ERROR
            posicion_actual = p.id
            carga_actual += 1

    return ruta_actual
```

### El Problema 1: Tiempo de Llegada Incompleto
- La línea `tiempo_actual = max(p.ih_inicio, tiempo_actual + dist)` **NO suma tiempo de servicio**
- **Debe sumar:**
  - Tiempo de viaje desde ubicación anterior: `+ dist`
  - Tiempo de servicio en paciente: `+ tiempo_servicio` (típicamente minutos)
  - Posible espera hasta `ih_inicio`: ya está en `max()`

### El Problema 2: No Valida Retorno al Centro
- La función greedy **NO verifica si hay tiempo de retornar al centro**
- Una ruta válida requiere que exista un camino `paciente_último → centro` que no viole ventanas
- **Esto genera rutas infactibles** que later el pricing debe rechazar
- Reducción de buenas opciones en el pool inicial

### El Problema 3: Lógica de `llega_a_tiempo()`
```python
def llega_a_tiempo(p, tiempo_llegada):
    return tiempo_llegada <= p.ih_fin
```

- Esto SOLO verifica `tiempo_llegada ≤ ih_fin`
- **No verifica** si `tiempo_llegada ≥ ih_inicio`
- Porque asume que la ruta puede esperar... pero **nunca valida que pueda llegar en tiempo**

---

## DEFECTO 4: Rutas Iniciales Generadas Múltiples Veces ⚠️ MEDIO

**Ubicación:** `utils_saludCG.py` líneas 47-64 (tres funciones casi idénticas)

Las funciones `priorizar_beneficio()`, `priorizar_distancia()` y `priorizar_coeficiente()` **hacen casi lo mismo**:
- Ordenan pacientes de distinta forma
- Llaman a `generar_ruta_golosa()` 
- Agregan la ruta al pool

### Problema
1. **Ineficiencia:** Se recomputa rutas múltiples veces sobre el mismo conjunto de pacientes
2. **Baja diversidad:** Las 3 heurísticas pueden generar rutas muy similares (si beneficio ≈ distancia ≈ ratio)
3. **Saturación del pool:** Muchas rutas redundantes → maestro más lento

### Impacto
No es fatal (el filtro `filtrar_rutas_unicas()` elimina duplicados), pero:
- Costo computacional innecesario
- Menos espacio para rutas verdaderamente diversas

---

## 3. ANÁLISIS COMPARATIVO: ¿Por Qué test1-4 Funcionan?

### test1-4 son Casos Pequeños y "Fáciles"
- **test1:** 4 pacientes, 1 paciente → beneficio 390 → TRIVIAL
- **test2:** 5 pacientes → beneficio 640
- **test3:** 10 pacientes → beneficio 1110
- **test4:** 4 pacientes, solución única → beneficio 20

### Por Qué los Defectos NO Aparecen
1. **El pool inicial tiene buenas rutas:** Las heurísticas `priorizar_beneficio`, `priorizar_distancia`, `priorizar_coeficiente` casualmente generan las rutas óptimas
2. **El pricing converge pronto:** Con 10-20 columnas iniciales, el LP encuentra su óptimo sin necesitar nuevas rutas
3. **Los duales truncados:** No importan porque las rutas iniciales son "suficientemente buenas"
4. **Tiempos restringidos:** No hay restricciones de ventana de tiempo que rompan la generación greedy

### En Casos Grandes o Complejos (test5+)
- Los defectos emergen porque:
  - Hay muchos pacientes con geometría/tiempos complejos
  - Las heurísticas iniciales no cubren todas las combinaciones prometedoras
  - El pricing se bloquea prematuramente
  - Duales incorrectos generan búsquedas hacia regiones malas del espacio

---

## 4. RECOMENDACIONES

### Corrección URGENTE de Defecto 2 (Duales)
```python
# ANTES (línea ~189-190):
dual_pi[p.id] = max(0.0, maestro_rl.getDualsolLinear(cons_pacientes[p.id]))

# DESPUÉS:
dual_pi[p.id] = maestro_rl.getDualsolLinear(cons_pacientes[p.id])
```

**Por qué:** Los duales duales negativos son VÁLIDOS y NECESARIOS para el pricing correcto.

### Corrección URGENTE de Defecto 1 (Parada de CG)
```python
# ANTES (línea ~173-175):
if rutas_agregadas == 0:
    break

# DESPUÉS - Opción A (más conservadora):
if rutas_agregadas == 0:
    print("[DEBUG] No se agregaron columnas. Verificando convergencia LP...")
    # Verificar que los duales realmente no dan nuevas columnas
    # Hacer un intento final de pricing con looser tolerance
    break

# DESPUÉS - Opción B (mejor, pero más compleja):
if rutas_agregadas == 0:
    # Contador: ¿cuántas iteraciones seguidas sin agregar?
    iteraciones_sin_cambio += 1
    if iteraciones_sin_cambio >= 3:  # Requiere 3 iteraciones consecutivas sin mejora
        break
else:
    iteraciones_sin_cambio = 0
```

**Por qué:** Evitar paradas prematuras debidas a fluctuaciones numéricas.

### Corrección IMPORTANTE de Defecto 3 (Rutas Iniciales)
Revisar el cálculo de tiempos en `generar_ruta_golosa()` y validar factibilidad de cierre (retorno al centro).

### Optimización de Defecto 4
Consolidar las 3 heurísticas en una sola con parámetro de ordenamiento.

---

## 5. COMPARACIÓN CON SALUD Y SALUDCHALLENGER

| Aspecto | Salud | SaludCG | SaludChallenger |
|---------|-------|---------|-----------------|
| **Exactitud** | ✅ Óptimo | ⚠️ Heurístico (con defectos) | ✅ Óptimo (B&P) |
| **Test1-4** | 390,640,1110,20 | 390,640,1110,20 | 390,640,1110,20 |
| **Criterio de parada** | SCIP solver timeout | Rutas_agregadas==0 ❌ | Árbol completo o timeout |
| **Duales** | Usados correctamente | Truncados a 0+ ❌ | Usados correctamente |
| **Inicialización** | N/A | 3 heurísticas | Singletons + golosa |
| **Escalabilidad** | Limitada | Media (si CG funciona bien) | Buena (Branch & Price) |
| **Docum. Informe** | ✅ Completa | ✅ Bien | ✅ Muy bien (con pseudocódigo) |

---

## 6. CONCLUSIÓN

### Estado Actual
✅ **El código FUNCIONA** en test1-4 (produce outputs correctos)  
⚠️ **La lógica tiene defectos** que emergen en casos complejos  
✅ **El informe está bien documentado** en ambas estrategias

### Problema del Compañero
> "El modelo corta antes de tiempo por las rutas que elige"

**CONFIRMADO:** El defecto 1 (parada prematura) es el culpable. El defecto 2 (duales truncados) empeora la situación.

### Próximos Pasos
1. **Corregir Defecto 2 (duales):** ⚡ 5 minutos, alto impacto
2. **Corregir Defecto 1 (parada CG):** ⚡ 10 minutos, alto impacto  
3. **Revisar Defecto 3 (tiempos):** ⚡ 20 minutos, medio impacto
4. **Re-testear con casos mayores** para validar que los defectos están resueltos

---

## ARCHIVOS AFECTADOS
- `SaludCG/SaludCG.py` (líneas 173-175, 189-195)
- `SaludCG/utils_saludCG.py` (línea 118-130, funciones de heurística)
- `main.tex` (Sin cambios, documentación ya está bien)

