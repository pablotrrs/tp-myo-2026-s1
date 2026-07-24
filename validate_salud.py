"""
Script de validación para la estrategia Salud.
Ejecuta Salud y luego SaludTest para verificar la solución.

Acepta las mismas rutas opcionales que los modelos, de modo que se lo puede
correr sin pisar los archivos de la entrega:

    python validate_salud.py test1 500                  # escribe en ./OUT_modelo1
    python validate_salud.py test1 500 ./tmp ./IN       # escribe en ./tmp
"""

import sys
import os

# Agregar Salud al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Salud'))

from Salud import Salud
from SaludTest import SaludTest


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python validate_salud.py <instancia> <threshold> [out_path] [in_path]")
        print("Ejemplo: python validate_salud.py test1 500")
        print("         python validate_salud.py test1 500 ./tmp ./IN")
        print("")
        print("Este script ejecuta:")
        print("  1. Salud(instancia, threshold) - resuelve el problema MILP")
        print("  2. SaludTest(instancia, ...)   - valida la solución sin LP")
        print("")
        print("NOTA: con out_path por defecto (./OUT_modelo1) se regenera el archivo")
        print("      de la entrega correspondiente a esa instancia. Para dejar la")
        print("      entrega intacta, pasar un out_path propio.")
        sys.exit(1)

    instancia = sys.argv[1]
    threshold = float(sys.argv[2])
    out_path = sys.argv[3] if len(sys.argv) > 3 else "./OUT_modelo1"
    in_path = sys.argv[4] if len(sys.argv) > 4 else "./IN"

    print("=" * 70)
    print("VALIDACION COMPLETA: Salud + SaludTest")
    print(f"Instancia: {instancia} | Threshold: {threshold}s")
    print(f"Entrada: {in_path} | Salida: {out_path}")
    print("=" * 70)

    # Ejecutar Salud
    print("\n1. Ejecutando Salud...")
    exito_salud = Salud(instancia, threshold, out_path, in_path)

    if not exito_salud:
        print("[ERROR] Error en Salud")
        sys.exit(1)

    # Ejecutar SaludTest sobre el archivo que acaba de generarse
    print("\n2. Ejecutando SaludTest...")
    archivo_salida = os.path.join(out_path, f"{instancia}.out")
    exito_test = SaludTest(instancia, archivo_salida, in_path)

    if exito_test:
        print("\n" + "=" * 70)
        print("[OK] VALIDACION EXITOSA")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("[ERROR] VALIDACION FALLIDA")
        print("=" * 70)
        sys.exit(1)
