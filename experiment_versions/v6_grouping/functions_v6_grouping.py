import os
import sys
import yaml
import json
import numpy as np

import os

def validate_experiment_folder(file_path):
    file_path = os.path.abspath(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    # Ensure filename starts with "main"
    if not file_name.startswith("main"):
        raise ValueError(f"File '{file_name}.py' must start with 'main'.")

    # Remove "main" from the start
    expected_folder_name = file_name[4:]  # remove leading "main"

    # Folder where the file actually lives
    file_directory = os.path.dirname(file_path)
    actual_folder_name = os.path.basename(file_directory)

    # If working directory is wrong → fix it
    if os.getcwd() != file_directory:
        print(f"Working directory mismatch. Changing to: {file_directory}")
        os.chdir(file_directory)

    # Optional: sanity check that folder matches filename rule
    # if actual_folder_name != expected_folder_name:
    #     print(
    #         f"WARNING: Folder name does not match filename rule.\n"
    #         f"Expected folder: '{expected_folder_name}'\n"
    #         f"Actual folder:   '{actual_folder_name}'"
    #     )


def mq(params: dict, mml_distances = None):

    '''
    Create MQ stimulus coordinates

    Returns dict with coordinates & updated params
    
    '''

    cycles = params.get("cycles", 10) * 2
    center = params.get("center", (0, 0))
    dist_hor_start = params.get("dist_hor_start", 100)
    dist_ver_start = params.get("dist_ver_start", 100)

    if isinstance(mml_distances, np.ndarray):
        dist_hor_start = mml_distances[0]
        dist_ver_start = mml_distances[1]

    dist_hor_stop = params.get("dist_hor_stop", dist_hor_start)
    dist_ver_stop = params.get("dist_ver_stop", dist_ver_start)

    dist_hor_linspace = np.linspace(dist_hor_start, dist_hor_stop, cycles)
    dist_ver_linspace = np.linspace(dist_ver_start, dist_ver_stop, cycles)


    params["elements_per_frame"] = 2

    pos_out = []
    idx = 0

    init_pos = params.get("init_pos", "lu")

    if init_pos == "lu":
        pos_switch = 1
    else: 
        pos_switch = -1

    disamb = params.get("disamb", None)

    for _ in range(cycles):
        shift_hor = int(dist_hor_linspace[idx] / 2)
        shift_ver = int(dist_ver_linspace[idx] / 2)

        if disamb == "ver":
            left_x  = center[0] - shift_hor 
            right_x = center[0] + shift_hor 
            up_y    = center[1] + shift_ver * pos_switch 
            down_y  = center[1] + shift_ver * pos_switch 
        elif disamb == "hor":
            left_x  = center[0] + shift_hor * pos_switch 
            right_x = center[0] + shift_hor * pos_switch 
            up_y    = center[1] + shift_ver 
            down_y  = center[1] - shift_ver 
        else:
            left_x  = center[0] - shift_hor 
            right_x = center[0] + shift_hor 
            up_y    = center[1] + shift_ver * pos_switch 
            down_y  = center[1] - shift_ver * pos_switch 

        xy = [(left_x,  down_y), (right_x, up_y)]

        pos_out.append(xy)
        idx += 1

        pos_switch *= -1


    return {"params": params, 
            "positions": pos_out}


def pad_frames(mqs, trial_params):

    mq_params= mqs["params"]
    positions= mqs["positions"]

    len_trial = int(trial_params["len_trial"] * 2)

    frames_out = np.zeros(shape=(len_trial, 2, 2))
    frames_out[:] = np.nan

    start_idx = mq_params["start_cycle"] * 2
    len_mq_idx = mq_params["cycles"] * 2

# Determine how many frames we can actually write
    end_frame = min(start_idx + len_mq_idx, frames_out.shape[0])
    write_len = max(0, end_frame - start_idx)

    # Assign, truncating positions if necessary
    frames_out[start_idx:end_frame, :, :] = np.array(
        positions[:write_len]
        )   

    return frames_out

def find_file(pattern):
    files_with_params = [
        f for f in os.listdir()
        if os.path.isfile(f) and pattern in f
    ]
    return files_with_params[0]


def open_params():
    # Get experiment parameters

    flow_file = find_file("exp_flow")
    params_file = find_file("exp_params")
    text_file = find_file("texts")

    flow_file_path = flow_file
    params_file_path = params_file
    texts_file_path = text_file

    # Get experiment flow
    with open(flow_file_path, 'r') as file:
        exp_flow = yaml.safe_load(file)

    # Get experiment params
    with open(params_file_path, 'r') as file:
        exp_params = yaml.safe_load(file)

    # Get instruction texts
    with open(texts_file_path, "r", encoding="utf-8") as f:
        exp_texts = json.load(f)

    return exp_flow, exp_params, exp_texts


def create_subject_dir(exp_version):
    # Create subject dir
    exit = False 
    while not exit:
        subject_id = input("Enter subject ID:")
        subject_dir = "logs_" + exp_version + "/" + subject_id

        if os.path.isdir(subject_dir):
            print("Please enter a subject ID that has not been used yet or delete the corresponsing directory if not in use!")
        else: 
            os.makedirs(subject_dir)
            exit = True
    return subject_id, subject_dir


def mml_distances(trial_results):
    out = []
    for mml_trial in trial_results: 
        distances = mml_trial["distance_switch"]
        out.append(list(np.abs(distances[0, :])))

    return np.mean(np.array(out), axis=0)

