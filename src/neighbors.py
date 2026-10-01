import numpy as np
from networkx import Graph, minimum_spanning_tree

from src.instance import Instance
from src.solution import Solution
from src.utils import timer

class Neighbors:
    ''' Neighborhood focused on the indivisibility of requests for the DARP '''
    
    def __init__(self, instance: Instance, k: int, solution: Solution):
        self.instance = instance
        self.k = k
        self.solution = solution
    
    def is_edge_feasible(self, i: int, j: int) -> bool:
        ''' Verify if the edge i -> j is temporally feasible '''
        
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

            # Garantir as arestas internas das rotas atuais que a heurística construtiva encontrou
            if len(route) > 0:
                matrix[0, route[0].id] = self.instance.distances[0, route[0].id]
                matrix[route[-1].id, 0] = self.instance.distances[route[-1].id, 0]
            for i in range(len(route) - 1):
                matrix[route[i].id, route[i + 1].id] = self.instance.distances[route[i].id, route[i + 1].id]
            
            # Extrair as requisições já presentes na rota para expandir a vizinhança a partir delas
            active_reqs = set()
            for node in route:
                if 1 <= node.id <= request_n: 
                    active_reqs.add(node.id)
                elif node.id > request_n: 
                    active_reqs.add(node.id - request_n)
            
            # Se a rota estiver vazia, inicializamos o cluster com os K primeiros requests globais
            if not active_reqs:
                active_reqs = set(range(1, min(self.k + 1, request_n + 1)))
            
            # Expandir o cluster: Para cada requisição ativa, encontrar as K requisições mais próximas
            expanded_reqs = set(active_reqs)
            for r in active_reqs:
                distances = [(self.requests_distance(r, other), other) for other in range(1, request_n + 1) if other != r]
                distances.sort()
                for _, other in distances[:self.k]:
                    expanded_reqs.add(other)
                    
            # Ativar arestas APENAS entre os nós (p, d) do cluster de requisições expandidas
            valid_nodes = []
            for r in expanded_reqs:
                valid_nodes.extend([r, r + request_n])
                
            # Garantir a precedência primária irrestrita de cada request (recolha -> entrega)
            for r in expanded_reqs:
                d = r + request_n
                if self.is_edge_feasible(r, d):
                    matrix[r, d] = self.instance.distances[r, d]

            # Permutações de arestas cruzadas entre todos os nós validados no cluster temporal
            for i in valid_nodes:
                for j in valid_nodes:
                    if i == j: continue
                    # Impede a aberração lógica de viajar da entrega de volta para a própria recolha
                    if j == i - request_n: continue
                    
                    if self.is_edge_feasible(i, j):
                        matrix[i, j] = self.instance.distances[i, j]
            
            matrices.append(matrix)
            
        return matrices