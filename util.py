import requests
import os

from dotenv import load_dotenv

import re
_TRANSLATION_CACHE = {}

ACRONYM_PATTERN = re.compile(
    r"\b[A-Z]{2,}[A-Z0-9]*s?\b"  # NASA, WHO, AIIMS, IITs, GPT4
)
import re

# English letter → Hindi sound map
LETTER_TO_HINDI = {
    "A": "ए-य", "B": "बी", "C": "सी", "D": "डी", "E": "ई",
    "F": "एफ़", "G": "जी", "H": "एच्", "I": "आ-ई", "J": "जे",
    "K": "के", "L": "एल", "M": "एम", "N": "एन", "O": "ओ",
    "P": "पी", "Q": "क्यू", "R": "आर", "S": "एस", "T": "टी",
    "U": "यू", "V": "वी", "W": "डबल-यू", "X": "एक्स",
    "Y": "वा-ई", "Z": "ज़ेड"
}




def spell_acronym(word: str) -> str:
    return " ".join(LETTER_TO_HINDI.get(ch, ch) for ch in word)

def fix_acronym_pronunciation(text: str) -> str:
    def replacer(match):
        return spell_acronym(match.group(0))

    return ACRONYM_PATTERN.sub(replacer, text)

def freeze_acronyms(text):
    acronyms = {}

    def replacer(match):
        key = f"__ACR_{len(acronyms)}__"
        acronyms[key] = match.group(0)
        return key

    frozen_text = ACRONYM_PATTERN.sub(replacer, text)
    return frozen_text, acronyms
def restore_acronyms(translated, acronyms):
    for key, value in acronyms.items():
        translated = translated.replace(key, value)
    return translated
def hinglish_to_hindi(text):
    load_dotenv()
    API_KEY = os.getenv("GROQ_API_KEY")
    examples = [
        # few-shot examples — source (Hinglish/English) -> target (Hindi in Devanagari)
        {
            "src": "kal milte hain, office mein 10 baje.",
            "tgt": "कल मिलते हैं, ऑफिस में १० बजे।"
        },
        {
            "src": "Can you send the report by tonight?",
            "tgt": "क्या आप रिपोर्ट आज रात तक भेज सकते हैं?"
        },
        {
            "src": "meri gaadi breakdown ho gayi hai",
            "tgt": "मेरी गाड़ी खराब हो गई है।"
        }
    ]

    example_text = "\n".join(
        f"Input: {ex['src']}\nHindi: {ex['tgt']}\n" for ex in examples
    )
    prompt = (
        "Task: Convert the given sentence (Hinglish or English) into simple, natural, "
        "spoken Hindi written in Devanagari script. Use conversational phrasing (not overly formal). "
        "Preserve named entities (names, places, acronyms) and punctuation. "
        "Return ONLY the Hindi sentence in Devanagari; do NOT return any explanations, transliteration, "
        "or meta text.\n\n"
        f"{example_text}\n"
        f"Input: {text}\n"
        "Hindi:"
    )
    

    payload = {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.1,
        "max_tokens": 250,
        "messages": [
            {"role": "system", "content": (
                    "You are a precise Hindi language expert translator. "
                    "Always respond with only the translated sentence in Devanagari Hindi. "
                    "Do not add commentary, transliteration, or extra lines."
                )},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return text
def hinglish_to_hindi_global(text):
    if text in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[text]

    result = restore_acronyms(
        hinglish_to_hindi(freeze_acronyms(text)[0]),
        freeze_acronyms(text)[1]
    )
    _TRANSLATION_CACHE[text] = result
    return result
