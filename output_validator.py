# This script does not check for errors or malformed files.
# It only validates that neighbooring cells sharing a wall have
#  both the correct encoding.
# Usage: python3 output_validator.py output_maze.txt

import sys


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: python3 {argv[0]} <output_file>")
        return 1

    filename = argv[1]
    grid: list[list[int]] = []

    try:
        with open(filename, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip() == "":
                    break
                grid.append([int(c, 16) for c in line.strip(" \t\n\r")])
    except OSError as error:
        print(f"Unable to open {filename}: {error}")
        return 1
    except ValueError as error:
        print(f"Invalid maze data in {filename}: {error}")
        return 1

    for row_index in range(len(grid)):
        for col_index in range(len(grid[0])):
            value = grid[row_index][col_index]
            if not all([
                    row_index < 1 or value & 1 == (
                        grid[row_index - 1][col_index] >> 2) & 1,
                    col_index >= len(grid[0]) - 1 or (
                        value >> 1) & 1 == (
                        grid[row_index][col_index + 1] >> 3) & 1,
                    row_index >= len(grid) - 1 or (
                        value >> 2) & 1 == grid[row_index + 1][col_index] & 1,
                    col_index < 1 or (
                        value >> 3) & 1 == (
                        grid[row_index][col_index - 1] >> 1) & 1,
            ]):
                print(f"Wrong encoding for ({col_index},{row_index})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
