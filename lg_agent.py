import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

import main   


@tool
def read_file(path: str) -> str:
    """Read a text file from the project and return its contents."""
    return main.read_file(path)

@tool
def list_files(directory: str) -> str:
    """List the files and folders inside a directory of the project. Folders end with '/'. Use this first to explore the project structure before reading files."""
    return main.list_files(directory)

@tool
def search_code(query: str) -> str:
    """Search the indexed codebase by meaning. Use this to find where something is implemented or handled, before reading whole files. Returns the best matching functions with file path, line range and the start of the code."""
    return main.search_code(query)

@tool
def replace_in_file(path: str, old_text: str, new_text: str) -> str:
    """Edit a file by replacing one exact piece of text with new text. old_text must match the file exactly (including whitespace and indentation) and must appear exactly once; include a few surrounding lines to make it unique. Read the file first so you copy the text exactly. Make the smallest change that does the job."""
    return main.replace_in_file(path, old_text, new_text)

@tool
def commit_changes(message: str) -> str:
    """Commit the files you have edited with replace_in_file. Call this only after finishing all edits for the task. The user reviews the diff and must approve. Use a short, clear commit message describing the change."""
    result = main.commit_changes(main.REPO_ROOT, message, main.changed_files, auto_approve=main.AUTO_APPROVE)
    if result.startswith("Success"):
        main.changed_files.clear()
    return result

@tool
def get_jira_ticket(ticket: str) -> str:
    """Fetch a Jira ticket's details (summary, status, assignee, priority, labels, description) by its issue key (e.g. 'TCE-5') or its full Jira URL. Use this at the start of a task when the user gives you a ticket key or link, before exploring or editing code."""
    return main.get_issue(ticket)

tools = [read_file, list_files, search_code, replace_in_file, commit_changes, get_jira_ticket]
model = ChatAnthropic(model="claude-sonnet-5-5", max_tokens=4000).bind_tools(tools)

system_prompt = SystemMessage(content=main.SYSTEM_PROMPT)

def agent(state: MessagesState):
    response = model.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

graph = StateGraph(MessagesState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools=tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges(
    "agent",
    tools_condition,
)
graph.add_edge("tools", "agent")
app = graph.compile()

try:
    with open("graph.png", "wb") as f:
        f.write(app.get_graph().draw_mermaid_png())
except Exception as e:
    print("Could not draw the graph image:", e)

result = app.invoke(
    {"messages": [("user", "Here's the ticket: https://yasmineldeeb.atlassian.net/browse/TCE-5 — read it, implement the required change, and commit it.")]},
    config={"max_concurrency": 1},
)
print(result["messages"][-1].content)