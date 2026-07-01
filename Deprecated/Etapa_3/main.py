#!/usr/bin/env python3
"""
Main entry point para el algoritmo de generación de columnas (Etapa 3).

Uso: python main.py [archivo_input] [--metodo {enumeracion,pgm_lineal}] [--verbose]
"""

import sys
import argparse
from column_generation import AlgoritmoGeneracionColumnas
from utils import leer_datos_vrp


def main():
    parser = argparse.ArgumentParser(
        description="Algoritmo de Generación de Columnas para VRP"
    )
    parser.add_argument(
        "archivo_input",
        nargs="?",
        default="input_vrp_colgen.txt",
        help="Archivo de entrada con datos del VRP (default: input_vrp_colgen.txt)"
    )
    parser.add_argument(
        "--metodo",
        choices=["enumeracion", "pgm_lineal"],
        default="enumeracion",
        help="Método para generar columnas (default: enumeracion)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar información detallada durante la ejecución"
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=100,
        help="Número máximo de iteraciones (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Leer datos del archivo
    print(f"Leyendo datos del archivo: {args.archivo_input}")
    pacientes, turnos, tolerancia, combis, capacidades, distancias = leer_datos_vrp(args.archivo_input)
    
    if pacientes is None:
        print("Error: No se pudieron leer los datos. Abortando.")
        sys.exit(1)
    
    print(f"[OK] Datos leidos exitosamente")
    print(f"  - Pacientes: {pacientes}")
    print(f"  - Combis: {combis}")
    print(f"  - Capacidades: {capacidades}")
    print(f"  - Tolerancia: {tolerancia} min")
    
    # Usar la capacidad máxima entre todas las combis (permite rutas heterogéneas)
    capacidad_combi = max(capacidades.values()) if capacidades else 2
    
    # Crear instancia del algoritmo
    print(f"\nCreando instancia del algoritmo...")
    algoritmo = AlgoritmoGeneracionColumnas(
        pacientes,
        distancias,
        capacidad_combi,
        turnos=turnos,
        tolerancia=tolerancia,
        combis=combis,
        capacidades=capacidades,
        max_iteraciones=args.max_iter
    )
    
    # Ejecutar algoritmo
    print(f"\nEjecutando algoritmo de generación de columnas...")
    valor_obj, rutas_usadas, historia = algoritmo.resolver(
        metodo_subproblema=args.metodo,
        verbose=args.verbose
    )
    
    # Mostrar resultados
    if len(rutas_usadas) == 0 and valor_obj == 0:
        # Caso infactible - ya fue reportado por el algoritmo
        return 1
    
    print(f"\n{'='*70}")
    print(f"SOLUCIÓN FINAL")
    print(f"{'='*70}")
    print(f"Valor objetivo (distancia total): {valor_obj:.4f} minutos")
    print(f"Número de rutas utilizadas: {len(rutas_usadas)}")
    print(f"\nDetalle de rutas:")
    for idx, ruta in enumerate(rutas_usadas, 1):
        pacientes_str = " -> ".join(str(p) for p in ruta.pacientes)
        print(f"  Ruta {idx}: 0 -> {pacientes_str} -> 0 (costo: {ruta.costo:.2f} min)")
    
    print(f"\nCoberturas de pacientes:")
    pacientes_cubiertos = set()
    for ruta in rutas_usadas:
        pacientes_cubiertos.update(ruta.pacientes)
    print(f"  Pacientes cubiertos: {sorted(pacientes_cubiertos)}")
    print(f"  Total: {len(pacientes_cubiertos)}/{len(pacientes)} [OK]")
    
    print(f"{'='*70}\n")
    
    print(f"{'='*70}")
    print(f"RESULTADOS FINALES - ITERACIONES")
    print(f"{'='*70}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
