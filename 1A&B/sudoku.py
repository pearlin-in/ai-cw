import sys
import time
import csv
import os

# Checks if the completed grid is valid and didn't change the original givens
def is_valid_solution(grid, original_grid):
    for r in range(9):
        for c in range(9):
            if original_grid[r][c] != 0 and grid[r][c] != original_grid[r][c]:
                return False
            val = grid[r][c]
            if val < 1 or val > 9: return False
            
            # check row and col
            for i in range(9):
                if i != c and grid[r][i] == val: return False
                if i != r and grid[i][c] == val: return False
                
            # check box
            box_r, box_c = (r // 3) * 3, (c // 3) * 3
            for i in range(box_r, box_r + 3):
                for j in range(box_c, box_c + 3):
                    if (i, j) != (r, c) and grid[i][j] == val: return False
    return True

def precompute_peers():
    # build a list of all 20 neighbors for each cell
    peers = {}
    for r in range(9):
        for c in range(9):
            neighbors = set()
            for i in range(9):
                if i != c: neighbors.add((r, i))
                if i != r: neighbors.add((i, c))
            box_r, box_c = (r // 3) * 3, (c // 3) * 3
            for i in range(box_r, box_r + 3):
                for j in range(box_c, box_c + 3):
                    if (i, j) != (r, c): neighbors.add((i, j))
            peers[(r, c)] = list(neighbors)
    return peers

PEERS = precompute_peers()


# --- Solver 1: Baseline (just plain backtracking for comparison) ---
class BaselineSolver:
    def __init__(self, grid, max_steps=200000):
        self.grid = [row[:] for row in grid]
        self.steps = 0
        self.backtracks = 0
        self.max_steps = max_steps

    def solve(self):
        self.steps = 0
        self.backtracks = 0
        return self._backtrack()

    def _backtrack(self):
        self.steps += 1
        if self.steps > self.max_steps:
            return "TIMEOUT"
            
        # find first empty cell
        cell = None
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    cell = (r, c)
                    break
            if cell: break
            
        if not cell:
            return True
            
        r, c = cell
        for val in range(1, 10):
            # just check if it's valid against peers
            valid = True
            for pr, pc in PEERS[(r, c)]:
                if self.grid[pr][pc] == val:
                    valid = False
                    break
            
            if valid:
                self.grid[r][c] = val
                res = self._backtrack()
                if res is True:
                    return True
                if res == "TIMEOUT":
                    return "TIMEOUT"
                    
                self.grid[r][c] = 0
                self.backtracks += 1 
            
        return False


# --- Solver 2: The MRV + FC approach ---
class MRVFCSolver:
    def __init__(self, grid):
        self.initial_grid = [row[:] for row in grid]
        self.grid = [row[:] for row in grid]
        self.steps = 0
        self.backtracks = 0

    def solve(self):
        self.steps = 0
        self.backtracks = 0
        domains = [[set(range(1, 10)) for _ in range(9)] for _ in range(9)]
        
        # initial forward check
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] != 0:
                    val = self.grid[r][c]
                    domains[r][c] = {val}
                    if not self._forward_check(domains, r, c, val):
                        return False
                        
        return self._backtrack(domains)

    def _forward_check(self, domains, r, c, val):
        for pr, pc in PEERS[(r, c)]:
            if self.grid[pr][pc] == 0:
                if val in domains[pr][pc]:
                    domains[pr][pc].remove(val)
                    if not domains[pr][pc]:
                        return False
        return True

    def _find_best_cell(self, domains):
        # MRV: pick cell with fewest remaining values
        best_cell = None
        min_size = 10
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0 and len(domains[r][c]) < min_size:
                    min_size = len(domains[r][c])
                    best_cell = (r, c)
                    if min_size == 1:
                        return best_cell
        return best_cell

    def _backtrack(self, domains):
        self.steps += 1
        
        cell = self._find_best_cell(domains)
        if cell is None:
            return True
            
        r, c = cell
        for val in sorted(domains[r][c]):
            # deep copy domains so we don't mess up the parent
            child_domains = [[set(d) for d in row] for row in domains]
            child_domains[r][c] = {val}
            self.grid[r][c] = val
            
            if self._forward_check(child_domains, r, c, val):
                if self._backtrack(child_domains):
                    return True
            
            self.backtracks += 1
            self.grid[r][c] = 0
            
        return False


# --- I/O and validation ---
def validate_grid(grid):
    for r in range(9):
        for c in range(9):
            val = grid[r][c]
            if val < 0 or val > 9:
                return False, f"Out-of-bounds {val} at row {r+1}, col {c+1}"
            if val != 0:
                for i in range(9):
                    if i != c and grid[r][i] == val:
                        return False, f"Duplicate {val} in row {r+1}"
                    if i != r and grid[i][c] == val:
                        return False, f"Duplicate {val} in col {c+1}"
                box_r, box_c = (r // 3) * 3, (c // 3) * 3
                for i in range(box_r, box_r + 3):
                    for j in range(box_c, box_c + 3):
                        if (i, j) != (r, c) and grid[i][j] == val:
                            return False, f"Duplicate {val} in box at row {r+1}, col {c+1}"
    return True, "Valid"

def load_puzzle(filepath):
    if not os.path.exists(filepath):
        return None, f"File not found: {filepath}"
        
    grid = []
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line: continue
                if ',' in line:
                    row = [int(x.strip()) for x in line.split(',')]
                else:
                    row = [int(x) for x in line.split()]
                if len(row) != 9:
                    return None, f"Row {line_num} has {len(row)} numbers (expected 9)"
                grid.append(row)
        if len(grid) != 9:
            return None, f"Grid has {len(grid)} rows (expected 9)"
    except ValueError:
        return None, "File contains non-integer characters"
        
    is_valid, msg = validate_grid(grid)
    if not is_valid:
        return None, msg
        
    return grid, "Valid"


# --- Evaluation harness ---
def run_evaluation(puzzle_files):
    results = []
    
    print(f"{'Puzzle':<15} | {'Solver':<10} | {'Time (ms)':<10} | {'Steps':<8} | {'Backtracks':<10} | {'Status'}")
    print("-" * 80)
    
    for filepath in puzzle_files:
        grid, msg = load_puzzle(filepath)
        filename = os.path.basename(filepath)
        
        if not grid:
            print(f"{filename:<15} | INVALID    | {'-':<10} | {'-':<8} | {'-':<10} | {msg}")
            results.append([filename, "Baseline", "ERROR", "-", "-", msg])
            results.append([filename, "MRV+FC", "ERROR", "-", "-", msg])
            continue
            
        # Baseline (3 runs)
        base_times, base_steps, base_bt, base_status = [], 0, 0, ""
        base_max_steps = 200000
        for _ in range(3):
            base_solver = BaselineSolver(grid)
            start = time.perf_counter()
            res = base_solver.solve()
            base_times.append((time.perf_counter() - start) * 1000)
            base_steps, base_bt = base_solver.steps, base_solver.backtracks
            base_max_steps = base_solver.max_steps
            if res == "TIMEOUT":
                base_status = "TIMEOUT"
                break
            elif res and not is_valid_solution(base_solver.grid, grid):
                base_status = "INVALID"
                break
            else:
                base_status = "Solved" if res else "No Solution"
        
        avg_base_ms = sum(base_times) / len(base_times) if base_times else 0
        
        # MRV+FC (3 runs)
        mrv_times, mrv_steps, mrv_bt, mrv_status = [], 0, 0, ""
        for _ in range(3):
            mrv_solver = MRVFCSolver(grid)
            start = time.perf_counter()
            res = mrv_solver.solve()
            mrv_times.append((time.perf_counter() - start) * 1000)
            mrv_steps, mrv_bt = mrv_solver.steps, mrv_solver.backtracks
            if res and not is_valid_solution(mrv_solver.grid, grid):
                mrv_status = "INVALID"
                break
            else:
                mrv_status = "Solved" if res else "No Solution"
                
        avg_mrv_ms = sum(mrv_times) / len(mrv_times) if mrv_times else 0
        
        base_step_str = f">{base_max_steps}" if base_status == "TIMEOUT" else str(base_steps)
        
        print(f"{filename:<15} | Baseline   | {avg_base_ms:<10.2f} | {base_step_str:<8} | {base_bt:<10} | {base_status}")
        print(f"{filename:<15} | MRV + FC   | {avg_mrv_ms:<10.2f} | {mrv_steps:<8} | {mrv_bt:<10} | {mrv_status}")
        print("-" * 80)
        
        results.append([filename, "Baseline", f"{avg_base_ms:.2f}", base_step_str, base_bt, base_status])
        results.append([filename, "MRV+FC", f"{avg_mrv_ms:.2f}", mrv_steps, mrv_bt, mrv_status])
        
    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Puzzle", "Solver", "Time (ms)", "Steps", "Backtracks", "Status"])
        writer.writerows(results)
    print(f"\nResults saved to 'results.csv'")


# --- Main ---
if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--eval":
        test_puzzles = ["easy1.txt", "medium1.txt", "hard1.txt", "expert1.txt", "unsolvable.txt", "invalid.txt"]
        run_evaluation(test_puzzles)
        
    elif len(sys.argv) == 2:
        filepath = sys.argv[1]
        grid, msg = load_puzzle(filepath)
        
        if not grid:
            print(f"Invalid Input: {msg}")
            sys.exit(1)
            
        print("--- Initial Grid ---")
        for r in range(9):
            print(" ".join(str(x) if x != 0 else "." for x in grid[r]))
            
        solver = MRVFCSolver(grid)
        start_time = time.perf_counter()
        is_solved = solver.solve()
        end_time = time.perf_counter()
        
        if is_solved and is_valid_solution(solver.grid, grid):
            print("\n--- Solved Grid ---")
            for r in range(9):
                print(" ".join(str(x) for x in solver.grid[r]))
            print(f"\nStatus: SOLVED (Time: {(end_time - start_time)*1000:.2f}ms, Steps: {solver.steps}, Backtracks: {solver.backtracks})")
        elif is_solved and not is_valid_solution(solver.grid, grid):
            print("\nError: Solver output failed validation.")
        else:
            print("\nStatus: NO SOLUTION EXISTS")
            
    else:
        print("Usage:")
        print("  python sudoku_solver.py <puzzle_file.txt>   (solves one file)")
        print("  python sudoku_solver.py --eval              (runs evaluation harness)")