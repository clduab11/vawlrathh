"""Direct upload using requests library to bypass huggingface_hub auth issues."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HF_TOKEN")

# Upload app.py
url = "https://huggingface.co/api/spaces/MCP-1st-Birthday/vawlrathh/upload/main"

headers = {
    "Authorization": f"Bearer {token}",
}

with open("app.py", "rb") as f:
    files = {
        "file": ("app.py", f, "text/x-python"),
    }
    data = {
        "commit_message": "Add premium dark theme CSS and remove FastAPI dependencies"
    }

    print(f"Uploading app.py...")
    print(f"Token: {token}")
    response = requests.post(url, headers=headers, files=files, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.ok:
        print("✅ Upload successful!")
    else:
        print(f"❌ Upload failed: {response.status_code}")
