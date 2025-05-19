import sys
from math import sqrt
from pathlib import Path
from typing import Dict, List

INSTANCE_USAGE = """Usage: python verifier.py <instance_file> <solution_file>

Checks that the solution is feasible and recomputes objective, workload, distance metrics."""

# Optional hardcoded list
HARDCODED = [
    (f"Instance_{i}.txt", f"Sol_Instance_{i}.txt")
    for i in [1, 3, 7, 8, 11, 12, 13, 14, 16, 18, 19]
]


def parse_instance(path: Path):
    with path.open() as f:
        lines = [ln for ln in f if ln.strip()]
    n_comm, m_centers = map(int, lines[0].split())
    start = 1
    if lines[1].split()[0] == "0":
        # old format, skip depot
        start = 2
    nodes = []  # (idx, x, y, capacity, population)
    for ln in lines[start:]:
        idx, x, y, cap, pop = ln.split()
        nodes.append((int(idx), float(x), float(y), int(cap), int(pop)))
    capacity = nodes[0][3]  # all same
    coords = {idx: (x, y) for idx, x, y, _, _ in nodes}
    # distance dict including self (0)
    dist = {
        (i, j): sqrt(
            (coords[i][0] - coords[j][0]) ** 2 + (coords[i][1] - coords[j][1]) ** 2
        )
        for i in coords
        for j in coords
    }
    pop = {idx: p for idx, _, _, _, p in nodes}
    return n_comm, m_centers, capacity, dist, pop


def parse_solution(path: Path):
    deployed: List[int] = []
    assignment: Dict[int, List[int]] = {}
    with path.open() as f:
        for ln in f:
            if ln.startswith("Healthcenter deployed at"):
                left, right = ln.strip().split(":")
                center = int(left.split()[-1])
                comm_str = right.split("=")[-1].strip().strip("{}")
                comms = [] if not comm_str else list(map(int, comm_str.split(", ")))
                deployed.append(center)
                assignment[center] = comms
            if ln.startswith("Objective Value"):
                obj_val_reported = float(ln.split(":")[-1])
                break
    return deployed, assignment, obj_val_reported


def verify(instance_file: str, solution_file: str):
    n, m, C, dist, pop = parse_instance(Path(instance_file))
    deployed, assign, obj_rep = parse_solution(Path(solution_file))

    # 0. basic sanity checks
    if len(deployed) > m:
        print(f"ERROR: Too many centers deployed: {len(deployed)} > {m}")
        return

    extra_keys = set(assign.keys()) - set(deployed)
    if extra_keys:
        print(f"ERROR: Assignments to non-deployed centers: {sorted(extra_keys)}")
        return

    # 1. uniqueness & completeness
    all_assigned = [c for lst in assign.values() for c in lst]
    if len(set(all_assigned)) != n:
        print("ERROR: Some communities missing or duplicated in assignments.")
        missing = set(range(1, n + 1)) - set(all_assigned)
        dup = [c for c in all_assigned if all_assigned.count(c) > 1]
        if missing:
            print("Missing:", sorted(missing))
        if dup:
            print("Duplicates:", sorted(set(dup)))
        return

    # 2. capacity feasibility
    for i in deployed:
        load = sum(pop[j] for j in assign[i])
        if load > C:
            print(f"ERROR: Capacity exceeded at center {i}: {load} > {C}")
            return

    # 3. objective value recomputation (max p_j * d(i,j))
    obj = 0.0
    for i in deployed:
        for j in assign[i]:
            obj = max(obj, pop[j] * dist[i, j])
    print(f"Reported objective  : {obj_rep:.10f}")
    print(f"Recomputed objective: {obj:.10f}")

    # 4. workload fairness
    workloads = [sum(pop[j] for j in assign[i]) for i in deployed]
    wl_min, wl_max = min(workloads), max(workloads)
    alpha = round(sum(pop.values()) / (5 * m))
    print(f"Workload gap        : {wl_max - wl_min} (alpha={alpha})")

    # 5. distance fairness metrics
    dists = [dist[i, j] for i in deployed for j in assign[i]]
    d_min, d_max = min(dists), max(dists)
    beta = max(dist[i, j] for i in range(1, n + 1) for j in range(1, i)) / 5
    print(f"Distance gap        : {d_max - d_min:.2f} (beta={beta:.2f})")

    if abs(obj - obj_rep) > 1e-6:
        print("FAIL: Objective mismatch.")
    elif wl_max - wl_min > alpha + 1e-6:
        print("FAIL: Workload gap exceeds alpha.")
    elif d_max - d_min > beta + 1e-6:
        print("FAIL: Distance gap exceeds beta.")
    else:
        print("Solution verified OK.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for inst, sol in HARDCODED:
            print(f"\n=== Verifying {sol} ===")
            root = "FINAL_ROUND_INSTANCES_OPTCHAL2025"
            inst = root + "/" + inst
            sol = root + "/" + sol
            verify(inst, sol)
    elif len(sys.argv) == 3:
        verify(sys.argv[1], sys.argv[2])
    else:
        print(INSTANCE_USAGE)
        sys.exit(1)
