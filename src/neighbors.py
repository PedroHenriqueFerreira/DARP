import numpy as np

from src.instance import Instance
from src.solution import Solution
from src.timer import timer

class Neighbors:
    ''' Neighborhood focused on the indivisibility of requests for the DARP '''
    
    def __init__(self, instance: Instance, k: int, solution: Solution):
        self.instance = instance
        self.k = k
        self.solution = solution
    
    def is_edge_feasible(self, i: int, j: int) -> bool:
        node_i = self.instance.nodes[i]
        node_j = self.instance.nodes[j]
        dist = self.instance.distances[i, j]
        
        earliest = node_i.ready_time + node_i.service_time + dist
        return earliest <= node_j.due_time

    def requests_distance(self, r1: int, r2: int) -> float:
        ''' Calculate the distance between two requests '''
        
        d1 = r1 + self.instance.request_number
        d2 = r2 + self.instance.request_number
        
        return self.instance.distances[r1, r2] + self.instance.distances[d1, d2]

    @timer
    def run(self) -> tuple[float, list[np.ndarray]]:
        ''' Generate sparse matrices focused on clusters of compatible requests '''
        
        matrices: list[np.ndarray] = []
        request_n = self.instance.request_number
        
        for route in self.solution.routes:
            matrix = np.full(
                (len(self.instance.nodes), len(self.instance.nodes)), -1, dtype=np.long
            )
            
            for i in range(len(self.instance.nodes)):
                matrix[i, i] = 0
            
            # Depot always connects to all pickups, and deliveries always return to the depot
            for i in range(1, request_n + 1):
                if self.is_edge_feasible(0, i): 
                    matrix[0, i] = self.instance.distances[0, i]
                    
                d = i + request_n
                
                if self.is_edge_feasible(d, 0): 
                    matrix[d, 0] = self.instance.distances[d, 0]

            # Guarantee the internal edges of the current routes that the constructive heuristic found
            if len(route) > 0:
                matrix[0, route[0].id] = self.instance.distances[0, route[0].id]
                matrix[route[-1].id, 0] = self.instance.distances[route[-1].id, 0]
            for i in range(len(route) - 1):
                matrix[route[i].id, route[i + 1].id] = self.instance.distances[route[i].id, route[i + 1].id]
            
            # Extract the requests already present in the route to expand the neighborhood from them
            active_reqs = set()
            for node in route:
                if 1 <= node.id <= request_n: 
                    active_reqs.add(node.id)
                elif node.id > request_n: 
                    active_reqs.add(node.id - request_n)
            
            # If the route is empty, we initialize the cluster with the first K global requests
            if not active_reqs:
                active_reqs = set(range(1, min(self.k + 1, request_n + 1)))
            
            # Expand the cluster: For each active request, find the K closest requests based on the defined distance metric
            expanded_reqs = set(active_reqs)
            for active_req in active_reqs:
                distances = [
                    (self.requests_distance(active_req, other_req), other_req) 
                    for other_req in range(1, request_n + 1) if other_req != active_req
                ]
                
                distances.sort()
                
                for _, other in distances[:self.k]:
                    expanded_reqs.add(other)
                    
            # Activate edges ONLY between the nodes (p, d) of the expanded request cluster
            valid_nodes = []
            for expanded_req in expanded_reqs:
                valid_nodes.extend([expanded_req, expanded_req + request_n])
                
            # Guarantee the primary precedence of each request (pickup -> delivery)
            for r in expanded_reqs:
                d = r + request_n
                if self.is_edge_feasible(r, d):
                    matrix[r, d] = self.instance.distances[r, d]

            # Permute edges between all validated nodes in the temporal cluster
            for i in valid_nodes:
                for j in valid_nodes:
                    if i == j: 
                        continue
                    
                    # Prevent the traveling from the delivery back to its own pickup
                    if j == i - request_n: 
                        continue
                    
                    if self.is_edge_feasible(i, j):
                        matrix[i, j] = self.instance.distances[i, j]
            
            matrices.append(matrix)
            
        return matrices