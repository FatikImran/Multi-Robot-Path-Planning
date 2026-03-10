from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple


Position = Tuple[int, int]
# State space: (x, y, checkpoint_index, time)
State = Tuple[int, int, int, int]


@dataclass(frozen=True)
class Robot:
    robot_id: int
    priority: int
    energy_limit: int
    start: Position
    goal: Position
    checkpoints: List[Position]


@dataclass
class Grid:
    height: int
    width: int
    rows_top_down: List[str]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def cell_at(self, x: int, y: int) -> str:
        row_index = self.height - 1 - y
        return self.rows_top_down[row_index][x]

    def is_blocked(self, x: int, y: int) -> bool:
        return self.cell_at(x, y) == "X"


def parse_int(token: str, field_name: str) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {field_name}: {token}") from exc


def validate_position(grid: Grid, pos: Position, label: str) -> None:
    x, y = pos
    if not grid.in_bounds(x, y):
        raise ValueError(f"{label} {pos} is out of grid bounds")
    if grid.is_blocked(x, y):
        raise ValueError(f"{label} {pos} cannot be on obstacle cell X")


def read_input(path: Path) -> Tuple[Grid, List[Robot]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input file: {path.name}")

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("input.txt is empty")

    first = lines[0].split()
    if len(first) != 2:
        raise ValueError("First line must contain N M")
    height = parse_int(first[0], "N")
    width = parse_int(first[1], "M")
    if height <= 0 or width <= 0:
        raise ValueError("N and M must be positive integers")

    if len(lines) < 1 + height:
        raise ValueError("Not enough grid lines")

    grid_lines = lines[1 : 1 + height]
    for row in grid_lines:
        if len(row) != width:
            raise ValueError("Grid row length mismatch")
        for ch in row:
            if ch not in {".", "X", "^", "v", "<", ">"}:
                raise ValueError("Grid contains invalid characters")

    grid = Grid(height=height, width=width, rows_top_down=grid_lines)

    tokens = []
    for line in lines[1 + height :]:
        tokens.extend(line.split())

    if not tokens:
        raise ValueError("Missing robot data")

    idx = 0
    robot_count = parse_int(tokens[idx], "R")
    idx += 1
    if robot_count < 0:
        raise ValueError("R (number of robots) cannot be negative")

    robots: List[Robot] = []
    seen_ids: Set[int] = set()

    for robot_no in range(1, robot_count + 1):
        if idx + 8 > len(tokens):
            raise ValueError("Incomplete robot header")
        robot_id = parse_int(tokens[idx], f"robot {robot_no} ID")
        priority = parse_int(tokens[idx + 1], f"robot {robot_no} priority")
        energy_limit = parse_int(tokens[idx + 2], f"robot {robot_no} energy limit")
        idx += 3
        if energy_limit <= 0:
            raise ValueError(f"Energy limit for Robot {robot_id} must be positive")
        if robot_id in seen_ids:
            raise ValueError(f"Duplicate robot ID found: {robot_id}")
        seen_ids.add(robot_id)

        start_x = parse_int(tokens[idx], f"robot {robot_id} startX")
        start_y = parse_int(tokens[idx + 1], f"robot {robot_id} startY")
        idx += 2

        goal_x = parse_int(tokens[idx], f"robot {robot_id} goalX")
        goal_y = parse_int(tokens[idx + 1], f"robot {robot_id} goalY")
        idx += 2

        checkpoint_count = parse_int(tokens[idx], f"robot {robot_id} checkpoint count")
        idx += 1
        if checkpoint_count < 0:
            raise ValueError(f"Checkpoint count for Robot {robot_id} cannot be negative")

        checkpoints: List[Position] = []
        for cp_no in range(1, checkpoint_count + 1):
            if idx + 2 > len(tokens):
                raise ValueError("Incomplete checkpoint list")
            cp_x = parse_int(tokens[idx], f"robot {robot_id} checkpoint {cp_no} x")
            cp_y = parse_int(tokens[idx + 1], f"robot {robot_id} checkpoint {cp_no} y")
            idx += 2
            checkpoints.append((cp_x, cp_y))

        start = (start_x, start_y)
        goal = (goal_x, goal_y)
        validate_position(grid, start, f"Robot {robot_id} start")
        validate_position(grid, goal, f"Robot {robot_id} goal")
        for cp_index, checkpoint in enumerate(checkpoints, start=1):
            validate_position(grid, checkpoint, f"Robot {robot_id} checkpoint {cp_index}")

        robots.append(
            Robot(
                robot_id=robot_id,
                priority=priority,
                energy_limit=energy_limit,
                start=start,
                goal=goal,
                checkpoints=checkpoints,
            )
        )

    if idx != len(tokens):
        raise ValueError("Unexpected extra tokens found after robot definitions")

    return grid, robots


def next_checkpoint_index(pos: Position, checkpoints: List[Position], idx: int) -> int:
    while idx < len(checkpoints) and pos == checkpoints[idx]:
        idx += 1
    return idx


def allowed_moves(grid: Grid, x: int, y: int) -> Iterable[Position]:
    cell = grid.cell_at(x, y)

    if cell == "^":
        yield (x, y + 1)
        return
    if cell == "v":
        yield (x, y - 1)
        return
    if cell == "<":
        yield (x - 1, y)
        return
    if cell == ">":
        yield (x + 1, y)
        return

    yield (x + 1, y)
    yield (x - 1, y)
    yield (x, y + 1)
    yield (x, y - 1)
    yield (x, y)  # wait only when not on a one-way cell


def find_path(
    grid: Grid,
    robot: Robot,
    reservations: Set[Tuple[int, int, int]],
) -> Optional[List[Position]]:
    # BFS: uniform step cost, time tracked in state for reservations.
    start_x, start_y = robot.start
    if not grid.in_bounds(start_x, start_y) or grid.is_blocked(start_x, start_y):
        return None

    start_cp = next_checkpoint_index(robot.start, robot.checkpoints, 0)
    if (start_x, start_y, 0) in reservations:
        return None

    start_state: State = (start_x, start_y, start_cp, 0)
    frontier: Deque[State] = deque([start_state])
    parents: Dict[State, Optional[State]] = {start_state: None}

    while frontier:
        x, y, cp_idx, t = frontier.popleft()

        if (x, y) == robot.goal and cp_idx == len(robot.checkpoints):
            return reconstruct_path(parents, (x, y, cp_idx, t))

        if t >= robot.energy_limit:
            continue

        for nx, ny in allowed_moves(grid, x, y):
            nt = t + 1
            if not grid.in_bounds(nx, ny):
                continue
            if grid.is_blocked(nx, ny):
                continue
            if (nx, ny, nt) in reservations:
                continue

            next_cp = next_checkpoint_index((nx, ny), robot.checkpoints, cp_idx)
            next_state: State = (nx, ny, next_cp, nt)
            if next_state in parents:
                continue

            parents[next_state] = (x, y, cp_idx, t)
            frontier.append(next_state)

    return None


def reconstruct_path(parents: Dict[State, Optional[State]], goal_state: State) -> List[Position]:
    path_rev: List[Position] = []
    current: Optional[State] = goal_state
    while current is not None:
        x, y, _, _ = current
        path_rev.append((x, y))
        current = parents[current]
    return list(reversed(path_rev))


def reserve_path(path: List[Position], reservations: Set[Tuple[int, int, int]]) -> None:
    for t, (x, y) in enumerate(path):
        reservations.add((x, y, t))


def plan_all(grid: Grid, robots: List[Robot]) -> Dict[int, Optional[List[Position]]]:
    by_priority = sorted(robots, key=lambda r: r.priority, reverse=True)
    reservations: Set[Tuple[int, int, int]] = set()
    results: Dict[int, Optional[List[Position]]] = {}

    for robot in by_priority:
        path = find_path(grid, robot, reservations)
        results[robot.robot_id] = path
        if path is not None:
            reserve_path(path, reservations)

    return results


def write_output(path: Path, robots: List[Robot], results: Dict[int, Optional[List[Position]]]) -> None:
    lines: List[str] = []
    for robot in sorted(robots, key=lambda r: r.robot_id):
        path_result = results.get(robot.robot_id)
        if not path_result:
            lines.append(f"Error: No valid path found for Robot {robot.robot_id}")
            lines.append("")
            continue

        coords = " -> ".join(f"({x},{y})" for x, y in path_result)
        total_time = len(path_result) - 1
        total_energy = total_time
        lines.append(f"Robot {robot.robot_id}: Path: {coords}")
        lines.append(f"Total Time: {total_time}")
        lines.append(f"Total Energy: {total_energy}")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
