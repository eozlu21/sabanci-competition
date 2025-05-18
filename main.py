#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

from gurobipy import GRB

from health_center_instance import (
    HealthCenterInstancePartOne,
    Distances,
    CombinedTerminationCallback,
)
from model_part_one import build_part_one_model

parser = argparse.ArgumentParser(
    description="Solve or continue optimization for health center instances"
)
parser.add_argument(
    "instances",
    nargs="*",
    type=int,
    help="List of instance IDs to process (e.g., 1 2 3). Defaults to [7] if not provided.",
)
parser.add_argument(
    "-verbose",
    action="store_true",
    help="Enable verbose logging of variables and constraints",
)
args = parser.parse_args()
INSTANCE_IDS = args.instances if args.instances else [11]
VERBOSE = args.verbose


def load_initial_solution(path: Path) -> dict[int, list[int]]:
    pattern = r"Healthcenter deployed at (\d+): Communities Assigned = \{([0-9,\s]*)\}"
    init: dict[int, list[int]] = {}
    for line in path.read_text().splitlines():
        m = re.search(pattern, line)
        if not m:
            continue
        center = int(m.group(1)) - 1
        comms = m.group(2).strip()
        assigned = [int(x) - 1 for x in comms.split(",")] if comms else []
        init[center] = assigned
    return init


def continue_instance(inst_path: Path, init_path: Path, out_path: Path) -> None:
    inst = HealthCenterInstancePartOne(str(inst_path))
    init = load_initial_solution(init_path)
    model = build_part_one_model(inst)
    model.update()
    N = inst.num_communities
    for i in range(N):
        x_var = model.getVarByName(f"x[{i}]")
        x_var.Start = 1 if i in init else 0
        for j in range(N):
            y_var = model.getVarByName(f"y[{i},{j}]")
            y_var.Start = 1 if j in init.get(i, []) else 0
    model.update()
    model.optimize(CombinedTerminationCallback())
    if model.status not in (GRB.OPTIMAL, GRB.INTERRUPTED):
        sys.exit("no solution found or interrupted")
    _write_solution(inst, model, out_path)


def solve_instance(inst_path: Path, output_path: Path) -> None:
    inst = HealthCenterInstancePartOne(str(inst_path))
    model = build_part_one_model(inst)
    model.optimize(CombinedTerminationCallback())
    if model.status not in (GRB.OPTIMAL, GRB.INTERRUPTED):
        print(f"{inst_path.name}: no solution")
        return
    _write_solution(inst, model, output_path)


def _write_solution(
    inst: HealthCenterInstancePartOne, model, output_path: Path
) -> None:
    N = inst.num_communities
    deployed = [i for i in range(N) if model.getVarByName(f"x[{i}]").X > 0.5]
    assignment = {i: [] for i in deployed}
    for i in deployed:
        for j in range(N):
            if model.getVarByName(f"y[{i},{j}]").X > 0.5:
                assignment[i].append(j)
    obj_val = model.getVarByName("D").X
    pop = [node["population"] for node in inst.nodes]
    workloads = [sum(pop[j] for j in assignment[i]) for i in deployed]
    wl_min, wl_max = min(workloads), max(workloads)
    alpha = round(sum(pop) / (5 * inst.num_health_centers))
    dist = Distances(inst)
    dists = [dist[i, j] for i in deployed for j in assignment[i]]
    d_min, d_max = min(dists), max(dists)
    beta = max(dist[i, j] for i in range(N) for j in range(i)) / 5
    with open(output_path, "w") as f:
        for i in deployed:
            comms = ", ".join(str(j + 1) for j in sorted(assignment[i]))
            f.write(
                f"Healthcenter deployed at {i + 1}: Communities Assigned = {{{comms}}}\n"
            )
        f.write(f"\nObjective Value: {obj_val:.10f}\n\n")
        f.write("Workload Fairness Check:\n")
        f.write(f"  Min workload = {wl_min:.2f}, Max workload = {wl_max:.2f}\n")
        f.write(
            f"  Workload Gap = {wl_max - wl_min:.2f} (Threshold Alpha = {alpha})\n\n"
        )
        f.write("Distance Fairness Check:\n")
        f.write(f"  Min Distance = {d_min:.2f}, Max Distance = {d_max:.2f}\n")
        f.write(f"  Distance Gap = {d_max - d_min:.2f} (Threshold Beta = {beta})\n")


def main() -> None:
    instances_dir = Path("FINAL_ROUND_INSTANCES_OPTCHAL2025")
    if not instances_dir.is_dir():
        print("instances directory not found")
        sys.exit(1)
    for idx in INSTANCE_IDS:
        inst_path = instances_dir / f"Instance_{idx}.txt"
        sol_path = instances_dir / f"Sol_Instance_{idx}.txt"
        print(f"Processing {inst_path.name}…")
        if sol_path.exists():
            print("Existing solution found. Continuing optimization.")
            continue_instance(inst_path, sol_path, sol_path)
        else:
            print("No existing solution. Running fresh optimization.")
            solve_instance(inst_path, sol_path)
        print(f"Saved → {sol_path.name}")


if __name__ == "__main__":
    main()
