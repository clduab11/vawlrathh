#!/usr/bin/env python3
"""Check PR #43 status and attempt to merge it on HuggingFace Space."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def main():
    try:
        import requests
    except ImportError:
        print("Installing requests...")
        os.system("pip install requests")
        import requests
    
    token = os.getenv('HF_TOKEN')
    if not token:
        print("ERROR: HF_TOKEN not found in environment")
        sys.exit(1)
    
    print(f"Token found (length: {len(token)})")
    
    repo_id = 'MCP-1st-Birthday/vawlrathh'
    discussion_num = 43
    
    # Get discussion details
    url = f'https://huggingface.co/api/spaces/{repo_id}/discussions/{discussion_num}'
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"\n=== Checking PR #{discussion_num} ===")
    print(f"URL: {url}")
    
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n--- PR Details ---")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")
        print(f"Is PR: {data.get('isPullRequest', 'N/A')}")
        print(f"Author: {data.get('author', {}).get('name', 'N/A')}")
        print(f"Created: {data.get('createdAt', 'N/A')}")
        print(f"Mergeable: {data.get('mergeable', 'N/A')}")
        
        # Check if we can merge
        if data.get('status') == 'open' and data.get('isPullRequest'):
            print("\n=== Attempting to Merge PR ===")
            merge_url = f'https://huggingface.co/api/spaces/{repo_id}/discussions/{discussion_num}/merge'
            merge_response = requests.post(merge_url, headers=headers)
            print(f"Merge Status Code: {merge_response.status_code}")
            if merge_response.status_code == 200:
                print("SUCCESS: PR merged successfully!")
            else:
                print(f"Merge Error: {merge_response.text}")
        else:
            print(f"\nPR is not in open state or not a PR (status: {data.get('status')})")
    else:
        print(f"Error: {response.text}")
    
    # Check Space status
    print("\n=== Checking Space Status ===")
    space_url = f'https://huggingface.co/api/spaces/{repo_id}'
    space_response = requests.get(space_url, headers=headers)
    
    if space_response.status_code == 200:
        space_data = space_response.json()
        print(f"Space ID: {space_data.get('id', 'N/A')}")
        runtime = space_data.get('runtime', {})
        print(f"Runtime Stage: {runtime.get('stage', 'N/A')}")
        print(f"Runtime Status: {runtime.get('status', 'N/A')}")
        print(f"Hardware: {runtime.get('hardware', {}).get('current', 'N/A')}")
    else:
        print(f"Space Error: {space_response.text}")

if __name__ == '__main__':
    main()