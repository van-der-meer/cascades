setwd("/Users/daniel/Documents/Arbeit/PHD/Research/Experiment/cascades")

rm(list = ls())

library(rjson)
library(readr)
library(dplyr)
library(ggplot2)

exp_version = "v5"

data_folder = paste0("experiment_versions/", exp_version, "/logs_", exp_version, "/")

subject = "test123"
#subject = "test_daniel"


exp_params = fromJSON(file = paste(data_folder, subject, '/', subject, '_exp_params.json', sep = ''))
events = read_tsv(paste(data_folder, subject, '/', subject, '_events.tsv', sep = ''))

trial_ids = c()

for (trial in exp_params){
  trial_ids = c(trial_ids, names(trial))
}

# pp 001 and 002
#trial_ids_numeric = as.numeric(trial_ids[1:(length(trial_ids)-1)])

trial_ids_numeric = as.numeric(trial_ids[1:(length(trial_ids)-2)])

trial = 1

main_trials = list()
main_trial_ids = c()

for (trial_id in trial_ids_numeric){
  trial = exp_params[[trial_ids_numeric[trial_id]]][[trial_ids[trial_id]]]
  
  if (grepl("main_exp", trial$trial_identifier)){
    main_trials = append(main_trials, list(trial))
    main_trial_ids = c(main_trial_ids, trial_id)
    }
  
}

main_trials[[1]][[1]]

prime_start = 4
cycles_prime = 2


params_df = data.frame(
  main_trial_ids,
  side = unlist(lapply(main_trials, function(x)
    x$params$side)),
  disamb = unlist(lapply(main_trials, function(x)
    x$params$disamb)),
  cue_present = unlist(lapply(main_trials, function(x)
    x$params$cue_present)),
  cue_delay = unlist(lapply(main_trials, function(x)
    x$params$cue_delay)),
  cue_onset = unlist(lapply(main_trials, function(x)
    x$params$cue_start)),
  trial_duration = unlist(lapply(main_trials, function(x)
    x$len_trial))
)



# no prime no cue:
params_df %>% filter(disamb == "none", cue_present == F) %>% nrow() 

# prime horizontal no cue:
params_df %>% filter(disamb == "hor", cue_present == F) %>% nrow()

# prime vertical no cue:
params_df %>% filter(disamb == "ver", cue_present == F) %>% nrow()

# prime horizontal and cue:
params_df %>% filter(disamb == "hor", cue_present == T) %>% nrow()

# prime horizontal and cue left:
params_df %>% filter(disamb == "hor", cue_present == T, side == "left") %>% nrow()

# prime horizontal and cue left and cue onset 2:
params_df %>% filter(disamb == "hor", cue_present == T, side == "left", cue_delay == 2) %>% nrow()
# prime horizontal and cue left and cue onset 4:
params_df %>% filter(disamb == "hor", cue_present == T, side == "left", cue_delay == 4) %>% nrow()
# prime horizontal and cue left and cue onset 6:
params_df %>% filter(disamb == "hor", cue_present == T, side == "left", cue_delay == 6) %>% nrow()

# primed and cue onset 2:
params_df %>% filter(cue_present == T, cue_delay == 2) %>% nrow()
# primes and cue onset 4:
params_df %>% filter(cue_present == T, cue_delay == 4) %>% nrow()
# primes and cue onset 6:
params_df %>% filter(cue_present == T, cue_delay == 6) %>% nrow()

# prime horizontal and cue right:
params_df %>% filter(disamb == "hor", cue_present == T, side == "right") %>% nrow()

# prime horizontal and cue right and cue onset 2:
params_df %>% filter(disamb == "hor", cue_present == T, side == "right", cue_delay == 2) %>% nrow()
# prime horizontal and cue right and cue onset 4:
params_df %>% filter(disamb == "hor", cue_present == T, side == "right", cue_delay == 4) %>% nrow()
# prime horizontal and cue right and cue onset 6:
params_df %>% filter(disamb == "hor", cue_present == T, side == "right", cue_delay == 6) %>% nrow()

# prime vertical and cue:
params_df %>% filter(disamb == "ver", cue_present == T) %>% nrow()

# prime vertical and cue left:
params_df %>% filter(disamb == "ver", cue_present == T, side == "left") %>% nrow()

# prime vertical and cue left and cue onset 2:
params_df %>% filter(disamb == "ver", cue_present == T, side == "left", cue_delay == 2) %>% nrow()
# prime vertical and cue left and cue onset 4:
params_df %>% filter(disamb == "ver", cue_present == T, side == "left", cue_delay == 4) %>% nrow()
# prime vertical and cue left and cue onset 6:
params_df %>% filter(disamb == "ver", cue_present == T, side == "left", cue_delay == 6) %>% nrow()

# prime vertical and cue right:
params_df %>% filter(disamb == "ver", cue_present == T, side == "right") %>% nrow()

# prime vertical and cue right and cue onset 4:
params_df %>% filter(disamb == "ver", cue_present == T, side == "right", cue_delay == 2) %>% nrow()
# prime vertical and cue right and cue onset 6:
params_df %>% filter(disamb == "ver", cue_present == T, side == "right", cue_delay == 4) %>% nrow()
# prime vertical and cue right and cue onset 8:
params_df %>% filter(disamb == "ver", cue_present == T, side == "right", cue_delay == 6) %>% nrow()

params_df %>% head()
events %>% head()

#valid_response_trials = main_trial_ids[25:length(main_trial_ids)]
#valid_response_trials = main_trial_ids[25:50]

#valid_response_trials = main_trial_ids[25:length(main_trial_ids)]

#valid_response_trials = main_trial_ids[0:24]

valid_response_trials = main_trial_ids


events_joined <- events %>%
  inner_join(params_df, by = c("trial_nr" = "main_trial_ids")) %>%
  filter(trial_nr %in% valid_response_trials)

events_joined$trial_nr %>% unique() %>% length()


# trial_durs <- events_joined %>%
#   group_by(trial_nr, cue_present, cue_delay, disamb) %>%
#   summarise(trial_dur = n(), .groups = "drop")


trial_starts <- events_joined %>%
  group_by(trial_nr) %>% 
  slice(1)

trial_ends <- events_joined %>%
  group_by(trial_nr) %>% 
  slice_tail(n=1)


trial_durs_df <- trial_starts %>%
  mutate("trial_start" = onset_abs) %>%
  cbind("trial_end" = trial_ends$onset_abs) %>%
  mutate("trial_duration_precise" = trial_end - trial_start)


trial_durs_df$trial_duration_precise


#?slice

trial_durs <- trial_durs_df %>%
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


cue_lines <- params_df %>%
  filter(cue_present) %>%
  mutate(
    condition = case_when(
      cue_delay == 8 ~ "Cue delay 8",
      cue_delay == 6  ~ "Cue delay 6",
      cue_delay == 4  ~ "Cue delay 4",
      cue_delay == 2  ~ "Cue delay 2"
    ),
    y = cue_onset * 2 * 0.2
  ) %>%
  group_by(condition) %>%
  summarise(y = unique(y), .groups = "drop")


trial_durs %>%
  #filter(disamb == "hor") %>%
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


# change 0 time to ambiguous start!

lm_1 <- lm(trial_duration_precise ~ condition, data = trial_durs)
summary(lm_1)


#hist(trial_durs$trial_dur, xlim = c(10, 70))

library(BayesFactor)


trial_durs_filtered = trial_durs %>% filter(disamb != "none")

bf_anova <- anovaBF(
  trial_dur ~ condition,
  data = trial_durs_filtered
)

1/bf_anova



control = events %>%
  filter(trial_nr %in% valid_response_trials) %>% 
  filter(trial_nr %in% filter(params_df, cue_present == F, disamb %in% c("hor", "ver"))$main_trial_ids) %>%
  group_by(trial_nr) %>% 
  summarise("trial_dur" = n()) %>% pull(trial_dur)

cued = events %>%
  filter(trial_nr %in% valid_response_trials) %>% 
  filter(trial_nr %in% filter(params_df, cue_present == T)$main_trial_ids) %>%
  group_by(trial_nr) %>% 
  summarise("trial_dur" = n()) %>% pull(trial_dur)



#t.test(control, cued, paired = F)







