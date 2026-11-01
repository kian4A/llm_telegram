# llm_telegram

Turning a private Telegram chat export into a small character-level GPT that
learns to answer **as Kian** (one participant) to messages from **Fatemeh**
(the other participant).

The notebook follows the classic *"train a MiniGPT from scratch"* exercise
(à la the Ferdowsi / Shahnameh notebook): the pipeline is fully visible —
example construction, loss masking, training, and sampling — so it works as a
learning baseline before moving to a pretrained model + LoRA.

## The pipeline

```text
Telegram export (messages*.html)
        │  merge_telegram_html.py
        ▼
all_messages.txt
        │  make_json.py
        ▼
messages.json
        │  merge_telegram_html.py -o conversation.json   (richer: timestamps, replies)
        ▼
conversation.json
        │  clean.py
        ▼
clean_messages.json / clean_messages_with_time.json
        │  telegram_kian_fatemeh_gpt(1).ipynb
        ▼
trained char-level GPT → reply_as_kian(...)
```

`conversation.json` is the most complete intermediate format; the notebook can
read any of the three JSON datasets, preferring `clean_messages_with_time.json`
because timestamps let it split the chat into sessions.

## Files

| File | What it does |
| --- | --- |
| `merge_telegram_html.py` | Reads all `messages*.html` pages from a Telegram export (sorted the Telegram way: `messages.html`, `messages2.html`, …), extracts sender + text, and writes `all_messages.txt` / `conversation.json`. |
| `make_json.py` | Parses `ChatExport_*/all_messages.txt` into `messages.json`, a simple `{sender: [messages]}` object. |
| `make_json_v2.py` | Earlier/alternate version of the HTML parser that produces the same plain text output. |
| `clean.py` | Normalizes `conversation.json` into `clean_messages.json` (sender + text) and `clean_messages_with_time.json` (sender + timestamp + text). |
| `telegram_kian_fatemeh_gpt(1).ipynb` | The experiment: loads a cleaned dataset, groups bubbles into sessions/turns, builds *Fatemeh → Kian* prompt/target pairs, trains a small char-level transformer with masked cross-entropy, plots loss, and generates replies. |

## Data format

The notebook expects records like:

```json
{"sender": "Fatemeh", "timestamp": "14.11.2023 18:49:54 UTC+03:30", "text": "سلام"}
```

Sender names are normalized to the two roles `Kian` and `Fatemeh`; everything
else (Telegram IDs, reply links) is ignored. Non-text messages (photos,
stickers, voice notes) are skipped.

## Usage

```bash
python -m venv .venv && source .venv/bin/activate
pip install beautifulsoup4 torch matplotlib jupyter

# 1. Merge a Telegram chat export (folder containing messages*.html)
python merge_telegram_html.py ChatExport_2026-10-03 -o conversation.json

# 2. Clean it into training-ready JSON
python clean.py        # reads conversation.json

# 3. Open the notebook and run it
jupyter notebook "telegram_kian_fatemeh_gpt(1).ipynb"
```

`merge_telegram_html.py` also auto-detects a single `ChatExport_*` folder if you
omit the argument.

## Notes on the model

- Character-level tokenizer (vocabulary learned from the training split only;
  unseen characters become `<UNK>`).
- 4 layers, 4 heads, `d_model=256` → ~3.3M trainable parameters.
- Loss is computed **only on Kian's reply characters** (prompt positions and
  padding are set to `-100`), so the model learns to answer, not to imitate both
  speakers — while still attending to Fatemeh's messages.
- Train/validation split is chronological (last 10% of sessions) to avoid
  leaking adjacent messages across the split.
- Validation loss measures character-level fit, not conversational realism.

## Privacy

This repository contains **code only**. The Telegram export, all intermediate
JSON, and any trained checkpoints are private and are excluded via
`.gitignore`. Provide your own export locally to reproduce the results.
