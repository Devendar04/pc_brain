

import json
import os
import re
import threading
from typing import Tuple, Dict

# original intent schema (kept for compatibility)
INTENT_SCHEMA = {
    "COLLEGE_DIRECTOR": ["college"],
    "COLLEGE_CHAIRMAN": ["college"],
    "DEPARTMENT_HOD": ["department"],
    "PLACEMENTS": ["college"],
    "COURSES": ["college"],
    "CAMPUS": ["college"]
}
ALLOWED_CTX_KEYS = {"college", "department", "year", "last_intent"}

# persistence (optional)
_CTX_FILE = os.path.join(os.path.dirname(__file__), "nlu_context.json")
_context_lock = threading.Lock()
_context = {}

def _load_context():
    global _context
    try:
        if os.path.exists(_CTX_FILE):
            with open(_CTX_FILE, "r", encoding="utf-8") as f:
                _context = json.load(f)
    except Exception:
        _context = {}

def _save_context():
    try:
        with _context_lock:
            with open(_CTX_FILE, "w", encoding="utf-8") as f:
                json.dump(_context, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# initial load
_load_context()

# helpers
def _clean(text: str) -> str:
    return (text or "").strip().lower()

def detect_intent_prod(text: str) -> str:
    t = _clean(text)
    # explicit phrase checks (keeps original behavior but safer)
    if any(k in t for k in ["owner", "chairman", "malik", "boss"]):
        return "COLLEGE_CHAIRMAN"
    if any(k in t for k in ["director", "principal"]):
        return "COLLEGE_DIRECTOR"
    if "hod" in t or "head of department" in t:
        return "DEPARTMENT_HOD"
    if any(k in t for k in ["placement", "package", "ctc", "lpa"]):
        return "PLACEMENTS"
    if any(k in t for k in ["course", "branch", "degree"]):
        return "COURSES"
    if any(k in t for k in ["campus", "hostel", "library", "infrastructure"]):
        return "CAMPUS"
    return "GENERAL"

def extract_slots_prod(text: str) -> Dict[str, str]:
    t = _clean(text)
    slots = {}

    # college name hints
    if any(k in t for k in ["gitanjali", "gits", "geetanjali", "college", "institute"]):
        slots["college"] = "GITS"

    # department detection
    if any(k in t for k in ["cse", "computer science", "computer", "cs"]):
        slots["department"] = "CSE"
    elif any(k in t for k in ["ai", "artificial intelligence"]):
        slots["department"] = "AI"
    elif "mechanical" in t:
        slots["department"] = "ME"
    elif "civil" in t:
        slots["department"] = "CE"
    elif "ece" in t or "electronics" in t:
        slots["department"] = "ECE"

    # quick numeric slot detection (year, batch)
    m = re.search(r"\b(19|20)\d{2}\b", t)
    if m:
        slots["year"] = m.group(0)

    return slots

def is_slot_complete(intent: str, slots: Dict[str, str]) -> bool:
    required = INTENT_SCHEMA.get(intent, [])
    return all(r in slots and slots[r] for r in required)

def resolve_context(intent: str, slots: Dict[str, str]) -> Dict[str, str]:
    """
    If slots missing and context exists, merge. Does not overwrite explicit slots.
    """
    with _context_lock:
        ctx = dict(_context) if _context else {}
    for k, v in ctx.items():
        if k not in slots or not slots.get(k):
            slots[k] = v
    return slots


def update_context(intent, slots):
    global _context
    if _context is None:
        _context = {}
    if isinstance(slots, dict):
        _context.update(slots)

def nlu_pipeline(text: str) -> Tuple[str, Dict[str,str], str]:
    """
    Primary pipeline. Returns (intent, slots, state).
    State is "OK" or "CLARIFY".
    """
    intent = detect_intent_prod(text)
    slots = extract_slots_prod(text)
    slots = resolve_context(intent, slots)

    if not is_slot_complete(intent, slots):
        return intent, slots, "CLARIFY"

    update_context(intent, slots)
    return intent, slots, "OK"