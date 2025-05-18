#!/usr/bin/env python3
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
    with open(out_path, "w") as f:
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


if __name__ == "__main__":
    root_path = Path("FINAL_ROUND_INSTANCES_OPTCHAL2025")
    idx = 7
    instance_path = root_path / Path(f"Instance_{idx}.txt")
    init_path = root_path / Path(f"Sol_Instance_{idx}.txt")
    output_path = root_path / Path(f"Sol_Instance_{idx}.txt")
    continue_instance(instance_path, init_path, output_path)
