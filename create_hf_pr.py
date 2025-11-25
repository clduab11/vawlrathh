#!/usr/bin/env python3
"""Create a PR on HuggingFace Space by uploading files with create_pr=True."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import CommitOperationAdd, HfApi

# Load token from .env file
load_dotenv()
token = os.getenv("HF_TOKEN")

if not token:
    print("❌ Error: HF_TOKEN not found in .env file")
    sys.exit(1)

# Configuration
REPO_ID = "MCP-1st-Birthday/vawlrathh"
REPO_TYPE = "space"
BRANCH_NAME = "deploy-pure-gradio-mvp"

COMMIT_MESSAGE = """Deploy: Pure Gradio MVP with premium dark theme

- Refactored from FastAPI+mounted Gradio to Pure Gradio architecture
- Added premium dark theme with purple/blue gradients and glassmorphism
- Fixed ZeroGPU compatibility (@spaces.GPU decorator)
- Removed FastAPI dependencies from requirements.txt
- Exports 'demo' object compatible with HF Spaces sdk: gradio
- Resolves psutil version conflict with spaces library
- Fixes "No @spaces.GPU function detected" runtime error"""

# Files to upload
FILES_TO_UPLOAD = ["app.py", "requirements.txt"]


def main():
    """Create a PR to upload files to HuggingFace Space."""
    print(f"🚀 Creating PR for HuggingFace Space: {REPO_ID}")
    print(f"   Branch: {BRANCH_NAME}")
    print(f"   Files: {', '.join(FILES_TO_UPLOAD)}")
    print()

    # Verify files exist
    for filename in FILES_TO_UPLOAD:
        if not Path(filename).exists():
            print(f"❌ Error: File not found: {filename}")
            sys.exit(1)
    print("✓ All files verified")

    # Initialize API
    api = HfApi(token=token)

    # Verify token works
    try:
        user_info = api.whoami()
        print(f"✓ Authenticated as: {user_info.get('name', 'Unknown')}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Prepare commit operations - read files as bytes
    operations = []
    for filename in FILES_TO_UPLOAD:
        with open(filename, "rb") as f:
            content = f.read()
        operations.append(
            CommitOperationAdd(path_in_repo=filename, path_or_fileobj=content)
        )
    print(f"✓ Prepared {len(operations)} file(s) for upload")

    # Create commit as a Pull Request
    print()
    print("📤 Creating Pull Request...")
    try:
        result = api.create_commit(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            operations=operations,
            commit_message=COMMIT_MESSAGE,
            create_pr=True,
        )

        # The result contains PR info when create_pr=True
        print()
        print("=" * 60)
        print("✅ SUCCESS: Pull Request created!")
        print("=" * 60)
        print()

        # Extract PR URL from result
        if hasattr(result, "pr_url"):
            pr_url = result.pr_url
        elif hasattr(result, "pr_num"):
            pr_url = f"https://huggingface.co/spaces/{REPO_ID}/discussions/{result.pr_num}"
        else:
            # Default discussions page if we can't get specific PR
            pr_url = f"https://huggingface.co/spaces/{REPO_ID}/discussions"
            print(f"Note: Could not extract specific PR URL from result: {result}")

        print(f"🔗 PR URL: {pr_url}")
        print()
        print("Next steps:")
        print("  1. Open the PR URL above in your browser")
        print("  2. Review the changes")
        print("  3. Click 'Merge' to deploy to the Space")
        print()

        # Also print the full result for debugging
        print(f"Full API response: {result}")

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: Failed to create PR")
        print("=" * 60)
        print()
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print()

        import traceback

        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()