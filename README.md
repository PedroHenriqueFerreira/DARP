# DARP Solver

Python implementation for solving the Dial-a-Ride Problem (DARP) through a three-stage pipeline:

1. **Constructive Heuristic**: *Parallel Regret-2* algorithm with insertion caching for initial solution generation and temporal validation via the *Simple Temporal Problem* (STP).
2. **Neighborhood Generation**: Creation of sparse adjacency matrices based on the $k$ closest requests to reduce the search space.
3. **Exact Solver**: Google OR-Tools CP-SAT model using the initial heuristic solution as a hot-start (*Solution Hinting*) over the reduced graph.

## Project Structure

```
.
├── instances/          # Directory containing instance files
├── src/
│   ├── heuristic.py    # Regret-2 constructive heuristic
│   ├── instance.py     # Data loading and time window tightening
│   ├── neighbors.py    # Neighborhood-based graph reduction (k-neighbors)
│   ├── node.py         # Node representation (depot, pickups, and deliveries)
│   ├── route.py        # Route management and feasibility validation (STP)
│   ├── solution.py     # Route aggregation, total cost, and validation
│   ├── solver.py       # Exact model using OR-Tools CP-SAT
│   └── timer.py        # Decorator for execution time measurement
├── main.py             # Batch execution (benchmark) and CSV export
├── run.py              # Single instance execution via CLI
├── ablation_stg2.py    # Stage 2 ablation (k-neighbors vs. full graph) and CSV export
└── requirements.txt    # Project dependencies
```

## Installation

1. Create and activate a virtual environment:

```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run all commands from the project root, with the virtual environment activated.

### Single Execution (`run.py`)

Runs the complete pipeline for a single instance and displays time and cost metrics in the terminal.

```bash
python run.py <instance_path> <num_neighbors>
```

Example:

```bash
python run.py instances/a2-16.txt 3
```

### Batch Execution (`main.py`)

Processes all instances in the `instances/` directory, running multiple trials and varying the neighborhood size from $1$ to $k$ and averaging the results.

```bash
python main.py [num_runs] [max_neighbors]
```

* `num_runs`: Number of repetitions to calculate the average time (default: `5`).
* `max_neighbors`: Maximum value of $k$ neighbors tested (default: `3`).

Example:

```bash
python main.py 5 3
```

After running, check the output file `results.csv` (supports resuming if the file already exists).

### Stage 2 Ablation (`ablation_stg2.py`)

Compares the CP-SAT solver on the $k$-neighbors graph (for $k$ from $1$ to `max_neighbors`) against the full graph, for every instance in `instances/` (time limit of 120 s per run).

```bash
python ablation_stg2.py [max_neighbors]
```

* `max_neighbors`: Maximum value of $k$ tested (default: `3`).

Example:

```bash
python ablation_stg2.py 3
```

After running, check the output file `ablation_results.csv` (overwritten at each execution).
