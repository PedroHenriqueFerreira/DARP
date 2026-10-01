import numpy as np

class Node:
    ''' Class representing a customer in the DARP problem '''
    
    def __init__(
        self, 
        id: int,
        x: float, 
        y: float,
        service_time: int,
        demand: int,
        ready_time: int, 
        due_time: int, 
        precision: int,
    ):
        self.id = int(id)
        self.pos = np.array([float(x), float(y)])
        self.service_time = int(round(service_time * 10 ** precision))
        self.demand = int(demand)
        self.ready_time = int(round(ready_time * 10 ** precision))
        self.due_time = int(round(due_time * 10 ** precision))
        
    @property
    def x(self):
        return self.pos[0]
    
    @property
    def y(self):
        return self.pos[1]
        
    def __repr__(self):
        return f'Node({self.id})'