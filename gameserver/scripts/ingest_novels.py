"""Ingest SAO Progressive novels into ChromaDB.

Main entry point: parses all 8 novels, chunks them, and stores in ChromaDB
with structured metadata (volume, story, section) and game-world annotations
(Aincrad layer, in-game date).

Usage:
    cd gameserver && uv run python -m scripts.ingest_novels
"""

import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from scripts.novel_parser import parse_all_novels, VOLUME_CONFIG
from scripts.text_chunker import chunk_section

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSET_DIR = PROJECT_ROOT / "asset"
CHROMADB_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"
COLLECTION_NAME = "sao_progressive_novels"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
BATCH_SIZE = 100


def main():
    print("=" * 60)
    print("SAO Progressive Novel Ingestion")
    print("=" * 60)

    # 1. Parse all novels
    print("\n[1/3] Parsing novels...")
    sections = parse_all_novels(ASSET_DIR)
    if not sections:
        print("ERROR: No sections parsed. Check asset/sao/ directory.")
        sys.exit(1)

    # 2. Chunk sections
    print("\n[2/3] Chunking sections...")
    all_ids = []
    all_documents = []
    all_metadatas = []

    volume_stats: dict[int, dict] = {}
    for section in sections:
        chunks = chunk_section(section.text)
        total_chunks = len(chunks)

        if section.volume not in volume_stats:
            volume_stats[section.volume] = {"sections": 0, "chunks": 0}
        volume_stats[section.volume]["sections"] += 1
        volume_stats[section.volume]["chunks"] += total_chunks

        for chunk_idx, chunk_text in enumerate(chunks):
            doc_id = f"vol{section.volume}_s{section.section_number}_c{chunk_idx}"
            # Handle duplicate IDs for volumes with multiple stories
            if doc_id in all_ids:
                doc_id = f"vol{section.volume}_{section.story_title[:4]}_s{section.section_number}_c{chunk_idx}"

            metadata = {
                # Basic structure annotations
                "volume": section.volume,
                "story_title": section.story_title,
                "section_number": section.section_number,
                "chunk_index": chunk_idx,
                "total_chunks_in_section": total_chunks,
                "source_file": section.source_file,
                # Game world annotations
                "aincrad_layer": section.aincrad_layer,
                "in_game_date": section.in_game_date,
            }

            all_ids.append(doc_id)
            all_documents.append(chunk_text)
            all_metadatas.append(metadata)

    print(f"  Total chunks: {len(all_documents)}")
    print("\n  Per-volume stats:")
    for vol in sorted(volume_stats.keys()):
        stats = volume_stats[vol]
        vol_cfg = next(c for c in VOLUME_CONFIG if c["volume"] == vol)
        story_names = ", ".join(s["title"] for s in vol_cfg["stories"])
        print(f"    Vol {vol}: {stats['sections']} sections, {stats['chunks']} chunks ({story_names})")

    # 3. Store in ChromaDB
    print(f"\n[3/3] Storing in ChromaDB at {CHROMADB_DIR}...")
    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))

    # Delete existing collection for idempotency
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
    )

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "SAO Progressive novels 1-8, chunked by chapter and text size"},
    )

    # Batch insert
    total = len(all_documents)
    for i in range(0, total, BATCH_SIZE):
        end = min(i + BATCH_SIZE, total)
        collection.add(
            ids=all_ids[i:end],
            documents=all_documents[i:end],
            metadatas=all_metadatas[i:end],
        )
        print(f"  Inserted {end}/{total} chunks...")

    print(f"\nDone! Collection '{COLLECTION_NAME}' now has {collection.count()} documents.")
    print(f"ChromaDB data stored at: {CHROMADB_DIR}")


if __name__ == "__main__":
    main()
