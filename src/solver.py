import numpy as np

from ortools.sat.python import cp_model

from src.instance import Instance
from src.route import Route
from src.solution import Solution
from src.timer import timer

class Solver:
    ''' Solver for the DARP using Constraint Programming (Google OR-Tools CP-SAT) '''
    
    def __init__(
        self, 
        instance: Instance, 
        matrices: list[np.ndarray], 
        time_limit: int = 300
    ):
        self.instance = instance 
        self.matrices = matrices 
        self.time_limit = time_limit
        
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

        # 1. Decision variables
        
        # x[i, j, v]: 1 if vehicle v travels from node i to node j, 0 otherwise
        x: dict[tuple[int, int, int], cp_model.CpBoolVar] = {}
        for v in range(num_veh):
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i != j and self.matrices[v][i, j] >= 0:
                        x[i, j, v] = self.model.NewBoolVar(f'x_{i}_{j}_{v}')

        # a[i]: integer variable representing the arrival time at node i
        a = {
            i: self.model.NewIntVar(nodes[i].ready_time, nodes[i].due_time, f'a_{i}') 
            for i in range(1, n_nodes)
        }
        
        # start[v]: integer variable representing the start time of vehicle v at the depot
        start = {
            v: self.model.NewIntVar(nodes[0].ready_time, nodes[0].due_time, f'start_{v}') 
            for v in range(num_veh)
        }
        # end[v]: integer variable representing the end time of vehicle v at the depot
        end = {
            v: self.model.NewIntVar(nodes[0].ready_time, nodes[0].due_time, f'end_{v}') 
            for v in range(num_veh)
        }

        # l[i]: integer variable for the load of the vehicle right after visiting node i
        l = {
            i: self.model.NewIntVar(
                max(0, nodes[i].demand),
                min(Q, Q + nodes[i].demand), 
                f'l_{i}'
            ) 
            for i in range(1, n_nodes)
        }

        # 2. Constraints

        # A. Visitation and Flow Constraints
        
        for i in range(1, req_num + 1):
            # Each pickup request must be visited by exactly one vehicle
            self.model.AddExactlyOne(
                x[i, j, v] for j in range(n_nodes) for v in range(num_veh) if (i, j, v) in x
            )

        for v in range(num_veh):
            # A vehicle can leave the depot at most once
            self.model.Add(sum(x[0, j, v] for j in range(1, n_nodes) if (0, j, v) in x) <= 1)
            
            # Conservation of flow at the depot: what leaves must return
            self.model.Add(
                sum(x[0, j, v] for j in range(1, n_nodes) if (0, j, v) in x) == \
                sum(x[i, 0, v] for i in range(1, n_nodes) if (i, 0, v) in x)
            )

            # Conservation of flow: everything that enters a node must leave
            for i in range(1, n_nodes):
                self.model.Add(
                    sum(x[j, i, v] for j in range(n_nodes) if (j, i, v) in x) == \
                    sum(x[i, j, v] for j in range(n_nodes) if (i, j, v) in x)
                )

            # Precedence (pickup and delivery in the same vehicle)
            for i in range(1, req_num + 1):
                d = i + req_num
                
                self.model.Add(
                    sum(x[i, j, v] for j in range(n_nodes) if (i, j, v) in x) == \
                    sum(x[d, j, v] for j in range(n_nodes) if (d, j, v) in x)
                )

        # B. Temporal and Load Transitions (Intelligent Big-M Substitution)
        
        for (i, j, v) in x:
            dist = self.instance.distances[i, j]
            s_i = nodes[i].service_time if i > 0 else 0
            dem_j = nodes[j].demand if j > 0 else 0

            # Conditional Logic: `.OnlyEnforceIf` applies the constraints ONLY if x[i,j,v] is true (1)
            
            if i == 0:
                self.model.Add(a[j] >= start[v] + dist).OnlyEnforceIf(x[i, j, v])
                self.model.Add(l[j] == dem_j).OnlyEnforceIf(x[i, j, v])
            elif j == 0:
                self.model.Add(end[v] >= a[i] + s_i + dist).OnlyEnforceIf(x[i, j, v])
            else:
                self.model.Add(a[j] >= a[i] + s_i + dist).OnlyEnforceIf(x[i, j, v])
                self.model.Add(l[j] == l[i] + dem_j).OnlyEnforceIf(x[i, j, v])

        # C. Ride Time and Total Duration Constraints
        
        for i in range(1, req_num + 1):
            d = i + req_num
            s_p = nodes[i].service_time
            dist_pd = self.instance.distances[i, d]
            
            # The delivery time must respect the physical distance from the pickup
            self.model.Add(a[d] >= a[i] + s_p + int(dist_pd))
            
            # The ride time for each request must not exceed the maximum allowed ride time
            self.model.Add(a[d] - a[i] - s_p <= int(max_rt))

        for v in range(num_veh):
            # The total time a vehicle operates must not exceed the maximum vehicle time
            self.model.Add(end[v] - start[v] <= int(max_vt))

        # 3. Objective Function
        
        # Minimize the total distance traveled by all vehicles
        self.model.Minimize(
            sum(self.instance.distances[i, j] * x[i, j, v] for (i, j, v) in x)
        )

        # 4. Solve the Model
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit
        solver.parameters.log_search_progress = False
        
        status = solver.Solve(self.model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise Exception(
                'Não foi possível encontrar uma solução (UNSATISFIABLE ou Timeout).'
            )

        # Decoding the routes based on the extraction of literal instances
        
        routes: list[Route] = []
        
        for v in range(num_veh):
            successors = {}
            for (i, j, veh) in x:
                if veh == v and solver.BooleanValue(x[i, j, v]):
                    successors[i] = j
                    
            if 0 not in successors:
                continue
                
            curr = successors[0]
            route_nodes = []
            
            while curr != 0:
                route_nodes.append(curr)
                curr = successors.get(curr, 0)
                
            if route_nodes:
                routes.append(Route(self.instance, route_nodes))

        return Solution(self.instance, routes)