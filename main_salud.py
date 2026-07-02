"""
Script de ejecución principal para el TP Salud - Estrategia 1.
Permite ejecutar la estrategia Salud desde la línea de comandos.
"""

import sys
import os

# Agregar Salud al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Salud'))

from Salud import Salud


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python main_salud.py <instancia> <threshold>")
        print("Ejemplo: python main_salud.py test1 30")
        sys.exit(1)
    
    instancia = sys.argv[1]
    threshold = float(sys.argv[2])
    
    Salud(instancia, threshold)
