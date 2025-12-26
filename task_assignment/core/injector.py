#
# Created on Fri Dec 26 2025
# Copyright (c) 2025 Huy Truong
# ------------------------------
# Purpose: Read excel, call solver, and, inject results into excel with styling.
# ------------------------------
#

from functools import partial
import os
from typing import Any, Literal
import pandas as pd
from task_assignment.core.solver_simple import solve_concern_day_group_better
import numpy as np


def highlight_values(value: str, checked_values: str, colors: str) -> str:
    for cv, color in zip(checked_values, colors):
        if value == cv:
            return f"color: {color}"
    else:
        return ""


def get_cumulative_increasement(checking_val, nan_indices) -> int:
    cumu_id = 0
    for i in range(len(nan_indices)):
        if checking_val + cumu_id >= nan_indices[i]:
            cumu_id += 1
        else:
            break

    return cumu_id


def read_inject_write(
    excel_path: str,
    usecols: list[str] = ["ĐẠI HỌC HUẾ", "Unnamed: 18", "Unnamed: 19"],
    starting_row: int = 7,
    group_ratios: list[int] = [7, 10, 11],
    assigned_prefix: str = "TACN",
    do_styling: bool = True,
    group_colors: list[str] = ["red", "black", "blue"],
    strategy: Literal["lite", "full"] = "lite",
    do_strict_cond_all_groups_are_avail_within_a_task_group: bool = False,
    debug: int = 0,
) -> pd.DataFrame:
    assert not do_styling or len(group_ratios) == len(group_colors), (
        f"Error! we expect group_colors <{len(group_colors)}> and group_ratios <{len(group_ratios)}> are equal in length."
    )

    # Read Excel
    base_name = os.path.basename(excel_path)[:-5]
    #############################1)simplify maindf before proceed#####################
    if strategy == "lite":
        main_df = pd.read_excel(excel_path)
        print(main_df.columns)
        # filter useful columns
        df = main_df[usecols]
    else:
        #############################2)use directly maindf as df#####################
        df = pd.read_excel(excel_path)
    if debug == 1:
        print(f"heads examples: {df.head()}")
        print(f"raw column names = {df.columns}")
    ## rename column
    new_column_names = ["id" if i == 0 else f"slot{i}" for i in range(len(usecols))]
    df = df.rename(columns=dict(zip(usecols, new_column_names)))
    # filter useful rows
    df = df.iloc[starting_row:].reset_index(drop=True)
    # identify null values in id columns
    nan_mask = df["id"].isna()
    nan_indices = df[nan_mask].index.tolist()
    if debug == 1:
        print(f"nan_indices = {nan_indices}")
    ntasks_per_group = []

    # loop over nan_indices (except the last)
    for i in range(len(nan_indices) - 1):
        start = 0 if i == 0 else nan_indices[i - 1]
        start = start + 1
        end = nan_indices[i]
        ntasks = end - start

        # if ntasks < len(group_ratios):
        #     # assert df.iloc[start:end, df.columns.get_loc("slot1")].notna().all() and df.iloc[start:end, df.columns.get_loc("slot2")].notna().all(), (
        #     #     "Error! Violate the condition a task group should have length is greater or equal to nworkers. "
        #     # )
        #     assert all([df.iloc[start:end, df.columns.get_loc(filling_col)].notna().all() for filling_col in new_column_names]), (
        #         "Error! Violate the condition a task group should have length is greater or equal to nworkers. "
        #     )
        #     # eliminate non-nan case
        #     nan_mask[start:end] = True
        # else:
        ntasks_per_group.append(ntasks)

    if strategy == "lite":
        # after counting, we must reset index
        df = df[~nan_mask].reset_index(drop=True)
        # remove old columns
        df = df.iloc[1:].reset_index(drop=True)

    updated_nan_indices = np.where(np.asarray(nan_mask, dtype=bool))[0]
    updated_nan_indices.sort()
    updated_nan_indices = updated_nan_indices.tolist()

    if debug == 1:
        print(f"new columns = {df.columns}")
        print(f"len(df) = {len(df)}")
        print(f"sum ntasks_per_group = {sum(ntasks_per_group)}")
        print(f"ntasks_per_group= {ntasks_per_group}")
        print(f"updated_nan_indices= {updated_nan_indices}")
    if strategy == "lite":
        df.to_excel("output_raw.xlsx", engine="openpyxl", index=False)

    tasks_per_worker_dict: dict[list[int]] = solve_concern_day_group_better(
        group_ratios=group_ratios,
        ntasks_per_group=ntasks_per_group,
        do_strict_cond_all_groups_are_avail_within_a_task_group=do_strict_cond_all_groups_are_avail_within_a_task_group,
    )

    assigned_values = []

    validated_tasks = []
    for worker, assigned_tasks in tasks_per_worker_dict.items():
        assigned_tasks = np.asarray(assigned_tasks) + 1
        assigned_tasks = assigned_tasks.tolist()

        if debug == 1:
            print(f"worker {worker}-> assigned  {len(assigned_tasks)} tasks: (old){assigned_tasks}")

        if strategy == "full":
            row_ids = []
            for t in assigned_tasks:
                cumu_id = get_cumulative_increasement(t, updated_nan_indices)
                row_ids.append(t + cumu_id)
            if debug == 1:
                print(f"worker {worker}-> assigned  {len(row_ids)} tasks: (new){row_ids}")
        else:
            row_ids = assigned_tasks

        assigned_value: str = f"{assigned_prefix}{worker + 1}"
        assigned_values.append(assigned_value)
        validated_tasks.extend(row_ids)

        for i in range(1, len(new_column_names)):
            filling_col = new_column_names[i]
            col_ids = df.columns.get_loc(filling_col)
            subset = df.iloc[row_ids, col_ids]
            mask = subset.notna()
            # Select only the rows that are non-NA using the mask
            rows_to_update = [row_ids[i] for i in range(len(row_ids)) if mask.iloc[i]]
            df.iloc[rows_to_update, col_ids] = assigned_value

    validated_tasks = np.asarray(validated_tasks, dtype=int)
    assert len(np.unique(validated_tasks)) == len(validated_tasks)

    sum_group_ratios = sum(group_ratios)
    num_tasks = sum(ntasks_per_group)
    if debug == 1:
        print(f"len(validated_tasks) = {len(validated_tasks)}")
        print(f"group_ratios = {group_ratios}| sum_group_ratios= {sum_group_ratios} | num_tasks = {num_tasks}")
        print(f"expected ratios = {[r / sum_group_ratios * num_tasks for r in group_ratios]}")
        print(f"actual ratios = {[len(task_list) for worker, task_list in tasks_per_worker_dict.items()]}")

    # styling
    if do_styling:
        df = df.style.applymap(partial(highlight_values, checked_values=assigned_values, colors=group_colors), subset=new_column_names)

    df.to_excel(f"output_{base_name}.xlsx", engine="openpyxl", index=False)


def inject(
    main_df: pd.DataFrame,
    usecols: list[str] = ["ĐẠI HỌC HUẾ", "Unnamed: 18", "Unnamed: 19"],
    starting_row: int = 7,
    group_ratios: list[int] = [7, 10, 11],
    assigned_prefix: str = "TACN",
    do_styling: bool = True,
    group_colors: list[str] = ["red", "black", "blue"],
    strategy: Literal["lite", "full"] = "lite",
    do_strict_cond_all_groups_are_avail_within_a_task_group: bool = False,
    debug: int = 0,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    assert not do_styling or len(group_ratios) == len(group_colors), (
        f"Error! we expect group_colors <{len(group_colors)}> and group_ratios <{len(group_ratios)}> are equal in length."
    )

    #############################1)simplify maindf before proceed#####################
    if strategy == "lite":
        # filter useful columns
        df = main_df[usecols]
    else:
        #############################2)use directly maindf as df#####################
        df = main_df
    if debug == 1:
        print(f"heads examples: {df.head()}")
        print(f"raw column names = {df.columns}")
    ## rename column
    new_column_names = ["id" if i == 0 else f"slot{i}" for i in range(len(usecols))]
    df = df.rename(columns=dict(zip(usecols, new_column_names)))
    # filter useful rows
    df = df.iloc[starting_row:].reset_index(drop=True)
    # identify null values in id columns
    nan_mask = df["id"].isna()
    nan_indices = df[nan_mask].index.tolist()
    if debug == 1:
        print(f"nan_indices = {nan_indices}")
    ntasks_per_group = []

    # loop over nan_indices (except the last)
    for i in range(len(nan_indices) - 1):
        start = 0 if i == 0 else nan_indices[i - 1]
        start = start + 1
        end = nan_indices[i]
        ntasks = end - start

        ntasks_per_group.append(ntasks)

    if strategy == "lite":
        # after counting, we must reset index
        df = df[~nan_mask].reset_index(drop=True)
        # remove old columns
        df = df.iloc[1:].reset_index(drop=True)

    updated_nan_indices = np.where(np.asarray(nan_mask, dtype=bool))[0]
    updated_nan_indices.sort()
    updated_nan_indices = updated_nan_indices.tolist()

    if debug == 1:
        print(f"new columns = {df.columns}")
        print(f"len(df) = {len(df)}")
        print(f"sum ntasks_per_group = {sum(ntasks_per_group)}")
        print(f"ntasks_per_group= {ntasks_per_group}")
        print(f"updated_nan_indices= {updated_nan_indices}")

    # if strategy == "lite":
    #    df.to_excel("output_raw.xlsx", engine="openpyxl", index=False)

    tasks_per_worker_dict: dict[list[int]] = solve_concern_day_group_better(
        group_ratios=group_ratios,
        ntasks_per_group=ntasks_per_group,
        do_strict_cond_all_groups_are_avail_within_a_task_group=do_strict_cond_all_groups_are_avail_within_a_task_group,
    )
    if len(tasks_per_worker_dict) == 0:
        return None, {}

    assigned_values = []

    validated_tasks = []
    for worker, assigned_tasks in tasks_per_worker_dict.items():
        assigned_tasks = np.asarray(assigned_tasks) + 1
        assigned_tasks = assigned_tasks.tolist()

        if debug == 1:
            print(f"worker {worker}-> assigned  {len(assigned_tasks)} tasks: (old){assigned_tasks}")

        if strategy == "full":
            row_ids = []
            for t in assigned_tasks:
                cumu_id = get_cumulative_increasement(t, updated_nan_indices)
                row_ids.append(t + cumu_id)
            if debug == 1:
                print(f"worker {worker}-> assigned  {len(row_ids)} tasks: (new){row_ids}")
        else:
            row_ids = assigned_tasks

        assigned_value: str = f"{assigned_prefix}{worker + 1}"
        assigned_values.append(assigned_value)
        validated_tasks.extend(row_ids)

        for i in range(1, len(new_column_names)):
            filling_col = new_column_names[i]
            col_ids = df.columns.get_loc(filling_col)
            subset = df.iloc[row_ids, col_ids]
            mask = subset.notna()
            # Select only the rows that are non-NA using the mask
            rows_to_update = [row_ids[i] for i in range(len(row_ids)) if mask.iloc[i]]
            df.iloc[rows_to_update, col_ids] = assigned_value

    validated_tasks = np.asarray(validated_tasks, dtype=int)
    assert len(np.unique(validated_tasks)) == len(validated_tasks)

    sum_group_ratios = sum(group_ratios)
    num_tasks = sum(ntasks_per_group)

    ret_dict = {
        "len_valid_tasks": len(validated_tasks),
        "group_ratios": group_ratios,
        "sum_group_ratios": sum_group_ratios,
        "num_tasks": num_tasks,
        "expected_ratios": [r / sum_group_ratios * num_tasks for r in group_ratios],
        "actual_ratios": [len(task_list) for worker, task_list in tasks_per_worker_dict.items()],
    }

    if debug == 1:
        print(f"len(validated_tasks) = {len(validated_tasks)}")
        print(f"group_ratios = {group_ratios}| sum_group_ratios= {sum_group_ratios} | num_tasks = {num_tasks}")
        print(f"expected ratios = {[r / sum_group_ratios * num_tasks for r in group_ratios]}")
        print(f"actual ratios = {[len(task_list) for worker, task_list in tasks_per_worker_dict.items()]}")

    # styling
    if do_styling:
        df = df.style.applymap(partial(highlight_values, checked_values=assigned_values, colors=group_colors), subset=new_column_names)

    return df, ret_dict
    # df.to_excel(f"{output_name}.xlsx", engine="openpyxl", index=False)
