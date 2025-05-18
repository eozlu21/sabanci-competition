from math import sqrt


class HealthCenterInstancePartOne:
    def __init__(self, file_path: str):
        self.num_communities: int = 0
        self.num_health_centers: int = 0
        self.depot_coords: tuple[float, float] = (0, 0)
        self.nodes: list[dict] = []
        _parse_instance_file(self, file_path)

    def __str__(self) -> str:
        return (
            f"HealthCenterInstance with {self.num_communities} communities and "
            f"{self.num_health_centers} health centers\n"
            f"Depot Coordinates: {self.depot_coords}\n"
            f"Nodes:\n"
            + "\n".join(
                f"  Index: {node['index']}, X: {node['x']}, Y: {node['y']}, "
                f"Capacity: {node['capacity']}, Population: {node['population']}"
                for node in self.nodes
            )
        )


class HealthCenterInstancePartTwo:
    def __init__(self, instance_file_path: str, solution_file_path: str):
        self.num_communities: int = 0
        self.num_health_centers: int = 0
        self.depot_coords: tuple[float, float] = (0, 0)
        self.nodes: list[dict] = []
        # The logic is as follows:
        # 1. The depot is always at index 0.
        # 2. The first key is just to represent the healthcare units' arbitrary index.
        # 3. The second key is the index of the community assigned to that health center.
        # 4. The value is a list of communities assigned to that health center.
        self.assignments: dict[int, tuple[int, list[int]]] = {}
        _parse_instance_file(self, instance_file_path)
        _parse_solution_file(self, solution_file_path)

    def __str__(self) -> str:
        return (
            f"HealthCenterInstance with {self.num_communities} communities and "
            f"{self.num_health_centers} health centers\n"
            f"Depot Coordinates: {self.depot_coords}\n"
            f"Nodes:\n"
            + "\n".join(
                f"  Index: {node['index']}, X: {node['x']}, Y: {node['y']}, "
                f"Capacity: {node['capacity']}, Population: {node['population']}"
                for node in self.nodes
            )
            + "\nAssignments:\n"
            + "\n".join(
                f"  Healthcenter deployed at {i}: Communities Assigned = {{{', '.join(map(str, assigned))}}}"
                for i, assigned in self.assignments.items()
            )
        )


def _parse_instance_file(
    instance: HealthCenterInstancePartOne | HealthCenterInstancePartTwo,
    instance_file_path: str,
) -> None:
    """
    Supports both formats:
      old → header, depot line (index 0), then N community lines
      new → header only, then N community lines (indices start at 1)
    """

    with open(instance_file_path, "r") as f:
        lines = [ln for ln in f if ln.strip()]

    instance.num_communities, instance.num_health_centers = map(int, lines[0].split())

    # detect depot line
    start = 1
    first_data = lines[1].split()
    if first_data[0] == "0":  # old format
        instance.depot_coords = (float(first_data[1]), float(first_data[2]))
        start = 2  # skip depot
    else:  # new format
        instance.depot_coords = None  # no depot

    for line in lines[start:]:
        idx, x, y, cap, pop = line.split()
        instance.nodes.append(
            {
                "index": int(idx),
                "x": float(x),
                "y": float(y),
                "capacity": int(cap),
                "population": int(pop),
            }
        )


def _parse_solution_file(
    instance: HealthCenterInstancePartTwo, solution_file_path: str
) -> None:
    """
    Parses the solution file (specifically the solution of the first stage) and initializes the relevant fields.
    """
    instance.assignments = {0: (0, [])}  # Depot
    index = 1
    with open(solution_file_path, "r") as file:
        for line in file:
            if "Healthcenter deployed at" in line:
                parts = (
                    line.strip().split("Healthcenter deployed at")[1].strip().split(":")
                )
                center_index = int(parts[0])
                assigned_str = parts[1].split("=")[-1].strip().strip("{}")
                assigned_indices = list(map(int, assigned_str.split(", ")))
                instance.assignments[index] = (center_index, assigned_indices)
                index += 1
            elif "Objective Value" in line:
                break


class Distances:
    def __init__(
        self, instance: HealthCenterInstancePartOne | HealthCenterInstancePartTwo
    ) -> None:
        if isinstance(instance, HealthCenterInstancePartTwo):
            self._coordinates = {
                node["index"]: (node["x"], node["y"]) for node in instance.nodes
            }
            self._coordinates[0] = instance.depot_coords
        else:
            self._coordinates = {
                node["index"] - 1: (node["x"], node["y"]) for node in instance.nodes
            }
        self.distances = {
            (i, j): sqrt(
                (self._coordinates[i][0] - self._coordinates[j][0]) ** 2
                + (self._coordinates[i][1] - self._coordinates[j][1]) ** 2
            )
            for i in self._coordinates
            for j in self._coordinates
        }

    def __getitem__(self, key: tuple[int, int]) -> float:
        return self.distances[key]


import gurobipy as gp


class CustomTerminationCallback:
    def __init__(
        self, improvement_threshold=0.01, time_limit=5400, mip_gap_threshold=0.25
    ):
        self.improvement_threshold = improvement_threshold  # 1% improvement
        self.time_limit = time_limit  # 1.5 hours in seconds
        self.mip_gap_threshold = mip_gap_threshold  # 25% gap
        self.last_improvement_time = time.time()
        self.best_obj = float("inf")

    def __call__(self, model, where):
        if where == GRB.Callback.MIP:
            current_time = time.time()
            try:
                best_obj = model.cbGet(GRB.Callback.MIP_OBJBST)
                best_bound = model.cbGet(GRB.Callback.MIP_OBJBND)
            except gp.GurobiError:
                return  # In case attributes are not available yet

            # Check for improvement
            if best_obj < self.best_obj * (1 - self.improvement_threshold):
                self.best_obj = best_obj
                self.last_improvement_time = current_time

            # Check time since last improvement
            if current_time - self.last_improvement_time > self.time_limit:
                print("Terminating: No significant improvement in the last hour.")
                model.terminate()

            # Check MIP gap
            if abs(best_obj) > 1e-10:  # Avoid division by zero
                mip_gap = abs(best_obj - best_bound) / abs(best_obj)
                if mip_gap <= self.mip_gap_threshold:
                    print(f"Terminating: MIP gap {mip_gap:.2%} is within threshold.")
                    model.terminate()


class TimeAfterFirstSolutionCallback:
    """
    Terminates the model t seconds after the first incumbent solution is found.
    """

    def __init__(self, time_after_first_solution: float = 3600):
        self.time_after_first_solution = time_after_first_solution
        self.first_solution_time: float | None = None

    def __call__(self, model: gp.Model, where: int):
        if where == GRB.Callback.MIP:
            # Try to get the current best incumbent objective
            try:
                best_obj = model.cbGet(GRB.Callback.MIP_OBJBST)
            except Exception:
                return

            # If no incumbent yet, cbGet returns infinity; skip until a real solution appears
            if best_obj < float("inf"):
                now = time.time()
                # Record the moment of the first real solution
                if self.first_solution_time is None:
                    self.first_solution_time = now
                # If enough time has passed since that first solution, terminate
                elif now - self.first_solution_time >= self.time_after_first_solution:
                    print(
                        f"Terminating: {self.time_after_first_solution:.0f}s elapsed "
                        "since first incumbent solution."
                    )
                    model.terminate()


import time
import gurobipy as gp
from gurobipy import GRB


class CombinedTerminationCallback:
    """
    Per-instance limit + target MIP gap + no-improve cutoff.
      max_time            total seconds allowed (wall clock)
      gap_threshold       terminate when MIP gap ≤ this (e.g. 0.04 for 4%)
      no_improve_time     seconds with no >improvement_threshold drop
      improvement_threshold  relative improvement fraction (e.g. 0.01 for 1%)
    """

    def __init__(
        self,
        max_time: float = 9000,
        gap_threshold: float = 0.00,
        no_improve_time: float = 9100,
        improvement_threshold: float = 0.03,
    ):
        self.max_time = max_time
        self.gap_threshold = gap_threshold
        self.no_improve_time = no_improve_time
        self.improvement_threshold = improvement_threshold
        self.start_time: float | None = None
        self.first_solution_time: float | None = None
        self.best_obj: float = float("inf")
        self.last_improve_time: float | None = None

    def __call__(self, model: gp.Model, where: int):
        if where != GRB.Callback.MIP:
            return
        now = time.time()
        if self.start_time is None:
            self.start_time = now
        # global wall‐clock cutoff
        if now - self.start_time >= self.max_time:
            model.terminate()
            return
        # fetch incumbent & bound
        try:
            bst = model.cbGet(GRB.Callback.MIP_OBJBST)
            bnd = model.cbGet(GRB.Callback.MIP_OBJBND)
        except gp.GurobiError:
            return
        if bst == float("inf"):
            return
        # record first solution
        if self.first_solution_time is None:
            self.first_solution_time = now
            self.last_improve_time = now
        # update best & last_improve_time
        if bst < self.best_obj * (1 - self.improvement_threshold):
            self.best_obj = bst
            self.last_improve_time = now
        # target gap cutoff
        gap = abs(bst - bnd) / abs(bst)
        if gap <= self.gap_threshold:
            model.terminate()
            return
        # no‐improvement cutoff
        if now - self.last_improve_time >= self.no_improve_time:
            model.terminate()
            return
