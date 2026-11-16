"""LLM client setup and query orchestration."""

import json

from openai import OpenAI

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from tools import execute_tool, tools

# The OpenAI client rejects a None api_key, so fall back to a placeholder to
# keep the app importable before OPENROUTER_API_KEY is configured.
client = OpenAI(
    api_key=OPENROUTER_API_KEY or "sk-missing",
    base_url=OPENROUTER_BASE_URL,
)


def process_query(query, messages=None):
    """Run a query against the LLM, executing any tool calls it requests.

    Args:
        query: The user's message.
        messages: Optional running conversation history. When provided, it is
            updated in place so conversation memory persists across queries.

    Returns:
        The final assistant text response.
    """
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": query})

    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=messages,
        tools=tools,
        max_tokens=2024,
    )

    while True:
        message = response.choices[0].message
        assistant_text = message.content or ""
        tool_calls = message.tool_calls or []

        # Record the assistant turn (with its tool_calls, if any).
        assistant_msg = {"role": "assistant", "content": assistant_text}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            # No tools requested -> this is the final answer.
            if assistant_text:
                print(assistant_text)
            return assistant_text

        # Execute each requested tool and append its result.
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments or "{}")
            print(f"Calling tool {tool_name} with args {tool_args}")

            result = execute_tool(tool_name, tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        # Send the tool results back and continue the loop.
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=tools,
            max_tokens=2024,
        )


def chat_loop():
    """Run an interactive CLI chat loop (used when running llm.py directly)."""
    print("Type your queries or 'quit' to exit.")
    while True:
        try:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break

            process_query(query)
            print("\n")
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    chat_loop()
