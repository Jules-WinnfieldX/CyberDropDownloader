import re
from pathlib import Path

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console

console = Console()


def edit_urls_prompt(URLs_File: Path, fix_strings=True) -> None:
    """Edit the URLs file"""
    console.clear()
    console.print(f"Editing URLs: {URLs_File}")
    with open(URLs_File, "r") as f:
        existing_urls = f.read()

    result = inquirer.text(
        message="URLs:", multiline=True, default=existing_urls,
        long_instruction="Press escape and then enter to finish editing.",
    ).execute()

    if fix_strings:
        result = result.replace(" ", "\n")
        result = re.sub(r"(\n)+", "\n", result)

    with open(URLs_File, "w") as f:
        f.write(result)


def edit_urls_passwords_prompt(URLs_File: Path) -> None:
    """Edit the URLs & Passwords file"""
    while True:
        console.clear()
        console.print(f"Editing URLs & Passwords: {URLs_File}")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Add New Links"),
                Choice(2, "Clear All Links"),
                Choice(3, "Edit URLs & Passwords"),
                Choice(4, "Done"),
            ],
        ).execute()

        if action == 1:
            url = inquirer.text(message="Enter the URL:").execute()
            password = inquirer.text(message="Enter the password:").execute()
            with open(URLs_File, "a") as f:
                f.write(f"\n{url} : {password}\n")
        elif action == 2:
            URLs_File.unlink(missing_ok=True)
            URLs_File.touch()
        elif action == 3:
            edit_urls_prompt(URLs_File, fix_strings=False)
        elif action == 4:
            return
