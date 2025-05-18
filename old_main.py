from gurobipy import GRB

from health_center_instance import (
    HealthCenterInstancePartOne,
    HealthCenterInstancePartTwo,
    CustomTerminationCallback,
    TimeAfterFirstSolutionCallback,
)
from model_part_one import build_part_one_model
from model_part_two import build_part_two_model


def _solve_and_save_results_part_one(instance_index: int) -> None:
    print("Creating model for instance:", instance_index)
    instance = HealthCenterInstancePartOne(f"instances/Instance_{instance_index}.txt")
    print("Building model...")
    model = build_part_one_model(instance)
    print("Model built successfully.")
    print("Solving...")
    callback = TimeAfterFirstSolutionCallback()
    model.optimize(callback)

    if model.status == GRB.OPTIMAL or model.status == GRB.INTERRUPTED:
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
            # if i somehow isn’t in assignment_map, fall back to empty list
            assigned = assignment_map.get(i, [])
            communities = ", ".join(str(j + 1) for j in sorted(assigned))
            f.write(
                f"Healthcenter deployed at {i + 1}: Communities Assigned = {{{communities}}}\n"
            )
        f.write(f"Objective Value: {objective_value}\n")


def extract_all_routes(model, M: int) -> list[list[int]]:
    """Extract all routes by checking every z[0,k] arc from the depot."""
    routes = []
    # All indices: 0 represents depot.
    for k in range(1, M):
        var = model.getVarByName(f"z[0,{k}]")
        if var is not None and var.X > 0.5:
            route = [0, k]
            current = k
            while True:
                next_node = None
                # For the current node, find an outgoing arc with value > 0.5.
                for j in range(M):
                    if j != current:
                        var_next = model.getVarByName(f"z[{current},{j}]")
                        if var_next is not None and var_next.X > 0.5:
                            next_node = j
                            break
                if next_node is None:
                    break  # In case no outgoing arc is found.
                route.append(next_node)
                if next_node == 0:
                    break  # Completed a cycle back to depot.
                current = next_node
            routes.append(route)
    return routes


def append_results_to_file_part_two(
    filename: str,
    routes: list[list[int]],
    objective_value: float,
    instance: HealthCenterInstancePartTwo,
) -> None:
    # Read the existing file to determine if a Stage-2 block exists.
    try:
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    stage2_marker = "Stage-2:"
    if stage2_marker in content:
        # Remove Stage-2 and everything after it while preserving Stage-1.
        content = content.split(stage2_marker)[0].rstrip()
        file_mode = "w"
    else:
        file_mode = "a"

    with open(filename, file_mode) as f:
        if file_mode == "w":
            f.write(content + "\n\n")
        else:
            f.write("\n")  # Blank line for separation when appending.
        f.write("Stage-2:\n")
        # For each route, build its description.
        for idx, route in enumerate(routes, start=1):
            route_description = []
            for node in route:
                if node == 0:
                    route_description.append("Depot")
                else:
                    # instance.assignments[node][0] corresponds to the healthcenter id from part one.
                    route_description.append(
                        f"Healthcenter at {instance.assignments[node][0]}"
                    )
            f.write(f"Route {idx}: {' -> '.join(route_description)}\n")
        f.write(f"Objective Value: {objective_value:.2f}\n")


def _solve_and_save_results_part_two(instance_index: int) -> None:
    instance = HealthCenterInstancePartTwo(
        f"instances/Instance_{instance_index}.txt",
        f"instances/Sol_Instance_{instance_index}.txt",
    )

    model = build_part_two_model(instance)
    callback = TimeAfterFirstSolutionCallback()
    model.optimize(callback)

    if model.status == GRB.OPTIMAL or model.status == GRB.INTERRUPTED:
        print("Objective Value:", model.ObjVal)
        M = instance.num_health_centers + 1  # Total nodes including depot.
        routes = extract_all_routes(model, M)

        # Optionally, print out all decision variables.
        for v in model.getVars():
            print(v.VarName, ":", v.X)

        # Write (or overwrite) the Stage-2 results in the solution file.
        append_results_to_file_part_two(
            f"instances/Sol_Instance_{instance_index}.txt",
            routes,
            model.ObjVal,
            instance,
        )
    else:
        print("Model did not solve to optimality.")


def solve_and_save_results(instance_index: int) -> None:
    _solve_and_save_results_part_one(instance_index)
    _solve_and_save_results_part_two(instance_index)


if __name__ == "__main__":
    # You can run part one and two consecutively or only run part two.

    NUM_INSTANCES = 25
    for i in range(24, NUM_INSTANCES):
        print(f"Solving instance {i}...")
        print("=" * 30)
        solve_and_save_results(i)
        print(f"Instance {i} solved and results saved.")
