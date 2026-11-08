import os
import re
import glob
from pathlib import Path
from typing import Optional, Any
import httpx
from src.config import get_settings

settings = get_settings()

CHROMA_DIR = os.getenv("CHROMA_DIR", "/app/knowledge_base/chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "/app/knowledge_base/docs")
COLLECTION_NAME = "abvos_knowledge"
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


def _get_persistent_client():
    import chromadb
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_chroma_collection():
    client = _get_persistent_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


async def generate_embedding_async(text: str) -> list[float]:
    """Gera embeddings de 3072 floats via Google GenAI v1beta usando httpx resiliente."""
    key = settings.GEMINI_API_KEY
    if not key:
        return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={key}"
    payload = {"content": {"parts": [{"text": text[:2048]}]}}

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, json=payload)
        if res.status_code == 200:
            return res.json().get("embedding", {}).get("values", [])
        return []


def chunk_markdown_file(file_path: str) -> list[dict[str, Any]]:
    """Divide um arquivo Markdown em chunks lógicos por seções (cabeçalhos # ou ##)."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    filename = Path(file_path).name
    sections = re.split(r"(^#{1,3}\s+.*$)", content, flags=re.MULTILINE)

    chunks = []
    current_heading = filename
    buffer = ""

    for item in sections:
        item_strip = item.strip()
        if not item_strip:
            continue
        if item.startswith("#"):
            if buffer.strip():
                chunks.append({
                    "title": current_heading,
                    "text": buffer.strip(),
                    "source": filename,
                })
                buffer = ""
            current_heading = item_strip.lstrip("#").strip()
        else:
            buffer += "\n" + item_strip

    if buffer.strip():
        chunks.append({
            "title": current_heading,
            "text": buffer.strip(),
            "source": filename,
        })

    return chunks


async def index_all_knowledge(force: bool = False) -> dict[str, Any]:
    """Indexa ou re-indexa todos os arquivos Markdown na base vetorial ChromaDB."""
    collection = get_chroma_collection()

    if force:
        # Limpa dados existentes
        existing_ids = collection.get().get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)

    files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    indexed_count = 0
    total_chunks = 0

    for file_path in files:
        chunks = chunk_markdown_file(file_path)
        for idx, chunk in enumerate(chunks):
            doc_id = f"{chunk['source']}__chunk_{idx}"
            full_text = f"Fonte: {chunk['source']} | Tópico: {chunk['title']}\n{chunk['text']}"

            # Gera embedding usando Google GenAI
            embedding = await generate_embedding_async(full_text)
            if not embedding:
                continue

            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[full_text],
                metadatas=[{
                    "source": chunk["source"],
                    "title": chunk["title"],
                }]
            )
            total_chunks += 1
        indexed_count += 1

    return {
        "status": "success",
        "files_processed": indexed_count,
        "chunks_indexed": total_chunks,
        "collection_count": collection.count(),
    }


async def search_knowledge(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Busca trechos semanticamente relevantes na base de conhecimento."""
    collection = get_chroma_collection()
    if collection.count() == 0:
        # Se a base estiver vazia, tenta auto-indexação rápida
        await index_all_knowledge(force=False)

    if collection.count() == 0:
        return []

    query_embedding = await generate_embedding_async(query)
    if not query_embedding:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(limit, collection.count()),
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        output.append({
            "content": doc,
            "source": meta.get("source", "unknown"),
            "title": meta.get("title", ""),
            "distance": float(dist) if dist is not None else 1.0,
        })

    return output


def get_knowledge_stats() -> dict[str, Any]:
    """Retorna estatísticas da base vetorial."""
    try:
        collection = get_chroma_collection()
        count = collection.count()
        files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
        return {
            "status": "ready",
            "indexed_chunks": count,
            "document_files_count": len(files),
            "chroma_dir": CHROMA_DIR,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "indexed_chunks": 0,
        }

