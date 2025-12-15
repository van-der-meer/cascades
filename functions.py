import os 
import numpy as np

def mq(params: dict, trial: dict, mml_distances = None):

    

    '''
    Create MQ stimulus coordinates

    Returns dict with coordinates & updated params
    
    '''

    fpc = int(trial.get("framerate", 120) / params.get("freq", 5))
    cycles = params.get("cycles", 10)
    n_frames = cycles * fpc
    center = params.get("center", (0, 0))
    dist_hor_start = params.get("dist_hor_start", 100)
    dist_ver_start = params.get("dist_ver_start", 100)

    if mml_distances is not None :
        dist_hor_start = mml_distances[0]
        dist_ver_start = mml_distances[1]

    dist_hor_stop = params.get("dist_hor_stop", dist_hor_start)
    dist_ver_stop = params.get("dist_ver_stop", dist_ver_start)

    dist_hor_linspace = np.linspace(dist_hor_start, dist_hor_stop, cycles)
    dist_ver_linspace = np.linspace(dist_ver_start, dist_ver_stop, cycles)

    dist_hor_list = np.repeat(dist_hor_linspace, fpc)
    dist_ver_list = np.repeat(dist_ver_linspace, fpc)

    params["elements_per_frame"] = 2

    frames_out = []
    idx = 0

    init_pos = params.get("init_pos", "lu")

    if init_pos == "lu":
        pos_switch = 1
    else: 
        pos_switch = -1

    disamb = params.get("disamb", None)

    for _ in range(cycles):
        for _ in range(fpc):

            shift_hor = int(dist_hor_list[idx] / 2)
            shift_ver = int(dist_ver_list[idx] / 2)

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

            frames_out.append(xy)
            idx += 1

        pos_switch *= -1


    return {"params": params, 
            "frames": frames_out}


def pad_frames(stim, trial):
    params = stim.get("params")
    frames = np.array(stim.get("frames"))
    start_frame = params.get("start_frame")
    len_trial = trial.get("trial_duration")
    frames_out = np.zeros(shape=(len_trial, params.get("elements_per_frame"), 2))
    frames_out[:] = np.nan
    if len_trial > start_frame:
        frames_out[start_frame:start_frame + frames.shape[0], :, :] = frames[0:len_trial-start_frame, :, :]
    return frames_out

def prepare_trial(params, trial, mml_distances = None):

    '''
    Create positions list and one frame corresponding to each frame in the trial
    '''

    type = params.get("type", "mq")

    if type == "mq": 
        stim = mq(params=params, trial=trial, mml_distances=mml_distances)
    else: 
        stim = mq(params=params, trial=trial, mml_distances=mml_distances)
    
    frames_padded = pad_frames(stim, trial=trial)

    return frames_padded

def create_subject_dir():
    # Create subject dir
    exit = False 
    while not exit:
        subject_id = input("Enter subject ID:")
        subject_dir = "logs/" + subject_id

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