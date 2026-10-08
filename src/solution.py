from src.instance import Instance
from src.route import Route

class Solution:
    ''' Class representing a DARP solution '''
    
    def __init__(self, instance: Instance, routes: list[Route]):
        self.instance = instance
        
        self.routes = routes
        self._cost: float | None = None
    
    def validate(self) -> None:
        all_nodes = list(range(1, self.instance.request_number * 2 + 1))
        route_nodes = [id for route in self.routes for id in route.nodes]
        
        if any(not route.feasible for route in self.routes):
            route = next(route for route in self.routes if not route.feasible)
            
            raise Exception(f'Infeable route found: {route}')
        
        if len(set(route_nodes)) != len(route_nodes):
            raise Exception('Duplicate nodes found in routes')
        
        if sorted(route_nodes) != all_nodes:
            raise Exception('Nodes in routes do not match all nodes')
    
    @property
    def cost(self) -> float:
        if self._cost is None:
            self._cost = sum(r.cost for r in self.routes) / (10 ** self.instance.precision)
            
        return self._cost
        
    def __repr__(self):
        return f'Solution({self.routes})'    
