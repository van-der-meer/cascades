library(tidyverse)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

LOG_DIR <- "logs_v8_kde"

# Key → rotation direction mapping.
# Assumption: init_amp = +1 means the prime rotated "right"; left key = aligned
# when init_amp = -1, right key = aligned when init_amp = +1.
# Flip this if the mapping is reversed in your setup.
ALIGNED_KEY <- list(`1` = "right", `-1` = "left")


# ─────────────────────────────────────────────────────────────────────────────
# Load data from all subject folders
# ─────────────────────────────────────────────────────────────────────────────

subject_dirs <- list.dirs(LOG_DIR, recursive = FALSE)

load_subject <- function(subj_dir) {
  subj_id     <- basename(subj_dir)
  events_file <- file.path(subj_dir, paste0(subj_id, "_events.tsv"))
  params_file <- file.path(subj_dir, "trial_params.csv")

  if (!file.exists(events_file) || !file.exists(params_file)) return(NULL)

  events <- read_tsv(events_file, show_col_types = FALSE) |>
    mutate(subject = subj_id)

  params <- read_csv(params_file, show_col_types = FALSE) |>
    mutate(subject = subj_id) |>
    filter(trial_type == "kde_simple_random")

  list(events = events, params = params)
}

all_data   <- map(subject_dirs, load_subject) |> compact()
all_events <- map(all_data, "events") |> bind_rows()
all_params <- map(all_data, "params") |> bind_rows()


# ─────────────────────────────────────────────────────────────────────────────
# Extract phase2 duration and probe-phase response per trial
# ─────────────────────────────────────────────────────────────────────────────

# Phase2 onset and end for each trial (used to identify the probe window)
phase3_windows <- all_events |>
  filter(event_type == "phase3") |>
  select(subject, trial_nr, phase3_onset = onset, phase3_duration = duration) |>
  mutate(phase3_end = phase3_onset + phase3_duration)

# First response that falls within the phase3 window
responses <- all_events |>
  filter(event_type == "response", response %in% c("left", "right")) |>
  select(subject, trial_nr, resp_onset = onset, response) |>
  inner_join(phase3_windows, by = c("subject", "trial_nr")) |>
  filter(resp_onset >= phase3_onset, resp_onset <= phase3_end) |>
  group_by(subject, trial_nr) |>
  slice_min(resp_onset, n = 1, with_ties = FALSE) |>
  ungroup()


# ─────────────────────────────────────────────────────────────────────────────
# Join with trial params and compute alignment
# ─────────────────────────────────────────────────────────────────────────────

df <- responses |>
  inner_join(all_params, by = c("subject", "trial_nr")) |>
  mutate(
    aligned_key = if_else(init_amp == 1, ALIGNED_KEY[["1"]], ALIGNED_KEY[["-1"]]),
    aligned     = response == aligned_key,
    # Round phase2_duration to nearest discrete value for clean x-axis labels
    probe_delay = factor(phase2_duration)
  )


# ─────────────────────────────────────────────────────────────────────────────
# Summarise and plot
# ─────────────────────────────────────────────────────────────────────────────

summary_df <- df |>
  group_by(probe_delay) |>
  summarise(
    n          = n(),
    n_aligned  = sum(aligned),
    prop_aligned = mean(aligned),
    se         = sqrt(prop_aligned * (1 - prop_aligned) / n),
    .groups    = "drop"
  )

print(summary_df)

p <- ggplot(summary_df, aes(x = probe_delay, y = prop_aligned)) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "grey60") +
  geom_errorbar(aes(ymin = prop_aligned - se, ymax = prop_aligned + se),
                width = 0.15, linewidth = 0.7) +
  geom_point(aes(size = n), shape = 21, fill = "steelblue", color = "white",
             stroke = 1.2) +
  scale_y_continuous(limits = c(0, 1), labels = scales::percent_format()) +
  scale_size_continuous(range = c(3, 8), guide = guide_legend(title = "n trials")) +
  labs(
    x     = "Probe delay – phase 2 duration (s)",
    y     = "Proportion aligned with prime direction",
    title = "KDE prime–probe alignment by probe delay"
  ) +
  theme_minimal(base_size = 13) +
  theme(panel.grid.minor = element_blank())

print(p)
ggsave("probe_delay_alignment.png", p, width = 7, height = 5, dpi = 150)
