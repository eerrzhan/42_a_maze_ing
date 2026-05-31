#!/usr/bin/env python3
"""
CLI entrypoint for the a_maze_ing project.

This module is responsible for parsing command-line arguments, loading the
configuration, performing the maze generation, solving, and output writing
processes, and launching the user interface loop.

It acts as the bridge between the reusable maze logic contained in the
`maze_files` package
(which handles maze generation algorithms, solving, and special markings) and
the user-facing command-line interface and visualization.

The main function validates input, loads the config, and then defines a state
factory function used by the UI loop to generate and display the maze and
solution repeatedly.
"""

from __future__ import annotations

import sys

from config_parser import load_config
from output_writer import write_output
from visualizer import run_ui_loop
from enum import Enum
from maze_files.maze_definitions import Maze
from maze_files.dfs_maze_generator import dfs_maze_generator
from maze_files.multiple_path_maze import multiple_path_maze
from maze_files.bfs_shortest_path_solver import bfs_shortest_path_solver
from maze_files.forty_two_marking import forty_two_marking


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


def _coords_to_path(coords: list[tuple[int, int]]) -> str:
    """
    Convert a coordinate path into a string of directional steps.

    Args:
        coords: A list of (x, y) tuples representing the path coordinates in
        order.

    Returns:
        A string consisting of characters 'N', 'E', 'S', 'W' that represent
        the step directions
        from one coordinate to the next.

    This conversion is necessary because the output format and the UI expect
    the path to be represented as a sequence of directional steps rather than
    raw coordinates.

    Assumes that each consecutive pair of coordinates are adjacent (differ by
    exactly one step in either x or y direction). Raises ValueError if
    non-adjacent steps are
    detected.
    """
    if not coords:
        return ""
    steps: list[str] = []
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 1 and dy == 0:
            steps.append("E")
        elif dx == -1 and dy == 0:
            steps.append("W")
        elif dx == 0 and dy == -1:
            steps.append("N")
        elif dx == 0 and dy == 1:
            steps.append("S")
        else:
            raise ValueError(
                f"Non-adjacent steps in path: " f"{(x1, y1)} -> {(x2, y2)}"
            )
    return "".join(steps)


def main(argv: list[str]) -> int:
    """
    Main entrypoint of the program.

    Args:
        argv: List of command-line arguments. Expected usage is:
              python3 a_maze_ing.py config.txt

    High-level flow:
        - Validate arguments and print usage on error.
        - Load configuration from the given file, handle errors gracefully.
        - Define a state factory function that generates the maze, solves it,
          and prepares output for the UI.
        - Launch the UI loop, which repeatedly calls the state factory to
        display or regenerate the maze as needed.
        - Return appropriate exit codes (0 on success, 1 on error, 2 on
        argument error).
    """
    # Validate command-line arguments: expect exactly one argument
    # (config file path).
    if len(argv) != 2:
        print(
            f"{C.BG_RED}Error:{C.RESET} No valid arguments.\n"
            f"Usage: python3 a_maze_ing.py config.txt"
        )
        return 2

    config_path = argv[1]

    def get_state() -> tuple[
        Maze,
        str,
        set[tuple[int, int]],
        tuple[int, int],
        tuple[int, int],
        list[str],
    ]:
        """
        State factory function for the UI loop.

        Reloads the configuration from disk and builds the current maze state.

        This allows the UI to regenerate using an updated config file after the
        user presses `r`.

        Returns:
            A tuple of:
                - Maze instance representing the generated maze.
                - String of directional steps for the solution path.
                - Set of coordinates representing forbidden "42" cells.
                - Entry coordinate from the latest config.
                - Exit coordinate from the latest config.
        """
        try:
            cfg = load_config(config_path)
        except (OSError, ValueError) as e:
            error_message = f"Failed to load config: {e}"
            raise RuntimeError(error_message) from e

        # Build a fresh maze (all walls closed initially).
        maze = Maze(cfg.height, cfg.width, cfg.entry, cfg.exit)

        # Use the provided seed if available; otherwise let Python choose
        # unpredictable randomness from the operating system.
        seed = cfg.seed

        # 1) Mark the cells of 42 as forbidden on map so DFS won't try to enter
        # that area. This prevents the maze generation from carving paths
        # through the "42" shape.
        forty_two_cells, warnings = forty_two_marking(maze)
        for cell in forty_two_cells:
            x, y = cell
            maze.grid[y][x] = 15

        # 2) Generate a perfect maze (DFS backtracker)
        # This creates a maze with exactly one path between any two points,
        # respecting the forbidden "42" cells.
        try:
            dfs_maze_generator(maze, seed, forty_two_cells)
        except ValueError as e:
            print(f"{e}")

        # 3) If PERFECT=False, open a few extra walls to create multiple
        # routes. This makes the maze less strict and adds complexity by
        # allowing multiple solutions.
        if not cfg.perfect:
            multiple_path_maze(maze, forty_two_cells, seed)

        # 4) Solve shortest path (BFS) and convert it to "NESW..." string. This
        # finds the shortest path from entry to exit avoiding forbidden cells.
        try:
            coords_path = bfs_shortest_path_solver(maze, forty_two_cells)
            path_str = _coords_to_path(coords_path)
        except ValueError as e:
            print(f"{e}")
            warnings.append(str(e))
            path_str = ""

        # 5) Write output file (grid in hex + entry/exit + path string). This
        # persists the generated maze and solution for external use.
        write_output(cfg.output_file, maze, cfg.entry, cfg.exit, path_str)

        return maze, path_str, forty_two_cells, cfg.entry, cfg.exit, warnings
    # Launch the UI loop. The UI repeatedly calls `get_state` to regenerate or
    # redisplay the maze.
    try:
        run_ui_loop(get_state)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"{C.BG_RED}Error:{C.RESET} {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
