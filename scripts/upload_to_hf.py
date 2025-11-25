"""Upload specific files to HF Space using huggingface_hub API."""
import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

token = os.getenv("HF_TOKEN")
print(f"Token loaded: {token[:10]}..." if token else "No token found")

api = HfApi(token=token)
repo_id = "MCP-1st-Birthday/vawlrathh"

print(f"Uploading files to {repo_id}...")

try:
    # Upload app.py
    print("Uploading app.py...")
    api.upload_file(
        path_or_fileobj="app.py",
        path_in_repo="app.py",
        repo_id=repo_id,
        repo_type="space",
        commit_message="Add premium dark theme CSS to match UI mockup"
    )
    print("✓ app.py uploaded successfully")

    # Upload requirements.txt
    print("Uploading requirements.txt...")
    api.upload_file(
        path_or_fileobj="requirements.txt",
        path_in_repo="requirements.txt",
        repo_id=repo_id,
        repo_type="space",
        commit_message="Remove FastAPI dependencies for Pure Gradio MVP"
    )
    print("✓ requirements.txt uploaded successfully")

    print("\n✅ All files uploaded successfully!")
    print(f"Visit: https://huggingface.co/spaces/{repo_id}")

except Exception as e:
    print(f"❌ Upload failed: {e}")
