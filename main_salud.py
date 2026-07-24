"""
Script de ejecución principal para el TP Salud - Estrategia 1.
Permite ejecutar la estrategia Salud desde la línea de comandos.

Equivale a `python Salud/Salud.py <instancia> <threshold> [out_path] [in_path]`
y acepta las mismas rutas opcionales:

    python main_salud.py test1 500                  # escribe en ./OUT_modelo1
    python main_salud.py test1 500 ./tmp ./IN       # escribe en ./tmp
"""

import sys
import os

# Agregar Salud al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Salud'))

from Salud import Salud


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python main_salud.py <instancia> <threshold> [out_path] [in_path]")
        print("Ejemplo: python main_salud.py test1 500")
        print("         python main_salud.py test1 500 ./tmp ./IN")
        print("")
        print("NOTA: con out_path por defecto (./OUT_modelo1) se regenera el archivo")
        print("      de la entrega correspondiente a esa instancia. Para dejar la")
        print("      entrega intacta, pasar un out_path propio.")
        sys.exit(1)

    instancia = sys.argv[1]
    threshold = float(sys.argv[2])
    out_path = sys.argv[3] if len(sys.argv) > 3 else "./OUT_modelo1"
    in_path = sys.argv[4] if len(sys.argv) > 4 else "./IN"

    Salud(instancia, threshold, out_path, in_path)
