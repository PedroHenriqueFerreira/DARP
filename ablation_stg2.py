import csv
import os
import re
from sys import argv

from src.instance import Instance
from src.heuristic import Heuristic
from src.neighbors import Neighbors
from src.solver import Solver

INSTANCES_DIR = 'instances'

def parse_cp_sat_stats(stats_str: str) -> dict:
    def extract(pattern: str, default: str = "0") -> str:
        match = re.search(pattern, stats_str, re.MULTILINE)
        return match.group(1) if match else default

    return {
        "integers": extract(r"^integers:\s*(\d+)"),
        "booleans": extract(r"^booleans:\s*(\d+)"),
        "conflicts": extract(r"^conflicts:\s*(\d+)"),
        "branches": extract(r"^branches:\s*(\d+)"),
        "propagations": extract(r"^propagations:\s*(\d+)"),
        "int_propagations": extract(r"^integer_propagations:\s*(\d+)"),
        "restarts": extract(r"^restarts:\s*(\d+)"),
    }

def run_ablation(k_values: list[int], time_limit: int = 120):
    sorted_instances = sorted(os.listdir(INSTANCES_DIR))

    with open("ablation_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "instance", "mode", "k", "init_cost", "final_cost", "best_bound",
            "gap_pct", "matrices_time", "solver_time", "total_time",
            "num_arc_vars", "presolve_integers", "presolve_booleans",
            "conflicts", "branches", "propagations", "int_propagations", "restarts"
        ])

        for name in sorted_instances:
            print(f' {name} '.center(80, '-'))
            instance = Instance(f'{INSTANCES_DIR}/{name}', precision=3)

            h_time, init_solution = Heuristic(instance).run()
            init_solution.validate()

            configs = [(f"k_{k}", k, False) for k in k_values] + [
                ("Full_Graph", instance.request_number, True)
            ]

            for mode, k_val, is_full in configs:
                matrices_time, matrices = Neighbors(
                    instance, k=k_val, solution=init_solution, full_graph=is_full
                ).run()

                num_arc_vars = sum(
                    1 for m in matrices for i in range(len(m)) for j in range(len(m))
                    if i != j and m[i, j] >= 0
                )

                solver_obj = Solver(
                    instance=instance,
                    matrices=matrices,
                    initial_solution=init_solution,
                    time_limit=time_limit,
                )
                solver_time, solver_solution = solver_obj.run()
                solver_solution.validate()

                cp = solver_obj.last_solver
                parsed = parse_cp_sat_stats(cp.ResponseStats())

                obj = solver_solution.cost
                bound = cp.BestObjectiveBound() / (10 ** instance.precision)
                gap = ((obj - bound) / obj * 100) if obj > 0 else 0.0
                total_time = matrices_time + solver_time

                writer.writerow([
                    name,                        # 1. instance
                    mode,                        # 2. mode
                    k_val,                       # 3. k
                    f"{init_solution.cost:.3f}", # 4. init_cost
                    f"{obj:.3f}",                # 5. final_cost
                    f"{bound:.3f}",              # 6. best_bound
                    f"{gap:.2f}",                # 7. gap_pct
                    f"{matrices_time:.3f}",      # 8. matrices_time
                    f"{solver_time:.3f}",        # 9. solver_time
                    f"{total_time:.3f}",         # 10. total_time
                    num_arc_vars,                # 11. num_arc_vars
                    parsed["integers"],          # 12. presolve_integers
                    parsed["booleans"],          # 13. presolve_booleans
                    parsed["conflicts"],         # 14. conflicts
                    parsed["branches"],          # 15. branches
                    parsed["propagations"],      # 16. propagations
                    parsed["int_propagations"],  # 17. int_propagations
                    parsed["restarts"],          # 18. restarts
                ])
                f.flush()

                print(
                    f"[{mode}] Cost: {init_solution.cost:.3f} -> {obj:.3f} | "
                    f"Gap: {gap:.2f}% | Time: {total_time:.3f}s | "
                    f"Arcs: {num_arc_vars} | Conflicts: {parsed['conflicts']}"
                )

if __name__ == '__main__':
    n_neighbors = int(argv[1] if len(argv) > 1 else 3)
    run_ablation(k_values=list(range(1, n_neighbors + 1)), time_limit=120)