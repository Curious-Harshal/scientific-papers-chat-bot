"""Tool schemas for the chatbot.

These schemas describe the functions exposed to the LLM (e.g. DeepSeek) as
tools. The `tools` list follows the OpenAI/DeepSeek function-calling format,
where each tool wraps a `function` object with a name, a description, and a
JSON `parameters` schema.
"""

import json

from papers import extract_info, search_papers

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search for papers on arXiv based on a topic and store their information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to retrieve",
                        "default": 5,
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_info",
            "description": "Search for information about a specific paper across all topic directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper to look for",
                    },
                },
                "required": ["paper_id"],
            },
        },
    },
]

mapping_tool_function = {
    "search_papers": search_papers,
    "extract_info": extract_info,
}


def execute_tool(tool_name, tool_args):
    """Execute a tool by name and normalize its result to a string."""
    result = mapping_tool_function[tool_name](**tool_args)

    if result is None:
        result = "The operation completed but didn't return any results."
    elif isinstance(result, list):
        result = ", ".join(result)
    elif isinstance(result, dict):
        # Convert dictionaries to formatted JSON strings
        result = json.dumps(result, indent=2)
    else:
        # For any other type, convert using str()
        result = str(result)

    return result
