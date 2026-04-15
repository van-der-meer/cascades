import csv
import os
import yaml
import numpy as np
from psychopy import visual
from psychopy.tools.monitorunittools import deg2pix
from exptools2.core import Trial, Session
from functions_v8_kde import validate_experiment_folder, create_subject_dir

# Vertices for a plus-sign fixation cross, normalised to [-0.5, 0.5].
# Multiply by `size` (deg) to get the rendered cross.  Arm width ≈ 20 % of size.
_CROSS_VERTS = [
    (-0.1,  0.5), ( 0.1,  0.5),
    ( 0.1,  0.1), ( 0.5,  0.1),
    ( 0.5, -0.1), ( 0.1, -0.1),
    ( 0.1, -0.5), (-0.1, -0.5),
    (-0.1, -0.1), (-0.5, -0.1),
    (-0.5,  0.1), (-0.1,  0.1),
]


# ─────────────────────────────────────────────────────────────────────────────
# KDE trial
# ─────────────────────────────────────────────────────────────────────────────

class KDE_Trial(Trial):

    def __init__(self, session, trial_nr, phase_durations, phase_names,
                 parameters, timing, load_next_during_phase, verbose,
                 fixation_by_phase=None):
        """ Initializes a KDE_Trial object.

        Stimulus parameters in `parameters` dict (all optional):
            n_dots         : int   - number of dots per sphere (default 200)
            sphere_radius  : float - sphere radius in degrees (default 5.0)
            dot_size       : float - dot diameter in degrees (default 0.15)
            rotation_speed : float - seconds per full rotation (default 2.0)
            random_seed    : int   - seed for dot placement (default 42)
            size_modulation: bool  - depth-based dot size modulation (default True)
            spheres        : list  - per-sphere overrides; each entry is a dict
                                     that can override any parameter above plus
                                     'position'       ([x, y] in deg, default [0, 0])
                                     'visible_phases' (list of phase names where this
                                                       sphere is shown; omit or None
                                                       means visible in all phases).
                                     'depth_mod_amp'  scalar OR [start, end] for a
                                                       linear ramp over the sphere's
                                                       total visible duration.
                                     If omitted, a single centred sphere is shown.

        fixation_by_phase : dict or None
            Maps phase name → fixation-cross spec dict.  Omit a phase name (or
            pass None) to show no fixation cross during that phase.  Each spec
            may contain:
                position : [x, y] in deg   (default [0, 0])
                size     : total cross span in deg (default 0.5)
                color    : [r, g, b]        (default [1, 1, 1])
        """
        # Pull sphere specs out before passing parameters to the parent, because
        # exptools2 tries to log every entry in `parameters` and a list-of-dicts
        # will crash the pandas logging code.
        sphere_specs   = parameters.pop('spheres', [{}])
        super().__init__(session, trial_nr, phase_durations, phase_names,
                         parameters, timing, load_next_during_phase, verbose)

        # Global defaults (apply to every sphere unless overridden)
        self._defaults = {
            'n_dots':           parameters.get('n_dots', 200),
            'sphere_radius':    parameters.get('sphere_radius', 5.0),
            'dot_size':         parameters.get('dot_size', 0.15),
            'rotation_speed':   parameters.get('rotation_speed', 2.0),
            'random_seed':      parameters.get('random_seed', 42),
            'depth_mod_center': parameters.get('depth_mod_center', 0.75),  # size = dot_size * (center + amp * depth_norm)
            'depth_mod_amp':    parameters.get('depth_mod_amp',    0.25),  # scalar or [start, end]
        }
        self._fixation_by_phase = fixation_by_phase or {}
        self._fixation_stim = visual.ShapeStim(
            self.session.win,
            vertices=_CROSS_VERTS,
            units='deg',
            size=0.5,
            fillColor=(1, 1, 1),
            lineColor=None,
            autoLog=False,
        )

        # Lookup used by _build_sphere_cache to compute ramp durations.
        _phase_dur_by_name = dict(zip(phase_names, phase_durations))

        self._sphere_caches     = []
        self._sphere_frame_idxs = []
        self._sphere_amp_idxs   = []   # separate counter for depth_mod_amp ramp

        for spec in sphere_specs:
            cache = self._build_sphere_cache(spec, _phase_dur_by_name)
            self._sphere_caches.append(cache)
            self._sphere_frame_idxs.append(0)
            self._sphere_amp_idxs.append(0)

        # Convert all cached coordinates and sizes from deg → pix once at init.
        # This eliminates PsychoPy's per-frame deg2pix transform inside draw().
        pix_per_deg = float(deg2pix(np.float32(1.0), self.session.win.monitor))
        for cache in self._sphere_caches:
            cache['xys']      *= pix_per_deg
            cache['dot_size']  = np.float32(cache['dot_size'] * pix_per_deg)
            if cache['sizes_cache'] is not None:
                cache['sizes_cache'] *= pix_per_deg

        # One combined ElementArrayStim for all dots across all sphere caches.
        # Reduces N OpenGL draw calls per frame to exactly 1.
        total_n_dots = sum(c['n_dots'] for c in self._sphere_caches)
        self._combined_xys   = np.full((total_n_dots, 2), 1e9, dtype=np.float32)
        self._combined_sizes = np.zeros(total_n_dots, dtype=np.float32)

        # Slice (start, end) into the combined arrays for each sphere cache.
        self._sphere_slices = []
        offset = 0
        for cache in self._sphere_caches:
            nd = cache['n_dots']
            self._sphere_slices.append((offset, offset + nd))
            offset += nd

        # Visible-cache list: rebuilt on phase transitions, not every frame.
        # Each entry is (frame_idx_ptr, amp_idx_ptr, cache, start, end).
        self._prev_phase_name = None
        self._visible_caches  = []   # populated on first draw()

        self._stim = visual.ElementArrayStim(
            self.session.win,
            nElements=total_n_dots,
            elementTex=None,
            elementMask='circle',
            units='pix',            # no per-frame deg→pix conversion
            sizes=1.0,
            colors=(1, 1, 1),
            colorSpace='rgb',
            autoLog=False,
        )

    def _build_sphere_cache(self, spec, phase_dur_by_name):
        """Pre-compute projected positions for one sphere for a full rotation.

        Parameters
        ----------
        spec : dict
            Per-sphere overrides (any key from _defaults, plus 'position' and
            'visible_phases').
        phase_dur_by_name : dict
            Maps phase name → duration in seconds.  Used to compute the total
            visible duration when depth_mod_amp is a [start, end] ramp.

        Returns
        -------
        dict with keys:
            xys              : (n_frames, n_dots, 2)
            depths           : (n_frames, n_dots)
            n_frames         : int
            n_dots           : int
            dot_size         : float
            sphere_radius    : float
            depth_mod_center : float  – size = dot_size * (center + amp * depth_norm)
            depth_mod_amp_start : float
            depth_mod_amp_delta : float  – end - start (0 for constant amplitude)
            amp_n_frames     : int    – total frames over which to ramp (1 = constant)
            position         : (2,) float array  – (x, y) offset in deg
            visible_phases   : list[str] or None – None means always visible
        """
        n_dots           = spec.get('n_dots',           self._defaults['n_dots'])
        sphere_radius    = spec.get('sphere_radius',    self._defaults['sphere_radius'])
        dot_size         = spec.get('dot_size',         self._defaults['dot_size'])
        rotation_speed   = spec.get('rotation_speed',   self._defaults['rotation_speed'])
        random_seed      = spec.get('random_seed',      self._defaults['random_seed'])
        depth_mod_center = spec.get('depth_mod_center', self._defaults['depth_mod_center'])
        raw_amp          = spec.get('depth_mod_amp',    self._defaults['depth_mod_amp'])
        position         = np.array(spec.get('position', [0.0, 0.0]), dtype=np.float32)
        visible_phases   = spec.get('visible_phases',   None)   # None = always visible

        # depth_mod_amp may be a scalar or [start, end] for a linear ramp.
        if isinstance(raw_amp, (list, tuple)):
            amp_start, amp_end = float(raw_amp[0]), float(raw_amp[1])
        else:
            amp_start = amp_end = float(raw_amp)

        fps = self.session.actual_framerate
        n_frames = max(1, int(round(fps * rotation_speed)))

        # Total frames over which to spread the ramp (1 = constant amplitude).
        if amp_start != amp_end:
            if visible_phases is None:
                total_dur = sum(phase_dur_by_name.values())
            else:
                total_dur = sum(phase_dur_by_name.get(p, 0.0) for p in visible_phases)
            amp_n_frames = max(1, int(round(fps * total_dur)))
        else:
            amp_n_frames = 1

        rng = np.random.default_rng(random_seed)
        pts = rng.standard_normal((n_dots, 3))
        pts /= np.linalg.norm(pts, axis=1, keepdims=True)
        pts *= sphere_radius

        x0 = pts[:, 0].astype(np.float32)
        y0 = pts[:, 1].astype(np.float32)
        z0 = pts[:, 2].astype(np.float32)

        angles = np.linspace(0.0, 2.0 * np.pi, n_frames, endpoint=False, dtype=np.float32)
        c = np.cos(angles)   # (n_frames,)
        s = np.sin(angles)   # (n_frames,)

        # Vectorised rotation — no Python loop.
        # xr[i,j] = x0[j]*c[i] + z0[j]*s[i]  →  outer products via broadcasting
        cache_xys = np.empty((n_frames, n_dots, 2), dtype=np.float32)
        cache_xys[:, :, 0] = x0 * c[:, None] + z0 * s[:, None]
        cache_xys[:, :, 1] = y0                                   # same for every frame
        cache_xys += position                                      # pre-add offset so draw() skips it

        # depth_norm ∈ [-1,1]: pre-divide once so draw() skips the per-frame division.
        depth_norm_cache = ((-x0 * s[:, None] + z0 * c[:, None]) / sphere_radius).astype(np.float32)

        # Pre-compute the full sizes array when amplitude is constant (most phases).
        # draw() can then index directly with no arithmetic.
        amp_delta = amp_end - amp_start
        if amp_delta == 0.0:
            sizes_cache = (dot_size * (depth_mod_center + amp_start * depth_norm_cache)).astype(np.float32)
        else:
            sizes_cache = None   # computed on the fly in draw() (only phase2)

        if self.verbose:
            print(f'KDE sphere cache built: {n_frames} frames '
                  f'({rotation_speed:.2f} s/rotation @ {fps:.1f} fps), '
                  f'{n_dots} dots, position={position}')

        return {
            'xys':                  cache_xys,        # world-space, position pre-added
            'depth_norm':           depth_norm_cache,  # depths / sphere_radius
            'sizes_cache':          sizes_cache,       # (n_frames, n_dots) or None
            'n_frames':             n_frames,
            'n_dots':               n_dots,
            'dot_size':             np.float32(dot_size),
            'depth_mod_center':     np.float32(depth_mod_center),
            'depth_mod_amp_start':  np.float32(amp_start),
            'depth_mod_amp_delta':  np.float32(amp_delta),
            'amp_n_frames':         amp_n_frames,
            # frozenset for O(1) membership test in draw()
            'visible_phases':       frozenset(visible_phases) if visible_phases is not None else None,
        }

    def _update_visible_caches(self, phase_name):
        """Called once per phase transition. Rebuilds the visible-cache list and
        pushes newly invisible sphere slots off-screen (once, not every frame)."""
        self._visible_caches = []
        for i, (cache, sl) in enumerate(zip(self._sphere_caches, self._sphere_slices)):
            vp = cache['visible_phases']
            if vp is not None and phase_name not in vp:
                self._combined_xys[sl[0]:sl[1]] = 1e9   # off-screen, done once
            else:
                self._visible_caches.append((i, cache, sl[0], sl[1]))
        self._prev_phase_name = phase_name

    def draw(self):
        """Draw all spheres visible in the current phase, then any fixation cross."""
        phase_name = self.phase_names[self.phase]

        # Rebuild visible list only when the phase changes (not every frame).
        if phase_name != self._prev_phase_name:
            self._update_visible_caches(phase_name)

        # Iterate only over visible caches — invisible ones are already off-screen.
        for i, cache, start, end in self._visible_caches:
            idx = self._sphere_frame_idxs[i] % cache['n_frames']
            self._combined_xys[start:end] = cache['xys'][idx]

            if cache['sizes_cache'] is not None:
                self._combined_sizes[start:end] = cache['sizes_cache'][idx]
            else:
                # Ramping amp (phase2 only): compute in-place into the combined buffer slice.
                amp_idx = self._sphere_amp_idxs[i]
                t   = min(amp_idx / (cache['amp_n_frames'] - 1), 1.0)
                amp = cache['depth_mod_amp_start'] + t * cache['depth_mod_amp_delta']
                buf = self._combined_sizes[start:end]
                np.multiply(cache['depth_norm'][idx], amp, out=buf)
                buf += cache['depth_mod_center']
                buf *= cache['dot_size']

            self._sphere_frame_idxs[i] += 1
            self._sphere_amp_idxs[i]   += 1

        # Single draw call for all dots.
        self._stim.xys   = self._combined_xys
        self._stim.sizes = self._combined_sizes
        self._stim.draw()

        fx = self._fixation_by_phase.get(phase_name)
        if fx is not None:
            self._fixation_stim.pos       = fx['position']
            self._fixation_stim.size      = fx['size']
            self._fixation_stim.fillColor = fx['color']
            self._fixation_stim.draw()


# ─────────────────────────────────────────────────────────────────────────────
# Text / instruction trial  (press SPACE to continue)
# ─────────────────────────────────────────────────────────────────────────────

class TextTrial(Trial):

    def __init__(self, session, trial_nr, text, verbose=False):
        super().__init__(
            session=session,
            trial_nr=trial_nr,
            phase_durations=(3600.0,),   # effectively infinite; space ends it
            phase_names=('text',),
            parameters={},
            timing='seconds',
            load_next_during_phase=None,
            verbose=verbose,
        )
        self._text_stim = visual.TextStim(
            session.win,
            text=text,
            units='deg',
            height=0.6,
            color=(1, 1, 1),
            wrapWidth=30,
            autoLog=False,
        )

    def draw(self):
        self._text_stim.draw()
        if self.last_resp == 'space':
            self.stop_phase()


# ─────────────────────────────────────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────────────────────────────────────

class KDE_Session(Session):

    def __init__(self, output_str, output_dir, settings_file, flow_file):
        super().__init__(output_str, output_dir, settings_file)
        self.flow_file = flow_file
        self.trials = []
        self._trial_params_log = []

    def create_trials(self):
        """Build the trial list from exp_flow_v8_kde.yml."""
        with open(self.flow_file, 'r') as f:
            flow = yaml.safe_load(f)

        global_defaults = flow.get('defaults', {})
        trial_nr = 0

        for entry in flow['trials']:
            trial_type = entry['type']

            if trial_type == 'text':
                trial = TextTrial(
                    session=self,
                    trial_nr=trial_nr,
                    text=entry['text'],
                    verbose=False,
                )
                self.trials.append(trial)
                trial_nr += 1

            elif trial_type == 'kde':
                # Merge: global defaults < trial-level overrides
                params = {**global_defaults}
                for key in ('n_dots', 'sphere_radius', 'dot_size',
                            'rotation_speed', 'random_seed', 'size_modulation'):
                    if key in entry:
                        params[key] = entry[key]
                params['spheres'] = entry.get('spheres', [{}])

                phases          = entry['phases']
                phase_names     = tuple(p['name']     for p in phases)
                phase_durations = tuple(p['duration'] for p in phases)

                fixation_by_phase = {}
                for p in phases:
                    if 'fixation' in p:
                        fx = p['fixation']
                        fixation_by_phase[p['name']] = {
                            'position': fx.get('position', [0.0, 0.0]),
                            'size':     fx.get('size',     0.5),
                            'color':    fx.get('color',    [1, 1, 1]),
                        }

                trial = KDE_Trial(
                    session=self,
                    trial_nr=trial_nr,
                    phase_durations=phase_durations,
                    phase_names=phase_names,
                    parameters=params,
                    timing='seconds',
                    load_next_during_phase=None,
                    verbose=True,
                    fixation_by_phase=fixation_by_phase,
                )
                self.trials.append(trial)
                trial_nr += 1

            elif trial_type == 'kde_simple_random':
                self._add_simple_random_kde_trials(entry, global_defaults, trial_nr)
                trial_nr += entry.get('n_trials', 1)

            elif trial_type == 'kde_random':
                self._add_random_kde_trials(entry, global_defaults, trial_nr)
                trial_nr += entry.get('n_trials', 1)

            else:
                raise ValueError(f"Unknown trial type: '{trial_type}'")

    def _add_simple_random_kde_trials(self, entry, global_defaults, start_trial_nr):
        """Generate randomised KDE trials from a kde_simple_random YAML entry.

        Structure mirrors the first kde trial: 3 phases, one main sphere and
        one ambiguous second sphere that appears in the final phase.

        Randomly varied per trial
        ─────────────────────────
        • phase2 duration : uniform in phase2_duration [min, max]
        • init_amp        : drawn from {-1, +1} (50 / 50)

        Sphere visibility
        ─────────────────
        • sphere_main   phase1 → depth_mod_amp =  init_amp  (unambiguous priming)
        • sphere_main   phase2+phase3 → depth_mod_amp = -init_amp  (opposite)
        • sphere_second phase3 → depth_mod_amp = 0  (no depth cue, ambiguous)
        """
        n_trials         = entry.get('n_trials', 1)
        rng              = np.random.default_rng(entry.get('random_seed', None))
        sphere_positions = entry['sphere_positions']
        n_spheres        = len(sphere_positions)

        # ITI: uniform [min, max]
        iti_raw = entry.get('iti_duration', [1.0, 3.0])
        if isinstance(iti_raw, list):
            iti_min, iti_max = float(iti_raw[0]), float(iti_raw[1])
        else:
            iti_min = iti_max = float(iti_raw)

        p1_dur = float(entry['phase1_duration'])
        p3_dur = float(entry['phase3_duration'])

        # phase2_duration: list of >2 elements → discrete choices;
        #                  list of 2 elements  → uniform [min, max];
        #                  scalar              → fixed.
        p2_raw = entry['phase2_duration']
        if isinstance(p2_raw, list) and len(p2_raw) > 2:
            p2_choices = [float(v) for v in p2_raw]
        elif isinstance(p2_raw, list):
            p2_choices = None
            p2_min, p2_max = float(p2_raw[0]), float(p2_raw[1])
        else:
            p2_choices = [float(p2_raw)]

        # Balanced schedules (independently shuffled, then interleaved so that
        # all four combinations of direction × switch occur equally often).
        half = n_trials // 2
        amp_schedule    = [1.0] * half + [-1.0] * (n_trials - half)
        switch_schedule = [True] * half + [False] * (n_trials - half)
        rng.shuffle(amp_schedule)
        rng.shuffle(switch_schedule)

        for i in range(n_trials):
            iti_duration = float(rng.uniform(iti_min, iti_max))

            if p2_choices is not None:
                p2_duration = float(rng.choice(p2_choices))
            else:
                p2_duration = float(rng.uniform(p2_min, p2_max))

            init_amp   = amp_schedule[i]
            switches   = switch_schedule[i]
            phase23_amp = -init_amp if switches else init_amp

            prime_idx = int(rng.integers(n_spheres))
            probe_idx = int(rng.choice([j for j in range(n_spheres) if j != prime_idx]))

            prime = sphere_positions[prime_idx]
            probe = sphere_positions[probe_idx]

            amb_dot = global_defaults.get('ambiguous_dot_size',
                                          global_defaults.get('dot_size', 0.15))
            spheres = [
                {'position': prime['position'], 'random_seed': prime['random_seed'],
                 'depth_mod_amp':  init_amp,   'visible_phases': ['phase1']},
                {'position': prime['position'], 'random_seed': prime['random_seed'],
                 'depth_mod_amp':  phase23_amp, 'visible_phases': ['phase2', 'phase3']},
                {'position': probe['position'], 'random_seed': probe['random_seed'],
                 'depth_mod_amp':  0.0, 'dot_size': amb_dot, 'visible_phases': ['phase3']},
            ]

            params = {**global_defaults, 'spheres': spheres}

            trial = KDE_Trial(
                session=self,
                trial_nr=start_trial_nr + i,
                phase_durations=(iti_duration, p1_dur, p2_duration, p3_dur),
                phase_names=('phase0', 'phase1', 'phase2', 'phase3'),
                parameters=params,
                timing='seconds',
                load_next_during_phase=None,
                verbose=True,
            )
            self.trials.append(trial)

            self._trial_params_log.append({
                'trial_nr':             start_trial_nr + i,
                'trial_type':           'kde_simple_random',
                'iti_duration':         round(iti_duration, 4),
                'phase1_duration':      p1_dur,
                'phase2_duration':      p2_duration,
                'phase3_duration':      p3_dur,
                'prime_init_amp':       init_amp,          # +1 or -1
                'prime_init_direction': 'right' if init_amp > 0 else 'left',
                'prime_switches':       switches,          # True = reverses in phase2/3
                'prime_position_x':     prime['position'][0],
                'prime_position_y':     prime['position'][1],
                'probe_position_x':     probe['position'][0],
                'probe_position_y':     probe['position'][1],
            })

    def _add_random_kde_trials(self, entry, global_defaults, start_trial_nr):
        """Generate randomised KDE trials from a kde_random YAML entry.

        Randomly varied per trial
        ─────────────────────────
        • phase0 duration  : uniform in phase0_duration [min, max]
        • phase3 duration  : uniform in phase3_duration [min, max]
        • disambiguation direction : ±phase2_initial_amp (50 / 50)
        • target sphere    : drawn uniformly from sphere_positions
        • cue sphere       : drawn uniformly from the non-target spheres

        Sphere visibility logic
        ────────────────────────
        • Every non-cue sphere (including the target):
            phase2 → [±amp, 0] ramp  (disambiguation → ambiguous)
            phases 3–7 → amp = 0     (fully ambiguous)
        • Cue sphere:
            phase2 → [±amp, 0] ramp
            phase3 → amp = 0
            phase4 → absent          (fixation cross marks the cue location)
            phase5 → ∓amp            (opposite disambiguation)
            phases 6–7 → amp = 0
        """
        def _dur(key):
            """Return (min, max) whether the YAML value is a scalar or [min, max]."""
            v = entry[key]
            return (float(v[0]), float(v[1])) if isinstance(v, list) else (float(v), float(v))

        n_trials       = entry.get('n_trials', 1)
        rng_seed       = entry.get('random_seed', None)
        rng            = np.random.default_rng(rng_seed)

        sphere_positions = entry['sphere_positions']
        n_spheres        = len(sphere_positions)

        p0_min, p0_max = _dur('phase0_duration')
        p1_dur         = float(entry['phase1_duration'])
        p2_dur         = float(entry['phase2_duration'])
        p2_amp         = float(entry['phase2_initial_amp'])
        p3_min, p3_max = _dur('phase3_duration')
        p4_dur         = float(entry['phase4_duration'])
        p5_dur         = float(entry['phase5_duration'])
        p6_dur         = float(entry['phase6_duration'])
        p7_dur         = float(entry['phase7_duration'])

        for i in range(n_trials):
            p0_duration = float(rng.uniform(p0_min, p0_max))
            p3_duration = float(rng.uniform(p3_min, p3_max))
            direction   = 1 if rng.random() < 0.5 else -1
            init_amp    = direction * p2_amp
            cue_amp_p5  = -direction * p2_amp

            target_idx       = int(rng.integers(n_spheres))
            non_target_idxs  = [j for j in range(n_spheres) if j != target_idx]
            cue_idx          = int(rng.choice(non_target_idxs))

            target_pos = sphere_positions[target_idx]['position']
            cue_pos    = sphere_positions[cue_idx]['position']

            phases = [
                {'name': 'phase0', 'duration': p0_duration},
                {'name': 'phase1', 'duration': p1_dur,
                 'fixation': {'position': target_pos, 'size': 2, 'color': [1, 1, 1]}},
                {'name': 'phase2', 'duration': p2_dur},
                {'name': 'phase3', 'duration': p3_duration},
                {'name': 'phase4', 'duration': p4_dur,
                 'fixation': {'position': cue_pos, 'size': 2, 'color': [1, 1, 1]}},
                {'name': 'phase5', 'duration': p5_dur},
                {'name': 'phase6', 'duration': p6_dur,
                 'fixation': {'position': target_pos, 'size': 2, 'color': [1, 1, 1]}},
                {'name': 'phase7', 'duration': p7_dur},
            ]

            amb_dot = global_defaults.get('ambiguous_dot_size',
                                          global_defaults.get('dot_size', 0.15))
            spheres = []
            for j, sp in enumerate(sphere_positions):
                pos  = sp['position']
                seed = sp['random_seed']
                if j == cue_idx:
                    spheres.extend([
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': [init_amp, 0], 'visible_phases': ['phase2']},
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': 0, 'dot_size': amb_dot, 'visible_phases': ['phase3']},
                        # absent in phase4
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': cue_amp_p5,    'visible_phases': ['phase5']},
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': 0, 'dot_size': amb_dot, 'visible_phases': ['phase6', 'phase7']},
                    ])
                else:
                    spheres.extend([
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': [init_amp, 0], 'visible_phases': ['phase2']},
                        {'position': pos, 'random_seed': seed,
                         'depth_mod_amp': 0, 'dot_size': amb_dot,
                         'visible_phases': ['phase3', 'phase4', 'phase5', 'phase6', 'phase7']},
                    ])

            params = {**global_defaults, 'spheres': spheres}

            phase_names     = tuple(p['name']     for p in phases)
            phase_durations = tuple(p['duration'] for p in phases)

            fixation_by_phase = {}
            for p in phases:
                if 'fixation' in p:
                    fx = p['fixation']
                    fixation_by_phase[p['name']] = {
                        'position': fx.get('position', [0.0, 0.0]),
                        'size':     fx.get('size',     0.5),
                        'color':    fx.get('color',    [1, 1, 1]),
                    }

            trial = KDE_Trial(
                session=self,
                trial_nr=start_trial_nr + i,
                phase_durations=phase_durations,
                phase_names=phase_names,
                parameters=params,
                timing='seconds',
                load_next_during_phase=None,
                verbose=True,
                fixation_by_phase=fixation_by_phase,
            )
            self.trials.append(trial)

    def _save_trial_params(self):
        if not self._trial_params_log:
            return
        log_path = os.path.join(self.output_dir, 'trial_params.csv')
        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self._trial_params_log[0].keys())
            writer.writeheader()
            writer.writerows(self._trial_params_log)
        print(f'Trial parameters saved to {log_path}')

    def run(self):
        self.create_trials()
        self.start_experiment()

        try:
            for trial in self.trials:
                trial.run()
        finally:
            self.close()
            self._save_trial_params()


if __name__ == '__main__':
    validate_experiment_folder(__file__)
    base_dir      = os.path.dirname(os.path.abspath(__file__))
    settings_file = os.path.join(base_dir, 'settings.yml')
    flow_file     = os.path.join(base_dir, 'exp_flow_v8_kde.yml')
    subject_id, subject_dir = create_subject_dir('v8_kde')
    my_sess = KDE_Session(subject_id, subject_dir, settings_file, flow_file)
    my_sess.run()
