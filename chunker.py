from dataclasses import dataclass
import tree_sitter_go as tsgo
from tree_sitter import Language, Parser
import os

GO = Language(tsgo.language())
parser = Parser(GO)


@dataclass
class Chunk:
    file: str
    kind: str
    name: str
    receiver: str
    start_line: int
    end_line: int
    code: str


def chunk_file(path):
    with open(path, "rb") as f:
        source = f.read()
    root = parser.parse(source).root_node

    def text(node):
        return source[node.start_byte:node.end_byte].decode("utf-8")

    chunks = []
    for child in root.children:
        if child.type == "function_declaration" or child.type == "method_declaration":
            name = text(child.child_by_field_name("name"))

            recv_node = child.child_by_field_name("receiver")
            receiver = text(recv_node) if recv_node is not None else ""

            kind = "method" if child.type == "method_declaration" else "function"

            chunks.append(Chunk(
                file=path,
                kind=kind,
                name=name,
                receiver=receiver,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                code=text(child),
            ))
    return chunks

def header(chunk, repo_root):
    rel_path = os.path.relpath(chunk.file, repo_root).replace("\\", "/")
    
    if chunk.kind == "method":
        label = f"Method: {chunk.receiver} {chunk.name}"
    else:
        label = f"Function: {chunk.name}"
    
    return f"File: {rel_path}" + "\n" + label + "\n\n" + chunk.code

SKIP_DIRS = {".git", "vendor", "node_modules", "pcap-output"}

def is_generated(path):
    with open(path, "rb") as f:
        head = f.read(1024)
    return b"Code generated" in head


def chunk_repo(repo_root):
    all_chunks = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for name in files:
            if not name.endswith(".go"):
                continue
            if name.endswith("_test.go"):
                continue

            path = os.path.join(root, name)
            if is_generated(path):
                continue

            all_chunks.extend(chunk_file(path))
    return all_chunks