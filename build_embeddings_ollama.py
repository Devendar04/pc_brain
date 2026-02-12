print("🔥 build_embeddings_ollama STARTED", flush=True)

import json, faiss, numpy as np, requests, os

OLLAMA_URL = "http://localhost:11434"
MODEL = "nomic-embed-text"

print("Loading chunks.json", flush=True)
with open("rag_data/chunks.json", encoding="utf-8") as f:
    data = json.load(f)

chunks = data["chunks"]
print("Total chunks:", len(chunks), flush=True)

vectors = []

for i, c in enumerate(chunks):
    if i % 5 == 0:
        print(f"Embedding {i}/{len(chunks)}", flush=True)

    r = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": MODEL, "prompt": c["text"]},
        timeout=60
    )
    r.raise_for_status()
    vectors.append(r.json()["embedding"])

print("All embeddings done", flush=True)

xb = np.array(vectors).astype("float32")
faiss.normalize_L2(xb)

index = faiss.IndexFlatIP(xb.shape[1])
index.add(xb)
faiss.write_index(index, "rag_data/index.faiss")

with open("rag_data/meta.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f)

print("✅ index.faiss + meta.json created", flush=True)
