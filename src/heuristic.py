from src.instance import Instance
from src.route import Route
from src.timer import timer
from src.solution import Solution

class Heuristic:
    ''' Parallel Regret-2 construction heuristic for the DARP with Insertion Caching '''

    def __init__(self, instance: Instance):
        self.instance = instance

    @timer
    def run(self) -> tuple[float, Solution]:
        nodes = self.instance.nodes
        request_n = self.instance.request_number
        vehicle_n = self.instance.vehicle_number

        routes = [Route(self.instance, []) for _ in range(vehicle_n)]
        unserved = set((nodes[i], nodes[i + request_n]) for i in range(1, request_n + 1))
        
        cache = {}

        for request in unserved:
            for route_index, route in enumerate(routes):
                if new_route := route.best_insertion(request):
                    cache[(request, route_index)] = (new_route.cost - route.cost, new_route)
                else:
                    cache[(request, route_index)] = (float('inf'), None)
        
        while unserved:
            candidates = []

            for request in unserved:
                best_insertion = None
                second_best_cost = float('inf')

                for route_index in range(len(routes)):
                    increase, new_route = cache[(request, route_index)]
                    
                    if increase == float('inf'):
                        continue
                        
                    if best_insertion is None or increase < best_insertion[0]:
                        if best_insertion is not None:
                            second_best_cost = best_insertion[0]
                        best_insertion = (increase, route_index, new_route)
                        
                    elif increase < second_best_cost:
                        second_best_cost = increase

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

            for remaining_request in unserved:
                if updated_route := new_route.best_insertion(remaining_request):
                    cache[(remaining_request, route_index)] = (updated_route.cost - new_route.cost, updated_route)
                else:
                    cache[(remaining_request, route_index)] = (float('inf'), None)

        return Solution(self.instance, [r for r in routes if len(r) > 0])