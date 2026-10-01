from sys import argv
from os import listdir

import pandas as pd

from src.instance import Instance
from run import run

n_runs = int(argv[1] if len(argv) > 1 else 5)
n_neighbors = int(argv[2] if len(argv) > 2 else 3)

instances = listdir('instances')
sorted_instances = sorted(instances, key=lambda x: (int(x[3:5]), int(x[1]), x[0]))

data: list[dict[str, str]] = []

for name in sorted_instances:
    print(f' {name} '.center(80, '-'))
    
    instance = Instance(f'instances/{name}', precision=3)
    
    line: dict[str, str] = {'Instance': name}
    
    for neighbors in range(1, n_neighbors + 1):
        print(f'Running {neighbors} neighbors...')
        
        to+tal_h_time = 0
        h_cost = 0
        total_neighbor_time = 0
        total_solver_time = 0
        solver_cost = 0
        
        for r in range(1, n_runs + 1):
            print(f'Run {r} of {n_runs}...')
            
            h_time, h_cost, neighbor_time, solver_time, solver_cost = run(instance, neighbors)
            
        
            total_h_time += h_time
            total_neighbor_time += neighbor_time
            total_solver_time += solver_time
        
        h_time = total_h_time / n_runs
        neighbor_time = total_neighbor_time / n_runs
        solver_time = total_solver_time / n_runs
                
        line[f'heuristic_time_k={neighbors}'] = round(h_time, 3)
        line[f'heuristic_cost_k={neighbors}'] = h_cost
        line[f'neighbors_time_k={neighbors}'] = round(neighbor_time, 3)
        line[f'solver_time_k={neighbors}'] = round(solver_time, 3)
        line[f'solver_cost_k={neighbors}'] = solver_cost
                                                    
    data.append(line)
    
    pd.DataFrame(data).to_csv('results.csv', index=False)
