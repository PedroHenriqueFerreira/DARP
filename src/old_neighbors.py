import numpy as np

from src.instance import Instance
from src.solution import Solution
from src.timer import timer

class Neighbors:
    ''' 
    Fast Union Strategy.
    Guarantees the superset of neighbors_2.py to NEVER return worse results, 
    but uses 100% Safe Physical Pruning to keep the matrix extremely sparse and the solver fast.
    '''
    
    def __init__(self, instance: Instance, k: int, solution: Solution):
        self.instance = instance
        self.k = k
        self.solution = solution
    
    def is_edge_feasible_safe(self, i: int, j: int) -> bool:
        # 0. Impossibilidades lógicas básicas
        if i == j: 
            return False
        
        req_n = self.instance.request_number
        
        # Impede viajar da entrega de volta para a sua própria recolha
        if j == i - req_n: 
            return False 
        
        node_i = self.instance.nodes[i]
        node_j = self.instance.nodes[j]
        dist = self.instance.distances[i, j]
        
        # 1. Poda Original de Janela de Tempo (A mesma do neighbors_2.py)
        earliest = node_i.ready_time + node_i.service_time + dist
        if earliest > node_j.due_time:
            return False
            
        if i == 0 or j == 0:
            return True
            
        # =========================================================
        # NOVAS PODAS FÍSICAS 100% SEGURAS (Imunes a wait-times)
        # =========================================================
        
        # 2. PODA DE CAPACIDADE ESTRITA
        # Se os dois nós são pickups, a soma das exigências não pode fisicamente exceder o veículo
        if 1 <= i <= req_n and 1 <= j <= req_n:
            if node_i.demand + node_j.demand > self.instance.vehicle_capacity:
                return False
                
        # 3. PODA FÍSICA DE RIDE TIME MINIMO
        # Se 'i' for uma recolha e 'j' NÃO for a sua entrega, o passageiro 'i' está preso no carro.
        if 1 <= i <= req_n and j != i + req_n:
            # Tempo MÍNIMO absoluto na física: conduzir para 'j' + servir 'j' + conduzir para a entrega de 'i'
            min_physical_ride = dist + node_j.service_time + self.instance.distances[j, i + req_n]
            
            # Se a própria distância geométrica direta já estoura o limite de tempo do passageiro, a aresta é impossível
            if min_physical_ride > self.instance.max_request_time:
                return False
                
        return True

    def requests_distance_original(self, r1: int, r2: int) -> float:
        ''' Distância original do neighbors_2.py '''
        d1 = r1 + self.instance.request_number
        d2 = r2 + self.instance.request_number
        return self.instance.distances[r1, r2] + self.instance.distances[d1, d2]

    def requests_distance_smart(self, r1: int, r2: int) -> float:
        ''' Distância focada no fluxo temporal '''
        request_n = self.instance.request_number
        spatial_dist = self.instance.distances[r1 + request_n, r2]
        time_diff = abs(self.instance.nodes[r1].ready_time - self.instance.nodes[r2].ready_time)
        return spatial_dist + time_diff

    @timer
    def run(self) -> tuple[float, list[np.ndarray]]:
        matrices: list[np.ndarray] = []
        request_n = self.instance.request_number
        
        for route in self.solution.routes:
            matrix = np.full(
                (len(self.instance.nodes), len(self.instance.nodes)), -1, dtype=np.int64
            )
            
            np.fill_diagonal(matrix, 0)
            
            # Ligações globais do depósito (agora protegidas pela Poda Segura)
            for i in range(1, request_n + 1):
                if self.is_edge_feasible_safe(0, i): 
                    matrix[0, i] = self.instance.distances[0, i]
                d = i + request_n
                if self.is_edge_feasible_safe(d, 0): 
                    matrix[d, 0] = self.instance.distances[d, 0]

            # Garantia das arestas da solução heurística
            if len(route) > 0:
                matrix[0, route[0].id] = self.instance.distances[0, route[0].id]
                matrix[route[-1].id, 0] = self.instance.distances[route[-1].id, 0]
            for i in range(len(route) - 1):
                matrix[route[i].id, route[i + 1].id] = self.instance.distances[route[i].id, route[i + 1].id]
            
            active_reqs = set()
            for node in route:
                if 1 <= node.id <= request_n: 
                    active_reqs.add(node.id)
                elif node.id > request_n: 
                    active_reqs.add(node.id - request_n)
            
            if not active_reqs:
                active_reqs = set(range(1, min(self.k + 1, request_n + 1)))
            
            expanded_reqs = set(active_reqs)
            
            # Union Strategy: Junta a métrica antiga com a nova
            for active_req in active_reqs:
                orig_dist = [
                    (self.requests_distance_original(active_req, other_req), other_req) 
                    for other_req in range(1, request_n + 1) if other_req != active_req
                ]
                orig_dist.sort()
                for _, other in orig_dist[:self.k]:
                    expanded_reqs.add(other)
                    
                smart_dist = [
                    (self.requests_distance_smart(active_req, other_req), other_req) 
                    for other_req in range(1, request_n + 1) if other_req != active_req
                ]
                smart_dist.sort()
                for _, other in smart_dist[:self.k]:
                    expanded_reqs.add(other)
                    
            valid_nodes = []
            for expanded_req in expanded_reqs:
                valid_nodes.extend([expanded_req, expanded_req + request_n])
                
            for r in expanded_reqs:
                d = r + request_n
                if self.is_edge_feasible_safe(r, d):
                    matrix[r, d] = self.instance.distances[r, d]

            # Permutação estritamente limpa pela Poda Segura (Acelera drasticamente o CP-SAT)
            for i in valid_nodes:
                for j in valid_nodes:
                    if self.is_edge_feasible_safe(i, j):
                        matrix[i, j] = self.instance.distances[i, j]
            
            matrices.append(matrix)
            
        return matrices