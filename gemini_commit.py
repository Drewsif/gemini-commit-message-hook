"""A git hook to generate a commit message using Google's Gemini AI."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
from http import HTTPStatus
from pathlib import Path

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_api_key() -> str:
    """Get the Gemini API key from the script or environment variables."""
    if config.GEMINI_API_KEY:
        return config.GEMINI_API_KEY

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("Error: GEMINI_API_KEY not found.")
        logger.error(
            "Please set the GEMINI_API_KEY in the script or as an "
            "environment variable.",
        )
        sys.exit(1)
    return api_key


def get_git_diff() -> str:
    """Get the staged git diff."""
    git_executable = shutil.which("git")
    if not git_executable:
        logger.error("git executable not found.")
        sys.exit(1)
    try:
        return subprocess.check_output(  # noqa: S603
            [git_executable, "diff", "--staged"],
            encoding="utf-8",
        )
    except subprocess.CalledProcessError:
        # It's not an error if there are no staged changes.
        return ""


def get_branch_name() -> str:
    """Get the current git branch name."""
    git_executable = shutil.which("git")
    if not git_executable:
        logger.error("git executable not found.")
        sys.exit(1)
    try:
        return subprocess.check_output(  # noqa: S603
            [git_executable, "rev-parse", "--abbrev-ref", "HEAD"],
            encoding="utf-8",
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def generate_commit_message(
    diff: str,
    branch_name: str,
    api_key: str,
    user_message: str | None = None,
) -> str | None:
    """Generate a commit message using the Gemini API."""
    user_prompt = ""
    if user_message:
        user_prompt = f"The user has provided the following hint: '{user_message}'"

    prompt = f"""
    Generate a commit message for the following changes on branch '{branch_name}'.
    {user_prompt}

    The commit message should be a 1-2 sentence high-level summary,
    followed by two newlines, and a markdown list of the changes in
    conventional commit format. You should only state facts and not
    assume the intentions of the change.

    Use the following conventional commit types: feat, fix, docs, style,
    refactor, perf, test, build, ci, chore, revert.

    Example:
    ```
    API now supports HTTPS connections and DELETE
    method for `Pancakes` type. Plus minor bug fixes.

    - feat(api): Add HTTPS support to api
    - feat(api): Add delete to `Pancakes` type
    - fix(pancakes): Fix for case when syrup is missing
    - docs(pancakes): Fix misspellings
    ```

    Here is the diff:
    ```
    {diff}
    ```
    """

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    },
                ],
            },
        ],
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            if response.status == HTTPStatus.OK:
                result = json.loads(response.read().decode("utf-8"))
                return result["candidates"][0]["content"]["parts"][0]["text"]
            logger.error(
                "Error: Gemini API request failed with status %s",
                response.status,
            )
            logger.error(response.read().decode("utf-8"))
            sys.exit(1)
    except urllib.error.URLError:
        logger.exception("Error: Could not connect to Gemini API")
        sys.exit(1)
    return None


def main() -> None:
    """Generate and write the commit message."""
    commit_msg_file = sys.argv[1]
    commit_source = sys.argv[2] if len(sys.argv) > 2 else ""  # noqa: PLR2004

    if commit_source == "merge":
        logger.info("Merge commit detected. Skipping.")
        sys.exit(0)

    user_message = None
    if commit_source == "message":
        user_message = Path(commit_msg_file).read_text().strip()

    api_key = get_api_key()
    diff = get_git_diff()
    branch_name = get_branch_name()

    if not diff:
        logger.info("No staged changes found. Aborting.")
        sys.exit(0)

    logger.info("Generating commit message...")
    if commit_message := generate_commit_message(
        diff,
        branch_name,
        api_key,
        user_message,
    ):
        Path(commit_msg_file).write_text(commit_message)


if __name__ == "__main__":
    main()
