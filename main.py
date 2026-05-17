"""
Linear Programming Solver for Multiple Problem Types
Supports: Maximum Flow, Vehicle Routing Problem with Time Windows (VRP-TW)
"""

from pyscipopt import Model, quicksum
import sys
from typing import List, Dict, Tuple, Any

# Import VRP-TW solver from combis_pacientes_modelo
from combis_pacientes_modelo import leer_datos_vrp, resolver_vrp_ventanas


def read_input(filename: str) -> Dict[str, Any]:
    """
    Read and parse input file for maximum flow problem.
    
    Expected format:
    - Line 1: number of nodes
    - Line 2: list of node names (space-separated)
    - Line 3: source node name
    - Line 4: sink node name
    - Line 5: number of directed edges
    - Lines 6+: each line contains "node1 node2 capacity"
    
    Args:
        filename: Path to the input file
        
    Returns:
        Dictionary containing parsed input data with keys:
            - 'nodes': list of node names
            - 'edges': list of tuples (source, dest, capacity)
            - 'source': source node name
            - 'sink': sink node name
    """
    data = {}
    try:
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
            
            # Parse nodes
            n_nodes = int(lines[0])
            nodes = lines[1].split()
            assert len(nodes) == n_nodes, f"Expected {n_nodes} nodes, got {len(nodes)}"
            
            # Parse source and sink
            source = lines[2]
            sink = lines[3]
            
            assert source in nodes, f"Source '{source}' not in nodes"
            assert sink in nodes, f"Sink '{sink}' not in nodes"
            
            # Parse edges
            n_edges = int(lines[4])
            edges = []
            for i in range(5, 5 + n_edges):
                parts = lines[i].split()
                u, v = parts[0], parts[1]
                capacity = float(parts[2])
                assert u in nodes and v in nodes, f"Edge ({u}, {v}) contains invalid nodes"
                edges.append((u, v, capacity))
            
            data['nodes'] = nodes
            data['edges'] = edges
            data['source'] = source
            data['sink'] = sink
            
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except (ValueError, IndexError, AssertionError) as e:
        print(f"Error parsing input file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error reading input file: {e}")
        sys.exit(1)
    
    return data


def create_model(data: Dict[str, Any]) -> Tuple[Model, Dict]:
    """
    Create and configure the maximum flow optimization model.
    
    Args:
        data: Dictionary containing:
            - 'nodes': list of node names
            - 'edges': list of tuples (source, dest, capacity)
            - 'source': source node name
            - 'sink': sink node name
        
    Returns:
        Tuple of (Model, variables_dict) where variables_dict contains:
            - 'flow': dict of flow variables indexed by (u, v)
            - 'F': total flow variable
    """
    model = Model("Maximum_Flow_Problem")
    
    nodes = data['nodes']
    edges = data['edges']
    source = data['source']
    sink = data['sink']
    
    variables = {}
    
    # Create flow variables for each directed edge with capacity upper bounds
    flow_vars = {}
    for u, v, capacity in edges:
        if u == source or v == sink:
            flow_vars[u, v] = model.addVar(name=f"flujo_{u}_{v}", vtype="C", lb=0, ub=capacity)
        else:
            flow_vars[u, v] = model.addVar(name=f"flujo_{u}_{v}", vtype="C", lb=-capacity, ub=capacity)
    
    # Create total flow variable
    F = model.addVar(name="Flujo_Total", vtype="C", lb=0)
    
    # Set objective: maximize total flow
    model.setObjective(F, sense="maximize")
    
    # Add flow conservation constraints
    for node in nodes:
        # Outgoing flow: sum of all edges leaving this node
        outgoing = quicksum(flow_vars[u, v] for (u, v) in flow_vars.keys() if u == node)
        
        # Incoming flow: sum of all edges pointing to this node
        incoming = quicksum(flow_vars[u, v] for (u, v) in flow_vars.keys() if v == node)
        
        # Apply balance constraints
        if node == source:
            # At source: outgoing - incoming = total flow
            model.addCons(outgoing - incoming == F, name=f"balance_source_{node}")
        elif node == sink:
            # At sink: incoming - outgoing = total flow
            model.addCons(incoming - outgoing == F, name=f"balance_sink_{node}")
        else:
            # At intermediate nodes: outgoing - incoming = 0 (conservation)
            model.addCons(outgoing - incoming == 0, name=f"balance_intermediate_{node}")
    
    variables['flow'] = flow_vars
    variables['F'] = F
    
    return model, variables


def solve_model(model: Model, variables: Dict) -> Tuple[bool, float, Dict[str, float]]:
    """
    Solve the optimization model.
    
    Args:
        model: The PySCIPOpt Model to solve
        variables: Dictionary containing the model variables
        
    Returns:
        Tuple containing (is_optimal, objective_value, solution_dict)
    """
    # Set time limit if needed (in seconds)
    # model.setParam("limits/time", 300)
    
    # Disable presolve if needed
    # model.setParam("presolving/maxrounds", 0)
    
    # Optimize
    model.optimize()
    
    # Get status and solution
    status = model.getStatus()
    is_optimal = (status == "optimal")
    obj_value = model.getObjVal() if model.getObjVal() is not None else None
    
    solution = {}
    if obj_value is not None:
        # Extract flow values for edges with non-zero flow
        flow_vars = variables['flow']
        for (u, v), var in flow_vars.items():
            val = model.getVal(var)
            if abs(val) > 1e-6:  # Only include non-zero flows
                solution[f"flujo_{u}_{v}"] = val
    
    return is_optimal, obj_value, solution


def print_solution(is_optimal: bool, obj_value: float, solution: Dict[str, float]) -> None:
    """
    Print the maximum flow solution in a readable format.
    
    Args:
        is_optimal: Whether the solution is optimal
        obj_value: The objective function value (maximum flow)
        solution: Dictionary containing flow values for each edge
    """
    print("\n" + "="*70)
    print("MAXIMUM FLOW SOLUTION")
    print("="*70)
    
    status = "OPTIMAL" if is_optimal else "FEASIBLE"
    print(f"Status: {status}")
    print(f"\nMaximum Flow Value: {obj_value} units\n")
    
    if solution:
        print("Flow distribution by channels:")
        for channel_name in sorted(solution.keys()):
            flow_value = solution[channel_name]
            print(f"  {channel_name.replace('flujo_', '')} ---> {flow_value:.6f} units")
    else:
        print("No flow through any channels.")
    
    print("="*70 + "\n")


def main_maxflow(input_file: str) -> None:
    """
    Main function to orchestrate the maximum flow problem solving process.
    
    Args:
        input_file: Path to the input file
    """
    print(f"Reading input from: {input_file}")
    data = read_input(input_file)
    
    print(f"Network: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
    print(f"Source: {data['source']}, Sink: {data['sink']}\n")
    
    print("Creating optimization model...")
    model, variables = create_model(data)
    
    print("Solving model...")
    is_optimal, obj_value, solution = solve_model(model, variables)
    
    print_solution(is_optimal, obj_value, solution)


def main_vrptw(input_file: str) -> None:
    """
    Main function to solve Vehicle Routing Problem with Time Windows.
    
    Args:
        input_file: Path to the input file
    """
    print(f"Loading: {input_file}")
    pacientes, combis, capacidades, tiempos_cita, tolerancia, distancias = leer_datos_vrp(input_file)
    print(f"Patients: {pacientes}")
    print(f"Vehicles: {combis}")
    print(f"Tolerance (minutes): {tolerancia}\n")
    
    resolver_vrp_ventanas(pacientes, combis, capacidades, tiempos_cita, tolerancia, distancias)
    

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <problem_type> <input_file>")
        print("\nProblem types:")
        print("  maxflow   - Maximum Flow Problem")
        print("  vrptw     - Vehicle Routing Problem with Time Windows")
        print("\nExamples:")
        print("  python main.py maxflow multi_st.txt")
        print("  python main.py vrptw input_combis_pacientes.txt")
        sys.exit(1)
    
    problem_type = sys.argv[1].lower()
    input_file = sys.argv[2]
    
    if problem_type == "maxflow":
        main_maxflow(input_file)
    elif problem_type == "vrptw":
        main_vrptw(input_file)
    else:
        print(f"Error: Unknown problem type '{problem_type}'")
        print("Supported types: maxflow, vrptw")
        sys.exit(1)
