import networkx as nx
import matplotlib.pyplot as plt
import sys

def parse_input_file(filename):
    """Parsea el archivo de input para obtener pacientes, combis y matriz de distancias"""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith('#')]
    
    idx = 0
    
    # Leer tolerancia
    tolerance = int(lines[idx])
    idx += 1
    
    # Leer pacientes hasta encontrar una línea con "Combi"
    patients = {}
    while idx < len(lines) and 'Combi' not in lines[idx]:
        parts = lines[idx].split(',')
        patient_id = int(parts[0].strip())
        appointment_time = int(parts[1].strip())
        patients[patient_id] = appointment_time
        idx += 1
    
    # Saltar línea de combis (no la usamos para el grafo)
    while idx < len(lines) and 'Combi' in lines[idx]:
        idx += 1
    
    # Leer matriz de distancias
    edges = []
    while idx < len(lines):
        parts = lines[idx].split(',')
        origin = int(parts[0].strip())
        destination = int(parts[1].strip())
        cost = int(parts[2].strip())
        edges.append((origin, destination, cost))
        idx += 1
    
    return tolerance, patients, edges

def create_graph_visualization(input_file, output_file='grafo_pacientes.png'):
    """Crea la visualización del grafo a partir del archivo de input"""
    
    # Parsear input
    tolerance, patients, edges = parse_input_file(input_file)
    
    # Crear grafo no dirigido
    G = nx.Graph()
    
    # Agregar nodos: 0 es el centro, 1-n son los pacientes
    nodes = {0: 'Centro\n(0)'}
    for patient_id, appointment_time in sorted(patients.items()):
        window_start = max(0, appointment_time - tolerance)
        window_end = appointment_time
        nodes[patient_id] = f'P{patient_id}\nCita:{appointment_time}\n[{window_start}, {window_end}]'
    
    # Agregar aristas (convertir a no dirigidas tomando el mínimo)
    edge_dict = {}
    for origin, destination, cost in edges:
        if origin != destination:  # Ignorar self-loops
            edge_pair = tuple(sorted([origin, destination]))
            if edge_pair not in edge_dict:
                edge_dict[edge_pair] = cost
            else:
                # Si hay arista inversa, tomar el mínimo (para grafo simétrico)
                edge_dict[edge_pair] = min(edge_dict[edge_pair], cost)
    
    G.add_weighted_edges_from([(u, v, w) for (u, v), w in edge_dict.items()])
    
    # Crear visualización
    plt.figure(figsize=(12, 10))
    
    # Posicionamiento
    pos = nx.spring_layout(G, seed=42, k=2, iterations=50, weight='weight')
    
    # Dibujar nodos
    node_colors = ['lightcoral' if n == 0 else 'skyblue' for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3500, edgecolors='black', linewidths=2)
    
    # Dibujar aristas
    nx.draw_networkx_edges(G, pos, width=2, alpha=0.5, edge_color='gray')
    
    # Dibujar etiquetas de nodos
    nx.draw_networkx_labels(G, pos, labels=nodes, font_size=9, font_weight='bold')
    
    # Dibujar etiquetas de aristas (costos)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_weight='bold', font_size=8)
    
    plt.title(f'Grafo de Traslado de Pacientes (Tolerancia: {tolerance} min)', fontsize=14, fontweight='bold')
    plt.axis('off')
    
    # Guardar imagen
    plt.savefig(output_file, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"✓ Grafo generado exitosamente: {output_file}")
    print(f"  - Nodos: {len(nodes)} (1 centro + {len(patients)} pacientes)")
    print(f"  - Aristas: {len(G.edges())}")
    print(f"  - Tolerancia temporal: {tolerance} minutos")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python test.py <archivo_input> [archivo_salida]")
        print("Ejemplo: python test.py input_combis_pacientes_2.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'grafo_pacientes.png'
    
    try:
        create_graph_visualization(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)