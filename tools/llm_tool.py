import anthropic
import weave

from core.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


@weave.op()
def tool_loop(
    system: str,
    user: str,
    tools: list[dict],
    tool_handlers: dict,
    model: str = "claude-sonnet-4-6",
    thinking: bool = False,
) -> str:
    """Run the Claude tool-use loop until no more tool calls are emitted.

    tool_handlers maps tool name → callable(**tool_input) → str.
    Returns the final text response from Claude.
    """
    messages: list[dict] = [{"role": "user", "content": user}]
    extra: dict = {}
    if thinking:
        extra["thinking"] = {"type": "enabled", "budget_tokens": settings.thinking_budget_tokens}

    max_tokens = (settings.thinking_budget_tokens + 4096) if thinking else 4096

    while True:
        resp = client.messages.create(
            model=model,
            system=system,
            tools=tools,
            messages=messages,
            max_tokens=max_tokens,
            **extra,
        )

        text_blocks = [b.text for b in resp.content if b.type == "text"]
        tool_calls = [b for b in resp.content if b.type == "tool_use"]

        if not tool_calls:
            return "\n".join(text_blocks)

        messages.append({"role": "assistant", "content": resp.content})
        results = [
            {
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": str(tool_handlers[tc.name](**tc.input)),
            }
            for tc in tool_calls
        ]
        messages.append({"role": "user", "content": results})
