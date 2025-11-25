import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

def deploy():
    # Load environment variables from .env file if present
    load_dotenv()

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN not found in environment variables.")
        return

    api = HfApi(token=token)
    repo_id = "MCP-1st-Birthday/vawlrathh"

    print(f"Deploying to {repo_id}...")
    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy: Pure Gradio MVP refactor and cleanup",
            ignore_patterns=[
                ".git/*", ".venv/*", "__pycache__/*",
                ".pytest_cache/*", ".mypy_cache/*", ".ruff_cache/*",
                "node_modules/*", "dist/*", "build/*", "data/*", "*.log"
            ],
            create_pr=False
        )
        print("Deployment successful! Changes pushed to main.")
    except Exception as e:
        print(f"Deployment failed: {e}")

if __name__ == "__main__":
    deploy()
