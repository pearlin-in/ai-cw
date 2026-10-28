"""Sudoku solver using backtracking search and CSP techniques.
 
The chosen approach is backtracking + forward checking + MRV (mode "fc_mrv").
Two weaker modes, plain backtracking ("bt") and forward checking with a fixed
cell order ("fc"), are included only as baselines for the quantitative
comparison in the report.
 
Usage: see usage() at the bottom of this file, or README.md.
"""
 
import sys
import time
import csv
import os
 
MODES = {
    "bt": "Plain backtracking",
    "fc": "Forward checking",
    "fc_mrv": "Forward checking + MRV",
}
DEFAULT_MODE = "fc_mrv"   # the approach chosen for the report
TIME_LIMIT = 30           # seconds allowed per run in --eval / --compare / GUI
 
 
def build_peers():
    """Return {(r, c): [20 other cells in the same row, column or box]}."""
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
 
 
# ---------- Solver ----------
 
class SearchTimeout(Exception):
    """Raised inside the search when the time limit is exceeded."""
 
 
class Solver:
    """Backtracking Sudoku solver with three selectable strategies.
 
    bt     : plain backtracking, first empty cell, values checked on assignment
    fc     : backtracking + forward checking, first empty cell
    fc_mrv : backtracking + forward checking + minimum remaining values
 
    The grid passed in must already be valid (see validate_grid).
    """
 
    def __init__(self, grid, mode=DEFAULT_MODE, time_limit=None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        self.original = [row[:] for row in grid]
        self.grid = [row[:] for row in grid]
        self.mode = mode
        self.time_limit = time_limit
        self.steps = 0         # number of calls to search()
        self.backtracks = 0    # number of values tried and then undone
        self.timed_out = False
        self.deadline = None
 
    def solve(self):
        """Solve the puzzle. Returns True if solved, False if no solution
        (or if the time limit was hit; check self.timed_out)."""
        self.steps = 0
        self.backtracks = 0
        self.timed_out = False
        self.grid = [row[:] for row in self.original]
        self.deadline = (time.perf_counter() + self.time_limit
                         if self.time_limit is not None else None)
 
        domains = None
        if self.mode != "bt":
            domains = [[set(range(1, 10)) for _ in range(9)] for _ in range(9)]
            # apply the given numbers first
            for r in range(9):
                for c in range(9):
                    v = self.grid[r][c]
                    if v != 0:
                        domains[r][c] = {v}
                        if not self.forward_check(domains, r, c, v):
                            return False
        try:
            return self.search(domains)
        except SearchTimeout:
            self.timed_out = True
            self.grid = [row[:] for row in self.original]
            return False
 
    def forward_check(self, domains, r, c, v):
        """Remove v from the domain of every empty peer of (r, c).
        Returns False if some peer is left with an empty domain."""
        for pr, pc in PEERS[(r, c)]:
            if self.grid[pr][pc] == 0 and v in domains[pr][pc]:
                domains[pr][pc].remove(v)
                if not domains[pr][pc]:
                    return False
        return True
 
    def pick_cell(self, domains):
        """Choose the next empty cell: first in row order, or MRV in fc_mrv."""
        if self.mode != "fc_mrv":
            for r in range(9):
                for c in range(9):
                    if self.grid[r][c] == 0:
                        return (r, c)
            return None
 
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
        """Recursive backtracking search. Returns True when the grid is full."""
        self.steps += 1
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise SearchTimeout()
 
        cell = self.pick_cell(domains)
        if cell is None:
            return True  # no empty cells left
 
        r, c = cell
 
        if self.mode == "bt":
            # plain backtracking: only check consistency when assigning
            used = {self.grid[pr][pc] for pr, pc in PEERS[(r, c)]}
            for v in range(1, 10):
                if v in used:
                    continue
                self.grid[r][c] = v
                if self.search(None):
                    return True
                self.grid[r][c] = 0
                self.backtracks += 1
            return False
 
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
    """True if grid is a complete Sudoku solution that keeps all givens."""
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
    """Check values are 0-9 and no given digit repeats. Returns (ok, message)."""
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
    """Read a 9x9 grid from a .txt (spaces) or .csv (commas) file.
    Returns (grid, "Valid") or (None, error message)."""
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
    """Print the grid with box separators; empty cells shown as '.'."""
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
 
def measure(grid, mode, runs=3, time_limit=TIME_LIMIT):
    """Solve grid `runs` times with `mode`.
    Returns (avg time in ms, steps, backtracks, status)."""
    times = []
    solver = None
    solved = False
    for _ in range(runs):
        solver = Solver(grid, mode, time_limit)
        start = time.perf_counter()
        solved = solver.solve()
        times.append((time.perf_counter() - start) * 1000)
        if solver.timed_out:
            break  # no point repeating a timed-out run
 
    # steps and backtracks are the same every run, so use the last one
    if solver.timed_out:
        status = f"Timeout (>{time_limit}s)"
    elif solved and not is_valid_solution(solver.grid, grid):
        status = "INVALID OUTPUT"
    elif solved:
        status = "Solved"
    else:
        status = "No solution"
    return sum(times) / len(times), solver.steps, solver.backtracks, status
 
 
def run_evaluation(files, runs=3, time_limit=TIME_LIMIT):
    """Evaluate the chosen solver (fc_mrv) on each file; write results.csv."""
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
        avg, steps, backtracks, status = measure(grid, DEFAULT_MODE, runs, time_limit)
        print(f"{name:<18} {empty:<6} {avg:<10.2f} {steps:<8} {backtracks:<11} {status}")
        rows.append([name, empty, f"{avg:.2f}", steps, backtracks, status])
 
    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Puzzle", "Empty cells", "Avg time (ms)", "Steps", "Backtracks", "Status"])
        writer.writerows(rows)
    print("\nResults saved to results.csv")
 
 
def run_comparison(files, runs=3, time_limit=TIME_LIMIT):
    """Compare all three modes on each file; write comparison.csv."""
    print(f"{'Puzzle':<16} {'Method':<24} {'Time (ms)':<11} {'Steps':<9} {'Backtracks':<11} Status")
    print("-" * 84)
    rows = []
 
    for path in files:
        name = os.path.basename(path)
        grid, msg = load_puzzle(path)
        if grid is None:
            print(f"{name:<16} skipped (invalid input: {msg})")
            continue
        for mode, label in MODES.items():
            avg, steps, backtracks, status = measure(grid, mode, runs, time_limit)
            print(f"{name:<16} {label:<24} {avg:<11.2f} {steps:<9} {backtracks:<11} {status}")
            rows.append([name, label, f"{avg:.2f}", steps, backtracks, status])
        print()
 
    with open("comparison.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Puzzle", "Method", "Avg time (ms)", "Steps", "Backtracks", "Status"])
        writer.writerows(rows)
    print("Results saved to comparison.csv")
 
 
# ---------- GUI ----------
 
def launch_gui():
    """Small Tkinter front end: Load, Solve, Clear and a method selector."""
    import tkinter as tk
    from tkinter import filedialog, messagebox
 
    root = tk.Tk()
    root.title("Sudoku Solver")
 
    only_digit = root.register(lambda p: p == "" or (len(p) == 1 and p in "123456789"))
    cells = [[None] * 9 for _ in range(9)]
 
    board = tk.Frame(root, padx=10, pady=10)
    board.pack()
    for r in range(9):
        for c in range(9):
            e = tk.Entry(board, width=2, font=("Arial", 20), justify="center",
                         validate="key", validatecommand=(only_digit, "%P"))
            # extra spacing marks the 3x3 box boundaries
            e.grid(row=r, column=c, ipady=4,
                   padx=(6 if c % 3 == 0 and c else 1, 1),
                   pady=(6 if r % 3 == 0 and r else 1, 1))
            cells[r][c] = e
 
    def read_grid():
        return [[int(cells[r][c].get() or 0) for c in range(9)] for r in range(9)]
 
    def show_grid(grid, givens=None):
        for r in range(9):
            for c in range(9):
                cells[r][c].delete(0, tk.END)
                if grid[r][c] != 0:
                    cells[r][c].insert(0, str(grid[r][c]))
                is_given = givens is None or givens[r][c] != 0
                cells[r][c].config(fg="black" if is_given else "blue")
 
    def on_load():
        path = filedialog.askopenfilename(filetypes=[("Sudoku files", "*.txt *.csv")])
        if not path:
            return
        grid, msg = load_puzzle(path)
        if grid is None:
            messagebox.showerror("Invalid puzzle", msg)
            return
        show_grid(grid)
        status.config(text=f"Loaded {os.path.basename(path)}")
 
    def on_solve():
        grid = read_grid()
        ok, msg = validate_grid(grid)
        if not ok:
            messagebox.showerror("Invalid puzzle", msg)
            return
        mode = [k for k, v in MODES.items() if v == method.get()][0]
        solver = Solver(grid, mode, TIME_LIMIT)
        start = time.perf_counter()
        solved = solver.solve()
        elapsed = (time.perf_counter() - start) * 1000
        if solver.timed_out:
            status.config(text=f"Timed out after {TIME_LIMIT}s")
        elif solved and is_valid_solution(solver.grid, grid):
            show_grid(solver.grid, givens=grid)
            status.config(text=f"Solved in {elapsed:.2f} ms "
                               f"({solver.steps} steps, {solver.backtracks} backtracks)")
        elif solved:
            status.config(text="Error: the answer failed the final check")
        else:
            status.config(text="No solution exists for this puzzle")
 
    def on_clear():
        show_grid([[0] * 9 for _ in range(9)])
        status.config(text="")
 
    controls = tk.Frame(root, pady=5)
    controls.pack()
    tk.Button(controls, text="Load", width=8, command=on_load).pack(side="left", padx=4)
    tk.Button(controls, text="Solve", width=8, command=on_solve).pack(side="left", padx=4)
    tk.Button(controls, text="Clear", width=8, command=on_clear).pack(side="left", padx=4)
 
    method = tk.StringVar(value=MODES[DEFAULT_MODE])
    tk.OptionMenu(controls, method, *MODES.values()).pack(side="left", padx=4)
 
    status = tk.Label(root, text="", pady=5)
    status.pack()
    root.mainloop()
 
 
# ---------- Main ----------
 
def usage():
    print("Usage:")
    print("  python sudoku_solver.py <puzzle_file> [--mode bt|fc|fc_mrv]   solve one puzzle (.txt or .csv)")
    print("  python sudoku_solver.py --eval [--timeout N]      evaluate the chosen solver, write results.csv")
    print("  python sudoku_solver.py --compare [--timeout N]   compare all three methods, write comparison.csv")
    print("  python sudoku_solver.py --gui                     open the graphical interface")
 
 
def solve_file(path, mode):
    """Load a puzzle, solve it and print the result."""
    grid, msg = load_puzzle(path)
    if grid is None:
        print(f"Invalid input: {msg}")
        sys.exit(1)
 
    print("--- Puzzle ---")
    print_grid(grid)
 
    solver = Solver(grid, mode)
    start = time.perf_counter()
    solved = solver.solve()
    elapsed = (time.perf_counter() - start) * 1000
 
    if solved and is_valid_solution(solver.grid, grid):
        print("\n--- Solution ---")
        print_grid(solver.grid)
        print(f"\nSolved with {MODES[mode]} in {elapsed:.2f} ms "
              f"({solver.steps} steps, {solver.backtracks} backtracks)")
    elif solved:
        print("\nError: the solver's answer failed the final check.")
    else:
        print("\nNo solution exists for this puzzle.")
 
 
def pop_option(args, name, default):
    """Remove `name value` from args and return value (or default)."""
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            usage()
            sys.exit(1)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default
 
 
def main():
    args = sys.argv[1:]
    mode = pop_option(args, "--mode", DEFAULT_MODE)
    timeout = pop_option(args, "--timeout", str(TIME_LIMIT))
    try:
        timeout = float(timeout)
    except ValueError:
        usage()
        sys.exit(1)
    if mode not in MODES:
        print(f"Unknown mode '{mode}'. Choose from: {', '.join(MODES)}")
        sys.exit(1)
 
    puzzles = ["easy1.txt", "medium1.txt", "hard1.txt", "expert1.txt",
               "killer.txt", "unsolvable.txt", "unsolvable2.txt", "invalid.txt"]
 
    if args == ["--eval"]:
        run_evaluation(puzzles, time_limit=timeout)
    elif args == ["--compare"]:
        run_comparison(puzzles, time_limit=timeout)
    elif args == ["--gui"]:
        launch_gui()
    elif len(args) == 1 and not args[0].startswith("--"):
        solve_file(args[0], mode)
    else:
        usage()
 
 
if __name__ == "__main__":
    main()
