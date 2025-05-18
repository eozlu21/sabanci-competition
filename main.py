import sys
from pathlib import Path

from gurobipy import GRB

from health_center_instance import (
    HealthCenterInstancePartOne,
    Distances,
    CombinedTerminationCallback,
)
from model_part_one import build_part_one_model

# Enable verbose logging if '-verbose' flag is passed
VERBOSE = "-verbose" in sys.argv

# List of instance IDs to solve (hardcoded)
INSTANCE_IDS = [1, 3, 7, 8, 11, 12, 13, 14, 16, 18, 19]


def solve_instance(instance_path: Path, output_path: Path) -> None:
    inst = HealthCenterInstancePartOne(str(instance_path))
    model = build_part_one_model(inst)

    model.optimize(CombinedTerminationCallback())

    if model.status not in (GRB.OPTIMAL, GRB.INTERRUPTED):
        print(f"{instance_path.name}: no solution")
        return

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

    # write standard solution
    with open(output_path, "w") as f:
        for i in deployed:
            comms = ", ".join(str(j + 1) for j in sorted(assignment[i]))
            f.write(
                f"Healthcenter deployed at {i + 1}: Communities Assigned = {{{comms}}}\n"
            )
        f.write(f"\nObjective Value: {obj_val:.10f}\n\n")
        f.write("Workload Fairness Check:\n")
        f.write(
            f"  Min workload = {wl_min:.2f}, Max workload = {wl_max:.2f}\n"
            f"  Workload Gap = {wl_max - wl_min:.2f} (Threshold Alpha = {alpha})\n"
        )
        f.write("\n\n")
        f.write("Distance Fairness Check:\n")
        f.write(
            f"  Min Distance = {d_min:.2f}, Max Distance = {d_max:.2f}\n"
            f"  Distance Gap = {d_max - d_min:.2f} (Threshold Beta = {beta})\n"
        )

    # verbose: write detailed vars & constraints
    if VERBOSE:
        vars_path = output_path.with_name(output_path.stem + "_vars.txt")
        with open(vars_path, "w") as vf:
            vf.write("# Variable values:\n")
            for v in model.getVars():
                vf.write(f"{v.VarName} = {v.X}\n")
            vf.write("\n# Constraints and evaluated LHS vs RHS:\n")
            for c in model.getConstrs():
                row = model.getRow(c)
                n = row.size()
                terms = []
                for k in range(n):
                    var_k = row.getVar(k)
                    coef_k = row.getCoeff(k)
                    terms.append(f"{coef_k}*{var_k.VarName}")
                expr = " + ".join(terms)
                sense = (
                    "<="
                    if c.Sense == GRB.LESS_EQUAL
                    else "==" if c.Sense == GRB.EQUAL else ">="
                )
                rhs = c.RHS
                lhs_val = sum(row.getCoeff(i) * row.getVar(i).X for i in range(n))
                vf.write(f"{expr} {sense} {rhs}\n")
                vf.write(f"{lhs_val} {sense} {rhs}\n\n")
        print(f"Verbose log written to {vars_path}")


def main() -> None:
    instances_dir = Path("FINAL_ROUND_INSTANCES_OPTCHAL2025")
    if not instances_dir.is_dir():
        print("instances directory not found")
        sys.exit(1)

    for idx in INSTANCE_IDS:
        inst_path = instances_dir / f"Instance_{idx}.txt"
        out_path = instances_dir / f"Sol_Instance_{idx}.txt"
        print(f"Solving {inst_path.name} …")
        solve_instance(inst_path, out_path)
        print(f"Saved → {out_path.name}")


if __name__ == "__main__":
    main()
