# ingest_docx_groq.py (MEMORY SAFE)
import re, json
from zipfile import ZipFile
from pathlib import Path
import argparse

def extract_text_stream(docx_path):
    with ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    for match in re.finditer(r"<w:t[^>]*>(.*?)</w:t>", xml, re.DOTALL):
        text = match.group(1).strip()
        if text:
            yield re.sub(r"\s+", " ", text)

def main(docx_path, out_dir="rag_data", chunk_size=400, overlap=80):
    Path(out_dir).mkdir(exist_ok=True)

    out_file = Path(out_dir) / "chunks.json"
    chunk_id = 0
    buffer = ""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write('{"chunks":[\n')

        first = True
        for piece in extract_text_stream(docx_path):
            buffer += " " + piece

            while len(buffer) >= chunk_size:
                chunk = buffer[:chunk_size]
                buffer = buffer[chunk_size - overlap:]

                record = {"id": chunk_id, "text": chunk}
                if not first:
                    f.write(",\n")
                json.dump(record, f, ensure_ascii=False)

                first = False
                chunk_id += 1

        f.write("\n]}")

    print(f"✅ Done. Created {chunk_id} chunks safely.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", nargs="?", default="Training data for CSE.docx")
    parser.add_argument("--out", default="rag_data")
    parser.add_argument("--chunk", type=int, default=400)
    parser.add_argument("--overlap", type=int, default=80)
    args = parser.parse_args()

    main(args.docx, args.out, args.chunk, args.overlap)
