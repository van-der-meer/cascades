import os
import sys
import yaml
import json

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
        subject_id = input("Enter subject ID (or 'q' to quit): ")
        if subject_id.strip().lower() == 'q':
            print("Experiment aborted.")
            sys.exit(0)
        subject_dir = "logs_" + exp_version + "/" + subject_id

        if os.path.isdir(subject_dir):
            print("Please enter a subject ID that has not been used yet or delete the corresponsing directory if not in use!")
        else:
            os.makedirs(subject_dir)
            exit = True
    return subject_id, subject_dir

