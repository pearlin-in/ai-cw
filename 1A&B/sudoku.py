#!/usr/bin/env python3
"""
F29AI Coursework 1, Part 1B: Sudoku solver (CSP + search).

Two solvers are implemented from scratch (standard library only):
  * BaselineSolver : plain backtracking, fixed cell order (evaluation yardstick)
  * MRVFCSolver    : backtracking + Minimum Remaining Values + Forward Checking
                     (the chosen approach)

Usage:
  python sudoku_solver.py <puzzle_file>            solve one puzzle with MRV+FC
  python sudoku_solver.py --eval                   compare both solvers on every
                                                   .txt/.csv file in ./puzzles
  python sudoku_solver.py --eval --folder DIR --runs 5 --cap 100000

Input format: 9 lines, 9 values per line, 0 = empty cell.
              Values are separated by spaces (.txt) or commas (.csv).

Metric definitions (identical for both solvers so results are comparable):
  steps       number of recursive search calls
  assignments number of times the search wrote a digit into a cell
  backtracks  number of those assignments that were later undone because they
              led to a dead end (including immediate forward-checking failures)

Exit codes (single-puzzle mode): 0 solved, 1 invalid input,
                                 2 valid but unsolvable, 3 internal error.
"""

import argparse
import csv
import os
import sys
import time

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
SIZE = 9                      # grid width/height
BOX = 3                       # box width/height
DIGITS = set(range(1, SIZE + 1))

DEFAULT_PUZZLE_DIR = "puzzles"
DEFAULT_RUNS = 3              # timing repetitions per puzzle and solver
DEFAULT_STEP_CAP = 200_000    # baseline gives up after this many steps
RESULTS_FILE = "results.csv"

# Status values returned by the solvers
SOLVED = "SOLVED"
UNSOLVABLE = "UNSOLVABLE"
TIMEOUT = "TIMEOUT"
INVALID_OUTPUT = "INVALID OUTPUT"   # solver claimed success but checker disagreed


# ----------------------------------------------------------------------------
# Shared data: peers
# ----------------------------------------------------------------------------
def precompute_peers():
    """For every cell, list the 20 other cells that share its row, column or box.

    Two peers may never hold the same digit, so this is the binary form of the
    27 all-different constraints. It is computed once and shared.
    """
    peers = {}
    for r in range(SIZE):
        for c in range(SIZE):
            neighbours = set()
            for i in range(SIZE):
                if i != c:
                    neighbours.add((r, i))      # same row
                if i != r:
                    neighbours.add((i, c))      # same column
            box_r, box_c = (r // BOX) * BOX, (c // BOX) * BOX
            for i in range(box_r, box_r + BOX):
                for j in range(box_c, box_c + BOX):
                    if (i, j) != (r, c):
                        neighbours.add((i, j))  # same box
            peers[(r, c)] = sorted(neighbours)
    return peers


PEERS = precompute_peers()


# ----------------------------------------------------------------------------
# Independent solution checker
# ----------------------------------------------------------------------------
def is_valid_solution(grid, original):
    """Check a finished grid without using PEERS or any solver logic.

    A grid is valid if the givens are preserved and every row, column and
    3x3 box contains each digit 1-9 exactly once. Kept separate from the
    solvers on purpose so a bug in them cannot hide itself.
    """
    if len(grid) != SIZE or any(len(row) != SIZE for row in grid):
        return False

    for r in range(SIZE):
        for c in range(SIZE):
            if original[r][c] != 0 and grid[r][c] != original[r][c]:
                return False

    units = []
    for i in range(SIZE):
        units.append([grid[i][j] for j in range(SIZE)])          # row i
        units.append([grid[j][i] for j in range(SIZE)])          # column i
    for box_r in range(0, SIZE, BOX):
        for box_c in range(0, SIZE, BOX):
            units.append([grid[r][c]
                          for r in range(box_r, box_r + BOX)
                          for c in range(box_c, box_c + BOX)])

    return all(len(unit) == SIZE and set(unit) == DIGITS for unit in units)


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
def print_grid(grid):
    """Print the grid with separators between the 3x3 boxes ('.' = empty)."""
    border = "+-------+-------+-------+"
    print(border)
    for r in range(SIZE):
        line = "| "
        for c in range(SIZE):
            line += (str(grid[r][c]) if grid[r][c] != 0 else ".") + " "
            if (c + 1) % BOX == 0:
                line += "| "
        print(line)
        if (r + 1) % BOX == 0:
            print(border)


# ----------------------------------------------------------------------------
# Solvers
# ----------------------------------------------------------------------------
class _SolverBase:
    """Holds the working grid and the three metric counters."""

    def __init__(self, grid):
        self.grid = [row[:] for row in grid]     # solver works on its own copy
        self.steps = 0
        self.assignments = 0
        self.backtracks = 0

    def _reset_counters(self):
        self.steps = 0
        self.assignments = 0
        self.backtracks = 0


class BaselineSolver(_SolverBase):
    """Plain backtracking: first empty cell, digits 1-9, legality tested on demand."""

    def __init__(self, grid, max_steps=DEFAULT_STEP_CAP):
        super().__init__(grid)
        self.max_steps = max_steps

    def solve(self):
        self._reset_counters()
        return self._backtrack()

    def _first_empty_cell(self):
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] == 0:
                    return r, c
        return None

    def _is_legal(self, r, c, val):
        """A digit is legal if none of the cell's 20 peers already holds it."""
        return all(self.grid[pr][pc] != val for pr, pc in PEERS[(r, c)])

    def _backtrack(self):
        self.steps += 1
        if self.steps > self.max_steps:
            return TIMEOUT

        cell = self._first_empty_cell()
        if cell is None:
            return SOLVED

        r, c = cell
        for val in range(1, SIZE + 1):
            if not self._is_legal(r, c, val):
                continue
            self.grid[r][c] = val
            self.assignments += 1
            result = self._backtrack()
            if result in (SOLVED, TIMEOUT):
                return result
            self.grid[r][c] = 0          # dead end: undo the assignment
            self.backtracks += 1
        return UNSOLVABLE


class MRVFCSolver(_SolverBase):
    """Backtracking with Minimum Remaining Values and Forward Checking.

    Keeps a domain (set of still-possible digits) for every cell.
      * MRV: always branch on the unassigned cell with the smallest domain.
      * Forward checking: after assigning a digit, remove it from the domains
        of the unassigned peers; if any domain becomes empty, reject the digit
        immediately without recursing.
    Each branch works on its own copy of the domains (copy-on-branch), so the
    parent's domains are never modified and need no explicit restoring.
    """

    def solve(self):
        self._reset_counters()
        domains = [[set(DIGITS) for _ in range(SIZE)] for _ in range(SIZE)]

        # Propagate the givens. validate_grid() has already ruled out
        # given-versus-given conflicts, so only empty cells are pruned here.
        for r in range(SIZE):
            for c in range(SIZE):
                val = self.grid[r][c]
                if val != 0:
                    domains[r][c] = {val}
                    if not self._forward_check(domains, r, c, val):
                        return UNSOLVABLE
        return self._backtrack(domains)

    def _forward_check(self, domains, r, c, val):
        """Remove val from unassigned peers. Return False if a domain empties."""
        for pr, pc in PEERS[(r, c)]:
            if self.grid[pr][pc] == 0 and val in domains[pr][pc]:
                domains[pr][pc].remove(val)
                if not domains[pr][pc]:
                    return False
        return True

    def _select_unassigned_variable(self, domains):
        """MRV: return the empty cell with the fewest remaining digits."""
        best_cell = None
        best_size = SIZE + 1
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] == 0 and len(domains[r][c]) < best_size:
                    best_size = len(domains[r][c])
                    best_cell = (r, c)
                    if best_size == 1:           # a forced move cannot be beaten
                        return best_cell
        return best_cell

    def _backtrack(self, domains):
        self.steps += 1

        cell = self._select_unassigned_variable(domains)
        if cell is None:
            return SOLVED

        r, c = cell
        for val in sorted(domains[r][c]):
            child = [[set(d) for d in row] for row in domains]   # copy-on-branch
            child[r][c] = {val}
            self.grid[r][c] = val
            self.assignments += 1

            if self._forward_check(child, r, c, val):
                if self._backtrack(child) == SOLVED:
                    return SOLVED

            self.grid[r][c] = 0                  # dead end: undo the assignment
            self.backtracks += 1
        return UNSOLVABLE


# ----------------------------------------------------------------------------
# Input and validation
# ----------------------------------------------------------------------------
def validate_grid(grid):
    """Return (True, 'Valid') or (False, reason) for a parsed 9x9 grid."""
    for r in range(SIZE):
        for c in range(SIZE):
            if not 0 <= grid[r][c] <= SIZE:
                return False, f"Value {grid[r][c]} at row {r + 1}, col {c + 1} is outside 0-9"

    for r in range(SIZE):
        for c in range(SIZE):
            val = grid[r][c]
            if val == 0:
                continue
            for pr, pc in PEERS[(r, c)]:
                if grid[pr][pc] == val:
                    if pr == r:
                        where = f"row {r + 1}"
                    elif pc == c:
                        where = f"column {c + 1}"
                    else:
                        where = "the same 3x3 box"
                    return False, (f"Duplicate {val} at (row {r + 1}, col {c + 1}) and "
                                   f"(row {pr + 1}, col {pc + 1}) in {where}")
    return True, "Valid"


def load_puzzle(filepath):
    """Read a puzzle file. Return (grid, 'Valid') or (None, error message)."""
    if not os.path.isfile(filepath):
        return None, f"File not found: {filepath}"

    grid = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            row_number = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue                      # ignore blank lines
                row_number += 1
                separator = "," if "," in line else None   # None splits on spaces
                row = [int(x) for x in line.split(separator)]
                if len(row) != SIZE:
                    return None, f"Row {row_number} has {len(row)} values (expected {SIZE})"
                grid.append(row)
    except UnicodeDecodeError:
        return None, "File is not readable text"
    except ValueError:
        return None, "File contains a value that is not an integer"
    except OSError as err:
        return None, f"Could not read file: {err}"

    if len(grid) != SIZE:
        return None, f"Grid has {len(grid)} rows (expected {SIZE})"

    ok, message = validate_grid(grid)
    if not ok:
        return None, message
    return grid, "Valid"


# ----------------------------------------------------------------------------
# Single-puzzle mode
# ----------------------------------------------------------------------------
def solve_file(filepath):
    """Solve one puzzle with MRV+FC and print the result. Return an exit code."""
    grid, message = load_puzzle(filepath)
    if grid is None:
        print(f"Invalid input: {message}")
        return 1

    print("--- Initial grid ---")
    print_grid(grid)

    solver = MRVFCSolver(grid)
    start = time.perf_counter()
    status = solver.solve()
    elapsed_ms = (time.perf_counter() - start) * 1000

    if status == SOLVED and is_valid_solution(solver.grid, grid):
        print("\n--- Solved grid ---")
        print_grid(solver.grid)
        code = 0
    elif status == SOLVED:
        print("\nInternal error: solver output failed verification.")
        code = 3
    else:
        print("\nNo solution exists for this puzzle.")
        code = 2

    print(f"\nTime: {elapsed_ms:.2f} ms | Steps: {solver.steps} | "
          f"Assignments: {solver.assignments} | Backtracks: {solver.backtracks}")
    return code


# ----------------------------------------------------------------------------
# Evaluation harness
# ----------------------------------------------------------------------------
CATEGORY_KEYWORDS = [
    ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("expert", "Expert"),
    ("solved", "Edge case"), ("empty", "Edge case"),
    ("unsolvable", "Edge case"), ("invalid", "Edge case"),
]


def categorise(filename):
    """Guess a difficulty category from the filename (e.g. hard_2.txt -> Hard)."""
    lowered = filename.lower()
    for keyword, label in CATEGORY_KEYWORDS:
        if keyword in lowered:
            return label
    return "Unknown"


def benchmark(make_solver, grid, runs):
    """Run one solver repeatedly on a grid and collect the measurements.

    Steps, assignments and backtracks are deterministic, so the last run's
    values are reported. Time is averaged (and the minimum is kept). A timed
    out solver is run only once.
    """
    times = []
    status = UNSOLVABLE
    solver = None
    for _ in range(runs):
        solver = make_solver(grid)
        start = time.perf_counter()
        status = solver.solve()
        times.append((time.perf_counter() - start) * 1000)
        if status == TIMEOUT:
            break
        if status == SOLVED and not is_valid_solution(solver.grid, grid):
            status = INVALID_OUTPUT
            break
    return {
        "avg_ms": sum(times) / len(times),
        "min_ms": min(times),
        "steps": solver.steps,
        "assignments": solver.assignments,
        "backtracks": solver.backtracks,
        "status": status,
    }


def run_evaluation(folder, runs, cap):
    """Compare both solvers on every puzzle file in a folder and save a CSV."""
    if not os.path.isdir(folder):
        print(f"Puzzle folder not found: {folder}")
        return 1

    files = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith((".txt", ".csv")) and f != RESULTS_FILE)
    if not files:
        print(f"No .txt or .csv puzzle files found in '{folder}'")
        return 1

    header = ["Puzzle", "Category", "Solver", "Avg time (ms)", "Min time (ms)",
              "Steps", "Assignments", "Backtracks", "Status"]
    widths = [22, 10, 9, 13, 13, 9, 11, 10, 14]
    rows = []
    mismatches = 0

    def show(values):
        print(" | ".join(str(v).ljust(w) for v, w in zip(values, widths)))

    show(header)
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))

    try:
        for filename in files:
            grid, message = load_puzzle(os.path.join(folder, filename))
            category = categorise(filename)

            if grid is None:                      # invalid input: report, don't solve
                for solver_name in ("Baseline", "MRV+FC"):
                    row = [filename, category, solver_name, "-", "-", "-", "-", "-",
                           f"INVALID: {message}"]
                    rows.append(row)
                    show(row)
                print("-" * (sum(widths) + 3 * (len(widths) - 1)))
                continue

            base = benchmark(lambda g: BaselineSolver(g, max_steps=cap), grid, runs)
            mrv = benchmark(MRVFCSolver, grid, runs)

            # Where both solvers finished, their verdicts must agree.
            finished = (SOLVED, UNSOLVABLE)
            if base["status"] in finished and mrv["status"] in finished \
                    and base["status"] != mrv["status"]:
                mrv["status"] += "  MISMATCH!"
                mismatches += 1

            for name, res in (("Baseline", base), ("MRV+FC", mrv)):
                timed_out = res["status"] == TIMEOUT
                row = [filename, category, name,
                       f"{res['avg_ms']:.2f}", f"{res['min_ms']:.2f}",
                       f">{cap}" if timed_out else res["steps"],
                       res["assignments"], res["backtracks"], res["status"]]
                rows.append(row)
                show(row)
            print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    finally:
        # Always save what has been collected, even if something goes wrong.
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"\nResults saved to '{RESULTS_FILE}'")

    print(f"Timing: average of {runs} run(s); baseline step cap = {cap}.")
    if mismatches:
        print(f"WARNING: {mismatches} puzzle(s) where the solvers disagree.")
    return 0


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Sudoku solver (backtracking + MRV + forward checking).")
    parser.add_argument("puzzle", nargs="?", help="puzzle file (.txt or .csv) to solve")
    parser.add_argument("--eval", action="store_true", help="run the solver comparison harness")
    parser.add_argument("--folder", default=DEFAULT_PUZZLE_DIR, help="folder of puzzles for --eval")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="timing runs per solver")
    parser.add_argument("--cap", type=int, default=DEFAULT_STEP_CAP, help="baseline step limit")
    args = parser.parse_args()

    if args.eval:
        return run_evaluation(args.folder, max(1, args.runs), max(1, args.cap))
    if args.puzzle:
        return solve_file(args.puzzle)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())