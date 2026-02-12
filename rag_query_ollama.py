import os, json, re, requests
import numpy as np
import faiss

# ---------------- CONFIG ----------------
RAG_DIR = "rag_data"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2:0.5b"

TOP_K = 5
MAX_CONTEXT_CHARS = 1200
DEFAULT_REPLY = "Information not available in the college document."

RAG_CACHE = {}
# ----------------------------------------


def load_index_meta():
    index = faiss.read_index(os.path.join(RAG_DIR, "index.faiss"))
    meta = json.load(open(os.path.join(RAG_DIR, "meta.json"), encoding="utf-8"))
    return index, meta


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def embed_query(text: str):
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=10
        )
        r.raise_for_status()
        vec = np.array(r.json()["embedding"], dtype="float32").reshape(1, -1)
        faiss.normalize_L2(vec)
        return vec
    except Exception:
        return None


# ---------- PERSON QUERY HELPERS ----------

def is_person_query(q: str) -> bool:
    return q.startswith("who is") or q.startswith("whos") or "hod" in q


def extract_name_tokens(q: str):
    stop = {"who", "is", "whos", "dr", "doctor", "the"}
    return [t for t in q.split() if t not in stop]


# ------------------------------------------

def build_prompt(question, contexts):
    return (
        "Answer ONLY using the information present in the context below.\n"
        "If the answer is not present, reply exactly:\n"
        "'Information not available in the college document.'\n\n"
        "Context:\n"
        + "\n\n".join(contexts)
        + f"\n\nQuestion: {question}\nAnswer:"
    )


def trim_contexts(contexts):
    out, total = [], 0
    for c in contexts:
        if total + len(c) > MAX_CONTEXT_CHARS:
            break
        out.append(c)
        total += len(c)
    return out


def query_rag(question: str) -> str:
    q_norm = normalize_text(question)

    if q_norm in RAG_CACHE:
        return RAG_CACHE[q_norm]

    index, meta = load_index_meta()
    contexts = []

    # 1️⃣ EXACT MATCH
    for c in meta:
        if q_norm in normalize_text(c["text"]):
            contexts.append(c["text"])

    # 2️⃣ PERSON NAME TOKEN MATCH (CRITICAL FIX)
    if not contexts and is_person_query(q_norm):
        name_tokens = extract_name_tokens(q_norm)
        for c in meta:
            chunk_norm = normalize_text(c["text"])
            if all(t in chunk_norm for t in name_tokens):
                contexts.append(c["text"])

    # 3️⃣ SEMANTIC SEARCH (ALWAYS ALLOWED)
    if not contexts:
        q_vec = embed_query(question)
        if q_vec is not None:
            _, I = index.search(q_vec, TOP_K)
            for idx in I[0]:
                if idx >= 0:
                    contexts.append(meta[idx]["text"])

    # 🚨 HARD STOP (ANTI-HALLUCINATION)
    if not contexts:
        RAG_CACHE[q_norm] = DEFAULT_REPLY
        return DEFAULT_REPLY

    contexts = trim_contexts(contexts[:3])
    prompt = build_prompt(question, contexts)

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        r.raise_for_status()
        reply = r.json().get("response", "").strip()
        final = reply if reply else DEFAULT_REPLY
    except Exception:
        final = DEFAULT_REPLY

    RAG_CACHE[q_norm] = final
    return final
