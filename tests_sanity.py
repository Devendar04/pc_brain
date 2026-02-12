# tests_sanity.py
from nlu_engine import nlu_pipeline
from server_logic import handle_text

def test_nlu_intent():
    intent, slots, state = nlu_pipeline("CSE HOD kaun hai")
    assert intent == "DEPARTMENT_HOD"
    assert slots.get("department") == "CSE"

def test_college_firewall():
    r = handle_text("GITS placement")
    assert "placement" in r["reply"].lower()

def test_no_hallucination():
    r = handle_text("GITS ranking in world")
    # firewall or fallback should avoid unsupported claims
    assert "confirm" in r["reply"].lower() or "available" in r["reply"].lower()

def test_llm_fallback():
    r = handle_text("Explain black hole")
    assert "reply" in r

def test_rag_basic():
    """
    This test requires:
      - rag_data/index.faiss and rag_data/metadata.json prepared
      - OLLAMA_URL accessible and model running OR GROQ_API_KEY set for fallback
    Adjust expected substring to something that appears in your Word doc.
    """
    q = "Who is the HOD of CSE?"
    r = handle_text(q)
    # If RAG returns an answer it should be present in the reply
    assert "hod" in r["reply"].lower() or "i don't know" in r["reply"].lower()
