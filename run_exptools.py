import yaml
import json
import numpy as np
from functions import *
from psychopy import visual, event, core
from exptools2.core import Trial, Session
#from psychopy.visual import TextStim, Circle


# Get experiment parameters
with open('exp_params.yml', 'r') as file:
    exp_params = yaml.safe_load(file)

# Get instruction texts
with open("exp_texts.json", "r", encoding="utf-8") as f:
    exp_texts = json.load(f)



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
                                        "distance_switch": distance_switch}

                        self.session.outputs.append(trial_output)

                        self.stop_trial()
                        break

            # Let exptools2 update phases (frame counter)
            self.phase += 1

        self.stop_trial()
        


class TextTrial(Trial):
    def __init__(self, session, trial_nr, text, params):
        # phase_durations=None → trial does not end until we say so
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=[1],     # IMPORTANT: unlimited duration
            phase_names=[1],
            timing="seconds", 
        )
        self.textstim = visual.TextStim(self.session.win, pos=params.get("pos", (0, 0)), text=text, height=30)
        self.continue_key = params.get("continue")

    def draw(self):
        """Draw the text every frame."""
        self.textstim.draw()

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

        
        

class CascExpSession(Session):

    def __init__(self, output_str, output_dir, settings_file):
        super().__init__(output_str, output_dir, settings_file)  # initialize parent class!
        
        self.inst_trials = []  # will be filled with Trials later

        self.exp_trials = [] 

        self.outputs = []
        
    def create_inst_trials(self):
        """ Creates trials (ideally before running your session!) """
            
        self.trial_names = list(exp_params.keys())

        for name in self.trial_names:

            trial_params = exp_params[name]

            if "inst" in trial_params.get("trial_identifier"):
            
                if trial_params["trial_type"] == "text":
                    text_id = trial_params.get("content")
                    text = exp_texts[text_id]

                    trial = TextTrial(
                            session=self,
                            trial_nr=0,
                            text=text, 
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
            
        self.trial_names = list(exp_params.keys())

        for name in self.trial_names:
            trial_params = exp_params[name]

            if "exp" in trial_params.get("trial_identifier"):

                if trial_params["trial_type"] == "text":
                    text_id = trial_params.get("content")
                    text = exp_texts[text_id]

                    trial = TextTrial(
                            session=self,
                            trial_nr=0,
                            text=text, 
                            params=trial_params
                            )
                    self.exp_trials.append(trial)
                    
                if trial_params["trial_type"] == "stim":

                    trial = CascTrial(
                        session=self,
                        trial_nr=name,
                        phase_durations=tuple([1]*trial_params["trial_duration"]),
                        parameters= {'condition': name},
                        load_next_during_phase=None,
                        verbose=False, 
                        trial_params = trial_params, 
                        mml_distances=mml_distances
                    )

                    self.exp_trials.append(trial)
            
    def run(self):
        self.create_inst_trials()
        self.start_experiment()
        
        for trial in self.inst_trials:
            trial.run()

        #print(self.outputs)

        distances = mml_distances(self.outputs)

        print(distances)

        self.create_exp_trials(mml_distances = distances)

        for trial in self.exp_trials:
            trial.run()
        
        self.close()


subject_id, subject_dir = create_subject_dir() #create subject directory for data storage

if __name__ == '__main__':
    my_sess = CascExpSession(subject_id, subject_dir, 'settings.yml')
    my_sess.run()