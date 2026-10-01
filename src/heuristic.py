from src.instance import Instance
from src.node import Node
from src.route import Route
from src.utils import timer
from src.solution import Solution

class Heuristic:
    '''
    Parallel Regret-2 construction heuristic for the DARP.

    At each iteration:
        1. Find all feasible insertions for every unserved request.
        2. For each request, keep its two best insertions.
        3. Calculate its regret:
               regret = second_best_cost - best_cost
        4. Insert the request with the largest regret.
    '''

    def __init__(self, instance: Instance):
        self.instance = instance

    @timer
    def run(self) -> tuple[float, Solution]:
        nodes = self.instance.nodes
        request_n = self.instance.request_number
        vehicle_n = self.instance.vehicle_number

        routes = [Route(self.instance, []) for _ in range(vehicle_n)]

        unserved = set((nodes[i], nodes[i + request_n]) for i in range(1, request_n + 1))
        
        while unserved:
            candidates = []

            for request in unserved:
                best_insertion = None
                second_best_cost = float('inf')

                for route_index, route in enumerate(routes):
                    if new_route := route.best_insertion(request):
                        increase = new_route.cost - route.cost
                        
                        if best_insertion is None or increase < best_insertion[0]:
                            if best_insertion is not None:
                                second_best_cost = best_insertion[0]
                            best_insertion = (increase, route_index, new_route)
                            
                        elif increase < second_best_cost:
                            second_best_cost = increase

                # Se não encontrou nenhuma inserção viável
                if best_insertion is None:
                    continue

                best_cost, best_route_index, best_route = best_insertion
                regret = second_best_cost - best_cost

                candidates.append((regret, best_cost, best_route_index, request, best_route))
                
            if not candidates:
                raise ValueError(f'Infeasible request remains: {next(iter(unserved))}')

            regret, _, route_index, request, new_route = min(candidates, key=lambda x: (-x[0], x[1]))

            routes[route_index] = new_route

            unserved.remove(request)

        return Solution(self.instance, [r for r in routes if len(r) > 0])