import gurobipy as gp
from gurobipy import GRB

from health_center_instance import HealthCenterInstancePartOne, Distances


def build_capacity_feasible_init(instance: HealthCenterInstancePartOne):
    """
    Build a guaranteed-feasible solution (incumbent) that respects
    capacity. Returns (x_init, y_init).
    x_init[i] = 1 if center i is used, else 0
    y_init[(i,j)] = 1 if j is assigned to center i

    Strategy:
    1) Sort communities by population descending.
    2) Keep list of open centers with their used capacity.
    3) For each community j, find an open center i with enough free
       capacity to serve P[j], picking the i that yields min
       P[j] * dist(i,j). If none can serve j, open a new center at j
       (if we still have fewer than M centers).
    4) If we exceed M, we can’t build a feasible solution.
    """

    N = instance.num_communities
    M = instance.num_health_centers
    C = instance.nodes[0]["capacity"]
    distances = Distances(instance)

    # Extract populations
    pops = [instance.nodes[j]["population"] for j in range(N)]

    # Sort communities by population descending
    communities_sorted = sorted(range(N), key=lambda j: pops[j], reverse=True)

    # We'll store:
    #   open_centers = list of (center_index, current_load)
    # Because each "center" is physically at some community 'i'
    open_centers = []  # each entry is [i, load_i]

    # Our final assignment dictionary
    x_init = [0] * N
    y_init = {}

    for j in communities_sorted:
        best_i = None
        best_cost = float("inf")
        # population of j
        pj = pops[j]

        # Try each open center i to see if we can fit j
        for c_idx, (i_center, load_i) in enumerate(open_centers):
            if load_i + pj <= C:
                # Evaluate cost = P[j]*dist(i_center,j) for min-max or min-sum?
                # Because your problem uses D >= P[j]*dist(i,j)*y[i,j],
                # the "cost" for j is effectively p_j * dist(i,j).
                # We'll pick the center that yields the smallest p_j*dist(i,j).
                cost_ij = pj * distances[i_center, j]
                if cost_ij < best_cost:
                    best_cost = cost_ij
                    best_i = c_idx

        # If we found an open center that can accommodate j:
        if best_i is not None:
            i_center, cur_load = open_centers[best_i]
            open_centers[best_i][1] = cur_load + pj  # update load
            y_init[(i_center, j)] = 1

        else:
            # We need to open a new center at j, if we haven't reached M yet
            if len(open_centers) < M:
                # open center i = j
                open_centers.append([j, pj])
                x_init[j] = 1
                y_init[(j, j)] = 1
            else:
                # we can't open a new center, so no feasible solution
                # , but we'll just keep going, won't be truly feasible
                # OR we can raise an Exception
                print(f"No more centers left! Community {j} not assigned feasibly.")
                return x_init, y_init  # partial/infeasible

    return x_init, y_init


def apply_initial_solution_to_model(x_vars, y_vars, x_init, y_init):
    """
    x_vars: dict from model.addVars(N, vtype=BINARY, name="x")
    y_vars: dict from model.addVars(N, N, vtype=BINARY, name="y")
    """
    N = len(x_init)
    for i in range(N):
        x_vars[i].Start = x_init[i]

    for i, j in y_vars.keys():
        y_vars[i, j].Start = 1 if (i, j) in y_init else 0


def build_part_one_model(instance: HealthCenterInstancePartOne) -> gp.Model:
    """
    Exactly like before, but we use build_capacity_feasible_init
    instead of a k-means-based solution to ensure feasibility.
    """
    model = gp.Model("HealthCenterMinMax")
    distances = Distances(instance)
    N = instance.num_communities
    M = instance.num_health_centers
    p = {j: instance.nodes[j]["population"] for j in range(N)}
    C = instance.nodes[0]["capacity"]

    x = model.addVars(N, vtype=GRB.BINARY, name="x")
    y = model.addVars(N, N, vtype=GRB.BINARY, name="y")
    D = model.addVar(vtype=GRB.CONTINUOUS, name="D")

    # New variables for alpha and beta
    W_max = model.addVar(vtype=GRB.CONTINUOUS, name="W_max")
    W_min = model.addVar(vtype=GRB.CONTINUOUS, name="W_min")
    delta_max = model.addVar(vtype=GRB.CONTINUOUS, name="delta_max")
    delta_min = model.addVar(vtype=GRB.CONTINUOUS, name="delta_min")

    # Alpha calculation
    total_population = sum(node["population"] for node in instance.nodes)
    alpha = total_population / (5 * M)
    alpha = int(round(alpha, 0))

    # Beta calculation
    max_distance = max(distances[i, j] for i in range(N) for j in range(N) if i > j)
    beta = max_distance / 5

    model.setObjective(D, GRB.MINIMIZE)

    # min-max constraints
    model.addConstrs(
        (
            D >= p[j] * y[i, j] * distances[i, j]
            for i in range(N)
            for j in range(N)
            if i != j
        ),
        name="D_definition",
    )

    model.addConstrs(
        (gp.quicksum(p[j] * y[i, j] for j in range(N)) <= C for i in range(N)),
        name="Capacity",
    )

    model.addConstrs(
        (y[i, j] <= x[i] for i in range(N) for j in range(N)),
        name="AssignmentLink",
    )

    model.addConstrs(
        (gp.quicksum(y[i, j] for i in range(N)) == 1 for j in range(N)),
        name="Community_coverage",
    )

    model.addConstr(gp.quicksum(x[j] for j in range(N)) <= M, name="Max_Center_Count")

    # New constraints for alpha and beta

    # Alpha constraints

    ALPHA_BIG_M = total_population
    model.addConstrs(
        (W_max >= gp.quicksum(y[i, j] * p[j] for j in range(N)) for i in range(N)),
        name="W_max_definition",
    )

    model.addConstrs(
        (
            W_min
            <= gp.quicksum(y[i, j] * p[j] for j in range(N)) + ALPHA_BIG_M * (1 - x[i])
            for i in range(N)
        ),
        name="W_min_definition",
    )

    model.addConstr(
        W_max - W_min <= alpha,
        name="Alpha_Constraint",
    )

    # Beta constraints
    model.addConstrs(
        (
            delta_max >= gp.quicksum(y[i, j] * distances[i, j] for i in range(N))
            for j in range(N)
        ),
        name="delta_max_definition",
    )

    model.addConstrs(
        (
            delta_min <= gp.quicksum(y[i, j] * distances[i, j] for i in range(N))
            for j in range(N)
        ),
        name="delta_min_definition",
    )

    model.addConstr(
        delta_max - delta_min <= beta,
        name="Beta_Constraint",
    )

    # x_init, y_init = build_initial_solution(instance)
    # apply_initial_solution_to_model(x, y, x_init, y_init)
    # model.setParam("StartNodeLimit", 1000)
    # model.setParam("PumpPasses", 20)  # or higher

    return model
