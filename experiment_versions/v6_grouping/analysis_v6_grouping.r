setwd("/Users/daniel/Documents/Arbeit/PHD/Research/Experiment/cascades/experiment_versions/v6_grouping")

rm(list = ls())

library(rjson)
library(readr)
library(dplyr)
library(ggplot2)


## WARNING file names have changed! not exp_params anymore but exp_flow/ inst_flow!

exp_version = "v6_grouping"

# Load helper functions
source("functions_analysis_v6_grouping.R")

data_folder = paste0("logs_", exp_version, "/")

subjects <- list.dirs(data_folder, full.names = FALSE, recursive = FALSE)
subjects <- subjects[!grepl("aborted", subjects)]

subject = "025"


dfs = get_all_subjects_data(subject)

grouping_df = dfs[[1]]
casc_df = dfs[[2]]


# Analysis grouping things


grouping_df


# Analysis cascading things

trial_durs <- casc_df %>%
  mutate(
    condition = case_when(
      cue_present & cue_delay == 6 ~ "Cue delay 6",
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
    "Cue delay 6",
    "Cue delay 4",
    "Cue delay 2",
    "Prime only",
    "No prime / no cue"
  )
)

summarise_design_cells(trial_durs)

cue_lines <- casc_df %>%
  filter(cue_present) %>%
  mutate(
    condition = case_when(
      cue_delay == 6  ~ "Cue delay 6",
      cue_delay == 4  ~ "Cue delay 4",
      cue_delay == 2  ~ "Cue delay 2"
    ),
    y = cue_onset * 2 * 0.2 - amb_1_onset
  ) %>%
  group_by(condition) %>%
  summarise(y = unique(y), .groups = "drop")


# filter all trials that ended at max trial duration
trial_durs_filtered = trial_durs %>% 
  filter(trial_duration_precise > 0) %>%
  filter(
    abs((trial_duration * 2 * 0.2 - amb_1_onset - 0.2) - # cycles * phases per cycle * s per phase
          round(trial_duration_precise, 1)) > 1e-6 # solve floating point issue
  )

trial_durs_filtered %>%
  filter(n_biased == 3) %>%
  #filter(side == "right") %>% 
  filter(disamb == "ver") %>%
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


trial_durs_filtered_test = trial_durs %>% 
  filter(disamb != "none") %>% 
  filter(n_biased == 3) 


bf_anova <- anovaBF(
  trial_duration_precise ~ condition,
  data = trial_durs_filtered_test
)

bf_anova



#summarise_design_cells(trial_durs_filtered)
