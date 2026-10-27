# TCE Agent: a Jira-ticket-to-commit coding agent

A personal project: an AI agent that reads a Jira ticket, finds the relevant code in a Go codebase, makes a small edit, and commits it. Every write and every commit needs a human `y/n` approval.

Status: a working learning project, run against a local sandbox copy of a Go service. It is not production software, and it has never pushed anything to a remote.

## What it does

1. Fetches a Jira ticket (or takes the task as plain text).
2. Searches the codebase by meaning (RAG over function-level chunks).
3. Reads the files it needs and makes the smallest edit that satisfies the task.
4. Shows you the diff and commits on a dedicated sandbox branch, after you approve.

I built it twice on purpose: first as a hand-written tool-use loop (`main.py`), then as a LangGraph graph (`lg_agent.py`) that reuses the same tools and system prompt.

## Architecture

Two phases that only share the `chroma_db/` folder:

```
OFFLINE (run by hand)                     ONLINE (every request)
Go source files                           ticket or task text
  -> chunker.py (functions, methods)        -> agent loop -> model
  -> header added (file, receiver)                |  asks for tools
  -> Chroma embeddings                            v
  -> chroma_db/  ------------------------> search_code
                                                  |
                                           read_file / list_files
                                                  |
                                           replace_in_file  (asks you first)
                                                  |
                                           commit_changes   (asks you first)
```

The model never touches files, git or the vector store itself. It requests a tool, and my code decides whether to run it.

| File | Role |
|---|---|
| `main.py` | Agent loop, system prompt, six tools, path sandbox, round limit |
| `lg_agent.py` | Same agent as a LangGraph graph (agent node, tools node, conditional edge) |
| `chunker.py` | Tree-sitter parser: one chunk per Go function or method, with a file and receiver header |
| `index.py` | Embeds the chunks into Chroma |
| `git_ops.py` | `run_git`, `commit_changes` (branch check, diff preview, approval), `reset_repo` |
| `jira_client.py` | Fetches a ticket and flattens it to text |
| `checks.py` | Check functions for evaluation: files changed, content added, commit made, build result |

## Tools

| Tool | What it does |
|---|---|
| `get_jira_ticket` | Fetches summary, status, priority, labels and description |
| `search_code` | Semantic search over the indexed functions |
| `list_files` | Lists a folder inside the repo |
| `read_file` | Reads a text file inside the repo |
| `replace_in_file` | Replaces one exact, unique piece of text (matches the file's CRLF or LF line endings) |
| `commit_changes` | Stages only the files the agent edited and commits, after approval |

## Safety design

- **Path sandbox.** Every path the model sends goes through `safe_path`. It rejects anything outside the repo root (`..`, absolute paths, other drives), `.env` files and the `.git` folder.
- **Branch guard.** Commits are refused unless the repo is on the `agent-sandbox` branch.
- **Human approval** before every edit and every commit, with a diff preview.
- **Scoped commits.** Only the files edited by the agent are staged, never `git add -A`.
- **Round limit** so a confused run stops.
- **Prompt rules.** Vague tasks get a question, not a guess. Ticket text is treated as data and cannot override the rules. The agent states that it cannot run the build.
- **Checked behaviors.** A vague request ("make the server faster") produced questions and no edits. A ticket telling the agent to paste `.env` into a comment was refused, and the sandbox also blocks that file in code.

## Retrieval

- Tree-sitter splits Go code into function and method chunks. Generated files (`Code generated` marker) and tests are skipped. The sandbox repo gave 56 chunks.
- Each chunk is embedded with a header (`File: ...`, `Method: (s *traceServer) handleMessage`) so a bare function name keeps its context.
- Embeddings use Chroma's default model.
- Small check on three questions with known answers: the right function was first in 2 of 3 and in the top 5 in 3 of 3.

## Setup

Requirements: Python 3.11+, Git, Go (only if you want to build-check the target repo), and a copy of a Go repository to work on.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
ANTHROPIC_API_KEY=...
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=...
JIRA_API_TOKEN=...
```

Then:

1. Point `REPO` in `main.py` at your sandbox copy of the target repo. Create the branch `agent-sandbox` there from a clean baseline commit.
2. Build the index: `python index.py`
3. Run the agent: `python main.py` (or `python lg_agent.py` for the LangGraph version)

On a low-memory Windows machine, put `os.environ["OPENBLAS_NUM_THREADS"] = "1"` at the very top of any script that imports `chromadb`.

## Observations

- Cost is mostly input tokens. A one-file edit that took 3 tool rounds used about 19,000 input tokens and about 600 output tokens, because each round re-sends the history, including every file read.
- The model's edits vary between runs on the same ticket (for example a different image tag or an extra healthcheck). Checks should therefore test what must be true, not compare exact text.
- A line-ending bug (Windows CRLF files) caused failed matches and mixed endings until `replace_in_file` was made to match the file's convention.

## Evaluation status

Built: a script-friendly reset of the sandbox repo, and check functions (files changed, required content in the added lines, commit expected or not, build result). Not built: the repeated-run loop and results table. No pass rates are claimed.

## Limitations and next steps

- Run the evaluation loop (several tickets, several runs each) and report pass rates.
- Add tracing and a per-run log of tool calls and token counts.
- Replace the `y/n` prompts in the LangGraph version with `interrupt` and a checkpointer, so a run can pause and resume.
- Let `read_file` return line ranges to cut token cost.
- Compare plain vector search against hybrid search and a code-specific embedding model.
- Build checks (`go build`) can fail from memory limits on small machines. The check should report that as an environment error, not as an agent failure.
- No push or merge-request step, by design for now.