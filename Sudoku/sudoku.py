import sys
import time
import csv
import os


def build_peers():
    # for each cell, the 20 other cells in the same row, column or box
    peers = {}
    for r in range(9):
        for c in range(9):
            p = set()
            for i in range(9):
                if i != c:
                    p.add((r, i))
                if i != r:
                    p.add((i, c))
            br, bc = (r // 3) * 3, (c // 3) * 3
            for i in range(br, br + 3):
                for j in range(bc, bc + 3):
                    if (i, j) != (r, c):
                        p.add((i, j))
            peers[(r, c)] = list(p)
    return peers


PEERS = build_peers()


# ---------- Solver: backtracking + MRV + forward checking ----------

class Solver:
    def __init__(self, grid):
        self.grid = [row[:] for row in grid]
        self.steps = 0        # number of calls to search()
        self.backtracks = 0   # number of values tried and then undone

    def solve(self):
        self.steps = 0
        self.backtracks = 0
        domains = [[set(range(1, 10)) for _ in range(9)] for _ in range(9)]

        # apply the given numbers first
        for r in range(9):
            for c in range(9):
                v = self.grid[r][c]
                if v != 0:
                    domains[r][c] = {v}
                    if not self.forward_check(domains, r, c, v):
                        return False
        return self.search(domains)

    def forward_check(self, domains, r, c, v):
        # remove v from the domain of every empty peer; fail if one becomes empty
        for pr, pc in PEERS[(r, c)]:
            if self.grid[pr][pc] == 0 and v in domains[pr][pc]:
                domains[pr][pc].remove(v)
                if not domains[pr][pc]:
                    return False
        return True

    def pick_cell(self, domains):
        # MRV: the empty cell with the fewest values left
        best = None
        best_size = 10
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0 and len(domains[r][c]) < best_size:
                    best = (r, c)
                    best_size = len(domains[r][c])
                    if best_size == 1:
                        return best
        return best

    def search(self, domains):
        self.steps += 1
        cell = self.pick_cell(domains)
        if cell is None:
            return True  # no empty cells left

        r, c = cell
        for v in sorted(domains[r][c]):
            # each branch gets its own copy of the domains
            new_domains = [[set(d) for d in row] for row in domains]
            new_domains[r][c] = {v}
            self.grid[r][c] = v

            if self.forward_check(new_domains, r, c, v):
                if self.search(new_domains):
                    return True

            self.grid[r][c] = 0
            self.backtracks += 1
        return False


# ---------- Checking and input ----------

def is_valid_solution(grid, original):
    # givens must be unchanged
    for r in range(9):
        for c in range(9):
            if original[r][c] != 0 and grid[r][c] != original[r][c]:
                return False
    digits = set(range(1, 10))
    for i in range(9):
        if set(grid[i]) != digits:
            return False
        if set(grid[r][i] for r in range(9)) != digits:
            return False
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            box = set(grid[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3))
            if box != digits:
                return False
    return True


def validate_grid(grid):
    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v < 0 or v > 9:
                return False, f"Value {v} at row {r+1}, col {c+1} is not between 0 and 9"
            if v != 0:
                for pr, pc in PEERS[(r, c)]:
                    if grid[pr][pc] == v:
                        return False, f"Digit {v} at row {r+1}, col {c+1} repeats in its row, column or box"
    return True, "Valid"


def load_puzzle(filepath):
    if not os.path.exists(filepath):
        return None, f"File not found: {filepath}"

    grid = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",") if "," in line else line.split()
                try:
                    row = [int(x.strip()) for x in parts]
                except ValueError:
                    return None, f"Line {line_num} contains a non-integer value"
                if len(row) != 9:
                    return None, f"Line {line_num} has {len(row)} values (expected 9)"
                grid.append(row)
    except UnicodeDecodeError:
        return None, "File could not be read as text"

    if len(grid) != 9:
        return None, f"Grid has {len(grid)} rows (expected 9)"

    ok, msg = validate_grid(grid)
    if not ok:
        return None, msg
    return grid, "Valid"


def print_grid(grid):
    for r in range(9):
        if r % 3 == 0 and r != 0:
            print("------+-------+------")
        row = ""
        for c in range(9):
            if c % 3 == 0 and c != 0:
                row += "| "
            row += (str(grid[r][c]) if grid[r][c] != 0 else ".") + " "
        print(row.rstrip())


# ---------- Evaluation ----------

def run_evaluation(files, runs=3):
    print(f"{'Puzzle':<18} {'Empty':<6} {'Time (ms)':<10} {'Steps':<8} {'Backtracks':<11} Status")
    print("-" * 70)
    rows = []

    for path in files:
        name = os.path.basename(path)
        grid, msg = load_puzzle(path)
        if grid is None:
            print(f"{name:<18} {'-':<6} {'-':<10} {'-':<8} {'-':<11} INVALID INPUT: {msg}")
            rows.append([name, "-", "-", "-", "-", "ERROR: " + msg])
            continue

        empty = sum(row.count(0) for row in grid)
        times = []
        for _ in range(runs):
            solver = Solver(grid)
            start = time.perf_counter()
            solved = solver.solve()
            times.append((time.perf_counter() - start) * 1000)

        # steps and backtracks are the same every run, so use the last one
        if solved and not is_valid_solution(solver.grid, grid):
            status = "INVALID OUTPUT"
        elif solved:
            status = "Solved"
        else:
            status = "No solution"

        avg = sum(times) / len(times)
        print(f"{name:<18} {empty:<6} {avg:<10.2f} {solver.steps:<8} {solver.backtracks:<11} {status}")
        rows.append([name, empty, f"{avg:.2f}", solver.steps, solver.backtracks, status])

    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Puzzle", "Empty cells", "Avg time (ms)", "Steps", "Backtracks", "Status"])
        writer.writerows(rows)
    print("\nResults saved to results.csv")


# ---------- Main ----------

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--eval":
        puzzles = ["easy1.txt", "medium1.txt", "hard1.txt", "expert1.txt",
                   "killer.txt", "unsolvable.txt", "unsolvable2.txt", "invalid.txt"]
        run_evaluation(puzzles)

    elif len(sys.argv) == 2:
        grid, msg = load_puzzle(sys.argv[1])
        if grid is None:
            print(f"Invalid input: {msg}")
            sys.exit(1)

        print("--- Puzzle ---")
        print_grid(grid)

        solver = Solver(grid)
        start = time.perf_counter()
        solved = solver.solve()
        elapsed = (time.perf_counter() - start) * 1000

        if solved and is_valid_solution(solver.grid, grid):
            print("\n--- Solution ---")
            print_grid(solver.grid)
            print(f"\nSolved in {elapsed:.2f} ms ({solver.steps} steps, {solver.backtracks} backtracks)")
        elif solved:
            print("\nError: the solver's answer failed the final check.")
        else:
            print("\nNo solution exists for this puzzle.")

    else:
        print("Usage:")
        print("  python sudoku_solver.py <puzzle_file>   solve one puzzle (.txt or .csv)")
        print("  python sudoku_solver.py --eval          run the evaluation and write results.csv")