import subprocess

AUTO_APPROVE = False

def run_git(args, repo):
    result = subprocess.run(
        ["git"] + args,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    
    ok = result.returncode == 0
    output = result.stdout.strip() if ok else result.stderr.strip()
    return ok, output

def current_branch(repo):
    ok, output = run_git(["branch", "--show-current"], repo)
    return output if ok else None

def commit_changes(repo, message, files, required_branch="agent-sandbox", auto_approve=False):
    branch = current_branch(repo)
    if branch != required_branch:
        return f"Error: on branch {branch}, expected {required_branch}"
    
    if not files:
        return "Error: no changes to commit"
    
    if not message.strip():
        return "Error: empty message"

    ok, output = run_git(["add", "--"] + list(files), repo)
    
    if not ok:
        return "Error: " + output

    ok, diff = run_git(["diff", "--staged", '--'], repo)
    if not diff:
       return "Error: nothing staged to commit"
    print("\nStaged changes:\n" + diff)
    
    if not auto_approve:
        answer = input("Commit these changes? (y/n): ").strip().lower()
        if answer != "y":
            run_git(["reset", "--"] + files, repo)
            return "Error: the user declined this commit; nothing was committed. Ask the user what to do instead."

    ok, output = run_git(["commit", "-m", message, "--"], repo)
    if not ok:
        return "Error: commit failed: " + output

    ok, short_hash = run_git(["rev-parse", "--short", "HEAD"], repo)
    if not ok:
        return "Committed, but could not read the commit hash"
    return "Success: committed " + short_hash

def reset_repo(repo, baseline="e6c8568", required_branch="agent-sandbox"):
    branch = current_branch(repo)
    if branch != required_branch:
        return False, f"Error: on branch {branch}, expected {required_branch}"
    ok, output = run_git(["reset", "--hard", baseline], repo)
    if not ok:
        return (False, output)
    ok, output = run_git(["clean", "-fd"], repo)
    if not ok:
        return (False, output)
    return True, "reset to " + baseline