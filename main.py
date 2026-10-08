from sys import argv
from os import listdir

import pandas as pd

from src.instance import Instance
from src.heuristic import Heuristic
from src.neighbors import Neighbors
from src.solver import Solver

INSTANCES_DIR = 'instances'

n_runs = int(argv[1] if len(argv) > 1 else 5)
n_neighbors = int(argv[2] if len(argv) > 2 else 3)

instances = listdir(INSTANCES_DIR)
sorted_instances = sorted(instances)

data: list[dict[str, str]] = []

try:
    df = pd.read_csv('results.csv')
    
    for name in df['instance'].tolist():
        sorted_instances.remove(name)
        data.append(df[df['instance'] == name].to_dict('records')[0])
    
except FileNotFoundError:
    df = pd.DataFrame()

for name in sorted_instances:
    print(f' {name} '.center(80, '-'))
    
    instance = Instance(f'{INSTANCES_DIR}/{name}', precision=3)
    
    total_initial_time = 0
    for r in range(1, n_runs + 1):
        initial_time, initial_solution = Heuristic(instance).run()
        total_initial_time += initial_time
        
        initial_solution.validate()
            
    initial_time = total_initial_time / n_runs
    
    line: dict[str, str] = { 
        'instance': name, 
        'initial_time': round(initial_time, 3),
        'initial_cost': initial_solution.cost
    }
    
    for k in range(1, n_neighbors + 1):
        print(f'Running {k} neighbors...')
        
        total_time = 0
            
        for r in range(1, n_runs + 1):
            matrices_time, matrices = Neighbors(instance, k, initial_solution).run()
            solver_time, solver_solution = Solver(instance, matrices, initial_solution).run()
            
            solver_solution.validate()
            
            curr_time = matrices_time + solver_time
            total_time += curr_time
            
            print(
                f'Run [{r} / {n_runs}] - ' 
                f'Time: [{curr_time:.3f}s] - '
                f'Cost: [{initial_solution.cost:.3f} -> {solver_solution.cost:.3f}]'
            )
            
        line[f'time_k_{k}'] = round(total_time / n_runs, 3)
        line[f'cost_k_{k}'] = solver_solution.cost
                                                            
    data.append(line)
    
    pd.DataFrame(data).to_csv('results.csv', index=False)
