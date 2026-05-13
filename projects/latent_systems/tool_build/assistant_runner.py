"""Tool-use loop for the in-app assistant.

Calls Anthropic with tools list, executes any tool_use blocks via
assistant_tools.execute_tool, feeds tool_results back, repeats until
end_turn or max_iterations. Tracks cost across all iterations.

Distinct from llm.call_claude (single-turn, no tools) — this module owns
the multi-step agent loop.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import anthropic

import assistant_tools
from llm import (
    DEFAULT_MODEL, MODEL_PRICING,
    CACHE_WRITE_MULTIPLIER, CACHE_READ_MULTIPLIER,
    LLMError, compute_cost,
)


MAX_ITERATIONS = 12
MAX_TOKENS_PER_TURN = 8000


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError(
            "ANTHROPIC_API_KEY not set in environment.", retryable=False,
        )
    return anthropic.Anthropic()


def _block_to_dict(block: Any) -> dict:
    """Anthropic SDK block → plain dict for messages list."""
    if hasattr(block, "model_dump"):
        return block.model_dump()
    return dict(block)


def run_assistant(
    *, system: str, user_message: str,
    history: Optional[list[dict]] = None,
) -> dict:
    """Run the agentic loop. history is a list of {role, content} dicts
    (content is the assistant's prior text reply or the user's prior message
    text — not full tool-use blocks; we keep history simple at the chat API
    boundary and rebuild full tool transcripts only within one /chat call).

    Returns: {
      response: str,       # final assistant text
      tool_trace: [        # list of tool calls executed in this turn
        {name, input, ok, preview}, ...
      ],
      cost_usd: float,     # cumulative across all iterations
      latency_s: float,
      iterations: int,
      tokens_in: int, tokens_out: int,
      cache_read_tokens: int, cache_creation_tokens: int,
      stop_reason: str,
    }
    """
    client = _client()
    started = time.perf_counter()

    # Build messages: prior history + new user message
    messages: list[dict] = []
    for h in (history or []):
        # history entries are simple {role, content: str}
        messages.append({"role": h["role"],
                         "content": [{"type": "text", "text": h["content"]}]})
    messages.append({"role": "user",
                     "content": [{"type": "text", "text": user_message}]})

    tool_trace: list[dict] = []
    total_cost = 0.0
    total_in = total_out = 0
    total_cache_read = total_cache_creation = 0
    final_text = ""
    stop_reason = "unknown"

    for iteration in range(MAX_ITERATIONS):
        # Cache the system prompt + tool defs (stable across the loop)
        system_blocks = [{
            "type": "text", "text": system,
            "cache_control": {"type": "ephemeral"},
        }]
        try:
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS_PER_TURN,
                system=system_blocks,
                messages=messages,
                tools=assistant_tools.ANTHROPIC_TOOLS,
            )
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"Anthropic API error (status {e.status_code}): {e}",
                retryable=(e.status_code in (429, 500, 502, 503, 504)),
                sdk_error=e,
            )
        except anthropic.APIError as e:
            raise LLMError(
                f"Anthropic SDK error: {e}",
                retryable=True, sdk_error=e,
            )

        # Cost accounting
        usage = response.usage
        in_tokens = usage.input_tokens
        out_tokens = usage.output_tokens
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cost = compute_cost(
            response.model,
            tokens_input=in_tokens, tokens_output=out_tokens,
            cache_read=cache_read, cache_creation=cache_creation,
        )
        total_cost += cost
        total_in += in_tokens
        total_out += out_tokens
        total_cache_read += cache_read
        total_cache_creation += cache_creation
        stop_reason = response.stop_reason

        # Collect any text in the response
        text_chunks = [b.text for b in response.content if b.type == "text"]
        if text_chunks:
            final_text = "\n\n".join(text_chunks)

        # If no tool_use, we're done
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks or stop_reason == "end_turn":
            break

        # Append the assistant turn (full content, including tool_use blocks)
        messages.append({
            "role": "assistant",
            "content": [_block_to_dict(b) for b in response.content],
        })

        # Execute each tool_use, build tool_result blocks
        tool_results: list[dict] = []
        for block in tool_use_blocks:
            result, is_image = assistant_tools.execute_tool(
                block.name, dict(block.input))
            preview = (
                "(image)" if is_image else
                str(result)[:300].replace("\n", " ⏎ ")
            )
            ok = not (isinstance(result, str) and result.startswith("ERROR"))
            tool_trace.append({
                "name": block.name,
                "input": dict(block.input),
                "ok": ok,
                "preview": preview,
            })
            if is_image:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": [result],
                })
            else:
                # Truncate very large outputs to keep messages manageable
                content_str = str(result)[:60000]
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content_str,
                    "is_error": not ok,
                })

        messages.append({"role": "user", "content": tool_results})
    else:
        # max iterations hit without end_turn
        stop_reason = "max_iterations"
        if not final_text:
            final_text = (
                f"[Stopped after {MAX_ITERATIONS} tool iterations without "
                "reaching a final answer. Last tool calls visible in trace.]"
            )

    return {
        "response": final_text or "(no text response)",
        "tool_trace": tool_trace,
        "cost_usd": round(total_cost, 6),
        "latency_s": round(time.perf_counter() - started, 2),
        "iterations": iteration + 1,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "cache_read_tokens": total_cache_read,
        "cache_creation_tokens": total_cache_creation,
        "model": response.model,
        "stop_reason": stop_reason,
    }
