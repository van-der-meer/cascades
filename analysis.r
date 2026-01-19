setwd("/Users/daniel/Documents/Arbeit/PHD/Research/Experiment/cascades")

rm(list = ls())

library(rjson)
library(readr)
library(dplyr)

data_folder = "logs/"

#subject = "lk"
subject = "test1"

exp_params = fromJSON(file = paste(data_folder, subject, '/', subject, '_exp_params.json', sep = ''))
events = read_tsv(paste(data_folder, subject, '/', subject, '_events.tsv', sep = ''))


trial_ids = c()

for (trial in exp_params){
  trial_ids = c(trial_ids, names(trial))
}

trial_ids_numeric = as.numeric(trial_ids[1:(length(trial_ids)-1)])

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

main_trials[[1]]


side = unlist(lapply(main_trials, function(x)  x$params$side))
disamb = unlist(lapply(main_trials, function(x)  x$params$disamb))
cue_present = unlist(lapply(main_trials, function(x)  x$params$cue_present))
cue_onset = unlist(lapply(main_trials, function(x)  x$params$cue_onset))


length(side)


# no prime no cue:
table(disamb == "none" & cue_present == F)

# prime horizontal no cue:
table(disamb == "hor" & cue_present == F)

# prime vertical no cue:
table(disamb == "ver" & cue_present == F)

# prime horizontal and cue:
table(disamb == "hor" & cue_present == T)

# prime horizontal and cue left:
table(disamb == "hor" & cue_present == T & side == "left")

# prime horizontal and cue left and cue onset 4:
table(disamb == "hor" & cue_present == T & side == "left" & cue_onset == 4)
# prime horizontal and cue left and cue onset 6:
table(disamb == "hor" & cue_present == T & side == "left" & cue_onset == 6)
# prime horizontal and cue left and cue onset 8:
table(disamb == "hor" & cue_present == T & side == "left" & cue_onset == 8)

# prime horizontal and cue right:
table(disamb == "hor" & cue_present == T & side == "right")

# prime horizontal and cue left and cue onset 4:
table(disamb == "hor" & cue_present == T & side == "right" & cue_onset == 4)
# prime horizontal and cue left and cue onset 6:
table(disamb == "hor" & cue_present == T & side == "right" & cue_onset == 6)
# prime horizontal and cue left and cue onset 8:
table(disamb == "hor" & cue_present == T & side == "right" & cue_onset == 8)

# prime vertical and cue:
table(disamb == "ver" & cue_present == T)

# prime vertical and cue left:
table(disamb == "ver" & cue_present == T & side == "left")

# prime horizontal and cue left and cue onset 4:
table(disamb == "ver" & cue_present == T & side == "left" & cue_onset == 4)
# prime horizontal and cue left and cue onset 6:
table(disamb == "ver" & cue_present == T & side == "left" & cue_onset == 6)
# prime horizontal and cue left and cue onset 8:
table(disamb == "ver" & cue_present == T & side == "left" & cue_onset == 8)

# prime vertical and cue right:
table(disamb == "ver" & cue_present == T & side == "right")

# prime horizontal and cue left and cue onset 4:
table(disamb == "ver" & cue_present == T & side == "right" & cue_onset == 4)
# prime horizontal and cue left and cue onset 6:
table(disamb == "ver" & cue_present == T & side == "right" & cue_onset == 6)
# prime horizontal and cue left and cue onset 8:
table(disamb == "ver" & cue_present == T & side == "right" & cue_onset == 8)

main_trial_ids

events %>% filter(trial_nr == main_trial_ids[2])





