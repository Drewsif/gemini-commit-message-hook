"""Install the git hook."""

import logging
import stat
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
HOOK_DIR = Path(".git/hooks")
HOOK_NAME = "prepare-commit-msg"
SCRIPT_NAME = "gemini_commit.py"


def main() -> None:
    """Install the git hook."""
    if not Path(".git").exists():
        logger.error("Error: This is not a git repository.")
        sys.exit(1)

    HOOK_DIR.mkdir(exist_ok=True)

    hook_path = HOOK_DIR / HOOK_NAME
    script_path = str((SCRIPT_DIR / SCRIPT_NAME).resolve()).replace("\\", "\\\\")

    hook_content = f"#!/bin/sh\npython {script_path} $1\n"

    hook_path.write_text(hook_content)

    # Make the hook executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    logger.info("Successfully installed %s hook.", HOOK_NAME)


if __name__ == "__main__":
    main()
