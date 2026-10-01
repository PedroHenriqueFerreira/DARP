from sys import argv

from src.instance import Instance
from src.heuristic import Heuristic
from src.neighbors import Neighbors
from src.solver import Solver

def run(instance: Instance, neighbors: int) -> None:
    initial_time, initial_solution = Heuristic(instance).run()

    print(f'Greedy Heuristic Time: {initial_time:.3f} seconds')
    print(f'Greedy Heuristic Solution: {initial_solution}') 
    print(f'Greedy Heuristic Cost: {initial_solution.cost}') 

    assert initial_solution.validate(), 'Initial solution is not valid'

    matrices_time, matrices = Neighbors(instance, neighbors, initial_solution).run()

    print(f'Neighbors Heuristic Time: {matrices_time:.3f} seconds')
    print(f'Neighbors Heuristic Matrices Shape: {len(matrices)} x {matrices[0].shape}')

    solver_time, solver_solution = Solver(instance, matrices).run()
    
    print(f'Solver Time: {solver_time:.3f} seconds')
    print(f'Solver Solution: {solver_solution}')
    print(f'Solver Cost: {solver_solution.cost:.2f}')

    assert solver_solution.validate(), 'Solver solution is not valid'

    # neighbors_time, neighbors_matrices = Neighbors(instance, neighbors, greedy_solution).run()
    
    # print(f'Neighbors Heuristic Time: {neighbors_time:.3f} seconds')
    # print(f'Neighbors Heuristic Matrices: {neighbors_matrices}')
    
    # solver_time, solver_solution = Z3Solver(instance, neighbors_matrices).run()
    
    # print(f'Solver Time: {solver_time:.3f} seconds')
    # print(f'Solver Solution: {solver_solution}')
    # print(f'Solver Cost: {solver_solution.cost:.2f}')
    
    # print(solver_solution)

if __name__ == '__main__':
    if len(argv) < 3:
        print('Usage: python main.py <instance_file> <neighbors>')
        exit(1)
    
    instance = Instance(argv[1], precision=3)
    
    _ = run(instance, int(argv[2]))
    
    # plot(data, to[1])
    # plot(data, solver[1])