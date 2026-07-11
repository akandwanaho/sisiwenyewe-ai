from pathlib import Path
import json
import re
import shutil

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "source_documents" / "Blue_Book_2017.pdf"

RAG_DIR = BASE_DIR / "rag_store"
INDEX_PATH = RAG_DIR / "cbrn.index"
DOCUMENTS_PATH = RAG_DIR / "documents.json"

BACKUP_DIR = BASE_DIR / "rag_backup"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
SOURCE_NAME = "Blue_Book_2017.pdf"


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def extract_blue_book() -> list[dict]:
    reader = PdfReader(str(PDF_PATH))
    records = []
    chunk_index = 0

    print(f"Reading {PDF_PATH.name}")
    print(f"Pages: {len(reader.pages)}")

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = clean_text(page.extract_text() or "")
        except Exception as exc:
            print(f"Skipping page {page_number}: {exc}")
            continue

        if not page_text:
            continue

        for page_chunk_index, text in enumerate(chunk_text(page_text)):
            records.append({
                "file": SOURCE_NAME,
                "text": text,
                "chunk_index": chunk_index,
                "page": page_number,
                "page_chunk_index": page_chunk_index,
                "title": (
                    "Recommended Operating Procedures for Analysis "
                    "in the Verification of Chemical Disarmament"
                ),
                "edition": "2017",
                "publisher": "University of Helsinki"
            })
            chunk_index += 1

        if page_number % 50 == 0:
            print(f"Processed {page_number} pages")

    return records


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")

    if not DOCUMENTS_PATH.exists():
        raise FileNotFoundError(
            f"Documents metadata not found: {DOCUMENTS_PATH}"
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        INDEX_PATH,
        BACKUP_DIR / "cbrn_before_blue_book_append.index"
    )

    shutil.copy2(
        DOCUMENTS_PATH,
        BACKUP_DIR / "documents_before_blue_book_append.json"
    )

    index = faiss.read_index(str(INDEX_PATH))

    with open(DOCUMENTS_PATH, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print("Existing FAISS vectors:", index.ntotal)
    print("Existing document records:", len(documents))
    print("Index type:", type(index).__name__)
    print("Embedding dimension:", index.d)

    if index.ntotal != len(documents):
        raise RuntimeError(
            "FAISS index and documents.json are not aligned. "
            "Append operation cancelled."
        )

    already_indexed = any(
        doc.get("file") == SOURCE_NAME
        for doc in documents
    )

    if already_indexed:
        raise RuntimeError(
            f"{SOURCE_NAME} is already present in documents.json. "
            "Append operation cancelled to prevent duplication."
        )

    new_documents = extract_blue_book()

    if not new_documents:
        raise RuntimeError("No readable text was extracted from the PDF.")

    print("New Blue Book chunks:", len(new_documents))
    print("Loading embedding model...")

    embedder = SentenceTransformer(MODEL_NAME)

    new_texts = [doc["text"] for doc in new_documents]

    new_embeddings = embedder.encode(
        new_texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32
    ).astype(np.float32)

    if new_embeddings.shape[1] != index.d:
        raise RuntimeError(
            f"Embedding dimension mismatch. "
            f"Existing index: {index.d}, "
            f"new embeddings: {new_embeddings.shape[1]}"
        )

    index.add(new_embeddings)
    documents.extend(new_documents)

    if index.ntotal != len(documents):
        raise RuntimeError(
            "Index and document metadata became misaligned. "
            "Files have not been saved."
        )

    faiss.write_index(index, str(INDEX_PATH))

    with open(DOCUMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            documents,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Blue Book appended successfully.")
    print("Total FAISS vectors:", index.ntotal)
    print("Total document records:", len(documents))
    print("Blue Book chunks added:", len(new_documents))


if __name__ == "__main__":
    main()
