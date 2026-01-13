import copy
import numpy as np
from functions import *
from psychopy import visual, event, core
from exptools2.core import Trial, Session
#from psychopy.visual import TextStim, Circle



exp_folder_path = "experiment_params/v1"

exp_params, exp_texts = open_params(exp_folder_path)

class CascTrial(Trial):
    
    def __init__(self, session, trial_nr, phase_durations, parameters, load_next_during_phase, verbose, trial_params, mml_distances=None):
        """ Initializes a StroopTrial object. """
        super().__init__(session, trial_nr, phase_durations=phase_durations, parameters=parameters, 
                         timing="frames", load_next_during_phase=load_next_during_phase, verbose=verbose)
        
        self.trial_params = trial_params

        self.check_key = trial_params.get("check_key")

        self.params = []

        #object_names = list(trial_params.keys())
        object_names = list(trial_params["trial_objects"].keys())

        for object in object_names:
            self.params.append(dict(trial_params["trial_objects"].get(object)))

        self.object_frames = []

        for object_params in self.params:
            self.object_frames.append(prepare_trial(object_params, trial_params, mml_distances))
            
        self.object_frames_array = np.concatenate(self.object_frames, axis=1)

        self.stims = []
        self.fixation = visual.TextStim(self.session.win, pos= (0, 0), text="+", height=20)

        for frame in self.object_frames_array:
            coords = frame[~np.isnan(frame).all(axis=1)]
            self.stims.append(visual.ElementArrayStim(
                                    win=self.session.win,
                                    units='pix',
                                    nElements=coords.shape[0],
                                    xys=coords,
                                    sizes=10,            # size of each element (scalar or list)
                                    sfs=0,                # spatial frequency 0 = filled circles
                                    elementTex=None,      # use disk instead of texture
                                    elementMask='circle', # circle elements
                                    colors=[1, 1, 1],   # RGB: red dots
                                    colorSpace='rgb'
                                    ))

    def draw(self):
        # Draw the stimulus corresponding to the current phase index
        stim = self.stims[self.phase]
        stim.draw()
        self.fixation.draw()

    def run(self):
        """Run the trial, record the frame index where space is pressed, interrupt."""
        
        self.space_frame = None   # store frame index where space was pressed

        keys = event.getKeys()

        while self.phase < self.n_phase:

            self.session.win.callOnFlip(self.log_phase_info, phase=self.phase)

            # Draw current frame
            self.draw()

            # Flip (advances a frame & phase index)
            self.session.win.flip()

            self.keys = self.get_events()
            self.session.nr_frames += 1


            if self.check_key:
                if self.keys:
                    if self.check_key in [ev[0] for ev in self.keys]:  # specific key in settings?
                    
                        # Record index of the frame when pressed
                        self.space_frame = self.phase   # because timing="frames"
                        
                        # Optional: log with exptools2
                        # t = self.session.clock.getTime()
                        # self.session.log("space_press_frame", self.phase)
                        # self.session.log("space_press_time", t)

                        # Stop the trial immediately
                        distance_switch = self.object_frames_array[self.space_frame, :, :]

                        trial_output = {"trial_identifier": self.trial_params.get("trial_identifier"), 
                                        "distance_switch": distance_switch
                                        }

                        self.session.outputs.append(trial_output)

                        self.stop_trial()
                        break

            # Let exptools2 update phases (frame counter)
            self.phase += 1

        self.stop_trial()
        

class TextTrial(Trial):
    def __init__(self, session, trial_nr, exp_texts, params):
        # phase_durations=None → trial does not end until we say so
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[1],     # IMPORTANT: unlimited duration
            phase_names=[1],
            timing="seconds", 
        )

        self.text_objects = []

        if params.get("trial_objects"):
            for text_object in list(params.get("trial_objects").values()):
                text_id = text_object.get("content")
                text = exp_texts[text_id]
                self.text_objects.append(visual.TextStim(self.session.win, pos=text_object.get("pos", (0, 0)), text=text, height=text_object.get("size", 30)))

        else:
            text_id = params.get("content")
            text = exp_texts[text_id]
            self.text_objects.append(visual.TextStim(self.session.win, pos=params.get("pos", (0, 0)), text=text, height=params.get("size", 30)))
        
        self.continue_key = params.get("continue")

    def draw(self):
        """Draw the text every frame."""

        for textstim in self.text_objects:
            textstim.draw()

    def run(self):
        """Override run() so we can wait for a keypress."""
        #self.start()  # starts timing + phase machinery

        win = self.session.win

        while True:
            # Draw text
            self.draw()

            # Flip screen
            win.flip()

            # Check for keypress
            keys = event.getKeys()
            if self.continue_key in keys:
                print("Key pressed:", keys)
                break   # Exit the loop and end the trial

        self.stop_trial()

        #self.session.win.flip()  # clear screen after trial
        core.wait(0.1)
        

class load_inst_trials(Trial):
    def __init__(self, session, trial_nr):
        # phase_durations=None → trial does not end until we say so
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[1],     # IMPORTANT: unlimited duration
            phase_names=[1],
            timing="seconds", 
        )


    def run(self):

        loading_text = visual.TextStim(
            self.session.win,
            text="Loading trials - please wait for a moment, this may take a while.",
            height=30
        )

        loading_text.draw()
        self.session.win.flip()

        self.session.create_inst_trials()

        # Clear key buffer
        keys = event.getKeys()

        self.session.win.flip()  # clear screen


class load_exp_trials(Trial):
    def __init__(self, session, trial_nr):
        # phase_durations=None → trial does not end until we say so
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[1],     # IMPORTANT: unlimited duration
            phase_names=[1],
            timing="seconds", 
        )


    def run(self):

        loading_text = visual.TextStim(
            self.session.win,
            text="Loading trials - please wait for a moment, this may take a while.",
            height=30
        )

        loading_text.draw()
        self.session.win.flip()

        self.session.create_exp_trials(mml_distances=self.session.distances)

        # Clear key buffer
        keys = event.getKeys()

        self.session.win.flip()  # clear screen
        

class CascExpSession(Session):

    def __init__(self, output_str, output_dir, settings_file):
        super().__init__(output_str, output_dir, settings_file)  # initialize parent class!
        
        self.inst_trials = []  # will be filled with Trials later

        self.exp_trials = [] 

        self.outputs = []

        self.output_str = output_str
        self.output_dir = output_dir
        
    def create_inst_trials(self):
        """ Creates trials (ideally before running your session!) """
            
        self.trial_names = list(exp_params.keys())

        for name in self.trial_names:

            trial_params = exp_params[name]

            if "inst" in trial_params.get("trial_identifier"):
            
                if trial_params["trial_type"] == "text":

                    trial = TextTrial(
                            session=self,
                            trial_nr=0,                             # change!!!
                            exp_texts=exp_texts, 
                            params=trial_params
                            )
                    self.inst_trials.append(trial)

                if trial_params["trial_type"] == "stim":
                    trial = CascTrial(
                        session=self,
                        trial_nr=name,
                        phase_durations=tuple([1]*trial_params["trial_duration"]),
                        parameters= {'condition': name},
                        load_next_during_phase=None,
                        verbose=False, 
                        trial_params = trial_params
                    )

                    self.inst_trials.append(trial)

    def create_exp_trials(self, mml_distances = None):
        """ Creates experiment trials (ideally before running your session!) """
            
        #self.trial_names = list(exp_params.keys())

        self.trial_params_list = list(exp_params.values())

        # create blocks
        # some code to create counterbalances conditions - takes all trials that 
        

        # condition combinations
        
        vals_side = np.repeat([0, -1], 2)

        vals_disamb = np.repeat(["hor", "ver", None], 2)

        timings = [240, 360, 480]

        combinations = [(x, y, z) for x in vals_side for y in vals_disamb for z in timings]

        #combinations = [(x, y) for x in vals_side for y in vals_disamb]


        np.random.shuffle(combinations)

        self.block_trials = []

        for trial in self.trial_params_list :

            if "block" in trial.get("trial_identifier"):


                self.block_trials.append(trial)

                
        self.block_trials_expanded = []

        counter = 0

        for combination in combinations:
            for block_trial in self.block_trials:

                bt = copy.deepcopy(block_trial)

                if "amb1" in bt["trial_identifier"]:
                    bt["trial_duration"] = combination[2]

                if "disamb" in bt["trial_identifier"]:
                    trial_objects = bt["trial_objects"]
                    for obj in trial_objects:
                        trial_objects[obj]["disamb"] = combination[1]

                elif "induce_casc" in bt["trial_identifier"]:
                    trial_objects = bt["trial_objects"]
                    names = list(trial_objects.keys())

                    if combination[1] == "hor":
                        cue = "ver"
                    elif combination[1] == "ver":
                        cue = "hor"
                    else:
                        cue = None

                    trial_objects[names[combination[0]]]["disamb"] = cue

                bt["trial_identifier"] += "_" + str(counter)

                self.block_trials_expanded.append(bt)

            counter += 1
        

        # remove block trials from original list 

        key_name = "trial_identifier"
        pattern = "block"

        self.trial_params_list  = [d for d in self.trial_params_list  if pattern not in str(d.get(key_name, ""))]

        self.thank_you = self.trial_params_list.pop()

        self.trial_params_list = self.trial_params_list + self.block_trials_expanded + [self.thank_you]

        output_name = self.output_str + "/" + self.output_dir + "_stim_params.json"

        with open(output_name, "w") as f:
            json.dump(self.trial_params_list, f, indent=4)


        for trial_params in self.trial_params_list:

            if "exp" in trial_params.get("trial_identifier"):

                if trial_params["trial_type"] == "text":

                    trial = TextTrial(
                            session=self,
                            trial_nr=0,
                            exp_texts=exp_texts, 
                            params=trial_params
                            )
                    self.exp_trials.append(trial)
                    
                if trial_params["trial_type"] == "stim":

                    trial = CascTrial(
                        session=self,
                        trial_nr=trial_params.get("trial_identifier"),
                        phase_durations=tuple([1]*trial_params["trial_duration"]),
                        parameters= {'condition': trial_params.get("trial_identifier")},
                        load_next_during_phase=None,
                        verbose=False, 
                        trial_params = trial_params, 
                        mml_distances=mml_distances
                    )

                    self.exp_trials.append(trial)


                
            
    def run(self):

        self.start_experiment()

        inst_trial_loader = load_inst_trials(session=self, trial_nr=111)
        inst_exp_loader = load_exp_trials(session=self, trial_nr=222)
        inst_trial_loader.run()
        
        for trial in self.inst_trials:
            trial.run()

        #print(self.outputs)

        self.distances = mml_distances(self.outputs)

        inst_exp_loader.run()

        for trial in self.exp_trials:
            trial.run()
        
        self.close()


subject_id, subject_dir = create_subject_dir() #create subject directory for data storage

if __name__ == '__main__':
    my_sess = CascExpSession(subject_id, subject_dir, 'settings.yml')
    my_sess.run()