# Scientific Papers Chat Bot

A small Flask web app that searches [arXiv](https://arxiv.org) for papers on a topic and pairs that
with an LLM chat assistant that can search for papers and look up paper details on its own via
tool calling.

There are two independent front ends sharing the same underlying arXiv search code:

1. **Search form** — type a topic, get back clickable links to matching papers.
2. **Chat widget** — talk to an LLM assistant that decides when to search arXiv or look up a paper
   you asked about.

## Features

- **Topic search on arXiv** — live query against the arXiv API, results cached locally to JSON.
- **Conversational assistant** — OpenAI-compatible function calling; the model chooses between
  `search_papers` and `extract_info`.
- **Tool calling loop** — tool results are fed back to the model until it produces a final answer.
- **Per-session memory** — each browser session gets its own conversation history, so follow-up
  questions keep context.
- **Paper detail lookup** — ask about a specific paper ID and the assistant reads its stored
  metadata (title, authors, abstract, PDF link, publication date).
- **Two interfaces** — browser UI and a terminal chat loop, no frontend framework or build step.

## Tech stack & LLM

| Layer | Choice |
| --- | --- |
| Language | Python 3 (developed on 3.13) |
| Web framework | [Flask](https://flask.palletsprojects.com/) + Jinja2 templates |
| LLM client | [`openai`](https://pypi.org/project/openai/) Python SDK, pointed at **OpenRouter** |
| LLM provider | [OpenRouter](https://openrouter.ai/) — `https://openrouter.ai/api/v1` |
| LLM model | `nvidia/nemotron-3.5-super-vl` (set via `OPENROUTER_MODEL`) |
| Paper search | [`arxiv`](https://pypi.org/project/arxiv/) Python package (live arXiv API) |
| Config | [`python-dotenv`](https://pypi.org/project/python-dotenv/) for `.env` loading |
| Frontend | Plain HTML/CSS/JavaScript in a single Jinja2 template |
| Storage | Local JSON files (no database) |

Dependencies are listed in [requirements.txt](requirements.txt) — `openai`, `arxiv`, `Flask`,
`python-dotenv`.

## Setup & installation

Requires Python 3 (developed on 3.13) and an [OpenRouter API key](https://openrouter.ai/keys).

```bash
git clone https://github.com/Curious-Harshal/scientific-papers-chat-bot.git
cd scientific-papers-chat-bot

python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-your-key-here
FLASK_SECRET_KEY=change-me-to-a-random-string
```

Then start the web app:

```bash
python app.py
```

Open <http://127.0.0.1:5000>.

## Configuration

All settings live in [config.py](config.py). The first two are read from the environment (with
`.env` support); `OPENROUTER_MODEL` and `PAPER_DIR` are fixed in code.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Yes | — | API key used to authenticate with OpenRouter. Without it the app still imports, but every chat request fails. |
| `FLASK_SECRET_KEY` | Recommended | `dev-secret-key-change-me` | Signs the Flask session cookie that identifies a conversation. Change it outside local development. |
| `OPENROUTER_MODEL` | No | `nvidia/nemotron-3.5-super-vl` | Model ID sent to OpenRouter. |
| `PAPER_DIR` | No | `papers` | Directory for the local arXiv cache. |

`.env` is gitignored. Never commit real keys.

## Usage

### Web UI

**Search form.** Enter a topic (for example `transformers`) and submit. The app queries arXiv for the
5 most relevant results, saves them, and renders the paper IDs as links to
`https://arxiv.org/abs/<id>`. If the topic is blank or the search fails, an error message is shown
instead.

**Chat widget.** Ask in natural language — *"find recent papers on graph neural networks"* or
*"what is paper 2209.07474v3 about?"*. The assistant either answers directly or calls a tool, then
answers. Replies stream into the log; history is preserved per browser session.

### CLI

`llm.py` also runs standalone as a terminal chat loop:

```bash
python llm.py
```

Type a query and press Enter, or `quit` to exit. Note that the CLI calls `process_query()` without a
persistent history, so each query starts fresh.

### HTTP API

All routes are defined in [app.py](app.py).

| Method | Path | Request | Success | Errors |
| --- | --- | --- | --- | --- |
| `GET` | `/` | — | `200` HTML page (search form + chat log) | — |
| `POST` | `/` | form field `topic` | `200` HTML page with results | `200` HTML page with an error message |
| `POST` | `/chat` | JSON or form field `query` (or `message`) | `200` `{"answer": "..."}` | `400` `{"error": "..."}`, `500` `{"error": "..."}` |
| `GET` | `/chat` | — | — | `405 Method Not Allowed` (only `POST` is registered) |

#### `GET /`

Renders [index.html](templates/index.html). Template context: `topic` (`""`), `paper_ids` (`None`),
`error` (`None`), and `chat_history` (from the session, empty if no session exists yet). This route
never creates a session.

#### `POST /`

Form-encoded only (`application/x-www-form-urlencoded`).

- `topic` — the search term; stripped before use.
- Blank topic → renders the page with `error = "Please enter a topic to search for."`.
- Otherwise calls `search_papers(topic)` — a **synchronous, blocking** call to the arXiv API that
  also writes the cache file.
- Any exception → `error = "Search failed: <message>"`. The response is still HTTP `200`.
- On success, `paper_ids` is a list of short IDs (possibly empty, which is a valid result).

#### `POST /chat`

Accepts either JSON (`{"query": "..."}`) or form-encoded data. The `query` key is preferred; if
absent or empty, `message` is used.

```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "find papers on attention mechanisms"}'
```

```json
{ "answer": "Here are some papers on attention mechanisms..." }
```

Behavior:

- Empty query → `400` `{"error": "Please enter a message."}`.
- First call for a browser creates a `session_id` (a UUID) in the signed session cookie and starts a
  history seeded with the system prompt.
- Runs the LLM tool-calling loop, which may hit the arXiv API and/or read local JSON files.
- Any exception → `500` `{"error": "Chat failed: <message>"}`.
- If the model returns no text, the answer becomes `"The assistant returned an empty response."`.

## Data storage & local cache

There is no database. Every `search_papers()` call writes to disk, whether it was triggered by the
form or by the assistant.

- **Location:** `papers/<topic.lower().replace(" ", "_")>/papers_info.json` — e.g. a search for
  `Graph Neural Network` writes to `papers/graph_neural_network/papers_info.json`.
- **Merge behavior:** an existing file is loaded first, then entries are added/overwritten, keyed by
  the arXiv short ID. Re-searching a topic merges new papers into the old file.
- **Schema:**

```json
{
  "2512.22190v1": {
    "title": "Physics-Informed Machine Learning for Transformer Condition Monitoring ...",
    "authors": ["Jose I. Aizpurua"],
    "summary": "Power transformers are critical assets in power networks ...",
    "pdf_url": "https://arxiv.org/pdf/2512.22190v1",
    "published": "2025-12-20"
  }
}
```

`search_papers()` returns only the list of IDs; the metadata above stays in the JSON file.

**Lookup.** When you ask about a specific paper, the assistant calls `extract_info(paper_id)`, which
scans every subdirectory under `papers/`, opens each `papers_info.json`, and returns the matching
entry as pretty-printed JSON. It is read-only and makes no network calls. If the ID is not found it
returns `"There's no saved information related to paper <id>."`

The `papers/` directory is gitignored (only `.gitkeep` is tracked) because it is a runtime cache.

## Limitations & gotchas

- **`summary` is the arXiv abstract**, not an LLM-generated summary. The assistant can rephrase it,
  but the text originates from arXiv at search time.
- **`extract_info` matches by paper ID only** — not by title or topic. A paper must have been
  fetched by a previous `search_papers` call before it can be looked up.
- **Conversation history is ephemeral.** It lives in a module-level dict and disappears when the
  process restarts. The CLI does not persist history at all.
- **Searches are always live.** `search_papers()` never reads from the local cache, so repeated
  searches re-query arXiv every time.
- **Cache directories can get odd names.** The LLM sometimes passes an awkward topic string straight
  through as a directory name, which is why directories such as
  `papers/search_for_papers_on_algebra/` exist.
- **Paper IDs may carry version suffixes** (e.g. `2512.22190v1`) because the code uses
  `get_short_id()`.
- **`app.py` runs with `debug=True`**, which is fine for local development but must not be used in
  production.
- **Synchronous requests.** Both a form search and a chat turn block until arXiv and/or the LLM
  respond, so responses can take several seconds.
