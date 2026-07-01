"""
Algoritmo Principal de Generación de Columnas para VRP.

El algoritmo itera entre:
1. Problema Maestro: Encuentra la mejor combinación de rutas dado el conjunto actual
2. Subproblema: Genera nuevas rutas rentables usando duales del maestro

Se detiene cuando no hay rutas rentables (criterio de parada del subproblema).
"""

from ruta import Rutas
from master_problem import ProblemaMaestro
from subproblem import SubproblemaGeneracionColumnas
from utils import leer_datos_vrp, imprimir_rutas, guardar_resultados

class AlgoritmoGeneracionColumnas:
    """Resuelve VRP usando generación de columnas."""
    
    def __init__(self, lista_pacientes, distancias, capacidad_combi, turnos=None, tolerancia=0,
                 combis=None, capacidades=None, max_iteraciones=100):
        """
        Inicializa el algoritmo.
        
        Args:
            lista_pacientes: Lista de IDs de pacientes
            distancias: Diccionario con distancias entre nodos
            capacidad_combi: Capacidad máxima entre todas las combis
            turnos: Diccionario {paciente_id: hora_turno} para ventanas de tiempo
            tolerancia: Margen de tolerancia antes del turno
            combis: Lista de nombres de combis (para asignación final)
            capacidades: Diccionario {nombre_combi: capacidad}
            max_iteraciones: Número máximo de iteraciones
        """
        self.lista_pacientes = lista_pacientes
        self.distancias = distancias
        self.capacidad_combi = capacidad_combi
        self.turnos = turnos or {}
        self.tolerancia = tolerancia
        self.max_iteraciones = max_iteraciones
        
        # Si no se proporcionan combis, generar automáticamente
        if combis is None:
            # Estimar número de combis basándose en capacidad
            num_pacientes = len(lista_pacientes)
            num_combis_needed = max(1, (num_pacientes + capacidad_combi - 1) // capacidad_combi)
            # Crear nombres genéricos: A, B, C, D, ...
            letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            self.combis = [letras[i % 26] for i in range(num_combis_needed)]
        else:
            self.combis = combis
        
        self.capacidades = capacidades or {}
        # Si no se proporcionan capacidades, asumir que todas tienen capacidad_combi
        if not self.capacidades:
            self.capacidades = {combi: capacidad_combi for combi in self.combis}
        
        # Generar rutas iniciales
        self.rutas_collection = Rutas(lista_pacientes, distancias, capacidad_combi,
                                      turnos=turnos, tolerancia=tolerancia)
        self.rutas = self.rutas_collection.rutas.copy()
        
        # Historial
        self.iteraciones_historia = []
        self.mejor_valor_objetivo = float('inf')
    
    def resolver(self, metodo_subproblema="enumeracion", verbose=True):
        """
        Ejecuta el algoritmo de generación de columnas.
        
        Args:
            metodo_subproblema: "enumeracion" o "pgm_lineal"
            verbose: Si True, imprime información del progreso
            
        Returns:
            (valor_objetivo, rutas_usadas, historia)
        """
        print(f"\n{'='*70}")
        print(f"ALGORITMO DE GENERACIÓN DE COLUMNAS PARA VRP")
        print(f"{'='*70}")
        print(f"Pacientes a visitar: {self.lista_pacientes}")
        print(f"Rutas iniciales: {len(self.rutas)}")
        print(f"Cap. máx. entre combis usada para generar rutas: {self.capacidad_combi}")
        if self.capacidades:
            caps_str = ", ".join(f"{k}={v}" for k, v in self.capacidades.items())
            print(f"Capacidades por combi: {caps_str}")
        print(f"Tolerancia de ventanas de tiempo: {self.tolerancia} min")
        print(f"Método de subproblema: {metodo_subproblema}")
        print(f"{'='*70}")
        
        print(f"\nPool de rutas iniciales:")
        for ruta in self.rutas:
            pacientes_str = " -> ".join(str(p) for p in ruta.pacientes)
            ventana_str = ""
            if self.turnos:
                ventanas = [f"P{p}:[{self.turnos[p]-self.tolerancia},{self.turnos[p]}]" for p in ruta.pacientes]
                ventana_str = f"  ventanas: {', '.join(ventanas)}"
            print(f"  Ruta {ruta.id_ruta:2d}: [0 -> {pacientes_str} -> 0]  costo={ruta.costo:.1f}{ventana_str}")
        print()
        
        iteracion = 0
        epsilon = 1e-6  # Tolerancia para criterio de parada
        contador_ruta_nueva = len(self.rutas)  # Para asignar IDs únicas
        primera_iteracion = True  # Flag para usar artificiales en primera iteración
        
        while iteracion < self.max_iteraciones:
            iteracion += 1
            
            if verbose:
                print(f"\n{'-'*70}")
                print(f"ITERACION {iteracion}")
                print(f"{'-'*70}")
                print(f"Rutas disponibles actualmente: {len(self.rutas)}")
            
            # ========== PASO 1: Resolver Problema Maestro (Relajado) ==========
            # Primera iteración: CON artificiales para obtener solución inicial
            # Iteraciones posteriores: SIN artificiales para evitar duales inflados
            usar_artificiales_ahora = primera_iteracion
            maestro = ProblemaMaestro(self.lista_pacientes, self.rutas, num_combis=len(self.combis))
            status, valor_obj, uso_rutas, duales = maestro.resolver(relajado=True, usar_artificiales=usar_artificiales_ahora)
            primera_iteracion = False  # Solo usar artificiales en primera iteración
            
            if status != "optimal":
                print(f"[Error] No se pudo resolver el problema maestro en iteración {iteracion}")
                print(f"[Status] {status}")
                break
            
            if verbose:
                print(f"[Maestro Relajado]")
                print(f"  Status: {status}")
                print(f"  Valor objetivo: {valor_obj:.6f}")
                print(f"  Rutas usadas: {len(uso_rutas)}")
                duales_sample = {p: duales[p] for p in list(duales.keys())[:3]}
                print(f"  Duales (muestra): {duales_sample}...")
            
            self.mejor_valor_objetivo = valor_obj
            
            # ========== PASO 2: Resolver Subproblema (Pricing) ==========
            # Busca nuevas rutas con costo reducido NEGATIVO
            
            # Ajustar duales si están inflados por variables artificiales
            # Si los duales son cercanos al BIG_M, significa que se están usando variables artificiales
            # En ese caso, usar duales "modificados" que sean más pequeños para permitir la generación de columnas
            duales_para_subproblema = duales.copy()
            if maestro.BIG_M > 0:
                # Si algún dual es cercano a BIG_M, significa que hay variable artificial en uso
                # Ajustar los duales para ser más razonables
                duales_inflados = {p: d for p, d in duales.items() if d >= maestro.BIG_M * 0.9}
                if duales_inflados:
                    # Usar duales más bajos para incentivar la generación de columnas
                    # Especificamente, restar el efecto de la variable artificial estimado
                    for paciente in duales_inflados:
                        # Ajustar el dual: usar solo el "valor real" sin la penalidad
                        # Heurística: dual_ajustado = dual - (BIG_M - valor_pequeño)
                        # Simplificado: dual_ajustado ≈ valor_pequeño (e.g., 10-100)
                        duales_para_subproblema[paciente] = max(10.0, duales[paciente] - maestro.BIG_M + 100.0)
                    
                    if verbose:
                        print(f"[Ajuste de Duales] Detectados duales inflados. Duales ajustados: {duales_para_subproblema}")
            
            subproblema = SubproblemaGeneracionColumnas(
                self.lista_pacientes,
                self.distancias,
                self.capacidad_combi,
                duales_para_subproblema,
                turnos=self.turnos,
                tolerancia=self.tolerancia
            )
            
            nueva_ruta, costo_reducido = subproblema.generar_nueva_ruta(metodo=metodo_subproblema)
            
            if verbose:
                print(f"\n[Subproblema]")
                print(f"  Costo reducido óptimo: {costo_reducido:.8f}")
                if nueva_ruta:
                    print(f"  Nueva ruta encontrada: {nueva_ruta}")
                else:
                    print(f"  No hay ruta rentable")
            
            # ========== CRITERIO DE PARADA: costo_reducido <= epsilon ==========
            if costo_reducido <= epsilon:
                if verbose:
                    print(f"\n✓ CRITERIO DE PARADA ALCANZADO")
                    print(f"  Costo reducido = {costo_reducido:.8f} <= {epsilon}")
                    print(f"  No hay columnas rentables -> Optimalidad (LP)\n")
                
                self.iteraciones_historia.append({
                    'iteracion': iteracion,
                    'num_rutas': len(self.rutas),
                    'valor_objetivo': valor_obj,
                    'costo_reducido': costo_reducido,
                    'nueva_ruta': None
                })
                break
            
            # ========== PASO 3: Agregar Nueva Ruta al Pool ==========
            nueva_ruta.id_ruta = contador_ruta_nueva
            contador_ruta_nueva += 1
            self.rutas.append(nueva_ruta)
            
            if verbose:
                pacientes_str = " -> ".join(str(p) for p in nueva_ruta.pacientes)
                print(f"\n[Columna Agregada] Ruta {nueva_ruta.id_ruta}: [0 -> {pacientes_str} -> 0]")
                print(f"  Costo: {nueva_ruta.costo:.2f}")
                print(f"  Costo reducido: {costo_reducido:.8f} (negativo ✓)")
            
            self.iteraciones_historia.append({
                'iteracion': iteracion,
                'num_rutas': len(self.rutas),
                'valor_objetivo': valor_obj,
                'costo_reducido': costo_reducido,
                'nueva_ruta': nueva_ruta
            })
            
            guardar_resultados(iteracion, duales, costo_reducido, nueva_ruta)
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"[CG] Ciclo terminado después de {iteracion} iteración(es)")
            print(f"[CG] Total de rutas en pool: {len(self.rutas)}")
            print(f"[CG] Mejor valor objetivo (LP): {self.mejor_valor_objetivo:.6f}")
            print(f"{'='*70}")
        
        return self._resolver_problema_entero()
    
    def _resolver_problema_entero(self):
        """Resuelve el problema maestro con variables enteras (con variables artificiales)."""
        print(f"\n{'='*70}")
        print(f"RESOLVIENDO PROBLEMA MAESTRO ENTERO (SOLUCION FINAL)")
        print(f"{'='*70}\n")
        
        # En la solución final, usar variables artificiales para garantizar factibilidad
        maestro = ProblemaMaestro(self.lista_pacientes, self.rutas, num_combis=len(self.combis))
        status, valor_obj, uso_rutas, duales = maestro.resolver(relajado=False, usar_artificiales=True)
        
        # Extraer rutas usadas
        rutas_usadas = [ruta for ruta in self.rutas if ruta.id_ruta in uso_rutas]
        
        print(f"Estado: {status}")
        
        # Manejo de caso infactible
        if status == "infeasible":
            print(f"\n{'!'*70}")
            print(f"NO SE ENCONTRÓ SOLUCIÓN FACTIBLE")
            print(f"{'!'*70}")
            print(f"Es imposible cubrir todos los pacientes con los siguientes recursos:")
            print(f"  - Número de combis disponibles: {len(self.combis)}")
            print(f"  - Pacientes a visitar: {len(self.lista_pacientes)}")
            print(f"  - Restricción: Máximo {len(self.combis)} ruta(s) simultánea(s)")
            print(f"\nPosibles causas:")
            print(f"  1. No hay suficientes combis para las rutas requeridas")
            print(f"  2. Las ventanas de tiempo no permiten combinar pacientes eficientemente")
            print(f"  3. Las capacidades de las combis son insuficientes")
            print(f"{'='*70}\n")
            
            return 0, [], self.iteraciones_historia
        
        if status != "optimal":
            print(f"Advertencia: No se encontró solución óptima entera. Status: {status}")
        
        print(f"Valor objetivo final: {valor_obj:.4f}")
        print(f"Rutas usadas: {len(rutas_usadas)}")
        print(f"Detalles de las rutas:")
        for ruta in rutas_usadas:
            print(f"  {ruta}")
        
        # Asignacion de combis
        if self.combis and self.capacidades:
            print(f"\nAsignacion de Combis a Rutas:")
            self._imprimir_asignacion_combis(rutas_usadas)
        
        print(f"{'='*70}\n")
        
        return valor_obj, rutas_usadas, self.iteraciones_historia
    
    def _imprimir_asignacion_combis(self, rutas_usadas):
        """
        Asigna combis a rutas de forma greedy (ruta más grande → combi con mayor cap)
        y muestra el cronograma de atención por combi.
        """
        # Ordenar: rutas por nro de pacientes desc, combis por capacidad desc
        rutas_ord = sorted(rutas_usadas, key=lambda r: len(r.pacientes), reverse=True)
        combis_disp = sorted(self.combis, key=lambda k: self.capacidades[k], reverse=True)
        
        asignacion = []  # lista de (combi_nombre, ruta)
        combis_usadas = list(combis_disp)
        for ruta in rutas_ord:
            asignada = None
            for i, combi in enumerate(combis_usadas):
                if len(ruta.pacientes) <= self.capacidades[combi]:
                    asignada = combis_usadas.pop(i)
                    break
            asignacion.append((asignada, ruta))
        
        # Ordenar por nombre de combi para imprimir
        asignacion.sort(key=lambda x: x[0] or "ZZZ")
        
        for combi, ruta in asignacion:
            nombre = combi if combi else "[Sin combi - capacidad insuficiente]"
            cap_str = f"cap={self.capacidades[combi]}" if combi else ""
            pacientes_str = " -> ".join(str(p) for p in ruta.pacientes)
            print(f"\n  --- {nombre} ({cap_str}) ---")
            
            # Reconstruir ruta con tiempos
            T_actual = 0
            nodo_actual = 0
            print(f"    Viaje: Nodo 0", end="")
            for p in ruta.pacientes:
                print(f" -> Nodo {p}", end="")
            print(f" -> Nodo 0")
            
            if self.turnos:
                print(f"    Cronograma de atencion:")
                for p in ruta.pacientes:
                    if (nodo_actual, p) in self.distancias:
                        T_llegada = T_actual + self.distancias[nodo_actual, p]
                        T_servicio = max(T_llegada, self.turnos[p] - self.tolerancia)
                        ventana_inf = self.turnos[p] - self.tolerancia
                        ventana_sup = self.turnos[p]
                        print(f"      Paciente {p}: Recogido a los {T_servicio:.1f} min "
                              f"(Turno: {self.turnos[p]}, Ventana: {ventana_inf} a {ventana_sup})")
                        T_actual = T_servicio
                        nodo_actual = p
            
            print(f"    Costo de transito: {ruta.costo:.1f} min")

    def imprimir_historia(self):
        """Imprime el historial de iteraciones."""
        print(f"\n{'='*70}")
        print(f"HISTORIAL DE ITERACIONES")
        print(f"{'='*70}")
        for info in self.iteraciones_historia:
            print(f"Iter {info['iteracion']:2d}: "
                  f"Rutas={info['num_rutas']:3d}, "
                  f"Objetivo={info['valor_objetivo']:10.4f}, "
                  f"Costo_Reducido={info['costo_reducido']:10.6f}")
        print(f"{'='*70}\n")


def main():
    """Función principal para pruebas."""
    import sys
    
    # Archivo de entrada (igual que para los modelos anteriores)
    archivo_input = "input_combis_pacientes.txt"
    
    # Intentar encontrar el archivo
    import os
    if not os.path.exists(archivo_input):
        # Buscar en directorio padre
        archivo_input = os.path.join("..", archivo_input)
    
    if not os.path.exists(archivo_input):
        print(f"Error: Archivo {archivo_input} no encontrado")
        print("Uso: python column_generation.py")
        sys.exit(1)
    
    # Leer datos
    pacientes, turnos, tolerancia, combis, capacidades, distancias = leer_datos_vrp(archivo_input)
    
    if pacientes is None:
        sys.exit(1)
    
    # Usar la capacidad máxima entre todas las combis
    capacidad_combi = max(capacidades.values()) if capacidades else 2
    
    # Crear y ejecutar algoritmo
    algoritmo = AlgoritmoGeneracionColumnas(
        pacientes,
        distancias,
        capacidad_combi,
        turnos=turnos,
        tolerancia=tolerancia,
        max_iteraciones=100
    )
    
    valor_obj, rutas_usadas, historia = algoritmo.resolver(
        metodo_subproblema="enumeracion",
        verbose=True
    )
    
    # Imprimir resultados finales
    print(f"\n{'='*70}")
    print(f"RESULTADOS FINALES")
    print(f"{'='*70}")
    print(f"Valor objetivo: {valor_obj:.4f}")
    print(f"Número de rutas utilizadas: {len(rutas_usadas)}")
    print(f"Rutas:")
    for ruta in rutas_usadas:
        print(f"  {ruta}")
    print(f"{'='*70}\n")
    
    algoritmo.imprimir_historia()


if __name__ == "__main__":
    main()
