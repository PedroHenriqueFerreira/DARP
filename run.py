from sys import argv

from src.instance import Instance
from src.heuristic import Heuristic
from src.neighbors import Neighbors
from src.solver import Solver

def run(instance: Instance, neighbors: int) -> None:
    initial_time, initial_solution = Heuristic(instance).run()

    # print(f'Initial Time: {initial_time:.3f} seconds')
    # print(f'Initial Solution: {initial_solution}') 
    # print(f'Initial Cost: {initial_solution.cost}') 

    valid, message = initial_solution.validate()
    assert valid, message

    matrices_time, matrices = Neighbors(instance, neighbors, initial_solution).run()
    solver_time, solver_solution = Solver(instance, matrices).run()
    
    # print(f'Solver Time: {solver_time:.3f} seconds')
    # print(f'Solver Solution: {solver_solution}')
    # print(f'Solver Cost: {solver_solution.cost:.2f}')

    valid, message = solver_solution.validate()
    assert valid, message

    # neighbors_time, neighbors_matrices = Neighbors(instance, neighbors, greedy_solution).run()
    
    # print(f'Neighbors Heuristic Time: {neighbors_time:.3f} seconds')
    # print(f'Neighbors Heuristic Matrices: {neighbors_matrices}')
    
    # solver_time, solver_solution = Z3Solver(instance, neighbors_matrices).run()
    
    # print(f'Solver Time: {solver_time:.3f} seconds')
    # print(f'Solver Solution: {solver_solution}')
    # print(f'Solver Cost: {solver_solution.cost:.2f}')
    
    # print(solver_solution)
    
    return (
        initial_time, 
        initial_solution.cost, 
        matrices_time, 
        solver_time, 
        solver_solution.cost
    )

if __name__ == '__main__':
    if len(argv) < 3:
        print('Usage: python main.py <instance_file> <neighbors>')
        exit(1)
    
    instance = Instance(argv[1], precision=3)
    
    initial_time, initial_cost, neighbors_time, solver_time, solver_cost = run(
        instance, 
        int(argv[2])
    )
    
    print(f'Heuristic Time: {initial_time:.3f} seconds')
    print(f'Heuristic Cost: {initial_cost:.3f}')
    print(f'Neighbors Time: {neighbors_time:.3f} seconds')
    print(f'Solver Time: {solver_time:.3f} seconds')
    print(f'Solver Cost: {solver_cost:.3f}')
    
    # plot(data, to[1])
    # plot(data, solver[1])