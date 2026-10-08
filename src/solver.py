import numpy as np
from ortools.sat.python import cp_model

from src.instance import Instance
from src.route import Route
from src.solution import Solution
from src.timer import timer

class Solver:
    ''' 
    State-of-the-Art Exact Solver for the DARP using Constraint Programming (Google OR-Tools CP-SAT).
    Features:
        - Presence Variables (y)
        - Global Circuit Constraint (AddCircuit) for implicit flow conservation and sub-tour elimination
        - Symmetry Breaking (Ordered vehicles)
        - Solution Hinting (Hot-start from heuristic)
    '''
    
    def __init__(
        self, 
        instance: Instance, 
        matrices: list[np.ndarray], 
        initial_solution: Solution,
        time_limit: int = 120,
    ):
        self.instance = instance 
        self.matrices = matrices 
        self.time_limit = time_limit
        self.initial_solution = initial_solution
        
        self.model = cp_model.CpModel()
        
    @timer
    def run(self) -> tuple[float, Solution]:
        nodes = self.instance.nodes
        req_num = self.instance.request_number
        
        n_nodes = 1 + (2 * req_num) 
        num_veh = len(self.matrices)
        Q = self.instance.vehicle_capacity
        max_vt = self.instance.max_vehicle_time
        max_rt = self.instance.max_request_time

        # 1. DECISION VARIABLES
        
        # x[i, j, v]: 1 if vehicle v travels from node i to node j, 0 otherwise
        x: dict[tuple[int, int, int], cp_model.CpBoolVar] = {}
        for v in range(num_veh):
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i != j and self.matrices[v][i, j] >= 0:
                        x[i, j, v] = self.model.NewBoolVar(f'x_{i}_{j}_{v}')

        # y[i, v]: 1 if vehicle v visits node i
        y = {}
        for i in range(1, n_nodes):
            for v in range(num_veh):
                y[i, v] = self.model.NewBoolVar(f'y_{i}_{v}')

        # veh_used[v]: 1 if vehicle v leaves the depot
        veh_used = {v: self.model.NewBoolVar(f'veh_used_{v}') for v in range(num_veh)}

        # Continuous constraints representation (Time and Load)
        a = {i: self.model.NewIntVar(nodes[i].ready_time, nodes[i].due_time, f'a_{i}') for i in range(1, n_nodes)}
        start = {v: self.model.NewIntVar(nodes[0].ready_time, nodes[0].due_time, f'start_{v}') for v in range(num_veh)}
        end = {v: self.model.NewIntVar(nodes[0].ready_time, nodes[0].due_time, f'end_{v}') for v in range(num_veh)}
        l = {i: self.model.NewIntVar(max(0, nodes[i].demand), min(Q, Q + nodes[i].demand), f'l_{i}') for i in range(1, n_nodes)}

        # 2. CONSTRAINTS

        # A. Presence and Precedence
        for i in range(1, req_num + 1):
            # Each pickup must be assigned to exactly one vehicle
            self.model.AddExactlyOne(y[i, v] for v in range(num_veh))
            
            # Pickup and Delivery must occur on the same vehicle
            d = i + req_num
            for v in range(num_veh):
                self.model.Add(y[i, v] == y[d, v])

        # Link veh_used to vehicle departures
        for v in range(num_veh):
            saidas_deposito = [x[0, j, v] for j in range(1, n_nodes) if (0, j, v) in x]
            if saidas_deposito:
                self.model.AddMaxEquality(veh_used[v], saidas_deposito)
            else:
                self.model.Add(veh_used[v] == 0)

        # B. Global Circuit Optimization (Replaces all flow conservation and sub-tour loops)
        for v in range(num_veh):
            arcs = []
            
            # Depot self-loop: If vehicle is NOT used, it loops at the depot
            arcs.append((0, 0, veh_used[v].Not()))

            for i in range(1, n_nodes):
                # Node self-loop: If vehicle v does NOT visit node i, it loops at node i
                arcs.append((i, i, y[i, v].Not()))
                
                # Active edges
                if (0, i, v) in x:
                    arcs.append((0, i, x[0, i, v]))
                if (i, 0, v) in x:
                    arcs.append((i, 0, x[i, 0, v]))
                    
                for j in range(1, n_nodes):
                    if i != j and (i, j, v) in x:
                        arcs.append((i, j, x[i, j, v]))

            # The AddCircuit constraint enforces exactly one valid closed tour
            self.model.AddCircuit(arcs)

        # C. Symmetry Breaking
        # Forces identical vehicles to be used sequentially. Vehicle v+1 is only used if Vehicle v is used.
        for v in range(num_veh - 1):
            self.model.AddImplication(veh_used[v + 1], veh_used[v])

        # D. Temporal and Load Transitions (Intelligent Big-M Substitution)
        for (i, j, v) in x:
            dist = self.instance.distances[i, j]
            s_i = nodes[i].service_time if i > 0 else 0
            dem_j = nodes[j].demand if j > 0 else 0
            
            if i == 0:
                self.model.Add(a[j] >= start[v] + dist).OnlyEnforceIf(x[i, j, v])
                self.model.Add(l[j] == dem_j).OnlyEnforceIf(x[i, j, v])
            elif j == 0:
                self.model.Add(end[v] >= a[i] + s_i + dist).OnlyEnforceIf(x[i, j, v])
            else:
                self.model.Add(a[j] >= a[i] + s_i + dist).OnlyEnforceIf(x[i, j, v])
                self.model.Add(l[j] == l[i] + dem_j).OnlyEnforceIf(x[i, j, v])

        # E. Ride Time and Total Duration Constraints
        for i in range(1, req_num + 1):
            d = i + req_num
            s_p = nodes[i].service_time
            dist_pd = self.instance.distances[i, d]
            
            # The delivery time must respect the physical distance from the pickup
            self.model.Add(a[d] >= a[i] + s_p + int(dist_pd))
            
            # Maximum ride time limit
            self.model.Add(a[d] - a[i] - s_p <= int(max_rt))

        for v in range(num_veh):
            # Maximum vehicle route duration limit
            self.model.Add(end[v] - start[v] <= int(max_vt))

        # 3. OBJECTIVE FUNCTION
        
        # Minimize total travel distance
        self.model.Minimize(sum(self.instance.distances[i, j] * x[i, j, v] for (i, j, v) in x))

        # 4. SOLUTION HINTING (Hot-Start)
        for v, route in enumerate(self.initial_solution.routes):
            if v >= num_veh: break
            
            self.model.AddHint(veh_used[v], 1)
            route_nodes = [0] + route.nodes + [0]
            
            for node_id in route.nodes:
                self.model.AddHint(y[node_id, v], 1)
            
            for k in range(len(route_nodes) - 1):
                n_from = route_nodes[k]
                n_to = route_nodes[k+1]
                if (n_from, n_to, v) in x:
                    self.model.AddHint(x[n_from, n_to, v], 1)

        # 5. SOLVER CONFIGURATION & EXECUTION
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit
        solver.parameters.log_search_progress = False 
        
        status = solver.Solve(self.model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise Exception('It was not possible to find a solution (UNSATISFIABLE or Timeout).')

        # Decoding the exact solution from the solver variables
        
        routes_sol: list[Route] = []
        for v in range(num_veh):
            successors = {}
            for (i, j, veh) in x:
                if veh == v and solver.BooleanValue(x[i, j, v]):
                    successors[i] = j
                    
            if 0 not in successors:
                continue
                
            curr = successors[0]
            route_nodes_sol = []
            while curr != 0:
                route_nodes_sol.append(curr)
                curr = successors.get(curr, 0)
                
            if route_nodes_sol:
                routes_sol.append(Route(self.instance, route_nodes_sol))

        return Solution(self.instance, routes_sol)