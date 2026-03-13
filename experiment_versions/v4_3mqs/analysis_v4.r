setwd("/Users/daniel/Documents/Arbeit/PHD/Research/Experiment/cascades")

rm(list = ls())

library(rjson)
library(readr)
library(dplyr)
library(ggplot2)

exp_version = "v4_3mqs"


# Load helper functions
source(paste("experiment_versions/", exp_version, "/functions_analysis.R", sep = ""))

data_folder = paste0("experiment_versions/", exp_version, "/logs_", exp_version, "/")

subjects <- list.dirs(data_folder, full.names = FALSE, recursive = FALSE)
subjects <- subjects[!grepl("aborted", subjects)]

subjects <- subjects[!grepl("pilot", subjects)]


#subjects = subjects[4]

# Subjects 1 and 4 (11) and (14) are excluded because they reportedly did not understand the instructions

subjects = subjects[c(2, 3, 5, 5, 6, 7, 8)]



#pp_df = get_pp_data(subject = subject)

#pp_df$subject_id

for (subject in 1:length(subjects)){
  if (subject == 1)(
    pp_df = get_pp_data(subject = subjects[subject])
  )
  else{
    pp_df = rbind(pp_df, get_pp_data(subject = subjects[subject]))
  }
}

#trial_durs %>% filter(side == "right")

trial_durs <- pp_df %>%
  mutate(
    condition = case_when(
      cue_present & cue_delay == 8 ~ "Cue delay 8",
      cue_present & cue_delay == 6  ~ "Cue delay 6",
      cue_present & cue_delay == 4  ~ "Cue delay 4",
      cue_present & cue_delay == 2  ~ "Cue delay 2",
      !cue_present & disamb %in% c("hor", "ver") ~ "Prime only",
      !cue_present & disamb == "none" ~ "No prime / no cue",
      TRUE ~ NA_character_
    )
  ) %>%
  filter(!is.na(condition))

trial_durs$condition <- factor(
  trial_durs$condition,
  levels = c(
    "Cue delay 8",
    "Cue delay 6",
    "Cue delay 4",
    "Cue delay 2",
    "Prime only",
    "No prime / no cue"
  )
)

summarise_design_cells(trial_durs)

cue_lines <- pp_df %>%
  filter(cue_present) %>%
  mutate(
    condition = case_when(
      cue_delay == 8  ~ "Cue delay 8",
      cue_delay == 6  ~ "Cue delay 6",
      cue_delay == 4  ~ "Cue delay 4",
      cue_delay == 2  ~ "Cue delay 2", 
      cue_delay == 2  ~ "Cue delay 2"
    ),
    y = cue_onset * 2 * 0.2 - amb_1_onset
  ) %>%
  group_by(condition) %>%
  summarise(y = unique(y), .groups = "drop")


# filter all trials that ended at max trial duration
trial_durs_filtered = trial_durs %>% 
  filter(trial_duration_precise > 0) %>%
  filter(trial_duration_precise < 8) %>%
  filter(
    abs((trial_duration * 2 * 0.2 - amb_1_onset - 0.2) - # cycles * phases per cycle * s per phase
          round(trial_duration_precise, 1)) > 1e-6 # solve floating point issue
  )

trial_durs_filtered %>%
  filter(disamb == "ver") %>%
  filter(side == "left") %>% pull(disamb)

trial_durs_filtered %>%
  filter(disamb == "none") %>% pull(disamb)

trial_durs_filtered %>%
  filter(condition == "Prime only")

trial_durs_filtered %>%
  ggplot(aes(x = condition, y = trial_duration_precise)) +
  geom_violin(trim = FALSE, alpha = 0.6) +
  geom_jitter(
    width = 0.15,
    height = 0,
    alpha = 0.2,
    size = 1
  ) +
  geom_boxplot(width = 0.15,
               outlier.shape = NA,
               alpha = 0.5, 
               color = "black") +
  geom_hline(
    data = cue_lines,
    aes(yintercept = y, color = condition),
    linetype = "dashed",
    inherit.aes = FALSE
  ) +
  theme_minimal(base_size = 14) +
  labs(
    x = NULL,
    y = "Trial duration (seconds)",
    title = "Trial duration by cueing condition"
  )


lm_1 <- lm(trial_duration_precise ~ condition, data = trial_durs)
summary(lm_1)


#hist(trial_durs$trial_dur, xlim = c(10, 70))

library(BayesFactor)


trial_durs_filtered_analysis = trial_durs %>% filter(disamb != "none")

bf_anova <- anovaBF(
  trial_duration_precise ~ condition,
  data = trial_durs_filtered_analysis
)

bf_anova







