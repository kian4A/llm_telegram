from pathlib import Path
from bs4 import BeautifulSoup
import re
import argparse


def telegram_page_number(path: Path) -> int:
    """
    Telegram exports files like:

        messages.html
        messages2.html
        messages3.html
        ...
        messages10.html

    Treat messages.html as page 1.
    """
    match = re.fullmatch(r"messages(\d*)\.html", path.name)

    if not match:
        return 999999999

    number = match.group(1)

    if number == "":
        return 1

    return int(number)


def get_html_files(folder: Path):
    """
    Find and correctly sort Telegram messages*.html files.
    """

    files = []

    for path in folder.iterdir():
        if path.is_file() and re.fullmatch(
            r"messages\d*\.html",
            path.name
        ):
            files.append(path)

    return sorted(files, key=telegram_page_number)


def find_export_folder(folder_argument=None):
    """
    Find the folder containing Telegram messages*.html files.

    Priority:

    1. Folder explicitly supplied on command line
    2. Current working directory
    3. Directory containing this Python script
    4. ChatExport_* directory inside either location
    """

    # --------------------------------------------------
    # User explicitly provided a folder
    # --------------------------------------------------

    if folder_argument:
        folder = Path(folder_argument).expanduser().resolve()

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder does not exist:\n{folder}"
            )

        if not folder.is_dir():
            raise NotADirectoryError(
                f"Not a directory:\n{folder}"
            )

        if not get_html_files(folder):
            raise FileNotFoundError(
                f"No Telegram messages*.html files found in:\n{folder}"
            )

        return folder

    # --------------------------------------------------
    # Places we automatically search
    # --------------------------------------------------

    current_directory = Path.cwd().resolve()
    script_directory = Path(__file__).resolve().parent

    search_roots = []

    for directory in [current_directory, script_directory]:
        if directory not in search_roots:
            search_roots.append(directory)

    # First check if messages.html files are directly here
    for directory in search_roots:
        if get_html_files(directory):
            return directory

    # Then look for ChatExport_* directories
    export_folders = []

    for root in search_roots:
        for candidate in root.glob("ChatExport_*"):
            if candidate.is_dir() and get_html_files(candidate):
                candidate = candidate.resolve()

                if candidate not in export_folders:
                    export_folders.append(candidate)

    # Exactly one export found
    if len(export_folders) == 1:
        return export_folders[0]

    # Nothing found
    if len(export_folders) == 0:
        searched = "\n".join(
            f"  - {path}"
            for path in search_roots
        )

        raise FileNotFoundError(
            "Could not find Telegram messages*.html files.\n\n"
            "Searched:\n"
            f"{searched}\n\n"
            "You can provide the export folder manually, for example:\n\n"
            "python merge_telegram_html.py ChatExport_2026-10-03"
        )

    # More than one export was found
    folders = "\n".join(
        f"  - {folder}"
        for folder in export_folders
    )

    raise RuntimeError(
        "Multiple Telegram export folders were found:\n\n"
        f"{folders}\n\n"
        "Please specify which one you want, for example:\n\n"
        "python merge_telegram_html.py ChatExport_2026-10-03"
    )


def extract_messages(folder: Path):
    """
    Extract sender + text from all Telegram HTML pages.
    """

    html_files = get_html_files(folder)

    if not html_files:
        raise FileNotFoundError(
            f"No messages*.html files found in:\n{folder}"
        )

    messages = []

    # Telegram sometimes doesn't repeat the sender name
    # for consecutive messages.
    current_sender = None

    for index, html_file in enumerate(html_files, start=1):

        print(
            f"[{index}/{len(html_files)}] "
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

        for message in soup.select("div.message.default"):

            body = message.find(
                "div",
                class_="body",
                recursive=False
            )

            if body is None:
                continue

            # --------------------------------------------------
            # Sender
            # --------------------------------------------------

            sender_element = body.find(
                "div",
                class_="from_name",
                recursive=False
            )

            if sender_element is not None:
                sender_name = sender_element.get_text(
                    " ",
                    strip=True
                )

                if sender_name:
                    current_sender = sender_name

            # --------------------------------------------------
            # Message text
            # --------------------------------------------------

            text_element = body.find(
                "div",
                class_="text",
                recursive=False
            )

            # Photos, videos, stickers, voice messages, etc.
            # may not have text.
            if text_element is None:
                continue

            text = text_element.get_text(
                "\n",
                strip=True
            )

            if not text:
                continue

            sender = current_sender or "UNKNOWN"

            messages.append(
                (sender, text)
            )

    return html_files, messages


def save_messages(messages, output_path: Path):
    """
    Write extracted messages to a UTF-8 text file.
    """

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as output_file:

        previous_sender = None

        for sender, text in messages:

            # Print sender only when sender changes
            if sender != previous_sender:

                if previous_sender is not None:
                    output_file.write("\n")

                output_file.write(
                    f"{sender}:\n"
                )

                previous_sender = sender

            output_file.write(text)
            output_file.write("\n")


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Merge Telegram messages*.html exports "
            "into one UTF-8 text file."
        )
    )

    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help=(
            "Telegram export folder. "
            "If omitted, the script automatically searches "
            "for ChatExport_*."
        )
    )

    parser.add_argument(
        "-o",
        "--output",
        default="all_messages.txt",
        help="Output filename. Default: all_messages.txt"
    )

    args = parser.parse_args()

    # --------------------------------------------------
    # Find Telegram export directory
    # --------------------------------------------------

    folder = find_export_folder(args.folder)

    print()
    print("Telegram export folder:")
    print(folder)
    print()

    # --------------------------------------------------
    # Extract messages
    # --------------------------------------------------

    html_files, messages = extract_messages(folder)

    # --------------------------------------------------
    # Output path
    # --------------------------------------------------

    output_path = Path(args.output)

    # If only a filename was supplied, save it
    # inside the Telegram export directory.
    if not output_path.is_absolute():
        output_path = folder / output_path

    output_path = output_path.resolve()

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    save_messages(
        messages,
        output_path
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print()
    print("=" * 50)
    print("Finished")
    print("=" * 50)
    print(f"HTML files processed : {len(html_files)}")
    print(f"Messages extracted   : {len(messages)}")
    print(f"Output file          : {output_path}")


if __name__ == "__main__":
    main()