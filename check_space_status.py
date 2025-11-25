#!/usr/bin/env python3
"""Check HuggingFace Space status and attempt restart."""

import os
import sys
import json
from dotenv import load_dotenv
import requests

load_dotenv()

def main():
    token = os.getenv('HF_TOKEN')
    if not token:
        print("ERROR: HF_TOKEN not found in environment")
        sys.exit(1)
    
    print(f"Token found (length: {len(token)})")
    
    repo_id = 'MCP-1st-Birthday/vawlrathh'
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Space Details ===")
    space_url = f'https://huggingface.co/api/spaces/{repo_id}'
    space_response = requests.get(space_url, headers=headers)
    
    if space_response.status_code == 200:
        space_data = space_response.json()
        print(f"Space ID: {space_data.get('id', 'N/A')}")
        print(f"SDK: {space_data.get('sdk', 'N/A')}")
        
        runtime = space_data.get('runtime', {})
        print(f"\n--- Runtime Info ---")
        print(f"Stage: {runtime.get('stage', 'N/A')}")
        print(f"Error Message: {runtime.get('errorMessage', 'None')}")
        print(f"Hardware Requested: {runtime.get('hardware', {}).get('requested', 'N/A')}")
        print(f"Hardware Current: {runtime.get('hardware', {}).get('current', 'N/A')}")
        print(f"Sleep Time: {runtime.get('gcTimeout', 'N/A')}")
        
        # Print last logs if available
        if 'lastLogs' in runtime:
            print(f"\n--- Last Logs ---")
            print(runtime.get('lastLogs', 'No logs'))
    else:
        print(f"Error getting space: {space_response.status_code}")
        print(space_response.text)
    
    # Try to restart the space using factory reboot
    print("\n=== Attempting Factory Reboot ===")
    restart_url = f'https://huggingface.co/api/spaces/{repo_id}/restart'
    restart_response = requests.post(restart_url, headers=headers)
    print(f"Restart Status Code: {restart_response.status_code}")
    if restart_response.text:
        print(f"Response: {restart_response.text}")
    else:
        print("Response: Empty (may indicate success)")
    
    # Check if there's a rebuild option
    print("\n=== Checking Rebuild Option ===")
    rebuild_url = f'https://huggingface.co/api/spaces/{repo_id}/sleeptime'
    rebuild_response = requests.get(rebuild_url, headers=headers)
    print(f"Sleep config status: {rebuild_response.status_code}")
    if rebuild_response.text:
        print(f"Sleep config: {rebuild_response.text}")
    
    # Get repo info
    print("\n=== Repository Info ===")
    repo_url = f'https://huggingface.co/api/spaces/{repo_id}'
    repo_response = requests.get(repo_url, headers=headers)
    if repo_response.status_code == 200:
        repo_data = repo_response.json()
        print(f"Private: {repo_data.get('private', 'N/A')}")
        print(f"Author: {repo_data.get('author', 'N/A')}")
        print(f"Created: {repo_data.get('createdAt', 'N/A')}")
        print(f"Last Modified: {repo_data.get('lastModified', 'N/A')}")
        
        # Check siblings (files)
        siblings = repo_data.get('siblings', [])
        print(f"\n--- Files ({len(siblings)}) ---")
        for s in siblings[:10]:
            print(f"  {s.get('rfilename', 'N/A')}")
        if len(siblings) > 10:
            print(f"  ... and {len(siblings) - 10} more files")

if __name__ == '__main__':
    main()