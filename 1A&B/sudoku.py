import sys
import time
import csv
import os

# ==========================================
# 1. INDEPENDENT SOLUTION CHECKER
# ==========================================
def is_valid_solution(grid, original_grid):
    """Verifies that the solved grid is correct and preserves the givens."""
    for r in range(9):
        for c in range(9):
            if original_grid[r][c] != 0 and grid[r][c] != original_grid[r][c]:
                return False
            val = grid[r][c]
            if val < 1 or val > 9: return False
            for i in range(9):
                if i != c and grid[r][i] == val: return False
                if i != r and grid[i][c] == val: return False
            box_r, box_c = (r // 3) * 3, (c // 3) * 3
            for i in range(box_r, box_r + 3):
                for j in range(box_c, box_c + 3):
                    if (i, j) != (r, c) and grid[i][j] == val: return False
    return True

# ==========================================
# 2. SHARED UTILITIES
# ==========================================
def precompute_peers():
    """Computes the 20 peers for every cell once, to share between solvers."""
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

# ==========================================
# 3. SOLVER A: BASELINE (Plain Backtracking)
# ==========================================
class BaselineSolver:
    def __init__(self, grid, max_steps=1000000):
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
                    
                # Fair counter: only count actual undos
                self.grid[r][c] = 0
                self.backtracks += 1 
            
        return False

# ==========================================
# 4. SOLVER B: CHOSEN APPROACH (MRV + FC)
# ==========================================
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
        
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] != 0:
                    val = self.grid[r][c]
                    domains[r][c] = {val}
                    # Initial forward check
                    if not self._forward_check(domains, r, c, val):
                        return False
                        
        return self._backtrack(domains)

    def _forward_check(self, domains, r, c, val):
        for pr, pc in PEERS[(r, c)]:
            if self.grid[pr][pc] == 0: # Skip assigned
                if val in domains[pr][pc]:
                    domains[pr][pc].remove(val)
                    if not domains[pr][pc]:
                        return False
        return True

    def _select_unassigned_variable(self, domains):
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
        
        cell = self._select_unassigned_variable(domains)
        if cell is None:
            return True
            
        r, c = cell
        for val in sorted(domains[r][c]):
            # Copy-on-branch
            child_domains = [[set(d) for d in row] for row in domains]
            child_domains[r][c] = {val}
            self.grid[r][c] = val
            
            if self._forward_check(child_domains, r, c, val):
                if self._backtrack(child_domains):
                    return True
            
            # Fair counter: only count actual undos
            self.backtracks += 1
            self.grid[r][c] = 0
            
        return False

# ==========================================
# 5. I/O AND VALIDATION
# ==========================================
def validate_grid(grid):
    """Explicitly checks ranges and duplicates in rows, cols, boxes."""
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

# ==========================================
# 6. EVALUATION HARNESS
# ==========================================
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
            
        # Test Baseline (Average of 3 runs)
        base_times, base_steps, base_bt, base_status = [], 0, 0, ""
        for _ in range(3):
            solver = BaselineSolver(grid)
            start = time.perf_counter()
            res = solver.solve()
            base_times.append((time.perf_counter() - start) * 1000)
            base_steps, base_bt = solver.steps, solver.backtracks
            if res == "TIMEOUT":
                base_status = "TIMEOUT"
                break
            elif res and not is_valid_solution(solver.grid, grid):
                base_status = "INVALID"
                break
            else:
                base_status = "Solved" if res else "No Solution"
        
        avg_base_ms = sum(base_times) / len(base_times) if base_times else 0
        
        # Test MRV+FC (Average of 3 runs)
        mrv_times, mrv_steps, mrv_bt, mrv_status = [], 0, 0, ""
        for _ in range(3):
            solver = MRVFCSolver(grid)
            start = time.perf_counter()
            res = solver.solve()
            mrv_times.append((time.perf_counter() - start) * 1000)
            mrv_steps, mrv_bt = solver.steps, solver.backtracks
            if res and not is_valid_solution(solver.grid, grid):
                mrv_status = "INVALID"
                break
            else:
                mrv_status = "Solved" if res else "No Solution"
                
        avg_mrv_ms = sum(mrv_times) / len(mrv_times) if mrv_times else 0
        
        # Print and save
        print(f"{filename:<15} | Baseline   | {avg_base_ms:<10.2f} | {base_steps:<8} | {base_bt:<10} | {base_status}")
        print(f"{filename:<15} | MRV + FC   | {avg_mrv_ms:<10.2f} | {mrv_steps:<8} | {mrv_bt:<10} | {mrv_status}")
        print("-" * 80)
        
        results.append([filename, "Baseline", f"{avg_base_ms:.2f}", base_steps, base_bt, base_status])
        results.append([filename, "MRV+FC", f"{avg_mrv_ms:.2f}", mrv_steps, mrv_bt, mrv_status])
        
    # Write to CSV
    with open("results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Puzzle", "Solver", "Time (ms)", "Steps", "Backtracks", "Status"])
        writer.writerows(results)
    print(f"\nResults saved to 'results.csv'")

# ==========================================
# 7. MAIN ENTRY POINT
# ==========================================
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