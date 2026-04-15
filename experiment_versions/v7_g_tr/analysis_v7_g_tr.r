setwd("/Users/daniel/Documents/Arbeit/PHD/Research/Experiment/cascades/experiment_versions/v7_g_tr")

rm(list = ls())

library(rjson)
library(readr)
library(dplyr)
library(tidyr)
library(ggplot2)
library(BayesFactor)


## WARNING file names have changed! not exp_params anymore but exp_flow/ inst_flow!

exp_version = "v7_g_tr"

# Load helper functions
source("functions_analysis_v7_g_tr.R")

data_folder = paste0("logs_", exp_version, "/")

subjects <- list.dirs(data_folder, full.names = FALSE, recursive = FALSE)
subjects <- subjects[!grepl("aborted", subjects)]
#subjects <- subjects[!grepl("test", subjects)]

subjects <- subjects[-1] # first is dummy subject to test data collection

length(subjects)

dfs = get_all_subjects_data(subjects)

grouping_df = dfs[[1]]
casc_df = dfs[[2]]


# Analysis grouping things
grouping_df$fixation %>% table


grouping_df %>% 
  group_by(subject_id, freq, n_mqs, fixation) %>%
  filter(response == "space") %>% pull(trial_nr) %>% unique()


# grouping_df %>% 
#   group_by(subject_id, freq, n_mqs, fixation, trial_nr) %>%
#   filter(response == "space") %>% 
#   filter(freq != 3) %>%
#   summarise(n_switches = n(), .groups = "drop") %>% 
#   mutate(fixation = ifelse(n_mqs == 1, FALSE, fixation),
#          condition = paste(freq, n_mqs, fixation, sep = "_"),
#          n_mqs = as.factor(n_mqs)) %>% 
#   ggplot(aes(x = condition, y = n_switches)) +
#   geom_violin(trim = FALSE) +
#   geom_boxplot(width = 0.2) +
#   geom_jitter(width = 0.1, alpha = 0.6) +
#   labs(
#     x = "Number of MQs",
#     y = "Number of Switches"
#   )

# Method 1:

t_test_df <- grouping_df %>%
  filter(response == "space", freq != 3) %>%
  filter(fixation == FALSE) %>%
  group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
  arrange(onset, .by_group = TRUE) %>%
  filter(n() >= 2) %>%
  summarise(
    dominance_durations = list(diff(onset)),
    n_switches = n() - 1,
    .groups = "drop"
  ) %>%
  unnest(dominance_durations) %>%
  group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
  slice(-1, -n()) %>%  # remove first & last (censored) durations
  ungroup() %>%
  mutate(
    cond = as.factor(paste(freq, n_mqs, fixation, sep = "_")),
    n_mqs = as.factor(n_mqs),
    dominance_duration_log = log(dominance_durations)
  ) 
  

t_test_df %>%
  ggplot(aes(x = n_mqs, y = dominance_duration_log)) +
  geom_violin(trim = FALSE) +
  geom_jitter(width = 0.1, alpha = 0.6) +
  geom_boxplot(width = 0.2) +
  labs(
    y = "diff switches"
  )


t.test(dominance_duration_log ~ n_mqs, t_test_df)


# Method 2

# t_test_df <- grouping_df %>% 
#   group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
#   filter(response == "space") %>% 
#   #filter(subject_id == subjects[5]) %>% 
#   filter(fixation == FALSE) %>% 
#   filter(freq != 3) %>%
#   summarise(diff_switches_log = mean(log(diff(onset)))) %>%
#   mutate(#fixation = ifelse(n_mqs == 1, FALSE, fixation),
#     cond = as.factor(paste(freq, n_mqs, fixation, sep = "_")),
#     n_mqs = as.factor(n_mqs))
# 
# t_test_df %>% 
#   ggplot(aes(x = n_mqs, y = diff_switches_log)) +
#   geom_violin(trim = FALSE) +
#   geom_boxplot(width = 0.2) +
#   geom_jitter(width = 0.1, alpha = 0.6) +
#   labs(
#     y = "diff switches"
#   )
# 
# t.test(diff_switches_log ~ n_mqs, t_test_df)

#### mixed model

library(lme4)
library(emmeans)
library(lmerTest)

model_df <- grouping_df %>%
  filter(response == "space", freq != 3) %>%
  group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
  arrange(onset, .by_group = TRUE) %>%
  filter(n() >= 2) %>%
  summarise(
    dominance_durations = list(diff(onset)),
    n_switches = n() - 1,
    .groups = "drop"
  ) %>%
  unnest(dominance_durations) %>%
  group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
  slice(-1, -n()) %>%
  ungroup() %>%
  mutate(
    n_mqs = as.factor(n_mqs),
    fixation = as.factor(fixation),
    dominance_duration_log = log(dominance_durations)
  )

mod <- lmer(
  dominance_duration_log ~ n_mqs * fixation + (1 | subject_id) + (1 | subject_id:trial_nr),
  data = model_df
)

summary(mod)
anova(mod)

emm <- emmeans(mod, ~ n_mqs | fixation)
pairs(emm)


# include random pps as random effects in model 


grouping_df %>% 
  group_by(subject_id, trial_nr, freq, n_mqs, fixation) %>%
  filter(response == "space") %>% 
  filter(freq != 3) %>%
  summarise(diff_switches = mean(diff(onset))) %>%
  mutate(#fixation = ifelse(n_mqs == 1, FALSE, fixation),
    cond = as.factor(paste(freq, n_mqs, fixation, sep = "_")),
    n_mqs = as.factor(n_mqs), 
    subject_id = as.factor(subject_id), 
    diff_switches_log = log(diff_switches)) %>% 
  anovaBF(diff_switches_log ~ n_mqs + subject_id, data = ., whichRandom = "subject_id")




grouping_df %>% 
  filter(freq != 3) %>%
  group_by(subject_id, trial_nr) %>%
  arrange(onset, .by_group = TRUE) %>%
  mutate(
    onset_rel = onset - first(onset),
  ) %>% 
  filter(onset_rel == 0 | response == "space") %>%
  mutate(
    onset_rel_diff = onset_rel - lag(onset_rel)
  ) %>% 
  filter(!is.na(onset_rel_diff)) %>%
  pull(onset_rel_diff) %>% log() %>% hist(breaks = 30, main = "Dominance durations combined")

diff_grouping_switches <- grouping_df %>% 
  filter(freq != 3) %>%
  group_by(subject_id, trial_nr) %>%
  arrange(onset, .by_group = TRUE) %>%
  mutate(
    onset_rel = onset - first(onset),
  ) %>% 
  filter(onset_rel == 0 | response == "space") %>%
  mutate(
    onset_rel_diff = onset_rel - lag(onset_rel)
  ) %>% 
  filter(!is.na(onset_rel_diff)) %>% 
  mutate(#fixation = ifelse(n_mqs == 1, FALSE, fixation),
         cond = as.factor(paste(freq, n_mqs, fixation, sep = "_")),
         n_mqs = as.factor(n_mqs)) 
  
diff_grouping_switches %>% 
  ggplot(aes(x = cond, y = onset_rel_diff)) +
  geom_violin(trim = FALSE) +
  geom_jitter(width = 0.4, alpha = 0.2) +
  geom_boxplot(width = 0.2) +
  labs(
    y = "diff switches"
  )


anova_grouping_switches <- anovaBF(onset_rel_diff ~ cond, data = data.frame(diff_grouping_switches))

1/anova_grouping_switches


?anovaBF()

# check for difference in time/ frequency as predictor for switch rate 
  
# Add experiments in netlogo (world parameters can be updated)

# Implement experiments in netlogo

# Do simulations to see how much data we need to falsify constant hazard rate (exponential dist)

# Analysis cascading things

# Good reason to contact people is me looking for conferences and looking for symposia to apply 

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

# check for difference in ceiling effects between conditions


trial_durs_filtered %>%
  filter(n_biased == 3) %>%
  #filter(side == "right") %>% 
  #filter(disamb == "ver") %>%
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


lm_1 <- lm(trial_duration_precise ~ condition, data = trial_durs_filtered)
summary(lm_1)


# combine data and compute bayes factors

# if no conclusive bf in either direction, collect more data 

# if the effect exists at all, it is a bit hard to find since we tried many different setups 

# effects are fickle 

# make sure to collect effects or 0 results!!

#hist(trial_durs$trial_dur, xlim = c(10, 70))

library(BayesFactor)

trial_durs_filtered$condition

trial_durs_filtered_test = trial_durs_filtered %>% 
  filter(disamb != "none") %>% 
  filter(n_biased == 3) %>%
  filter(condition %in% c("Cue delay 2", "Prime only")) 


t.test(trial_duration_precise ~ condition, trial_durs_filtered_test)



bf_anova <- anovaBF(
  trial_duration_precise ~ condition,
  data = trial_durs_filtered_test
)

bf_anova
  
