"""
Imperfect maze helper (PERFECT=False).

This module modifies an already-generated perfect maze by opening a small
number of extra walls. This creates multiple possible routes (loops)
while keeping the maze connected.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Set, Tuple
from . import wall_operations as wo
from . import direction_definitions as dirdef
from .maze_definitions import Maze
import random

Coord = Tuple[int, int]
Candidate = Tuple[Coord, Coord, str]


def _cells_are_open(grid: list[list[int]], cell1: Coord, cell2: Coord) -> bool:
    """Return True if the shared wall between two adjacent cells is open."""
    x1, y1 = cell1
    x2, y2 = cell2
    if abs(x1 - x2) + abs(y1 - y2) != 1:
        return False

    dir_from_1_to_2 = None
    if x2 == x1 + 1 and y2 == y1:
        dir_from_1_to_2 = "E"
    elif x2 == x1 - 1 and y2 == y1:
        dir_from_1_to_2 = "W"
    elif y2 == y1 - 1 and x1 == x2:
        dir_from_1_to_2 = "N"
    elif y2 == y1 + 1 and x1 == x2:
        dir_from_1_to_2 = "S"

    if dir_from_1_to_2 is None:
        return False

    bit_value = dirdef.walls_to_bits(dir_from_1_to_2)
    wall1_closed = wo.is_it_solid_wall(grid[y1][x1], bit_value)
    if wall1_closed:
        return False

    opposite_dir = dirdef.opposite_wall(dir_from_1_to_2)
    opposite_bit = dirdef.walls_to_bits(opposite_dir)
    wall2_closed = wo.is_it_solid_wall(grid[y2][x2], opposite_bit)
    return not wall2_closed


def _creates_3x3_open_area(maze: Maze, coord1: Coord, coord2: Coord) -> bool:
    """Return True if opening a wall between coord1 and coord2 creates a
    3x3 open area."""
    x1, y1 = coord1
    x2, y2 = coord2
    direction = (
        "E" if x2 == x1 + 1 and y2 == y1 else
        "W" if x2 == x1 - 1 and y2 == y1 else
        "N" if y2 == y1 - 1 and x1 == x2 else
        "S"
    )
    bit_value = dirdef.walls_to_bits(direction)
    opposite_bit = dirdef.walls_to_bits(
        dirdef.opposite_wall(direction)
    )

    simulated = [row[:] for row in maze.grid]
    simulated[y1][x1] = wo.remove_a_wall(simulated[y1][x1], bit_value)
    simulated[y2][x2] = wo.remove_a_wall(simulated[y2][x2], opposite_bit)

    x_start = max(0, min(x1, x2) - 2)
    x_end = min(maze.width - 3, max(x1, x2))
    y_start = max(0, min(y1, y2) - 2)
    y_end = min(maze.height - 3, max(y1, y2))

    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            all_open = True
            for yy in range(y, y + 3):
                for xx in range(x, x + 3):
                    if xx + 1 < x + 3:
                        if not _cells_are_open(
                            simulated,
                            (xx, yy),
                            (xx + 1, yy),
                        ):
                            all_open = False
                            break
                    if yy + 1 < y + 3:
                        if not _cells_are_open(
                            simulated,
                            (xx, yy),
                            (xx, yy + 1),
                        ):
                            all_open = False
                            break
                if not all_open:
                    break
            if all_open:
                return True
    return False


class C(str, Enum):
    """ANSI color codes used to make terminal output easier to read."""
    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RED = "\033[31m"
    BG_RED = "\033[41m"

    def __str__(self) -> str:
        return self.value


def check_neighbor_pair(maze: Maze, coord1: Coord, direction: str) -> bool:
    """
    Check if the wall in the given direction from coord1 is closed.

    Args:
        maze: The maze object containing the grid.
        coord1: Tuple (x, y) coordinates of the first cell.
        direction: Direction string ('N', 'E', 'S', 'W') to check.

    Returns:
        True if the wall in the specified direction from coord1 is closed
        (candidate for opening), False otherwise.
    """
    x1, y1 = coord1

    # Read the mask value from the maze grid at position (y, x)
    coord1_mask = maze.grid[y1][x1]
    # Check if the wall bit for the given direction is set (wall is closed)
    if wo.is_it_solid_wall(coord1_mask, dirdef.DIR_BIT_VALUE[direction]):
        return True
    else:
        return False


def multiple_path_maze(
    maze: Maze,
    forbidden_cells: Set[Coord],
    seed: Optional[int] = None,
) -> None:
    """
    Modify a perfect maze to create an imperfect maze by opening extra walls.

    This implements the PERFECT=False option by opening K extra walls, where
    K is chosen as max(1, (width * height) // 25), scaling with maze size.
    It scans east and south neighbor pairs only to avoid duplicates.
    The maze.grid is mutated in-place to open walls and create loops.
    Randomness is used to pick which walls to open; a seed is accepted for
    reproducible output.

    Args:
        maze: Maze object to be modified.
        forbidden_cells: Coordinates that must not be opened/connected.
        seed: Optional seed to make the extra-wall openings reproducible.
    """
    if seed is not None:
        random.seed(seed)

    # Number of extra walls to open, scaling with maze size
    extra_paths = max(1, (maze.width * maze.height) // 25)

    # List of candidate cells to open walls between:
    # ((x, y), (nx, ny), direction)
    candidate_cells: List[Candidate] = []

    # Scan every cell in the maze
    for y in range(maze.height):
        for x in range(maze.width):
            # Check east neighbor if within bounds and wall is currently closed
            if x + 1 < maze.width:
                if (check_neighbor_pair(maze, (x, y), "E") is True and
                        (x, y) not in forbidden_cells and
                        (x + 1, y) not in forbidden_cells and
                        not _creates_3x3_open_area(maze, (x, y), (x + 1, y))):
                    candidate_cells.append(((x, y), (x + 1, y), "E"))

            # Check south neighbor if within bounds and wall is currently
            # closed
            if y + 1 < maze.height:
                if (check_neighbor_pair(maze, (x, y), "S") is True and
                        (x, y) not in forbidden_cells and
                        (x, y + 1) not in forbidden_cells and
                        not _creates_3x3_open_area(maze, (x, y), (x, y + 1))):
                    candidate_cells.append(((x, y), (x, y + 1), "S"))

    # Cannot open more walls than available candidates
    extra_paths = min(extra_paths, len(candidate_cells))

    # Open walls randomly from candidates to create multiple paths. We
    # validate each carve at the time of opening because prior openings may
    # change whether a candidate would create a forbidden 3x3 open area.
    opened = 0
    while opened < extra_paths and candidate_cells:
        random_pick = random.randint(0, len(candidate_cells) - 1)
        carving_pair = candidate_cells[random_pick]

        if _creates_3x3_open_area(maze, carving_pair[0], carving_pair[1]):
            candidate_cells.pop(random_pick)
            continue

        wo.carve_coordinate(maze, carving_pair[0], carving_pair[1])
        opened += 1
        candidate_cells.pop(random_pick)
