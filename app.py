"""Flask web application: routes, session state, and the HTTP entry point."""

import uuid

from flask import Flask, render_template, request, session, jsonify

from config import SECRET_KEY, SYSTEM_PROMPT
from llm import process_query
from papers import search_papers

app = Flask(__name__)
app.secret_key = SECRET_KEY

# In-memory conversation histories, keyed by per-browser session id.
conversations = {}


def get_or_create_history():
    """Return the message history for the current session, creating it if needed."""
    session_id = session.get("session_id")
    if not session_id or session_id not in conversations:
        session_id = str(uuid.uuid4())
        session["session_id"] = session_id
        conversations[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return conversations[session_id]


def visible_messages(history):
    """Return only user/assistant text turns for display in the UI."""
    visible = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user" and content:
            visible.append({"role": "user", "content": content})
        elif role == "assistant" and content and not msg.get("tool_calls"):
            visible.append({"role": "assistant", "content": content})
    return visible


@app.route("/", methods=["GET", "POST"])
def home():
    topic = ""
    paper_ids = None
    error = None

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        if topic:
            try:
                paper_ids = search_papers(topic)
            except Exception as e:
                error = f"Search failed: {e}"
        else:
            error = "Please enter a topic to search for."

    session_id = session.get("session_id")
    history = conversations.get(session_id, []) if session_id else []
    chat_history = visible_messages(history)

    return render_template(
        "index.html",
        topic=topic,
        paper_ids=paper_ids,
        error=error,
        chat_history=chat_history,
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or request.form
    query = (data.get("query") or data.get("message") or "").strip()

    if not query:
        return jsonify({"error": "Please enter a message."}), 400

    history = get_or_create_history()

    try:
        answer = process_query(query, history)
    except Exception as e:
        return jsonify({"error": f"Chat failed: {e}"}), 500

    if not answer:
        answer = "The assistant returned an empty response."

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
