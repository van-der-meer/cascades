import copy
import numpy as np
from functions_v7_g_tr import *
from psychopy import visual, core, event
from exptools2.core import Trial, Session


# Make sure the experiment main version matches the current folder
file_path = os.path.abspath(__file__)
validate_experiment_folder(file_path)

run_istruction = True

exp_version = os.path.basename(os.getcwd())

exp_flow, exp_params, exp_texts = open_params()


class MQTrial(Trial):
    """
    Displays multiple bistable motion quartets simultaneously.
    Each phase corresponds to one alternation (horizontal <-> vertical).
    """

    def __init__(
        self,
        session,
        trial_nr,
        phase_durations,
        params,
        mml_distances = None
    ):


        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=phase_durations,
            phase_names=["alternation"] * len(phase_durations),
            timing="seconds"
        )

        self.params = params

        self.button = params.get("continue")
        self.mml = params.get("mml")
        self.fixation = params.get("fixation", False)

        self.mml_distances = mml_distances

        self.create_trial()

    def create_trial(self):
        """Create dot stimuli for all quartets."""

        self.quartets = []

        self.colors = []

        for mq_pars in self.params["mqs"].values():

            mq_pars = copy.deepcopy(mq_pars)

            self.colors.extend([mq_pars.get("color", [1, 1, 1])] * mq_pars.get("n_dots", 2))

            if isinstance(self.mml_distances, np.ndarray):
                mq_pars["dist_hor_start"] = self.mml_distances[0]
                mq_pars["dist_ver_start"] = self.mml_distances[1]

            self.coords = mq(mq_pars)
            self.quartets.append(pad_frames(self.coords, self.params))

        self.concatenated = np.concatenate(self.quartets, axis=1)

        self.fixation_stim = visual.TextStim(
            win=self.session.win,
            text="+",
            color='white',
            height=20,
            pos=[0, 0]
        )

        self.stims = []

        for frame in self.concatenated:
            #coords = frame[~np.isnan(frame).all(axis=1)]

            mask = ~np.isnan(frame).all(axis=1)
            coords = frame[mask]
            colors = np.array(self.colors)[mask]


            if coords.shape[0] == 0:
                # Create "empty" stim by putting a single element off-screen
                coords = np.array([[9999, 9999]])
                n_elements = 1
            else:
                n_elements = coords.shape[0]

            self.stims.append(
                visual.ElementArrayStim(
                    win=self.session.win,
                    units='pix',
                    nElements=n_elements,
                    xys=coords,
                    sizes=10,            # size of each element (scalar or list)
                    sfs=0,               # spatial frequency 0 = filled circles
                    elementTex=None,     # use disk instead of texture
                    elementMask='circle',
                    colors=colors,     # single RGB color for all dots
                    colorSpace='rgb'
                )
            )


    def draw(self):
        """Draw stimuli for the current phase (one frame)."""

        if self.fixation:
            self.fixation_stim.draw()

        frame_idx = self.phase

        if frame_idx < len(self.stims):
            self.stims[frame_idx].draw()

        if self.last_resp == "s":
            self.stop_trial()

        if self.button:
            if self.last_resp == self.button:

                if self.mml:
                    self.session.output.append(self.concatenated[frame_idx])

                self.stop_trial()


class TextTrial(Trial):
    """A trial that shows some text and waits for space press."""

    def __init__(self, session, trial_nr, params, texts):
        # This trial has one phase of arbitrary length (we ignore duration)
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[params.get("duration", float("inf"))],  # run until space is pressed
            phase_names=["text_phase"],
            timing="seconds"
        )

        self.params = params
        self.exp_texts = texts

        self.text_stims = []

        self.button = self.params.get("continue")

        self.create_trial()

    def create_trial(self):
        """Create the PsychoPy TextStim."""

        for element in self.params["texts"].values():

            text = exp_texts[element["content"]]

            self.text_stims.append(visual.TextStim(
                win=self.session.win,
                text=text,
                color='white',
                height=element["size"],
                pos=element["pos"]
            ))


    def draw(self):
        """Draw text and wait for space bar."""

        for text_stim in self.text_stims:
            text_stim.draw()

        if self.last_resp == "s":
            self.stop_trial()

        # Check for button press
        if self.button:
            if self.last_resp == self.button:
                self.stop_trial()


class PromptTrial(Trial):
    """A trial that shows text, collects a typed response, and continues on button click."""

    def __init__(self, session, trial_nr, params, texts):
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[params.get("duration", float("inf"))],
            phase_names=["prompt_phase"],
            timing="seconds"
        )

        self.params = params
        self.exp_texts = texts
        self.text_stims = []
        self._button_clicked = False
        self._mouse_was_down = False

        self.create_trial()

    def create_trial(self):
        """Create display texts and store layout params; input box is created at run time."""

        for element in self.params["texts"].values():
            text = exp_texts[element["content"]]
            self.text_stims.append(visual.TextStim(
                win=self.session.win,
                text=text,
                color='white',
                height=element["size"],
                pos=element["pos"]
            ))

        # input_box, btn_rect, btn_label are created lazily in run() so that
        # only one editable TextBox2 exists at a time (PsychoPy routes keystrokes
        # to every registered editable box, causing all pre-created boxes to
        # accumulate the same text).
        self.input_box = None
        self.btn_rect = None
        self.btn_label = None
        self.mouse = None

    def run(self):
        """Run trial with mouse visible. Widgets are created here so only one
        editable TextBox2 is registered with PsychoPy at a time."""

        input_pos = self.params.get("input_pos", [0, 0])
        self.input_box = visual.TextBox2(
            win=self.session.win,
            text='',
            font='Arial',
            pos=input_pos,
            size=(600, 200),
            units='pix',
            color='black',
            fillColor='white',
            borderColor='gray',
            editable=True,
            letterHeight=25
        )

        btn_pos = self.params.get("button_pos", [0, -150])
        self.btn_rect = visual.Rect(
            win=self.session.win,
            width=200,
            height=50,
            pos=btn_pos,
            fillColor='gray',
            lineColor='white',
            units='pix'
        )
        self.btn_label = visual.TextStim(
            win=self.session.win,
            text='Continue',
            color='white',
            height=25,
            pos=btn_pos
        )

        self.mouse = event.Mouse(win=self.session.win)

        self._button_clicked = False
        self._mouse_was_down = self.mouse.getPressed()[0]  # treat any held button as "already down"
        self.session.win.mouseVisible = True
        super().run()
        self.session.win.mouseVisible = False

    def draw(self):
        """Draw text, input box, and continue button; handle click."""

        for text_stim in self.text_stims:
            text_stim.draw()

        self.input_box.draw()
        self.btn_rect.draw()
        self.btn_label.draw()

        currently_down = self.mouse.getPressed()[0]
        fresh_click = currently_down and not self._mouse_was_down
        self._mouse_was_down = currently_down

        if not self._button_clicked and fresh_click and self.mouse.isPressedIn(self.btn_rect):
            self._button_clicked = True
            self._save_response()
            self.stop_trial()

    def get_events(self):
        """ Logs responses/triggers """
        events = event.getKeys(timeStamped=self.session.clock)
        if events:

            for key, t in events:

                if key == self.session.mri_trigger:
                    event_type = 'pulse'
                else:
                    event_type = 'response'

                idx = self.session.global_log.shape[0]
                self.session.global_log.loc[idx, 'trial_nr'] = self.trial_nr
                self.session.global_log.loc[idx, 'onset'] = t
                self.session.global_log.loc[idx, 'event_type'] = event_type
                self.session.global_log.loc[idx, 'phase'] = self.phase
                self.session.global_log.loc[idx, 'response'] = key

                for param, val in self.parameters.items():  # add parameters to log
                    if type(val) == np.ndarray or type(val) == list:
                        for i, x in enumerate(val):
                            self.session.global_log.loc[idx, param+'_%4i'%i] = x 
                    else:       
                        self.session.global_log.loc[idx, param] = val

                if self.eyetracker_on:  # send msg to eyetracker
                    msg = f'start_type-{event_type}_trial-{self.trial_nr}_phase-{self.phase}_key-{key}_time-{t}'
                    self.session.tracker.sendMessage(msg)

                if key != self.session.mri_trigger:
                    self.last_resp = key
                    self.last_resp_onset = t

        return events


    def _save_response(self):
        """Save the typed input directly to file, appending if it already exists."""
        question = " | ".join(s.text for s in self.text_stims)
        output_name = self.session.output_dir + "/" + self.session.output_str + "_prompt_responses.txt"
        with open(output_name, "a") as f:
            f.write(f"Trial {self.trial_nr} [{self.params.get('trial_identifier', '')}]\n"
                    f"  Q: {question}\n"
                    f"  A: {self.input_box.text}\n")


# --------------------------------------------------
# Session class
# --------------------------------------------------

class CascExpSession(Session):

    def __init__(self, output_str, output_dir, settings_file, exp_flow, exp_params, exp_texts):
        super().__init__(output_str, output_dir, settings_file)

        self.inst_trials = []
        self.exp_trials = []
        self.output = []
        self.trial_params_output = []
        self.trial_counter = 1
        self.exp_flow = exp_flow
        self.exp_params = exp_params
        self.exp_texts = exp_texts

        output_name_params = self.output_dir + "/" + self.output_str + "_exp_params.json"

        with open(output_name_params, "w") as f:
            json.dump(self.exp_params, f, indent=4)

    def create_inst_mml_trials(self):
        """Create all trials before running the experiment."""

        self.trial_names = list(self.exp_flow)

        for trial in self.trial_names:

            self.trial_params = self.exp_flow[trial]

            if "mml" in trial:

                n_mml_reps = self.exp_params["mml_params"]["n_reps"]

                base_distance = self.exp_params["mml_params"]["base_dist_mml_trials"]
                mml_dist = self.exp_params["mml_params"]["max_mml_stretch"]
                mml_multipliers = [-1, 1] * n_mml_reps
                mml_durs = self.exp_params["mml_params"]["durs_mml_trials"] * 2  # should be n
                mml_idx = np.arange(0, n_mml_reps * 2)

                np.random.shuffle(mml_idx)

                phase_durations = [1/self.trial_params["freq"]] * self.trial_params["len_trial"] * 2

                for idx in mml_idx:

                    if mml_multipliers[idx] == -1:
                        init_pos = "lu",
                    else:
                        init_pos = "ru",

                    mq_idx = list(self.trial_params["mqs"])[0]

                    mq_params = self.trial_params["mqs"][mq_idx]

                    self.trial_params["len_trial"] = mml_durs[idx]

                    mq_params["dist_hor_start"] = base_distance + mml_multipliers[idx] * mml_dist
                    mq_params["dist_ver_start"] = base_distance - mml_multipliers[idx] * mml_dist
                    mq_params["dist_hor_stop"] = base_distance - mml_multipliers[idx] * mml_dist
                    mq_params["dist_ver_stop"] = base_distance + mml_multipliers[idx] * mml_dist
                    mq_params["cycles"] = mml_durs[idx]

                    mq_params["init_pos"] = init_pos

                    self.trial_params["mqs"][mq_idx] = mq_params

                    phase_durations = [1/self.trial_params["freq"]] * self.trial_params["len_trial"] * 2

                    self.inst_trials.append(
                        MQTrial(
                            session=self,
                            trial_nr=self.trial_counter,
                            phase_durations=phase_durations,
                            params=self.trial_params)
                            )

                    self.trial_params_output.append({self.trial_counter: self.trial_params})

                    self.trial_counter += 1



            elif "inst" in trial and self.trial_params["trial_type"] == "text":
                self.inst_trials.append(
                     TextTrial(self, trial_nr=self.trial_counter, params=self.trial_params, texts=self.exp_texts)
                )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

            elif "inst" in trial and self.trial_params["trial_type"] == "prompt":
                self.inst_trials.append(
                    PromptTrial(self, trial_nr=self.trial_counter, params=self.trial_params, texts=self.exp_texts)
                )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

            elif "inst" in trial and self.trial_params["trial_type"] == "stim":

                phase_durations = [1/self.trial_params["freq"]] * self.trial_params["len_trial"] * 2

                self.inst_trials.append(
                    MQTrial(
                        session=self,
                        trial_nr=self.trial_counter,
                        phase_durations=phase_durations,
                        params=self.trial_params)
                        )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

        output_name = self.output_dir + "/" + self.output_str + "_inst_flow.json"

        with open(output_name, "w") as f:
            json.dump(self.trial_params_output, f, indent=4)

    def create_exp_trials(self):
        """Create all trials before running the experiment."""


        self.trial_names = list(self.exp_flow)

        self.mml_distances = np.mean(np.abs(self.output), axis = 0)[0]

        self.mml_distances = self.mml_distances * self.exp_params["main_exp_params"]["size_scalar"] # scale this up or down a bit


        self.break_text_trial_params = self.exp_flow["break_text"] # unelegant...

        for trial in self.trial_names:

            self.trial_params = self.exp_flow[trial]

            if trial == "main_exp_grouping":

                reps = self.exp_params["main_params_grouping"]["reps_per_cell"]

                n_mqs = self.exp_params["main_params_grouping"]["n_mqs"] * reps 

                frequencies = self.exp_params["main_params_grouping"]["frequencies"]

                fixation = self.exp_params["main_params_grouping"]["fixation"]

                trial_dur = self.exp_params["main_params_grouping"]["trial_dur"] / 2

                combinations_grouping = [
                            (x, y, z)
                            for x in fixation
                            for y in n_mqs
                            for z in frequencies
                            ]

                np.random.shuffle(combinations_grouping)

                for combin in range(len(combinations_grouping)):

                    trial_copy = copy.deepcopy(self.trial_params)

                    trial_copy["freq"] = combinations_grouping[combin][2]
                    trial_copy["fixation"] = combinations_grouping[combin][0]

                    if combinations_grouping[combin][1] == 9:

                        mq_keys = list(trial_copy["mqs"])

                        mq_params = trial_copy["mqs"][mq_keys[0]]

                        trial_copy["mqs"].pop(mq_keys[0])

                        spacing = 200
                        coords_1d = np.linspace(-spacing, spacing, 3)

                        x, y = np.meshgrid(coords_1d, coords_1d)

                        grid = np.column_stack([x.ravel(), y.ravel()])

                        for mq in range(len(grid)):
                            new_mq = copy.deepcopy(mq_params)   # create fresh copy
                            new_mq["center"] = grid[mq].tolist()
                            trial_copy["mqs"][str(mq)] = new_mq

                    trial_copy["trial_nr"] = self.trial_counter

                    trial_copy["len_trial"] = trial_dur * trial_copy["freq"] + 2

                    phase_durations = [1/trial_copy["freq"]] * int(trial_copy["len_trial"]) * 2

                    distances_grouping = self.mml_distances 

                    self.exp_trials.append(
                                MQTrial(
                                    session=self,
                                    trial_nr=self.trial_counter,
                                    phase_durations=phase_durations,
                                    params=trial_copy,
                                    mml_distances=distances_grouping
                                    )
                                    )

                    trial_copy["params"] = {"id": "exp_grouping",
                                            "freq": combinations_grouping[combin][2],
                                            "n_mqs": combinations_grouping[combin][1],
                                            "fixation": combinations_grouping[combin][0],
                                            "trial_nr": self.trial_counter
                                            }

                    self.trial_params_output.append({self.trial_counter: trial_copy})
                    self.trial_counter += 1

                    if combin != (len(combinations_grouping)-1):
                        self.exp_trials.append(
                                    TextTrial(self, trial_nr=self.trial_counter, params=self.break_text_trial_params, texts = self.exp_texts)
                                )
                        self.trial_params_output.append({self.trial_counter: self.break_text_trial_params})
                        self.trial_counter += 1




            if trial == "main_exp_cascades":

                # vars

                vals_side = self.exp_params["main_params_cascades"]["vals_side"]

                vals_disamb = self.exp_params["main_params_cascades"]["vals_disamb"]

                n_cue = self.exp_params["main_params_cascades"]["n_cue"] # how many mqs are affected on one side

                cue_present = self.exp_params["main_params_cascades"]["cue_present"]

                timings = self.exp_params["main_params_cascades"]["cue_timings"] # cycles (1 cycle is 2 phases a 0.2s)

                # should balance classes by preventing too many conditions without prime
                combinations = [
                    (v, w, x, y, z)
                    for v in n_cue
                    for w in vals_side
                    for x in vals_disamb
                    for y in timings
                    for z in cue_present
                    if not (
                        (x is None and z is True) or
                        (x is None and z is False and y in [2, 4]) or
                        (x == "hor" and z is False and (w == 0 or y in [2, 4])) or
                        (x == "ver" and z is False and (w == 0 or y in [2, 4])) or
                        (x is None and w == 0)
                    )
                ]

                # Determines experiment duration

                reps_per_cell = self.exp_params["main_params_cascades"]["reps_per_cell"]

                self.trials_before_break = 20
                self.break_counter = 0

                for rep in range(reps_per_cell):

                    np.random.shuffle(combinations)

                    for combination in combinations:

                        trial_copy = copy.deepcopy(self.trial_params)

                        side = combination[1]

                        if not combination[2]:
                            side = "none"

                        if combination[2] == "hor":
                            disamb = "hor"
                        elif combination[2] == "ver":
                            disamb = "ver"
                        else:
                            disamb = "none"

                        trial_copy["trial_nr"] = self.trial_counter

                        mq_idxs = list(self.trial_params["mqs"])

                        prime_idxs = np.where(["prime" in x for x in mq_idxs])[0]
                        amb1_idxs = np.where(["amb1" in x for x in mq_idxs])[0]
                        cue_idxs = np.where(["cue" in x for x in mq_idxs])[0]
                        amb2_idxs = np.where(["amb2" in x for x in mq_idxs])[0]

                        # once cycle is 2 phases

                        prime_start = 4  # 4 cycles = 8 * 0.2 s = 1.6 s
                        cycles_prime = 2 # 2 cycles = 4 * 0.2 s = 0.8 s

                        amb_1_start = prime_start + cycles_prime # 2.4 s

                        amb_1_dur = combination[3]

                        cue_start = amb_1_dur + amb_1_start # 2 cycles prime

                        cue_dur = 8

                        amb_2_start = cue_start + cue_dur

                        #amb_2_dur = total_dur - amb_2_start

                        amb_2_dur = 24 - cue_start

                        total_dur = amb_2_start + amb_2_dur

                        trial_copy["len_trial"] = total_dur


                        trial_copy["params"] = {"id": "exp_casc",
                                                "side": side,
                                                "disamb": disamb,
                                                "cue_present": combination[4],
                                                "cue_delay": combination[3],
                                                "trial_nr": self.trial_counter,
                                                "prime_start": prime_start,
                                                "cycles_prime": cycles_prime,
                                                "amb_1_start": amb_1_start,
                                                "amb_2_start": amb_2_start,
                                                "amb_2_dur": amb_2_dur,
                                                "total_dur": amb_2_start + amb_2_dur,
                                                "cue_start": cue_start,
                                                "cue_dur": cue_dur,
                                                "n_biased": combination[0],
                                                "prime_start": prime_start}



                        if combination[2] == "hor":
                            #cue_dir = "ver"
                            cue_dist_hor =  self.mml_distances[0] * 1.75
                            cue_dist_ver =  self.mml_distances[1] * 1/1.75

                            for mq in mq_idxs:
                                trial_copy["mqs"][mq]["dist_hor_start"] = self.mml_distances[0]# * 0.95
                                trial_copy["mqs"][mq]["dist_ver_start"] = self.mml_distances[1]# * 1.05

                        elif combination[2] == "ver":
                            #cue_dir = "hor"
                            cue_dist_hor =  self.mml_distances[0] * 1/1.75
                            cue_dist_ver =  self.mml_distances[1] * 1.75
                            for mq in mq_idxs:
                                trial_copy["mqs"][mq]["dist_hor_start"] = self.mml_distances[0]# * 1.05
                                trial_copy["mqs"][mq]["dist_ver_start"] = self.mml_distances[1]# * 0.95
                        else:
                            cue_dist_hor =  self.mml_distances[0]
                            cue_dist_ver =  self.mml_distances[1]
                            for mq in mq_idxs:
                                trial_copy["mqs"][mq]["dist_hor_start"] = self.mml_distances[0]
                                trial_copy["mqs"][mq]["dist_ver_start"] = self.mml_distances[1]
                            #cue_dir = None





                        for prime in prime_idxs:
                            trial_copy["mqs"][mq_idxs[prime]]["start_cycle"] = prime_start
                            trial_copy["mqs"][mq_idxs[prime]]["cycles"] = cycles_prime
                            trial_copy["mqs"][mq_idxs[prime]]["disamb"] = combination[2]

                        for amb1_idx in amb1_idxs:
                            trial_copy["mqs"][mq_idxs[amb1_idx]]["start_cycle"] = amb_1_start
                            trial_copy["mqs"][mq_idxs[amb1_idx]]["cycles"] = amb_1_dur

                        for cue_idx in cue_idxs:
                            trial_copy["mqs"][mq_idxs[cue_idx]]["start_cycle"] = cue_start
                            trial_copy["mqs"][mq_idxs[cue_idx]]["cycles"] = cue_dur

                        if combination[4]:
                            #trial_copy["mqs"][mq_idxs[cue_idxs[combination[1]]]]["disamb"] = cue_dir

                            if combination[1] == "left":
                                cue_idxs_screen = cue_idxs[:combination[0]]
                            else:
                                cue_idxs_screen = cue_idxs[-combination[0]:]

                            for cue_idx_screen in cue_idxs_screen:
                                trial_copy["mqs"][mq_idxs[cue_idx_screen]]["dist_hor_start"] = cue_dist_hor
                                trial_copy["mqs"][mq_idxs[cue_idx_screen]]["dist_ver_start"] = cue_dist_ver

                        for amb2_idx in amb2_idxs:
                            trial_copy["mqs"][mq_idxs[amb2_idx]]["start_cycle"] = amb_2_start
                            trial_copy["mqs"][mq_idxs[amb2_idx]]["cycles"] = amb_2_dur



                        phase_durations = [1/trial_copy["freq"]] * trial_copy["len_trial"] * 2

                        self.exp_trials.append(
                            MQTrial(
                                session=self,
                                trial_nr=self.trial_counter,
                                phase_durations=phase_durations,
                                params=trial_copy#,
                                #mml_distances=mml_distances
                                )
                                )

                        self.trial_params_output.append({self.trial_counter: trial_copy})
                        self.trial_counter += 1
                        self.break_counter += 1

                        # Insert break if this trial is a break position
                        if self.break_counter == self.trials_before_break:
                            self.exp_trials.append(
                                TextTrial(self, trial_nr=self.trial_counter, params=self.break_text_trial_params, texts = self.exp_texts)
                            )
                            self.trial_params_output.append({self.trial_counter: self.break_text_trial_params})
                            self.trial_counter += 1
                            self.break_counter = 0

                    #self.trial_counter += 1

                    # if rep < (reps_main_block-1):
                    #     self.exp_trials.append(
                    #         TextTrial(self, trial_nr=self.trial_counter, params=self.break_text_trial_params)
                    #     )

                    #     self.trial_params_output.append({self.trial_counter: self.break_text_trial_params})
                    #     self.trial_counter += 1




            elif "exp_expl" in trial and self.trial_params["trial_type"] == "text":
                self.exp_trials.append(
                     TextTrial(self, trial_nr=self.trial_counter, params=self.trial_params, texts=self.exp_texts)
                )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

            elif "exp_expl" in trial and self.trial_params["trial_type"] == "prompt":
                self.exp_trials.append(
                    PromptTrial(self, trial_nr=self.trial_counter, params=self.trial_params, texts=self.exp_texts)
                )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

            elif "exp_expl" in trial and self.trial_params["trial_type"] == "stim":

                phase_durations = [1/self.trial_params["freq"]] * self.trial_params["len_trial"] * 2

                self.exp_trials.append(
                    MQTrial(
                        session=self,
                        trial_nr=self.trial_counter,
                        phase_durations=phase_durations,
                        params=self.trial_params,
                        mml_distances=self.mml_distances)
                        )

                self.trial_params_output.append({self.trial_counter: self.trial_params})

                self.trial_counter += 1

        output_name = self.output_dir + "/" + self.output_str + "_exp_flow.json"

        self.trial_params_output.append({"mml_results": list(self.mml_distances)})
        self.trial_params_output.append({"exp_version": exp_version})

        with open(output_name, "w") as f:
            json.dump(self.trial_params_output, f, indent=4)

    def _create_fresh_mml_trials(self):
        """
        Create and return a fresh list of MML trial objects.
        Called on each calibration attempt so there is no stale exptools2 state.
        """
        trials = []
        for trial_name in list(self.exp_flow):
            trial_params = self.exp_flow[trial_name]
            if "mml" not in trial_name:
                continue

            n_mml_reps = self.exp_params["mml_params"]["n_reps"]
            base_distance = self.exp_params["mml_params"]["base_dist_mml_trials"]
            mml_dist = self.exp_params["mml_params"]["max_mml_stretch"]
            mml_multipliers = [-1, 1] * n_mml_reps
            mml_durs = self.exp_params["mml_params"]["durs_mml_trials"] * 2
            mml_idx = np.arange(0, n_mml_reps * 2)
            np.random.shuffle(mml_idx)

            for idx in mml_idx:
                tp = copy.deepcopy(trial_params)

                init_pos = "lu" if mml_multipliers[idx] == -1 else "ru"
                mq_idx = list(tp["mqs"])[0]
                mq_params = tp["mqs"][mq_idx]

                tp["len_trial"] = mml_durs[idx]
                mq_params["dist_hor_start"] = base_distance + mml_multipliers[idx] * mml_dist
                mq_params["dist_ver_start"] = base_distance - mml_multipliers[idx] * mml_dist
                mq_params["dist_hor_stop"]  = base_distance - mml_multipliers[idx] * mml_dist
                mq_params["dist_ver_stop"]  = base_distance + mml_multipliers[idx] * mml_dist
                mq_params["cycles"]   = mml_durs[idx]
                mq_params["init_pos"] = init_pos,
                tp["mqs"][mq_idx] = mq_params

                phase_durations = [1 / tp["freq"]] * tp["len_trial"] * 2

                trials.append(
                    MQTrial(
                        session=self,
                        trial_nr=0,  # dummy nr; calibration results go to self.output
                        phase_durations=phase_durations,
                        params=tp,
                    )
                )
        return trials

    def show_mml_results_and_confirm(self):
        """
        Display MML calibration results to the researcher after MML trials.
        Returns True if researcher approves the values, False to restart.
        Shows distances, aspect ratio, and allows restart or quit.
        """
        if not self.output:
            msg = (
                "MML CALIBRATION FAILED: No responses were recorded.\n\n"
            )
            approved = False
        else:
            raw = np.mean(np.abs(self.output), axis=0)[0]
            dist_hor = raw[0]
            dist_ver = raw[1]

            if np.any(np.isnan(raw)) or (len(self.output) != 8):
                msg = (
                    "MML CALIBRATION FAILED: NA values in response"
                )
                approved = False
            else:
                aspect_ratio = dist_hor / dist_ver if dist_ver != 0 else float('inf')
                scaled = raw * self.exp_params["main_exp_params"]["size_scalar"]
                n_responses = len(self.output)
                msg = (
                    f"MML Calibration Results  ({n_responses} response(s) recorded)\n\n"
                    #f"Raw distances:       H = {dist_hor:.1f} px    V = {dist_ver:.1f} px\n"
                    f"Aspect ratio (H/V):  {aspect_ratio:.3f}\n"
                    #f"Scaled distances:    H = {scaled[0]:.1f} px    V = {scaled[1]:.1f} px\n\n"
                    #"Press  SPACE  to accept and continue.\n"
                    #"Press  R  to restart the MML calibration.\n"
                    #"Press  Q  to quit the experiment."
                )
                approved = True

        result_stim = visual.TextStim(
            win=self.win,
            text=msg,
            color='white',
            height=22,
            wrapWidth=900,
            pos=(0, 0)
        )

        # Drive the display with an explicit flip loop instead of event.waitKeys.
        # waitKeys() pumps pyglet's event loop, which can continue dispatching
        # scheduled frame callbacks from the just-finished MML trial, causing
        # spurious appends to self.output and visual glitches.
        event.clearEvents()
        keys = []
        while not keys:
            result_stim.draw()
            self.win.flip()
            keys = event.getKeys(keyList=['return', 'r', 'q'])

        if 'q' in keys:
            self.close()
            core.quit()

        if 'return' in keys and approved:
            return True
        else:
            return False

    def show_loading_screen(self):

        """Display a loading screen immediately."""
        self.loading_text = visual.TextStim(
            win=self.win,
            text="Preparing experiment. This can take a moment. \nPlease wait",
            color="white",
            height=30
        )

        self.loading_text.draw()
        self.win.flip()

        self.create_exp_trials()

        keys = event.getKeys()

        self.win.flip()
        core.wait(0.01)  # ensures flip actually happens


    def run(self):

        self.start_experiment()

        self.create_inst_mml_trials()

        if run_istruction:
            # Run instruction (text/prompt/stim) trials once; MML trials are recreated fresh per attempt
            non_mml_trials = [t for t in self.inst_trials
                              if not (isinstance(t, MQTrial) and t.params.get("mml"))]

            for trial in non_mml_trials:
                trial.run()

            # MML calibration loop: retry until researcher approves
            while True:
                self.output = []
                self.timer.reset()  # prevent accumulated clock time from skipping phases
                for trial in self._create_fresh_mml_trials():
                    trial.run()

                approved = self.show_mml_results_and_confirm()
                event.clearEvents()  # flush any keys pressed during the display phase
                if approved:
                    break
        else:
            self.output = [[[60, 60], [60, 60]]]

        self.show_loading_screen()

        for trial in self.exp_trials:
            trial.run()

        self.close()


# --------------------------------------------------
# Run experiment
# --------------------------------------------------

if __name__ == '__main__':
    subject_id, subject_dir = create_subject_dir(exp_version)
    my_sess = CascExpSession(subject_id, subject_dir, 'settings.yml', exp_flow = exp_flow, exp_params = exp_params, exp_texts = exp_texts)
    my_sess.run()