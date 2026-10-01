from __future__ import annotations

from typing import Generator

from src.instance import Instance
from src.node import Node

class Route:
    '''Class representing a DARP vehicle route '''

    def __init__(self, instance: Instance, nodes: list[int]):
        self.instance = instance
        self.nodes = nodes

        self._cost: float | None = None
        self._feasible: bool | None = None

    def __repr__(self) -> str:
        return f'Route({self.nodes})'

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Generator[Node, None, None]:
        return (self.instance.nodes[node_id] for node_id in self.nodes)

    def __getitem__(self, index: int) -> Node:
        return self.instance.nodes[self.nodes[index]]

    @property
    def cost(self) -> float:
        ''' Total travel cost of the route '''
        if self._cost is None:
            self._cost = 0
            
            if self.nodes:
                self._cost += self.instance.distances[0, self.nodes[0]]
                for i in range(len(self.nodes) - 1):
                    self._cost += self.instance.distances[self.nodes[i], self.nodes[i + 1]]
                self._cost += self.instance.distances[self.nodes[-1], 0]
            
        return self._cost

    def set_feasible(self):
        self._feasible = True
        return self._feasible
    
    def set_unfeasible(self):
        self._feasible = False
        return self._feasible

    @property
    def feasible(self) -> bool:
        ''' Validates the route's feasibility using bound propagation for the Simple Temporal Problem (STP). This approach mathematically guarantees to find a valid schedule if one exists, distributing waiting times correctly to protect the passenger's ride_time. '''
        
        if self._feasible is not None:
            return self._feasible

        if not self.nodes:
            self._feasible = True
            return True

        nodes: list[Node] = []
        
        nodes.append(self.instance.nodes[0])  # Start at depot
        nodes.extend([self.instance.nodes[n] for n in self.nodes])
        nodes.append(self.instance.nodes[0])  # Return to depot
        
        # Capacity and precedence check
        
        load = 0
        visited_pickup_ids: set[int] = set()
        
        for i in range(1, len(nodes) - 1):
            node = nodes[i]
            load += node.demand
            
            if load < 0 or load > self.instance.vehicle_capacity:
                return self.set_unfeasible()
                
            if node.demand > 0:
                visited_pickup_ids.add(node.id)
            elif node.demand < 0:
                pickup_id = node.id - self.instance.request_number
                if pickup_id not in visited_pickup_ids:
                    return self.set_unfeasible()

        # Bound Propagation (STP)
        
        # Map the pairs (pickup, delivery) inside the route for ride time constraints
        
        pairs: list[tuple[int, int]] = []
        
        for i in range(1, len(nodes) - 1):
            if nodes[i].demand <= 0:
                continue
            
            delivery_id = nodes[i].id + self.instance.request_number
            for j in range(i + 1, len(nodes) - 1):
                if nodes[j].id == delivery_id:
                    pairs.append((i, j))
                    
                    break
        
        E = [n.ready_time for n in nodes] # earliest arrival times
        L = [n.due_time for n in nodes] # latest arrival times
        S = [n.service_time for n in nodes] # service times
        
        # Safe maximum iteration limit for Bellman-Ford convergence (2 * |V|)
        for _ in range(2 * len(nodes)):
            changed = False
            
            # Forward Pass: Travel Times & Time Windows
            for i in range(1, len(nodes)):
                earliest_arrival = E[i-1] + S[i-1]
                earliest_arrival += self.instance.distances[nodes[i - 1].id, nodes[i].id]
                
                if earliest_arrival > E[i]:
                    E[i] = earliest_arrival
                    changed = True
                
                # Failure: Cannot arrive before the final limit
                if E[i] > L[i]:
                    return self.set_unfeasible()
                    
            # Backward Pass: Travel Times & Time Windows
            for i in range(len(nodes) - 2, -1, -1):
                travel = self.instance.distances[nodes[i].id, nodes[i+1].id]
                latest_departure = L[i + 1] - travel - S[i]
                
                if latest_departure < L[i]:
                    L[i] = latest_departure
                    changed = True
                
                if E[i] > L[i]:
                    return self.set_unfeasible()

            # Ride time constraints (B_d - B_p - s_p <= self.instance.max_request_time)
            for p, d in pairs:
                # Passenger cannot stay longer than the maximum ride time
                # Force the pickup to happen as late as possible
                min_p = E[d] - S[p] - self.instance.max_request_time
                if min_p > E[p]:
                    E[p] = min_p
                    changed = True
                    
                if E[p] > L[p]:
                    return self.set_unfeasible()
                    
                # Force the delivery to happen as early as possible
                max_d = L[p] + S[p] + self.instance.max_request_time
                if max_d < L[d]:
                    L[d] = max_d
                    changed = True
                if E[d] > L[d]:
                    return self.set_unfeasible()

            # Maximum route duration constraint (B_{end} - B_{start} <= max_vehicle_time)
            min_0 = E[len(nodes) - 1] - self.instance.max_vehicle_time

            if min_0 > E[0]:
                E[0] = min_0
                changed = True
                
            if E[0] > L[0]:
                return self.set_unfeasible()
            
            max_last = L[0] + self.instance.max_vehicle_time
            if max_last < L[len(nodes) - 1]:
                L[len(nodes) - 1] = max_last
                changed = True
                
            if E[len(nodes) - 1] > L[len(nodes) - 1]:
                return self.set_unfeasible()
                
            if not changed:
                break
        else:
            # The temporal bounds are logically unsatisfiable if the algorithm does not converge within the mathematical limit of nodes. This indicates that the constraints cannot be satisfied simultaneously, leading to an infeasible route.
            return self.set_unfeasible()

        return self.set_feasible()

    def best_insertion(self, request: tuple[Node, Node]) -> Route | None:
        ''' Find the cheapest feasible insertion of a request '''
        
        pickup, delivery = request
        best_route: Route | None = None
        best_increase = float('inf')

        for pickup_position in range(len(self.nodes) + 1):
            for delivery_position in range(pickup_position + 1, len(self.nodes) + 2):
                nodes = self.nodes.copy()
                
                nodes.insert(pickup_position, pickup.id)
                nodes.insert(delivery_position, delivery.id)

                new_route = Route(self.instance, nodes)

                if not new_route.feasible:
                    continue

                increase = new_route.cost - self.cost

                if increase < best_increase:
                    best_increase = increase
                    best_route = new_route

        return best_route