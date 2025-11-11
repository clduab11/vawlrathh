#!/usr/bin/env python3
"""
Claude AI Issue Assistant

This script uses Anthropic's Claude API to analyze and provide assistance
for GitHub issues.
"""

import argparse
import json
import os
import sys
from typing import Any

try:
    import anthropic
    from github import Github
except ImportError:
    print("Error: Required packages not installed")
    print("Please run: pip install anthropic PyGithub")
    sys.exit(1)


class ClaudeIssueAssistant:
    """Automated issue assistant using Claude AI."""

    def __init__(self, api_key: str, github_token: str) -> None:
        """Initialize the assistant with API credentials."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.github = Github(github_token)
        self.model = "claude-sonnet-4-5-20250929"

    def get_issue_context(self, repo_name: str, issue_number: int) -> dict[str, Any]:
        """Get context about the issue."""
        repo = self.github.get_repo(repo_name)
        issue = repo.get_issue(issue_number)

        # Get comments
        comments = []
        for comment in issue.get_comments():
            comments.append({
                "author": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at.isoformat()
            })

        # Get labels
        labels = [label.name for label in issue.labels]

        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "author": issue.user.login,
            "state": issue.state,
            "labels": labels,
            "comments": comments,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
        }

    def search_similar_issues(self, repo_name: str, title: str) -> list[dict[str, Any]]:
        """Search for similar issues in the repository."""
        repo = self.github.get_repo(repo_name)

        # Search for similar issues
        query = f"repo:{repo_name} is:issue {title[:50]}"
        results = self.github.search_issues(query)

        similar = []
        for issue in list(results)[:5]:  # Limit to 5 similar issues
            similar.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "url": issue.html_url
            })

        return similar

    def get_relevant_code(self, repo_name: str, issue_body: str) -> str:
        """Extract file paths from issue and get relevant code snippets."""
        repo = self.github.get_repo(repo_name)

        # Try to find file references in the issue body
        # Look for patterns like: src/file.py, file.py:123, etc.
        import re
        file_pattern = r'(?:src/)?[\w/]+\.py(?::\d+)?'
        files = re.findall(file_pattern, issue_body)

        code_snippets = []
        for file_ref in files[:3]:  # Limit to 3 files
            file_path = file_ref.split(':')[0]
            try:
                content = repo.get_contents(file_path)
                if hasattr(content, 'decoded_content'):
                    code = content.decoded_content.decode('utf-8')
                    code_snippets.append(f"### {file_path}\n\n```python\n{code[:1000]}\n```")
            except UnknownObjectException:
                continue

        return "\n\n".join(code_snippets) if code_snippets else "No code files referenced"

    def create_analysis_prompt(
        self, context: dict[str, Any], similar: list[dict[str, Any]], code: str
    ) -> str:
        """Create the prompt for Claude to analyze the issue."""
        comments_text = "\n".join([
            f"- {c['author']}: {c['body'][:200]}"
            for c in context['comments'][:5]
        ]) if context['comments'] else "No comments yet"

        similar_text = "\n".join([
            f"- #{s['number']}: {s['title']} ({s['state']})"
            for s in similar[:3]
        ]) if similar else "No similar issues found"

        return f"""You are an expert technical assistant for a Python project called "arena-improver",
an AI-powered Magic: The Gathering Arena deck analysis platform.

Project Technology Stack:
- Python 3.9+ with FastAPI
- SQLAlchemy + SQLite for database
- OpenAI API for AI features
- Sentence Transformers for embeddings
- Pytest for testing
- AGPL-3.0 license

Issue Information:
- Number: #{context['number']}
- Title: {context['title']}
- Author: {context['author']}
- Labels: {', '.join(context['labels']) if context['labels'] else 'None'}
- State: {context['state']}

Issue Description:
{context['body']}

Recent Comments:
{comments_text}

Similar Issues:
{similar_text}

Relevant Code:
{code}

Please analyze this issue and provide:

1. **Root Cause Analysis**: What is likely causing this issue?
2. **Recommended Solution**: Step-by-step fix or implementation
3. **Code Examples**: Provide specific code changes if applicable
4. **Testing Strategy**: How to verify the fix works
5. **Prevention**: How to prevent similar issues in the future
6. **Related Issues**: Connections to other parts of the codebase

Provide your response in this markdown format:

## Analysis

### Issue Type
[bug | feature request | question | enhancement | documentation]

### Root Cause
[Detailed explanation of what's causing the issue]

### Recommended Solution

#### Step 1: [Description]
```python
# Code example if applicable
```

#### Step 2: [Description]
```python
# Code example if applicable
```

[Continue as needed]

### Testing Strategy
- [ ] [Test case 1]
- [ ] [Test case 2]
- [ ] [Test case 3]

### Prevention
[How to prevent this issue in the future]

### Additional Notes
[Any other relevant information, warnings, or considerations]

### Related Files
[List of files that may need changes]

---

**Confidence Level**: [High | Medium | Low]
**Estimated Effort**: [Simple | Moderate | Complex]
"""

    def analyze_issue(
        self, repo_name: str, issue_number: int
    ) -> tuple[str, dict[str, Any]]:
        """Analyze a GitHub issue."""
        print(f"Fetching issue #{issue_number} from {repo_name}...")
        context = self.get_issue_context(repo_name, issue_number)

        print("Searching for similar issues...")
        similar = self.search_similar_issues(repo_name, context['title'])

        print("Gathering relevant code...")
        code = self.get_relevant_code(repo_name, context['body'])

        print("Requesting Claude analysis...")
        prompt = self.create_analysis_prompt(context, similar, code)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            analysis_text = message.content[0].text

            # Compile metrics
            metrics = {
                "issue_number": issue_number,
                "model_used": self.model,
                "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
                "similar_issues_found": len(similar),
                "comments_analyzed": len(context['comments']),
            }

            print("✓ Analysis completed successfully")
            return analysis_text, metrics

        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            print(f"✗ {error_msg}")
            return f"## Error\n\n{error_msg}", {}

    def save_analysis(
        self, analysis_text: str, metrics: dict[str, Any],
        output_file: str = "claude_issue_response.md"
    ) -> None:
        """Save the analysis to a file."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(analysis_text)

        # Save detailed metrics
        with open("claude_issue_details.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"✓ Analysis saved to {output_file}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Claude AI Issue Assistant")
    parser.add_argument("--issue-number", type=int, required=True, help="Issue number")
    parser.add_argument("--repo", required=True, help="Repository (owner/name)")
    parser.add_argument(
        "--output", default="claude_issue_response.md", help="Output file for analysis"
    )

    args = parser.parse_args()

    # Get API keys from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    # Perform analysis
    assistant = ClaudeIssueAssistant(api_key, github_token)
    analysis_text, metrics = assistant.analyze_issue(args.repo, args.issue_number)

    # Save results
    assistant.save_analysis(analysis_text, metrics, args.output)

    print("\n" + "="*80)
    print("Analysis Summary:")
    print("="*80)
    print(analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text)
    print("="*80)


if __name__ == "__main__":
    main()
