# helper functions for analysis

get_pp_data = function(subject){
  
  exp_params = fromJSON(file = paste(data_folder, subject, '/', subject, '_exp_params.json', sep = ''))
  events = read_tsv(paste(data_folder, subject, '/', subject, '_events.tsv', sep = ''))
  
  trial_ids = c()
  
  for (trial in exp_params){
    trial_ids = c(trial_ids, names(trial))
  }
  
  
  trial_ids_numeric = as.numeric(trial_ids[1:(length(trial_ids)-2)]) # -2 to take away "mml_results" and "exp_version"
  
  
  main_trials = list()
  main_trial_ids = c()
  
  for (trial_id in trial_ids_numeric){
    trial = exp_params[[trial_ids_numeric[trial_id]]][[trial_ids[trial_id]]]
    
    if (grepl("main_exp", trial$trial_identifier)){
      main_trials = append(main_trials, list(trial))
      main_trial_ids = c(main_trial_ids, trial_id)
    }
    
  }
  
  
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
      x$len_trial)), 
    cycles_prime = unlist(lapply(main_trials, function(x)
      x$params$cycles_prime)), 
    amb_2_start = unlist(lapply(main_trials, function(x)
      x$params$amb_2_start)),
    amb_2_dur = unlist(lapply(main_trials, function(x)
      x$params$amb_2_dur))
  )
  
  # 1 cycle is 2 phases
  # 1 phase is 0.2 seconds 
  
  prime_onset = 4 * 2 * 0.2
  amb_1_onset = prime_onset + 2 * 2 * 0.2
  
  
  params_df = params_df %>% mutate(max_dur_calculated = amb_2_dur + amb_2_start, 
                                   max_dur_seconds = max_dur_calculated * 0.2, 
                                   amb_1_onset = amb_1_onset, 
                                   subject_id = as.numeric(subject))
  
  
  
  events_joined <- events %>%
    inner_join(params_df, by = c("trial_nr" = "main_trial_ids")) 
  
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
  
  combined_df <- params_df %>%
    left_join(trial_durs_df %>% select(trial_nr, trial_start, trial_end, trial_duration_precise),
              by = c("main_trial_ids" = "trial_nr"))
  
  return(combined_df)
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
      name = "n"
    ) %>%
    mutate(level = "full_cell")
  
  # ---- DISAMB × CUE (your requested combination) ----
  disamb_cue <- data_clean %>%
    count(disamb, cue_present, name = "n") %>%
    mutate(
      side = NA,
      cue_delay = NA,
      level = "disamb_x_cue"
    )
  
  bind_rows(full_cells, disamb_cue) %>%
    arrange(level, disamb, cue_present, side, cue_delay)
}
