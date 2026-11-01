from pathlib import Path
from bs4 import BeautifulSoup
import argparse
import json
import re


# ---------------------------------------------------------
# Sort Telegram HTML pages correctly
#
# messages.html
# messages2.html
# messages3.html
# ...
# messages10.html
# ---------------------------------------------------------

def telegram_page_number(path: Path) -> int:
    match = re.fullmatch(r"messages(\d*)\.html", path.name)

    if not match:
        return 999999999

    number = match.group(1)

    # messages.html = first page
    if number == "":
        return 1

    return int(number)


def get_html_files(folder: Path):
    files = []

    for path in folder.iterdir():
        if (
            path.is_file()
            and re.fullmatch(r"messages\d*\.html", path.name)
        ):
            files.append(path)

    return sorted(
        files,
        key=telegram_page_number
    )


# ---------------------------------------------------------
# Automatically find ChatExport_* directory
# ---------------------------------------------------------

def find_export_folder(folder_argument=None):

    if folder_argument:
        folder = Path(folder_argument).expanduser().resolve()

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder does not exist: {folder}"
            )

        if not get_html_files(folder):
            raise FileNotFoundError(
                f"No messages*.html files found in: {folder}"
            )

        return folder

    script_directory = Path(__file__).resolve().parent
    current_directory = Path.cwd().resolve()

    roots = []

    for root in [
        current_directory,
        script_directory
    ]:
        if root not in roots:
            roots.append(root)

    # Maybe we're already inside the export directory
    for root in roots:
        if get_html_files(root):
            return root

    # Search ChatExport_* directories
    export_folders = []

    for root in roots:
        for candidate in root.glob("ChatExport_*"):

            if (
                candidate.is_dir()
                and get_html_files(candidate)
            ):
                candidate = candidate.resolve()

                if candidate not in export_folders:
                    export_folders.append(candidate)

    if len(export_folders) == 1:
        return export_folders[0]

    if len(export_folders) == 0:
        raise FileNotFoundError(
            "Could not find a ChatExport_* directory "
            "containing messages*.html"
        )

    print("Multiple Telegram exports found:")

    for folder in export_folders:
        print(folder)

    raise RuntimeError(
        "Please specify the export directory manually."
    )


# ---------------------------------------------------------
# Extract Telegram message ID
# ---------------------------------------------------------

def extract_message_id(message):
    """
    Telegram message elements usually have IDs such as:

        message12345

    Return 12345 if available.
    """

    html_id = message.get("id")

    if not html_id:
        return None

    match = re.search(
        r"message(\d+)",
        html_id
    )

    if match:
        return int(match.group(1))

    return None


# ---------------------------------------------------------
# Extract timestamp
# ---------------------------------------------------------

def extract_timestamp(body):
    """
    Telegram normally stores the full date/time in:

        <div class="date details"
             title="03.10.2026 14:35:02 UTC+03:30">

    We prefer the title because it contains more detail.
    """

    date_element = body.select_one(
        "div.date.details"
    )

    if date_element is None:
        return None

    # Full datetime is usually here
    title = date_element.get("title")

    if title:
        return title.strip()

    # Fallback to visible time
    text = date_element.get_text(
        " ",
        strip=True
    )

    return text or None


# ---------------------------------------------------------
# Extract reply target
# ---------------------------------------------------------

def extract_reply_to(body):
    """
    Telegram replies often contain something like:

        href="#go_to_message123"

    or another link containing the target message ID.

    Return the Telegram message ID when possible.
    """

    reply = body.select_one(
        "div.reply_to"
    )

    if reply is None:
        return None

    link = reply.find(
        "a",
        href=True
    )

    if link is None:
        return None

    href = link.get("href", "")

    # Examples:
    # #go_to_message123
    # #message123
    match = re.search(
        r"(?:go_to_message|message)(\d+)",
        href
    )

    if match:
        return int(match.group(1))

    return None


# ---------------------------------------------------------
# Extract conversation
# ---------------------------------------------------------

def extract_messages(folder: Path):

    html_files = get_html_files(folder)

    if not html_files:
        raise FileNotFoundError(
            f"No messages*.html files found in {folder}"
        )

    messages = []

    current_sender = None

    sequence = 0

    for page_index, html_file in enumerate(
        html_files,
        start=1
    ):

        print(
            f"[{page_index}/{len(html_files)}] "
            f"Reading {html_file.name}"
        )

        html = html_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # This includes normal and joined messages
        for message in soup.select(
            "div.message.default"
        ):

            body = message.find(
                "div",
                class_="body",
                recursive=False
            )

            if body is None:
                continue

            # ---------------------------------------------
            # Sender
            # ---------------------------------------------

            sender_element = body.find(
                "div",
                class_="from_name",
                recursive=False
            )

            if sender_element is not None:

                sender_text = (
                    sender_element
                    .get_text(
                        " ",
                        strip=True
                    )
                )

                if sender_text:
                    current_sender = sender_text

            if current_sender is None:
                current_sender = "UNKNOWN"

            # ---------------------------------------------
            # Message text
            # ---------------------------------------------

            text_element = body.find(
                "div",
                class_="text",
                recursive=False
            )

            # Skip media-only messages for now
            if text_element is None:
                continue

            text = text_element.get_text(
                "\n",
                strip=True
            )

            if not text:
                continue

            # ---------------------------------------------
            # Metadata
            # ---------------------------------------------

            telegram_id = extract_message_id(
                message
            )

            timestamp = extract_timestamp(
                body
            )

            reply_to_telegram_id = (
                extract_reply_to(body)
            )

            sequence += 1

            messages.append(
                {
                    "sequence": sequence,
                    "telegram_id": telegram_id,
                    "sender": current_sender,
                    "timestamp": timestamp,
                    "text": text,
                    "reply_to_telegram_id":
                        reply_to_telegram_id
                }
            )

    return html_files, messages


# ---------------------------------------------------------
# Convert Telegram reply IDs -> JSON sequence numbers
# ---------------------------------------------------------

def connect_replies(messages):

    id_to_sequence = {}

    for message in messages:

        telegram_id = message[
            "telegram_id"
        ]

        if telegram_id is not None:

            id_to_sequence[
                telegram_id
            ] = message["sequence"]

    for message in messages:

        reply_id = message[
            "reply_to_telegram_id"
        ]

        if reply_id is not None:

            message["reply_to"] = (
                id_to_sequence.get(reply_id)
            )

        else:
            message["reply_to"] = None


# ---------------------------------------------------------
# Add previous-message relationship
# ---------------------------------------------------------

def add_previous_message(messages):
    """
    This is NOT the same as a Telegram explicit reply.

    It simply tells us which message came immediately before
    this message, making later time-series/conversation
    analysis easier.
    """

    for index, message in enumerate(messages):

        if index == 0:
            message[
                "previous_message"
            ] = None

        else:
            message[
                "previous_message"
            ] = messages[
                index - 1
            ]["sequence"]


# ---------------------------------------------------------
# Collect participant names
# ---------------------------------------------------------

def get_participants(messages):

    participants = []

    for message in messages:

        sender = message["sender"]

        if (
            sender != "UNKNOWN"
            and sender not in participants
        ):
            participants.append(sender)

    return participants


# ---------------------------------------------------------
# Remove internal helper field
# ---------------------------------------------------------

def cleanup_messages(messages):

    for message in messages:

        message.pop(
            "reply_to_telegram_id",
            None
        )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert a Telegram HTML export "
            "into chronological JSON."
        )
    )

    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help="Telegram ChatExport_* directory"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="conversation.json",
        help=(
            "Output JSON filename. "
            "Default: conversation.json"
        )
    )

    args = parser.parse_args()

    folder = find_export_folder(
        args.folder
    )

    print()
    print(
        f"Export folder: {folder}"
    )
    print()

    html_files, messages = (
        extract_messages(folder)
    )

    # Connect Telegram replies
    connect_replies(messages)

    # Preserve immediate chronological relationship
    add_previous_message(messages)

    participants = get_participants(
        messages
    )

    cleanup_messages(messages)

    conversation = {
        "participants": participants,
        "total_messages": len(messages),
        "messages": messages
    }

    output_path = Path(
        args.output
    )

    if not output_path.is_absolute():
        output_path = (
            folder / output_path
        )

    output_path = (
        output_path.resolve()
    )

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            conversation,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("Finished")
    print("=" * 60)

    print(
        f"HTML files processed : "
        f"{len(html_files)}"
    )

    print(
        f"Messages extracted   : "
        f"{len(messages)}"
    )

    print(
        f"Participants         : "
        f"{', '.join(participants)}"
    )

    print(
        f"Saved to             : "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()