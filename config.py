"""Configuration and environment loading for the chatbot."""

import os

from dotenv import load_dotenv

# Load environment variables from a .env file (if present) before reading them.
load_dotenv()

PAPER_DIR = "papers"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl"

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

SYSTEM_PROMPT = (
    "You are a helpful research assistant. You can search for papers on arXiv "
    "and look up details about specific papers. Use the available tools when "
    "the user asks about papers."
)
