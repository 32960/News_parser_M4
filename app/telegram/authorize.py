"""
One-time Telegram login.

Run from project root (with .env configured):

    python -m app.telegram.authorize

Telethon will ask for phone number, login code, and 2FA password if needed.
After that a session file is saved and Celery workers can use it without prompts.
"""

from app.log_config import configure_logs
from app.telegram.client import authorize


def main() -> None:
    configure_logs()
    authorize()


if __name__ == "__main__":
    main()
