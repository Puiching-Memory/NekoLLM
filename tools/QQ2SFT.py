import jsonl
from pprint import pprint

data = jsonl.load("group_765049040.jsonl")

for message in data:
    del message["group_id"] # 同一个文件内group_id相同
    del message["image_urls"] # QQ信息中图片的链接很快就会失效
    pprint(message)
    print("="*50)