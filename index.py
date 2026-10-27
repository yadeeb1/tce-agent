import os
import chromadb
from chunker import chunk_repo, header

REPO = r"C:\Users\HYGZ1558\Documents\TCE"

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("tce_code")

chunks = chunk_repo(REPO)

ids, documents, metadatas = [], [], []
for c in chunks:
    rel_path = os.path.relpath(c.file, REPO).replace("\\", "/")
    ids.append(f"{rel_path}:{c.start_line}")   
    documents.append(header(c, REPO))
    metadatas.append({
        "file": rel_path,
        "kind": c.kind,
        "name": c.name,
        "receiver": c.receiver,
        "start_line": c.start_line,
        "end_line": c.end_line,
    })

collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
print("indexed:", collection.count())