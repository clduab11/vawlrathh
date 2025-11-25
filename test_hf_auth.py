"""Test HF authentication and upload single file."""
import os
from huggingface_hub import HfApi, login
from dotenv import load_dotenv

# Load environment
load_dotenv()
token = os.getenv("HF_TOKEN")

print(f"Token: {token}")
print("Logging in...")

try:
    # Try logging in first
    login(token=token, add_to_git_credential=True)
    print("✓ Login successful!")

    # Now try uploading
    api = HfApi()
    print("Uploading app.py...")

    result = api.upload_file(
        path_or_fileobj="app.py",
        path_in_repo="app.py",
        repo_id="MCP-1st-Birthday/vawlrathh",
        repo_type="space",
        commit_message="Add premium dark theme CSS via Python API"
    )

    print(f"✅ Success! {result}")

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
