import gurobipy as gp
from gurobipy import GRB

from health_center_instance import HealthCenterInstancePartTwo, Distances


def build_part_two_model(instance: HealthCenterInstancePartTwo) -> gp.Model:
    model = gp.Model("HealthCenterScheduling")
    distances = Distances(instance)
    assignments = instance.assignments
    Q = 10_000  # Might be a parameter in the future
    N = instance.num_communities
    M = instance.num_health_centers
    P = {j: instance.nodes[j]["population"] for j in range(N)}
    Y = {
        (i, j): 1 if j in instance.assignments[i][1] else 0
        for i in range(M)
        for j in range(N)
    }

    T = {i: sum(P[j] * Y[i, j] for j in range(N)) for i in range(M)}

    z = model.addVars(M, M, vtype=GRB.BINARY, name="z")
    u = model.addVars(M, vtype=GRB.CONTINUOUS, name="u")

    model.setObjective(
        gp.quicksum(
            z[i, k] * distances[assignments[i][0], assignments[k][0]]
            for i in range(1, M)
            for k in range(M)
        )
    )

    # Constraints
    model.addConstrs(gp.quicksum(z[i, k] for i in range(1, M)) == 1 for k in range(M))

    model.addConstrs(gp.quicksum(z[i, k] for i in range(M)) <= 1 for k in range(M))

    model.addConstr(u[0] == 0)

    model.addConstrs(
        u[i] - u[k] + Q * z[i, k] <= Q - T[k]
        for i in range(1, M)
        for k in range(M)
        if i != k
    )

    return model
