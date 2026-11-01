from pathlib import Path
import json


INPUT_FILE = Path(
    "ChatExport_2026-10-03/all_messages.txt"
)

OUTPUT_FILE = Path(
    "messages.json"
)


# These are the two people we want in the JSON.
SENDERS = {
    "kian aghmashe": "kian aghmashe",
    "fatemeh": "fatemeh",
}


def main():
    data = {
        "kian aghmashe": [],
        "fatemeh": [],
    }

    current_sender = None
    current_message_lines = []


    def save_current_message():
        nonlocal current_message_lines

        if current_sender is None:
            current_message_lines = []
            return

        message = "\n".join(current_message_lines).strip()

        if message:
            data[current_sender].append(message)

        current_message_lines = []


    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        for raw_line in file:
            line = raw_line.rstrip("\n")

            stripped = line.strip()

            # -----------------------------------
            # Detect sender
            # -----------------------------------

            if stripped.endswith(":"):
                possible_sender = (
                    stripped[:-1]
                    .strip()
                    .lower()
                )

                if possible_sender in SENDERS:

                    save_current_message()

                    current_sender = SENDERS[
                        possible_sender
                    ]

                    continue

            # -----------------------------------
            # Message content
            # -----------------------------------

            if current_sender is not None:
                current_message_lines.append(line)


    # Save final message
    save_current_message()


    # -----------------------------------
    # Write JSON
    # -----------------------------------

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


    print("Finished!")
    print(
        f"Kian Aghmashe messages: "
        f"{len(data['kian aghmashe'])}"
    )

    print(
        f"Fatemeh messages: "
        f"{len(data['fatemeh'])}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE.resolve()}"
    )


if __name__ == "__main__":
    main()