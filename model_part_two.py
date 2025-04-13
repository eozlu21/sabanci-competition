import gurobipy as gp
from gurobipy import GRB

from health_center_instance import HealthCenterInstancePartTwo, Distances


def build_part_two_model(instance: HealthCenterInstancePartTwo) -> gp.Model:
    model = gp.Model("HealthCenterScheduling")
    distances = Distances(instance)
    assignments = instance.assignments
    Q = 10_000  # Might be a parameter in the future
    N = instance.num_communities
    M = instance.num_health_centers + 1  # Including depot
    P = {j: instance.nodes[j]["population"] for j in range(N)}
    Y = {
        (i, j): 1 if j in instance.assignments[i][1] else 0
        for i in range(M)
        for j in range(N)
    }
    T = {i: sum(P[j] * Y[i, j] for j in range(N)) for i in range(M)}

    # Decision variables
    z = model.addVars(M, M, vtype=GRB.BINARY, name="z")
    u = model.addVars(M, vtype=GRB.CONTINUOUS, name="u")

    # Objective: sum of distances for all arcs used (i != k)
    model.setObjective(
        gp.quicksum(
            z[i, k] * distances[assignments[i][0], assignments[k][0]]
            for i in range(M)
            for k in range(M)
            if i != k
        ),
        GRB.MINIMIZE,
    )

    model.addConstrs(gp.quicksum(z[i, k] for i in range(M)) == 1 for k in range(1, M))
    model.addConstrs(gp.quicksum(z[k, i] for i in range(M)) == 1 for k in range(1, M))

    model.addConstr(gp.quicksum(z[i, i] for i in range(M)) == 0)

    model.addConstr(
        gp.quicksum(z[0, k] for k in range(1, M))
        == gp.quicksum(z[k, 0] for k in range(1, M))
    )
    model.addConstr(u[0] == 0, name="u0_zero")

    model.addConstrs(
        (
            u[i] - u[k] + Q * z[i, k] <= Q - T[k]
            for i in range(M)
            for k in range(1, M)
            if i != k
        ),
        name="mtz",
    )

    return model
