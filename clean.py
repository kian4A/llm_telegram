import json

# Load original dataset
with open("conversation.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Support both JSON formats
messages = data["messages"] if isinstance(data, dict) else data

clean_messages = []
clean_messages_with_time = []

for msg in messages:
    if not isinstance(msg, dict):
        continue

    sender = msg.get("sender")
    text = msg.get("text")
    timestamp = msg.get("timestamp")

    # Skip empty or invalid text messages
    if not isinstance(text, str) or not text.strip() or not sender:
        continue

    # Dataset 1: Without time
    clean_messages.append({
        "sender": sender,
        "text": text
    })

    # Dataset 2: With time
    clean_messages_with_time.append({
        "sender": sender,
        "timestamp": timestamp,
        "text": text
    })

# Save dataset 1
with open("clean_messages.json", "w", encoding="utf-8") as f:
    json.dump(clean_messages, f, ensure_ascii=False, indent=2)

# Save dataset 2
with open("clean_messages_with_time.json", "w", encoding="utf-8") as f:
    json.dump(clean_messages_with_time, f, ensure_ascii=False, indent=2)

print(f"Original messages: {len(messages)}")
print(f"Cleaned messages: {len(clean_messages)}")
print("Saved: clean_messages.json")
print("Saved: clean_messages_with_time.json")