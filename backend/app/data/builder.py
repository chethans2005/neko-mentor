from scraper import get_topic_content
import json

topics = [
    "Caching",
    "Load Balancer",
    "Database Sharding",
    "Rate Limiting",
    "CAP Theorem"
]

dataset = {}

for topic in topics:
    print(f"Fetching: {topic}")
    raw = get_topic_content(topic)

    dataset[topic] = {
        "raw_content": raw
    }

with open("knowledge_raw.json", "w") as f:
    json.dump(dataset, f, indent=2)