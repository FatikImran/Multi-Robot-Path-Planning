# Assignment 1 - Multi-Robot Path Planning

## Overview
This project solves a grid-based multi-robot path planning problem using a single search-based planner (**BFS**).

Each robot must:
- start at its given start cell,
- visit checkpoints in order,
- reach its goal within its energy limit,
- obey one-way cell constraints,
- avoid time-step collisions with higher-priority robots.

The solver reads from `input.txt` and writes results to `output.txt`.

## Core Approach
- Robots are sorted by descending priority.
- A path is planned for each robot one-by-one.
- Occupied cells are reserved as `(x, y, t)` and treated as blocked for lower-priority robots.
- BFS state representation: `(x, y, checkpoint_index, time)`.

## Project Files
- `main.py`: Primary solver implementation.
- `input.txt`: Input instance.
- `output.txt`: Generated output.
- `reference_output.txt`: Example/reference output.
- `animated_comparison.html`: Optional visualization UI for comparing outputs.
- `app_server.py`: Optional local server to run solver from the visualization page.

## Requirements
- Python 3.10+ (standard library only; no external packages required).

## How to Run
1. Place/edit your problem instance in `input.txt`.
2. Run the solver from the project folder:

```bash
python main.py
```

3. Open `output.txt` to see planned paths or error messages.

## Output Behavior
### Success format (per robot, sorted by Robot ID)
- `Robot <ID>: Path: (x0,y0) -> ... -> (xT,yT)`
- `Total Time: T`
- `Total Energy: E`

### Failure format
- `Error: No valid path found for Robot <ID>`

## Optional: Animated Comparison Viewer
If you want to visually compare `reference_output.txt` and `output.txt`:

1. Start the local server:

```bash
python app_server.py
```

2. Open `http://127.0.0.1:8000/animated_comparison.html` in your browser.
3. Use **Run Solver** or **Reload Files** in the page controls.

## Notes
- `main.py` resolves paths relative to its own directory, so keep `input.txt` in this folder.
- Collision handling blocks same-cell occupancy at the same time step.
- Edge-swap conflict handling is intentionally not required for this assignment.
