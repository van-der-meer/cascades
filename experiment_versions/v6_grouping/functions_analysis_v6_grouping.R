# helper functions for analysis

get_pp_data = function(subject){
  
  exp_params = fromJSON(file = paste(data_folder, subject, '/', subject, '_exp_flow.json', sep = ''))
  events = read_tsv(paste(data_folder, subject, '/', subject, '_events.tsv', sep = ''), show_col_types = FALSE)
  
  trial_ids = c()
  
  for (trial in exp_params){
    trial_ids = c(trial_ids, names(trial))
  }
  
  
  trial_ids_numeric = as.numeric(trial_ids[1:(length(trial_ids)-2)]) # -2 to take away "mml_results" and "exp_version"
  
  group_trials = list()
  group_trial_ids = c()
  
  cascade_trials = list()
  cascade_trial_ids = c()
  
  for (trial_id in trial_ids_numeric){
    trial = exp_params[[trial_ids_numeric[trial_id]]][[trial_ids[trial_id]]]
    
    if (grepl("main_exp_cascades", trial$trial_identifier)){
      cascade_trials = append(cascade_trials, list(trial))
      cascade_trial_ids = c(cascade_trial_ids, trial_id)
    }
    
    if (grepl("main_exp_grouping", trial$trial_identifier)){
      group_trials = append(group_trials, list(trial))
      group_trial_ids = c(group_trial_ids, trial_id)
    }
    
  }
  
  grouping_trials_df = data.frame(
    group_trial_ids,
    cue_present = unlist(lapply(group_trials, function(x)
      x$params$freq)), 
    n_mqs = unlist(lapply(group_trials, function(x)
      x$params$n_mqs)), 
    fixation = unlist(lapply(group_trials, function(x)
      x$params$fixation))
  )
  
  grouping_trials_joined <- events %>%
    inner_join(grouping_trials_df, by = c("trial_nr" = "group_trial_ids")) %>%
    group_by(trial_nr) %>%
    mutate(onset_rel = onset - min(onset, na.rm = TRUE)) %>%
    ungroup()
  
  
  cascade_trials_df = data.frame(
    cascade_trial_ids,
    side = unlist(lapply(cascade_trials, function(x) {
      val <- x$params$side
      if (is.null(val)) "none" else val
    })),
    disamb = unlist(lapply(cascade_trials, function(x)
      x$params$disamb)),
    cue_present = unlist(lapply(cascade_trials, function(x)
      x$params$cue_present)),
    cue_delay = unlist(lapply(cascade_trials, function(x)
      x$params$cue_delay)),
    cue_onset = unlist(lapply(cascade_trials, function(x)
      x$params$cue_start)),
    trial_duration = unlist(lapply(cascade_trials, function(x)
      x$len_trial)), 
    cycles_prime = unlist(lapply(cascade_trials, function(x)
      x$params$cycles_prime)), 
    amb_2_start = unlist(lapply(cascade_trials, function(x)
      x$params$amb_2_start)),
    amb_2_dur = unlist(lapply(cascade_trials, function(x)
      x$params$amb_2_dur)), 
    n_biased= unlist(lapply(cascade_trials, function(x)
      x$params$n_biased))
  )
  
  # 1 cycle is 2 phases
  # 1 phase is 0.2 seconds 
  
  prime_onset = 4 * 2 * 0.2
  amb_1_onset = prime_onset + 2 * 2 * 0.2
  
  
  cascade_trials_df = cascade_trials_df %>% mutate(max_dur_calculated = amb_2_dur + amb_2_start, 
                                   max_dur_seconds = max_dur_calculated * 0.2, 
                                   amb_1_onset = amb_1_onset, 
                                   subject_id = as.numeric(subject))
  
  
  
  events_joined <- events %>%
    inner_join(cascade_trials_df, by = c("trial_nr" = "cascade_trial_ids")) 
  
  events_joined$trial_nr %>% unique() %>% length()
  
  
  trial_starts <- events_joined %>%
    group_by(trial_nr) %>% 
    slice(1)
  
  trial_ends <- events_joined %>%
    group_by(trial_nr) %>% 
    slice_tail(n=1)
  
  
  trial_durs_df <- trial_starts %>%
    mutate("trial_start" = onset_abs) %>%
    cbind("trial_end" = trial_ends$onset_abs) %>%
    mutate("trial_duration_precise" = trial_end - trial_start - amb_1_onset)
  
  combined_casc_df <- cascade_trials_df %>%
    left_join(trial_durs_df %>% select(trial_nr, trial_start, trial_end, trial_duration_precise),
              by = c("cascade_trial_ids" = "trial_nr"))
  
  return(list(grouping_trials_joined, combined_casc_df))
}

get_all_subjects_data = function(subjects){
  for (subject in 1:length(subjects)){
    if (subject == 1){
      pp_dfs = get_pp_data(subject = subjects[subject])
      grouping_df = pp_dfs[[1]]
      casc_df = pp_dfs[[2]]
    }
    else{
      pp_dfs = get_pp_data(subject = subjects[subject])
      grouping_df = rbind(grouping_df, pp_dfs[[1]])
      casc_df = rbind(casc_df, pp_dfs[[2]])
    }
  }
  return(list(grouping_df, casc_df))
}


summarise_design_cells <- function(data) {
  
  # Keep only TRUE/FALSE cue_present
  data_clean <- data %>%
    filter(cue_present %in% c(TRUE, FALSE))
  
  # ---- FULL CELLS ----
  full_cells <- data_clean %>%
    count(
      disamb,
      cue_present,
      side,
      cue_delay,
      n_biased,
      name = "n"
    ) %>%
    mutate(level = "full_cell")
  
  # ---- DISAMB × CUE (your requested combination) ----
  disamb_cue <- data_clean %>%
    count(disamb, cue_present, name = "n") %>%
    mutate(
      side = NA,
      cue_delay = NA,
      n_biased = NA,
      level = "disamb_x_cue"
    )
  
  bind_rows(full_cells, disamb_cue) %>%
    arrange(level, disamb, cue_present, side, cue_delay, n_biased)
}
