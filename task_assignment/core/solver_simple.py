#
# Created on Fri Dec 26 2025
# Copyright (c) 2025 Huy Truong
# ------------------------------
# Purpose: Simple Solver
# Require: ortools
# ------------------------------
#

from collections import defaultdict
from typing import Literal
from ortools.sat.python import cp_model


def solve(group_ratios: list[int] = [7, 11, 12], num_tasks: int = 30):
    total_ratio = sum(group_ratios)

    model = cp_model.CpModel()

    num_workers = len(group_ratios)
    workers = range(num_workers)
    tasks = range(num_tasks)

    # Boolean assignment variables. 1 indicates worker i is assigned to task t
    x = {(w, t): model.NewBoolVar(f"x_{w}_{t}") for w in workers for t in tasks}

    # Each task assigned to exactly one worker
    for t in tasks:
        model.Add(sum(x[w, t] for w in workers) == 1)

    # Load per worker
    load = {}
    for w in workers:
        load[w] = model.NewIntVar(0, len(tasks), f"load_{w}")
        model.Add(load[w] == sum(x[w, t] for t in tasks))

    # Target load
    total_ratio = sum(group_ratios)
    targets = [len(tasks) * group_ratios[w] / total_ratio for w in workers]

    # Deviation variables
    dev = {}
    for w in workers:
        dev[w] = model.NewIntVar(0, len(tasks), f"dev_{w}")
        model.AddAbsEquality(dev[w], load[w] - int(targets[w]))

    # Objective: minimize total deviation
    model.Minimize(sum(dev[w] for w in workers))

    # Solve
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    # Print solution.
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Total cost = {solver.objective_value}\n")
        for worker in range(num_workers):
            for task in range(num_tasks):
                if solver.boolean_value(x[worker, task]):
                    print(f"Worker {worker} assigned to task {task}.")
    else:
        print("No solution found.")


def solve_concern_day_group(group_ratios: list[int] = [7, 11, 12], ntasks_per_group=[10, 10, 10]) -> None:
    num_tasks = sum(ntasks_per_group)
    task_groups = {}  # {0: range(10), 1: range(10, 20), 2: range(20, 30)}
    cur_idx = 0
    for g in range(len(ntasks_per_group)):
        task_groups[g] = range(cur_idx, cur_idx + ntasks_per_group[g])
        cur_idx += ntasks_per_group[g]

    total_ratio = sum(group_ratios)

    model = cp_model.CpModel()

    num_workers = len(group_ratios)
    workers = range(num_workers)
    tasks = range(num_tasks)

    # Boolean assignment variables. 1 indicates worker i is assigned to task t
    x = {(w, t): model.NewBoolVar(f"x_{w}_{t}") for w in workers for t in tasks}

    # Each task assigned to exactly one worker
    for t in tasks:
        model.Add(sum(x[w, t] for w in workers) == 1)

    y = {}
    group_active = {}
    for g, group_tasks in task_groups.items():
        # if len(group_tasks) > num_workers:
        for w in workers:
            y[w, g] = model.NewBoolVar(f"y_{w}_{g}")

            # If y[w,g] = 1, worker w must do at least one task in group g
            model.Add(sum(x[w, t] for t in group_tasks) >= y[w, g])

        # Constraints: ensure num_workers distinct worker per group
        # model.Add(sum(y[w, g] for w in workers) >= num_workers)

    for g in task_groups:
        model.Add(sum(y[w, g] for w in workers) >= num_workers)
    ###################################MAIN OBJECTIVE PHASE 1 ######################################
    # Load per worker
    load = {}
    for w in workers:
        load[w] = model.NewIntVar(0, len(tasks), f"load_{w}")
        model.Add(load[w] == sum(x[w, t] for t in tasks))

    # Target load
    total_ratio = sum(group_ratios)
    targets = [len(tasks) * group_ratios[w] / total_ratio for w in workers]
    # Deviation variables
    dev = {}
    for w in workers:
        dev[w] = model.NewIntVar(0, len(tasks), f"dev_{w}")
        model.AddAbsEquality(dev[w], load[w] - int(targets[w]))

    # Objective 1: minimize total deviation
    model.Minimize(sum(dev[w] for w in workers))
    #########################################################################
    # Solve
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status == cp_model.OPTIMAL or status == cp_model.FEASIBLE, "No solution found"
    best = solver.ObjectiveValue()

    ###################################PHASE 2######################################
    model.Add(sum(dev[w] for w in workers) == int(best))

    group_task_load = {}
    for g, group_tasks in task_groups.items():
        for w in workers:
            group_task_load[w, g] = model.NewIntVar(0, len(group_tasks), f"group_task_load_{w}_{g}")
            model.Add(group_task_load[w, g] == sum(x[w, t] for t in group_tasks))
    # total Load per group
    total_load = {}
    for g, group_tasks in task_groups.items():
        total_load[g] = model.NewIntVar(0, len(group_tasks) * len(workers), f"total_load_{g}")
        model.Add(total_load[g] == sum(group_task_load[w, g] for w in workers))

    imbalance = {}

    for g in task_groups:
        for w in workers:
            diff = model.NewIntVar(-1000, 1000, f"diff_{w}_{g}")
            imbalance[w, g] = model.NewIntVar(0, 1000, f"imbalance_{w}_{g}")

            model.Add(diff == group_task_load[w, g] * total_ratio - group_ratios[w] * total_load[g])
            model.AddAbsEquality(imbalance[w, g], diff)

    # Objective 2: minimize imbalance
    model.Minimize(sum(imbalance[w, g] for w in workers for g in task_groups))
    status = solver.Solve(model)
    # #########################################################################

    # Print solution.
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Total cost = {solver.objective_value}\n")
        ntasks_per_worker_dict = {}
        for worker in range(num_workers):
            ntasks_per_worker_dict[worker] = 0
            for task in range(num_tasks):
                if solver.boolean_value(x[worker, task]):
                    print(f"Worker {worker} assigned to task {task + 1}.")
                    ntasks_per_worker_dict[worker] += 1
        print(ntasks_per_worker_dict)
    else:
        print("No solution found.")


def solve_concern_day_group_better(
    group_ratios: list[int] = [7, 11, 12],
    ntasks_per_group: list[int] = [10, 10, 10],
    verbose: bool = False,
    do_strict_cond_all_groups_are_avail_within_a_task_group: bool = False,
) -> dict[int, list[int]]:
    """Able to handle task groups which have ntasks < number of workers

    Args:
        group_ratios (list[int], optional): worker group ratio. Defaults to [7, 11, 12].
        ntasks_per_group (list, optional): number tasks per task group. Defaults to [10, 10, 10].
        verbose (bool): if True, we show extra information (useful for debugging). Defaults to False.
        do_strict_cond_all_groups_are_avail_within_a_task_group (bool): strictly requires all groups are available within a day (task group). Defaults to False.
    """
    num_tasks = sum(ntasks_per_group)
    task_groups = {}  # {0: range(10), 1: range(10, 20), 2: range(20, 30)}
    cur_idx = 0
    for g in range(len(ntasks_per_group)):
        task_groups[g] = range(cur_idx, cur_idx + ntasks_per_group[g])
        cur_idx += ntasks_per_group[g]

    total_ratio = sum(group_ratios)

    model = cp_model.CpModel()

    num_workers = len(group_ratios)
    workers = range(num_workers)
    tasks = range(num_tasks)

    # Boolean assignment variables. 1 indicates worker i is assigned to task t
    x = {(w, t): model.NewBoolVar(f"x_{w}_{t}") for w in workers for t in tasks}

    # Each task assigned to exactly one worker
    for t in tasks:
        model.Add(sum(x[w, t] for w in workers) == 1)

    y = {}
    for g, group_tasks in task_groups.items():
        for w in workers:
            y[w, g] = model.NewBoolVar(f"y_{w}_{g}")

            if do_strict_cond_all_groups_are_avail_within_a_task_group or len(group_tasks) >= num_workers:
                # If y[w,g] = 1, worker w must do at least one task in group g
                model.Add(sum(x[w, t] for t in group_tasks) >= y[w, g])

        # Constraints: ensure num_workers distinct worker per group
        model.Add(sum(y[w, g] for w in workers) >= num_workers)

    ###################################MAIN OBJECTIVE PHASE 1 ######################################
    # Load per worker
    load = {}
    for w in workers:
        load[w] = model.NewIntVar(0, len(tasks), f"load_{w}")
        model.Add(load[w] == sum(x[w, t] for t in tasks))

    # Target load
    total_ratio = sum(group_ratios)
    targets = [len(tasks) * group_ratios[w] / total_ratio for w in workers]
    # Deviation variables
    dev = {}
    for w in workers:
        dev[w] = model.NewIntVar(0, len(tasks), f"dev_{w}")
        model.AddAbsEquality(dev[w], load[w] - int(targets[w]))

    # Objective 1: minimize total deviation
    model.Minimize(sum(dev[w] for w in workers))
    #########################################################################
    # Solve
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status == cp_model.OPTIMAL or status == cp_model.FEASIBLE, "No solution found"
    best = solver.ObjectiveValue()

    ###################################PHASE 2######################################
    model.Add(sum(dev[w] for w in workers) == int(best))

    group_task_load = {}
    for g, group_tasks in task_groups.items():
        for w in workers:
            group_task_load[w, g] = model.NewIntVar(0, len(group_tasks), f"group_task_load_{w}_{g}")
            model.Add(group_task_load[w, g] == sum(x[w, t] for t in group_tasks))
    # total Load per group
    total_load = {}
    for g, group_tasks in task_groups.items():
        total_load[g] = model.NewIntVar(0, len(group_tasks) * len(workers), f"total_load_{g}")
        model.Add(total_load[g] == sum(group_task_load[w, g] for w in workers))

    imbalance = {}

    for g in task_groups:
        for w in workers:
            diff = model.NewIntVar(-1000, 1000, f"diff_{w}_{g}")
            imbalance[w, g] = model.NewIntVar(0, 1000, f"imbalance_{w}_{g}")

            model.Add(diff == group_task_load[w, g] * total_ratio - group_ratios[w] * total_load[g])
            model.AddAbsEquality(imbalance[w, g], diff)

    # Objective 2: minimize imbalance
    model.Minimize(sum(imbalance[w, g] for w in workers for g in task_groups))
    status = solver.Solve(model)
    # #########################################################################

    tasks_per_work_dict = defaultdict(list[int])
    # Print solution.
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        if verbose:
            print(f"Total cost = {solver.objective_value}\n")
        for worker in range(num_workers):
            for task in range(num_tasks):
                if solver.boolean_value(x[worker, task]):
                    if verbose:
                        print(f"Worker {worker} assigned to task {task + 1}.")
                    tasks_per_work_dict[worker].append(task)

    else:
        print("No solution found in phase 2.")
    return tasks_per_work_dict
