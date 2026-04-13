import json

file_path = r"C:\Users\yzhang28\Desktop\rocoAnalysis\output\all_pokemon.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for pokemon in data:
    base_stats_sum = sum(pokemon["base_stats"].values())
    pokemon["base_stats_sum"] = base_stats_sum

data.sort(key=lambda x: x["base_stats_sum"], reverse=True)

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"处理完成，共 {len(data)} 只精灵")
print("前三名:")
for i, p in enumerate(data[:3]):
    print(f"  {i+1}. {p['name']}: {p['base_stats_sum']}")