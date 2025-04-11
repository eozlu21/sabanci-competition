import gurobipy as gp

from health_center_instance import (
    HealthCenterInstancePartOne,
    HealthCenterInstancePartTwo,
)
from model_part_one import build_part_one_model
from model_part_two import build_part_two_model


def solve_and_save_results_part_one(instance_index: int) -> None:
    print("Creating model for instance:", instance_index)
    instance = HealthCenterInstancePartOne(f"instances/Instance_{instance_index}.txt")
    print("Building model...")
    model = build_part_one_model(instance)
    print("Model built successfully.")
    print("Solving...")
    model.optimize()

    if model.status == gp.GRB.OPTIMAL or model.status == gp.GRB.INTERRUPTED:
        deployed_centers = [
            i
            for i in range(instance.num_communities)
            if model.getVarByName(f"x[{i}]").X > 0.5
        ]

        # Map: center i → assigned communities j
        assignment_map = {i: [] for i in deployed_centers}
        for i in deployed_centers:
            for j in range(instance.num_communities):
                if model.getVarByName(f"y[{i},{j}]").X > 0.5:
                    assignment_map[i].append(j)

        save_results_to_file_part_one(
            f"instances/Sol_Instance_{instance_index}.txt",
            deployed_centers,
            assignment_map,
            model.getVarByName("D").X,
        )
    else:
        print("Model did not solve to optimality.")


def save_results_to_file_part_one(
    filename: str,
    deployed_centers: list[int],
    assignment_map: dict[int, list[int]],
    objective_value: float,
) -> None:
    with open(filename, "w") as f:
        f.write("Stage-1:\n")
        for i in deployed_centers:
            communities = ", ".join(str(j + 1) for j in sorted(assignment_map[i]))
            f.write(
                f"Healthcenter deployed at {i + 1}: Communities Assigned = {{{communities}}}\n"
            )
        f.write(f"Objective Value: {objective_value}\n")


def solve_and_save_results_part_two(instance_index: int) -> None:

    instance = HealthCenterInstancePartTwo(
        f"instances/Instance_{instance_index}.txt",
        f"instances/Sol_Instance_{instance_index}.txt",
    )

    model = build_part_two_model(instance)
    model.optimize()
    # Just print all decision variables and objective value
    if model.status == gp.GRB.OPTIMAL or model.status == gp.GRB.INTERRUPTED:
        print("Objective Value:", model.ObjVal)
        for v in model.getVars():
            print(v.VarName, ":", v.X)
    else:
        print("Model did not solve to optimality.")


if __name__ == "__main__":
    # solve_and_save_results_part_one(0)
    solve_and_save_results_part_two(0)
