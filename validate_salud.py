"""
Script de validación para la estrategia Salud.
Ejecuta Salud y luego SaludTest para verificar la solución.
"""

import sys
import os

# Agregar Salud al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Salud'))

from Salud import Salud
from SaludTest import SaludTest


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python validate_salud.py <instancia> <threshold>")
        print("Ejemplo: python validate_salud.py test1 30")
        print("")
        print("Este script ejecuta:")
        print("  1. Salud(instancia, threshold) - resuelve el problema MILP")
        print("  2. SaludTest(instancia) - valida la solución sin LP")
        sys.exit(1)
    
    instancia = sys.argv[1]
    threshold = float(sys.argv[2])
    
    print("=" * 70)
    print("VALIDACIÓN COMPLETA: Salud + SaludTest")
    print("=" * 70)
    
    # Ejecutar Salud
    print("\n1. Ejecutando Salud...")
    exito_salud = Salud(instancia, threshold)
    
    if not exito_salud:
        print("✗ Error en Salud")
        sys.exit(1)
    
    # Ejecutar SaludTest
    print("\n2. Ejecutando SaludTest...")
    exito_test = SaludTest(instancia)
    
    if exito_test:
        print("\n" + "=" * 70)
        print("✓ VALIDACIÓN EXITOSA")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("✗ VALIDACIÓN FALLIDA")
        print("=" * 70)
        sys.exit(1)
