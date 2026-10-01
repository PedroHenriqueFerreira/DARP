from os import system, remove
from math import log2, ceil

import numpy as np

from src.instance import Instance
from src.route import Route
from src.solution import Solution
from src.utils import timer

class Solver:
    """ Class for the DARP exact solver using PB / SAT encoding """
    
    def __init__(self, instance: Instance, matrices: list[np.ndarray]):
        self.instance = instance 
        self.matrices = matrices 
        
        self.counter = 1
        
        self.mapping: dict[str, int] = {} 
        self.mapping_inv: dict[int, str] = {} 
        
        self.constraints: list[str] = [] 
        self.objectives: list[str] = [] 
    
    def get(self, variable: str):
        if variable not in self.mapping:
            self.mapping[variable] = self.counter
            self.mapping_inv[self.counter] = variable
            self.counter += 1
        return self.mapping[variable]

    def encode_literal(self, factor: int, literal: int):
        return f'{factor} {["~", ""][literal >= 0]}x{abs(literal)}'

    def encode_clause(self, factors: list[int], clause: list[int]):
        return ' '.join(self.encode_literal(f, l) for f, l in zip(factors, clause))

    def add_constraint(self, factors: list[int], clause: list[int], operator: str, value: int):
        if factors is None:
            factors = [1] * len(clause)
        self.constraints.append(f'{self.encode_clause(factors, clause)} {operator} {value} ;')

    def add_constraint_eq(self, factors: list[int], clause: list[int], value: int):
        self.add_constraint(factors, clause, '=', value)
        
    def add_constraint_leq(self, factors: list[int], clause: list[int], value: int):
        if factors is None:
            factors = [1] * len(clause)
        
        self.add_constraint_geq([-f for f in factors], clause, -value)
        
    def add_constraint_geq(self, factors: list[int], clause: list[int], value: int):
        self.add_constraint(factors, clause, '>=', value)

    def add_objective(self, factor: int, literal: int):
        self.objectives.append(self.encode_literal(factor, literal))

    def create_objective_string(self):
        return ' '.join(self.objectives)

    def create_constraint_string(self):
        return '\n'.join(self.constraints)

    def encode(self):
        string = f'* #variable= {self.counter - 1} #constraint= {len(self.constraints)}\n'
        string += f'min: {self.create_objective_string()}  ; \n'
        string += f'{self.create_constraint_string()} \n'
        return string
    
    def decode(self, output: list[str]):
        values = []

        for line in output:
            if line.startswith('s UNSATISFIABLE'):
                raise Exception('Cannot find a solution')
            
            if line.startswith('o'): 
                continue
            
            if line.startswith('v'):
                values += [int(v) for v in line[2:].replace('x', '').replace('c', '').split()] 
            
        vehicles: list[dict[int, int]] = [{} for _ in range(len(self.matrices))]
                                 
        for item in values:
            if item not in self.mapping_inv:
                continue
            
            edge = self.mapping_inv[item]
            
            if not edge.startswith('w_'):
                continue
            
            parts = edge.split('_')
            i, j, v = map(int, parts[1:])
            vehicles[v][i] = j
        
        routes: list[Route] = []
        
        for vehicle_dict in vehicles:
            if not vehicle_dict:
                continue
                
            curr = vehicle_dict.get(0, 0)
            route_nodes = []
            
            while curr != 0:
                route_nodes.append(curr)
                curr = vehicle_dict.get(curr, 0)
            
            if route_nodes:
                routes.append(Route(self.instance, route_nodes))
            
        return Solution(self.instance, routes)
    
    def solve(self):
        with open('input.txt', 'w+') as input_file:
            input_file.write(self.encode())
        
        system(f'./clasp input.txt > output.txt --time-limit={100}')
        
        with open('output.txt', 'r') as output_file:
            routes = self.decode(output_file.readlines())
    
        remove('./input.txt')
        remove('./output.txt')

        return routes 
        
    def load_model(self):
        nodes = self.instance.nodes
        req_num = self.instance.request_number
        
        # Filtro de Sanidade: Isola o depósito de retorno duplicado (Nó 33) 
        # garantindo que operamos somente do nó 0 ao 32.
        n_nodes = 1 + (2 * req_num) 
        
        num_veh = len(self.matrices)
        Q = self.instance.vehicle_capacity
        
        def to_int(val):
            return int(round(val))
            
        max_time = to_int(nodes[0].due_time)
        a_bits = ceil(log2(max_time)) + 1 if max_time > 0 else 1
        l_bits = ceil(log2(Q)) + 1 if Q > 0 else 1
        
        a_powers = [2 ** b for b in range(a_bits)]
        a_neg = [-item for item in a_powers]
        
        l_powers = [2 ** b for b in range(l_bits)]
        l_neg = [-item for item in l_powers]
        
        # Big-M estritamente largo para anular com segurança restrições desligadas
        BIG_M = max_time + 1000000 
        
        # ---------------------------------------------------------
        # 1. Restrições Básicas de Roteamento (Flow)
        # ---------------------------------------------------------
        
        for i in range(1, n_nodes):
            w_out = [self.get(f'w_{i}_{j}_{v}') for v in range(num_veh) for j in range(n_nodes) if i != j]
            self.add_constraint_eq(None, w_out, 1)

        for v in range(num_veh):
            w_0_out = [self.get(f'w_{0}_{j}_{v}') for j in range(1, n_nodes)]
            self.add_constraint_leq(None, w_0_out, 1)
            
            w_in_0 = [self.get(f'w_{i}_{0}_{v}') for i in range(1, n_nodes)]
            self.add_constraint_leq(None, w_in_0, 1)
            
            for i in range(1, n_nodes):
                w_in = [self.get(f'w_{j}_{i}_{v}') for j in range(n_nodes) if i != j]
                w_out = [self.get(f'w_{i}_{j}_{v}') for j in range(n_nodes) if i != j]
                t_i_v = self.get(f't_{i}_{v}')
                
                self.add_constraint_eq([1]*len(w_in) + [-1], w_in + [t_i_v], 0)
                self.add_constraint_eq([1]*len(w_out) + [-1], w_out + [t_i_v], 0)

        # ---------------------------------------------------------
        # 2. Precedência de Passageiros (Pickup vs Delivery)
        # ---------------------------------------------------------
        
        for i in range(1, req_num + 1):
            d = i + req_num
            for v in range(num_veh):
                t_p_v = self.get(f't_{i}_{v}')
                t_d_v = self.get(f't_{d}_{v}')
                self.add_constraint_eq([1, -1], [t_p_v, t_d_v], 0)
                
        # ---------------------------------------------------------
        # 3. Janelas de Tempo Iniciais
        # ---------------------------------------------------------
        
        for i in range(1, n_nodes):
            a_i = [self.get(f'a_{i}_{b}') for b in range(a_bits)]
            self.add_constraint_geq(a_powers, a_i, to_int(nodes[i].ready_time))
            self.add_constraint_leq(a_powers, a_i, to_int(nodes[i].due_time))

        for v in range(num_veh):
            start_v = [self.get(f'start_{v}_{b}') for b in range(a_bits)]
            end_v = [self.get(f'end_{v}_{b}') for b in range(a_bits)]
            
            self.add_constraint_geq(a_powers, start_v, to_int(nodes[0].ready_time))
            self.add_constraint_leq(a_powers, start_v, to_int(nodes[0].due_time))
            self.add_constraint_geq(a_powers, end_v, to_int(nodes[0].ready_time))
            self.add_constraint_leq(a_powers, end_v, to_int(nodes[0].due_time))

        # ---------------------------------------------------------
        # 4. Continuidade do Tempo e Deslocamento Temporal 
        # ---------------------------------------------------------
        
        for v in range(num_veh):
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i == j: continue
                    
                    if self.matrices[v][i, j] < 0:
                        w_i_j_v = self.get(f'w_{i}_{j}_{v}')
                        self.add_constraint_eq(None, [w_i_j_v], 0)
                        continue
                        
                    w_i_j_v = self.get(f'w_{i}_{j}_{v}')
                    dist_ij = to_int(self.instance.distances[i, j])
                    s_i = to_int(nodes[i].service_time)
                    
                    if i == 0: 
                        a_j = [self.get(f'a_{j}_{b}') for b in range(a_bits)]
                        start_v = [self.get(f'start_{v}_{b}') for b in range(a_bits)]
                        # Big-M Corrigido: a_j - start_v - M * w >= s_0 + dist - M
                        self.add_constraint_geq(a_powers + a_neg + [-BIG_M], a_j + start_v + [w_i_j_v], s_i + dist_ij - BIG_M)
                        
                    elif j == 0: 
                        end_v = [self.get(f'end_{v}_{b}') for b in range(a_bits)]
                        a_i = [self.get(f'a_{i}_{b}') for b in range(a_bits)]
                        # Big-M Corrigido: end_v - a_i - M * w >= s_i + dist - M
                        self.add_constraint_geq(a_powers + a_neg + [-BIG_M], end_v + a_i + [w_i_j_v], s_i + dist_ij - BIG_M)
                        
                    else: 
                        a_j = [self.get(f'a_{j}_{b}') for b in range(a_bits)]
                        a_i = [self.get(f'a_{i}_{b}') for b in range(a_bits)]
                        # Big-M Corrigido: a_j - a_i - M * w >= s_i + dist - M
                        self.add_constraint_geq(a_powers + a_neg + [-BIG_M], a_j + a_i + [w_i_j_v], s_i + dist_ij - BIG_M)

        # ---------------------------------------------------------
        # 5. DARP: Ride Time Máximo e Fluxo de Viagem
        # ---------------------------------------------------------
        
        max_rt = to_int(self.instance.max_request_time)
        for i in range(1, req_num + 1):
            d = i + req_num
            a_p = [self.get(f'a_{i}_{b}') for b in range(a_bits)]
            a_d = [self.get(f'a_{d}_{b}') for b in range(a_bits)]
            s_p = to_int(nodes[i].service_time)
            dist_pd = to_int(self.instance.distances[i, d])
            
            # Chegada D > Chegada P 
            self.add_constraint_geq(a_powers + a_neg, a_d + a_p, s_p + dist_pd)
            # Limite do Ride Time
            self.add_constraint_geq(a_powers + a_neg, a_p + a_d, -max_rt - s_p)

        # ---------------------------------------------------------
        # 6. DARP: Duração Máxima da Rota do Veículo
        # ---------------------------------------------------------
        
        max_vt = to_int(self.instance.max_vehicle_time)
        for v in range(num_veh):
            start_v = [self.get(f'start_{v}_{b}') for b in range(a_bits)]
            end_v = [self.get(f'end_{v}_{b}') for b in range(a_bits)]
            self.add_constraint_geq(a_powers + a_neg, start_v + end_v, -max_vt)

        # ---------------------------------------------------------
        # 7. Capacidade Contínua (Flutuante de +1/-1)
        # ---------------------------------------------------------
        
        for i in range(1, n_nodes):
            l_i = [self.get(f'l_{i}_{b}') for b in range(l_bits)]
            dem_i = int(nodes[i].demand)
            self.add_constraint_geq(l_powers, l_i, max(0, dem_i))
            self.add_constraint_leq(l_powers, l_i, min(Q, Q + dem_i))
            
        for v in range(num_veh):
            for i in range(n_nodes):
                for j in range(1, n_nodes):
                    if i == j or self.matrices[v][i, j] < 0: continue
                    
                    w_i_j_v = self.get(f'w_{i}_{j}_{v}')
                    l_j = [self.get(f'l_{j}_{b}') for b in range(l_bits)]
                    dem_j = int(nodes[j].demand)

                    if i == 0:
                        self.add_constraint_geq(l_powers + [-Q], l_j + [w_i_j_v], dem_j - Q)
                        self.add_constraint_geq(l_neg + [-Q], l_j + [w_i_j_v], -dem_j - Q)
                    else:
                        l_i = [self.get(f'l_{i}_{b}') for b in range(l_bits)]
                        self.add_constraint_geq(l_powers + l_neg + [-Q], l_j + l_i + [w_i_j_v], dem_j - Q)
                        self.add_constraint_geq(l_neg + l_powers + [-Q], l_j + l_i + [w_i_j_v], -dem_j - Q)

        # ---------------------------------------------------------
        # 8. Função Objetivo
        # ---------------------------------------------------------
        
        for v in range(num_veh):
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i == j or self.matrices[v][i, j] < 0: continue
                    
                    w_i_j_v = self.get(f'w_{i}_{j}_{v}')
                    dist_ij = to_int(self.instance.distances[i, j])
                    
                    if dist_ij > 0:
                        self.add_objective(dist_ij, w_i_j_v)

    @timer
    def run(self) -> tuple[float, Solution]:
        self.load_model()
        return self.solve()