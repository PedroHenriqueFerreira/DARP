import numpy as np

from src.node import Node
from src.utils import number

class Instance:
    ''' Class representing a DARP instance.'''
    
    def __init__(self, file: str, precision: int = 3):
        self.file = file # Instance file
        self.precision = precision # Distance precision (number of decimal places)
        
        self.vehicle_number = 0 # Number of vehicles
        self.request_number = 0 # Number of requests
        self.max_vehicle_time = 0 # Maximum vehicle time
        self.vehicle_capacity = 0 # Each vehicle capacity
        self.max_request_time = 0 # Maximum request time
        
        self.nodes: list[Node] = [] # List of nodes
        
        self.distances: np.ndarray = None # Distance matrix
        
        self._load()
    
    def _load(self):
        ''' Load an instance from the file '''
        
        with open(self.file, 'r') as file:
            lines = file.readlines()
            
        for i, line in enumerate(lines):
            cfg = list(map(float, line.strip().split()))
            
            if i == 0: # First line contains instance configuration
                self.vehicle_number = int(cfg[0])
                self.request_number = int(cfg[1])
                self.max_vehicle_time = round(float(cfg[2]) * 10 ** self.precision)
                self.vehicle_capacity = int(cfg[3])
                self.max_request_time = round(float(cfg[4]) * 10 ** self.precision)
                
            else: # Subsequent lines contain node information
                self.nodes.append(Node(*cfg, precision=self.precision))

        self.distances = np.zeros((len(self.nodes), len(self.nodes)), dtype=np.long)  
                
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                self.distances[i][j] = self.distances[j][i] = round(
                    np.linalg.norm(self.nodes[i].pos - self.nodes[j].pos) * 10 ** self.precision
                )
    
        # Time window tightening
        for i in range(1, self.request_number + 1):
            pickup, delivery = self.nodes[i], self.nodes[i + self.request_number]

            # Earliest pickup time considering the maximum ride time constraint
            pickup.ready_time = max(
                pickup.ready_time, 
                delivery.ready_time - pickup.service_time - self.max_request_time
            )
            
            # Latest pickup time considering the delivery's due time
            pickup.due_time = min(
                pickup.due_time,
                delivery.due_time - pickup.service_time - self.distances[pickup.id, delivery.id]
            )

            # Earliest delivery time considering the pickup's ready time and service time
            delivery.ready_time = max(
                delivery.ready_time,
                pickup.ready_time + pickup.service_time + self.distances[pickup.id, delivery.id]
            )

            # Latest delivery time considering the maximum ride time constraint
            delivery.due_time = min(
                delivery.due_time,
                pickup.due_time + pickup.service_time + self.max_request_time
            )