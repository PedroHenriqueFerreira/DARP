from sys import argv
from os import listdir

from src.instance import Instance
from run import run

n_runs = int(argv[1] if len(argv) > 1 else 5)

instances = listdir('instances')
sorted_instances = sorted(instances, key=lambda x: (int(x[3:5]), int(x[1]), x[0]))

for instance in sorted_instances:
    print(f' {instance} '.center(80, '-'))
    
    for i in range(1, n_runs + 1):
        columns += [f'Heuristic Time {i}', f'Solver Time {i}', f'KM+TO Distance {i}', f'KN+Solver Distance {i}', f'Vehicles {i}']

    columns += ['KM+TO Time', 'KM+TO+KN+Solver Time']

    new_df = pd.DataFrame(columns=columns)

    for line in df.itertuples():
        data = Data(f'instances/{group}/{line.Instance}.txt').load()
        
        km_to_times = []
        kn_solver_times = []
        km_costs = []
        to_costs = []
        solver_costs = []
        vehicle_counts = []
        
        for i in range(n_runs):
            km, to, kn, solver = main(data, 5)
            
            km_to_times.append(km[0] + to[0])
            kn_solver_times.append(kn[0] + solver[0])
            
            km_costs.append(sum(route.cost for route in km[1]))
            to_costs.append(sum(route.cost for route in to[1]))
            solver_costs.append(sum(route.cost for route in solver[1]))
            vehicle_counts.append(len(solver[1]))
    
        dic = { 'Instance': line.Instance }
        
        for i in range(n_runs):
            dic[f'KM+TO Time {i + 1}'] = round(km_to_times[i], 3)
            dic[f'KM+TO+KN+Solver Time {i + 1}'] = round(km_to_times[i] + kn_solver_times[i], 3)
            dic[f'KM+TO Distance {i + 1}'] = to_costs[i]
            dic[f'KN+Solver Distance {i + 1}'] = solver_costs[i]
            dic[f'Vehicles {i + 1}'] = vehicle_counts[i]
            
        km_to_time_mean = sum(km_to_times) / n_runs
        kn_solver_time_mean = sum(kn_solver_times) / n_runs
            
        dic[f'KM+TO Time'] = round(km_to_time_mean, 3)
        dic[f'KM+TO+KN+Solver Time'] = round(km_to_time_mean + kn_solver_time_mean, 3)
        
        new_df.loc[len(new_df)] = dic
        
        print(f'Instance {line.Instance} processed')
                
    new_df.to_csv(f'{group}_results.csv', index=False)