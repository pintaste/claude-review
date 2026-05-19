"""Core review logic for claude-review GitHub Action."""


def chunk_diff(diff: str, max_chars: int = 12000) -> list[str]:
    """Split diff into chunks at file boundaries (lines starting with 'diff --git')."""
    if not diff:
        return []

    lines = diff.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        # Start a new chunk at file boundary if current chunk is large enough
        if line.startswith("diff --git") and current_size >= max_chars:
            if current_chunk:
                chunks.append("".join(current_chunk))
            current_chunk = [line]
            current_size = len(line)
        else:
            current_chunk.append(line)
            current_size += len(line)

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks if chunks else [diff]


def build_prompt(diff_chunk: str, focus: str) -> tuple[str, str]:
    """Build system and user prompts for the review."""
    system = "You are a senior software engineer performing a code review. Be concise and actionable."

    focus_instruction = ""
    if focus and focus.lower() != "all":
        areas = [f.strip() for f in focus.split(",")]
        focus_instruction = f"\n\nFocus your review on: {', '.join(areas)}."
    else:
        focus_instruction = "\n\nReview for correctness, security, performance, style, and maintainability."

    user = (
        f"Please review the following code diff and provide actionable feedback.{focus_instruction}\n\n"
        f"```diff\n{diff_chunk}\n```"
    )

    return system, user


def review_diff(diff: str, focus: str, max_tokens: int, client) -> str:
    """Iterate chunks, call Claude, collect and join responses."""
    chunks = chunk_diff(diff)
    responses = []

    for chunk in chunks:
        system, user = build_prompt(chunk, focus)
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        responses.append(message.content[0].text)

    return "\n\n---\n\n".join(responses)


def format_comment(review_text: str, focus: str) -> str:
    """Wrap review text in markdown with header and footer."""
    return (
        f"## Claude Code Review\n\n"
        f"{review_text}\n\n"
        f"> Focus: {focus} · Powered by [claude-review](https://github.com/pintaste/claude-review)"
    )
