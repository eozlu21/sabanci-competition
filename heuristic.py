# heuristic.py
from __future__ import annotations

from typing import List, Dict, Tuple, Optional

from health_center_instance import HealthCenterInstancePartOne, Distances


def build_initial_solution(
    instance: HealthCenterInstancePartOne,
) -> Tuple[List[int], Dict[Tuple[int, int], int]]:
    N = instance.num_communities
    M = instance.num_health_centers
    pops = [n["population"] for n in instance.nodes]
    cap = instance.nodes[0]["capacity"]
    dist = Distances(instance)

    total_pop = sum(pops)
    alpha = round(total_pop / (5 * M))
    beta = max(dist[i, j] for i in range(N) for j in range(i)) / 5

    communities = sorted(range(N), key=pops.__getitem__, reverse=True)

    x_best: List[int] = []
    y_best: Dict[Tuple[int, int], int] = {}

    # state arrays
    x = [0] * N
    load = [0] * N  # current workload per open center
    residual = [0] * N
    y: Dict[Tuple[int, int], int] = {}

    open_centers: List[int] = []

    d_min: Optional[float] = None
    d_max: Optional[float] = None

    def backtrack(idx: int) -> bool:
        nonlocal d_min, d_max, x_best, y_best
        if idx == len(communities):
            x_best = x[:]
            y_best = dict(y)
            return True

        j = communities[idx]
        # generate candidate centers sorted by distance
        candidates = open_centers[:]
        candidates.sort(key=lambda i: dist[i, j])
        if len(open_centers) < M:
            candidates.append(j)  # option to open new center
        for i in candidates:
            opening = False
            if i == j and x[i] == 0:  # open new
                x[i] = 1
                open_centers.append(i)
                residual[i] = cap
                opening = True
            # capacity check
            if residual[i] < pops[j]:
                if opening:
                    open_centers.pop()
                    x[i] = 0
                continue
            # tentative assign
            y[(i, j)] = 1
            residual[i] -= pops[j]
            load[i] += pops[j]

            # distance stats update
            old_dmin, old_dmax = d_min, d_max
            dj = dist[i, j]
            d_min = dj if d_min is None else min(d_min, dj)
            d_max = dj if d_max is None else max(d_max, dj)

            # fairness pruning
            if d_max - d_min <= beta:
                w_vals = [load[c] for c in open_centers]
                gap = max(w_vals) - min(w_vals) if w_vals else 0
                if gap <= alpha:
                    if backtrack(idx + 1):
                        return True
            # undo
            d_min, d_max = old_dmin, old_dmax
            residual[i] += pops[j]
            load[i] -= pops[j]
            y.pop((i, j))
            if opening:
                open_centers.pop()
                residual[i] = 0
                x[i] = 0
        return False

    if not backtrack(0):
        raise ValueError("No feasible solution found by backtracking.")

    return x_best, y_best


def apply_initial_solution_to_model(
    x_vars, y_vars, x_init: List[int], y_init: Dict[Tuple[int, int], int]
) -> None:
    for i, v in enumerate(x_init):
        x_vars[i].Start = v
    for i, j in y_vars.keys():
        y_vars[i, j].Start = 1 if (i, j) in y_init else 0
