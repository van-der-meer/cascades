import json

# Get instruction texts
with open("exp_texts.json", "r", encoding="utf-8") as f:
    exp_texts = json.load(f)


events = [['space', 8.485667000059038]]

print("space" in events)
print(events[0])

print("mml" in "mm1")

