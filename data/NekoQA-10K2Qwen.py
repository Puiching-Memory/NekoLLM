# 将https://huggingface.co/datasets/liumindmind/NekoQA-10K格式转换为Qwen格式

from datasets import load_dataset
import json

dataset = load_dataset("liumindmind/NekoQA-10K")

all_meta = []

for instruction, output in zip(dataset["train"]["instruction"], dataset["train"]["output"]):
    meta = {"messages": [{"role": "system", "content": "你将扮演neko参与到聊天群聊的话题中"},]}
    meta["messages"].append({"role": "user", "content": instruction})
    meta["messages"].append({"role": "assistant", "content": output})
    all_meta.append(meta)

with open("NekoQA-10K.jsonl", "w", encoding="utf-8") as f:
    for meta in all_meta:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
