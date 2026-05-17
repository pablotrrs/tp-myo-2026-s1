"""
Maximum Flow Problem Solver
Main module for solving maximum flow problems using PySCIPOpt
"""

from pyscipopt import Model, quicksum
import sys
from typing import List, Dict, Tuple, Any

# Reserved node names for the super-source / super-sink reduction (must not appear in input).
SUPER_S = "__SRC__"
SUPER_T = "__SNK__"


def _big_m_capacity(edges: List[Tuple[str, str, float]]) -> float:
    """Finite upper bound on total feasible flow (sum of positive edge capacities)."""
    total = sum(c for _, _, c in edges if c > 0)
    return total if total > 0 else 1.0


def read_input(filename: str) -> Dict[str, Any]:
    """
    Read and parse input file for maximum flow problem.
    
    Expected format:
    - Line 1: number of nodes
    - Line 2: list of node names (space-separated)
    - Line 3: source node name(s), space-separated (one or more)
    - Line 4: sink node name(s), space-separated (one or more)
    - Line 5: number of directed edges
    - Lines 6+: each line contains "node1 node2 capacity"
    
    Args:
        filename: Path to the input file
        
    Returns:
        Dictionary containing parsed input data with keys:
            - 'nodes': list of node names
            - 'edges': list of tuples (source, dest, capacity)
            - 'sources': list of source node names
            - 'sinks': list of sink node names
    """
    data = {}
    try:
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
            
            # Parse nodes
            n_nodes = int(lines[0])
            nodes = lines[1].split()
            assert len(nodes) == n_nodes, f"Expected {n_nodes} nodes, got {len(nodes)}"
            
            assert SUPER_S not in nodes, f"Node name '{SUPER_S}' is reserved for the model"
            assert SUPER_T not in nodes, f"Node name '{SUPER_T}' is reserved for the model"
            
            # Parse sources and sinks (multiple allowed; duplicates removed, order kept)
            sources = list(dict.fromkeys(lines[2].split()))
            sinks = list(dict.fromkeys(lines[3].split()))
            
            assert sources, "At least one source node is required"
            assert sinks, "At least one sink node is required"
            for s in sources:
                assert s in nodes, f"Source '{s}' not in nodes"
            for t in sinks:
                assert t in nodes, f"Sink '{t}' not in nodes"
            
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
            data['sources'] = sources
            data['sinks'] = sinks
            
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
            - 'sources': list of source node names (supply nodes)
            - 'sinks': list of sink node names (demand nodes)
        
    Returns:
        Tuple of (Model, variables_dict) where variables_dict contains:
            - 'flow': dict of flow variables indexed by (u, v)
            - 'F': total flow variable
    """
    model = Model("Maximum_Flow_Problem")
    
    nodes = data['nodes']
    edges = data['edges']
    sources: List[str] = data['sources']
    sinks: List[str] = data['sinks']
    
    variables = {}
    M = _big_m_capacity(edges)
    
    # Create flow variables for each directed edge with capacity upper bounds
    flow_vars = {}
    for u, v, capacity in edges:
        # Standard maximum-flow formulation: each directed edge can carry
        # between 0 and its capacity in the given direction. If you need
        # the opposite direction, include the reverse edge in the input.
        flow_vars[u, v] = model.addVar(name=f"flujo_{u}_{v}", vtype="C", lb=0, ub=capacity)
    
    # Super-source -> each network source; each network sink -> super-sink
    for s in sources:
        flow_vars[SUPER_S, s] = model.addVar(name=f"flujo_{SUPER_S}_{s}", vtype="C", lb=0, ub=M)
    for t in sinks:
        flow_vars[t, SUPER_T] = model.addVar(name=f"flujo_{t}_{SUPER_T}", vtype="C", lb=0, ub=M)
    
    # Create total flow variable
    F = model.addVar(name="Flujo_Total", vtype="C", lb=0)
    
    # Set objective: maximize total flow
    model.setObjective(F, sense="maximize")
    
    extended_nodes = nodes + [SUPER_S, SUPER_T]
    
    # Add flow conservation constraints
    for node in extended_nodes:
        # Outgoing flow: sum of all edges leaving this node
        outgoing = quicksum(flow_vars[u, v] for (u, v) in flow_vars.keys() if u == node)
        
        # Incoming flow: sum of all edges pointing to this node
        incoming = quicksum(flow_vars[u, v] for (u, v) in flow_vars.keys() if v == node)
        
        if node == SUPER_S:
            model.addCons(outgoing - incoming == F, name="balance_super_source")
        elif node == SUPER_T:
            model.addCons(incoming - outgoing == F, name="balance_super_sink")
        else:
            # All original nodes (sources/sinks of the instance) are transshipment here
            model.addCons(outgoing - incoming == 0, name=f"balance_{node}")
    
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


def main(input_file: str) -> None:
    """
    Main function to orchestrate the maximum flow problem solving process.
    
    Args:
        input_file: Path to the input file
    """
    print(f"Reading input from: {input_file}")
    data = read_input(input_file)
    
    print(f"Network: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
    print(f"Sources: {', '.join(data['sources'])}")
    print(f"Sinks: {', '.join(data['sinks'])}\n")
    
    print("Creating optimization model...")
    model, variables = create_model(data)
    
    print("Solving model...")
    is_optimal, obj_value, solution = solve_model(model, variables)
    
    print_solution(is_optimal, obj_value, solution)
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_file>")
        print("\nInput file format:")
        print("  Line 1: number of nodes")
        print("  Line 2: node names (space-separated)")
        print("  Line 3: source node name(s), space-separated")
        print("  Line 4: sink node name(s), space-separated")
        print("  Line 5: number of edges")
        print("  Lines 6+: node1 node2 capacity")
        sys.exit(1)
    
    input_file = sys.argv[1]
    main(input_file)
