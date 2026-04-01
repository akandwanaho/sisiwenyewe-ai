from pathlib import Path
import json
import re
import faiss
import numpy as np

ONEDRIVE_FOLDER = Path.home() / "Library/CloudStorage/OneDrive-Personal/CBRN_AI_Model/DOCUMENTATION/Deployment_Guides/extra data for the ai"
INDEX_DIR = Path(__file__).parent / "rag_store"
INDEX_DIR.mkdir(exist_ok=True)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
CHUNK_SIZE = 900
CHUNK_OVERLAP = 180


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()

    try:
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            import fitz
            text_parts = []
            with fitz.open(path) as doc:
                for i in range(len(doc)):
                    page_text = doc[i].get_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
            return "\n".join(text_parts)

        if suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)

    except Exception as e:
        print(f"Could not read {path.name}: {e}")
        return ""

    return ""


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()

        if len(chunk) > 120:
            chunks.append(chunk)

        if end == text_len:
            break

        start = end - overlap

    return chunks


def load_documents():
    docs = []

    if not ONEDRIVE_FOLDER.exists():
        raise FileNotFoundError(f"OneDrive folder not found: {ONEDRIVE_FOLDER}")

    for file_path in ONEDRIVE_FOLDER.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        print(f"Reading: {file_path.name}")
        raw_text = extract_text_from_file(file_path)
        if not raw_text:
            continue

        cleaned = clean_text(raw_text)
        if not cleaned:
            continue

        chunks = chunk_text(cleaned)

        for i, chunk in enumerate(chunks):
            docs.append({
                "id": f"{file_path.stem}_{i}",
                "file": file_path.name,
                "path": str(file_path),
                "chunk_index": i,
                "text": chunk
            })

    return docs


def build_index():
    from sentence_transformers import SentenceTransformer

    docs = load_documents()
    if not docs:
        raise ValueError("No documents/chunks found to index.")

    print(f"Loaded {len(docs)} chunks.")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    texts = [d["text"] for d in docs]
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, str(INDEX_DIR / "cbrn.index"))

    with open(INDEX_DIR / "documents.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print("Index built successfully.")
    print(f"Saved to: {INDEX_DIR}")


if __name__ == "__main__":
    print("Starting indexing...")
    print(f"Reading from: {ONEDRIVE_FOLDER}")
    build_index()