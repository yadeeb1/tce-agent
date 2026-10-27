import subprocess
from git_ops import run_git

BASELINE = "e6c8568"

def files_changed(repo):
    ok, output = run_git(["diff", "--name-only", BASELINE], repo)
    if not ok or not output:
        return []
    
    return output.split("\n")

def added_lines(repo):
    ok, output = run_git(["diff", BASELINE, "-U0"], repo)
    if not ok:
        return ""
    added = []
    for line in output.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return "\n".join(added)
    
def commit_count(repo):
    ok, output = run_git(["rev-list", "--count", BASELINE + "..HEAD"], repo)
    if not ok:
        return 0
    return int(output)

def builds(repo):
    try:
        result = subprocess.run(["go", "build", "./..."], cwd=repo, capture_output=True, text=True)
    except:
        return (False, "go not found on PATH")
    return (result.returncode == 0, result.stderr)

def check_ticket(repo, expected_files, must_contain, expect_commit=True):
    results = {}
    results["files_ok"]   = set(files_changed(repo)) == set(expected_files)
    added = added_lines(repo)
    results["content_ok"] = all(s in added for s in must_contain)
    committed = commit_count(repo) >= 1
    results["commit_ok"] = committed == expect_commit
    build_passed, build_output = builds(repo)
    results["build_ok"] = build_passed
    return results
