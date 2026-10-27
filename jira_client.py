import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def adf_to_text(node):
    if node.get("text"):
        return node.get("text")
    elif node.get("content"):
        pieces = []
        for child in node.get("content"):
            result = adf_to_text(child)
            pieces.append(result)
        text = "".join(pieces)  
        if node.get("type") in ("paragraph", "heading", "listItem"):
            text = text + "\n" 
        return text
    elif node.get("type") == "hardBreak":
        return "\n"
    else:
        return ""

def extract_issue_key(ticket):
    match = re.search(r"[A-Z][A-Z0-9]*-\d+", ticket)
    if match:
        return match.group(0)
    return None

def get_issue(ticket):
    key = extract_issue_key(ticket)
    if key is None:
        return "Error: could not find a Jira issue key in: " + ticket

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{key}"

    response = requests.get(url,
                            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                            headers={"Accept": "application/json"},
                            params={"fields": "summary,description,status,assignee,priority,labels,comment"})

    if response.status_code == 401:
        return "Error: Jira rejected the credentials (check JIRA_EMAIL and JIRA_API_TOKEN)"
    if response.status_code == 404:
        return "Error: issue " + key + " not found, or you do not have permission to see it"
    if response.status_code != 200:
        return "Error: Jira returned " + str(response.status_code) + " for " + key

    data = response.json()
    fields = data["fields"]

    description_node = fields.get("description")
    if description_node:
        description = adf_to_text(description_node)
    else:
        description = "(no description)"

    summary = fields.get("summary", "(no summary)")
    status = (fields.get("status") or {}).get("name", "(unknown)")
    assignee_field = fields.get("assignee")
    assignee = assignee_field.get("displayName") if assignee_field else "(unassigned)"
    priority = (fields.get("priority") or {}).get("name", "(none)")
    labels = fields.get("labels", [])

    return (
        f"Key: {key}\n"
        f"Summary: {summary}\n"
        f"Status: {status}\n"
        f"Assignee: {assignee}\n"
        f"Priority: {priority}\n"
        f"Labels: {', '.join(labels) if labels else '(none)'}\n"
        f"Description:\n{description}"
    )
