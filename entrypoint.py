"""Entrypoint for claude-review GitHub Action."""

import json
import os
import sys

import anthropic
from github import Github

from review import format_comment, review_diff


def main() -> int:
    # Read environment variables
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    focus = os.environ.get("REVIEW_FOCUS", "all")
    max_tokens = int(os.environ.get("MAX_TOKENS", "2048"))

    if not anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 1
    if not github_token:
        print("Error: GITHUB_TOKEN is not set", file=sys.stderr)
        return 1
    if not event_path:
        print("Error: GITHUB_EVENT_PATH is not set", file=sys.stderr)
        return 1

    try:
        # Parse GitHub event
        with open(event_path, "r") as f:
            event = json.load(f)

        pr_number = event["pull_request"]["number"]
        repo_full_name = event["repository"]["full_name"]

        # Set up GitHub client
        gh = Github(github_token)
        repo = gh.get_repo(repo_full_name)
        pull = repo.get_pull(pr_number)

        # Reconstruct diff string from PR files
        diff_parts = []
        for file in pull.get_files():
            if file.patch:
                diff_parts.append(
                    f"diff --git a/{file.filename} b/{file.filename}\n{file.patch}"
                )
        diff = "\n".join(diff_parts)

        if not diff.strip():
            print("No diff found for this PR. Skipping review.")
            return 0

        # Run review
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        review_text = review_diff(diff, focus, max_tokens, client)

        # Post comment
        comment = format_comment(review_text, focus)
        pull.create_issue_comment(comment)

        print(f"Review posted successfully on PR #{pr_number} in {repo_full_name}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
