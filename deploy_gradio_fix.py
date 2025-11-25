#!/usr/bin/env python3
"""Deploy Gradio 5.0.0 compatibility fix to HuggingFace Space."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import CommitOperationAdd, HfApi

# Load token from .env file
load_dotenv()
token = os.getenv("HF_TOKEN")

if not token:
    print("[ERROR] HF_TOKEN not found in .env file")
    sys.exit(1)

# Configuration
REPO_ID = "MCP-1st-Birthday/vawlrathh"
REPO_TYPE = "space"

COMMIT_MESSAGE = "Fix Gradio 5.0.0 - remove show_copy_button parameter"


def main():
    """Upload app.py to HuggingFace Space with PR creation."""
    print(f"[DEPLOY] HuggingFace Space: {REPO_ID}")
    print(f"         Commit message: {COMMIT_MESSAGE}")
    print()

    # Verify file exists
    if not Path("app.py").exists():
        print("[ERROR] app.py not found")
        sys.exit(1)
    print("[OK] app.py verified")

    # Initialize API
    api = HfApi(token=token)

    # Verify token works
    try:
        user_info = api.whoami()
        print(f"[OK] Authenticated as: {user_info.get('name', 'Unknown')}")
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)

    # Read file content
    with open("app.py", "rb") as f:
        content = f.read()

    operations = [CommitOperationAdd(path_in_repo="app.py", path_or_fileobj=content)]
    print("[OK] Prepared app.py for upload")

    # Create commit as a Pull Request
    print()
    print("[UPLOAD] Creating Pull Request...")
    try:
        result = api.create_commit(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            operations=operations,
            commit_message=COMMIT_MESSAGE,
            create_pr=True,
        )

        print()
        print("=" * 60)
        print("[SUCCESS] Pull Request created!")
        print("=" * 60)
        print()

        # Extract PR URL from result
        if hasattr(result, "pr_url"):
            pr_url = result.pr_url
        elif hasattr(result, "pr_num"):
            pr_url = f"https://huggingface.co/spaces/{REPO_ID}/discussions/{result.pr_num}"
        else:
            pr_url = f"https://huggingface.co/spaces/{REPO_ID}/discussions"

        print(f"[PR URL] {pr_url}")
        print()
        print(f"Full API response: {result}")

    except Exception as e:
        print()
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()