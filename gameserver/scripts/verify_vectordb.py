"""Verify ChromaDB ingestion results.

Connects to the ChromaDB instance and runs diagnostics:
- Total document count
- Per-volume statistics
- Sample semantic queries
- Metadata completeness check

Usage:
    cd gameserver && uv run python -m scripts.verify_vectordb
"""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMADB_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"
COLLECTION_NAME = "sao_progressive_novels"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


def main():
    print("=" * 60)
    print("ChromaDB Verification Report")
    print("=" * 60)

    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
    )

    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
    except Exception as e:
        print(f"ERROR: Collection '{COLLECTION_NAME}' not found: {e}")
        print("Run 'make ingest-novels' first.")
        return

    total = collection.count()
    print(f"\nTotal documents: {total}")

    # Per-volume stats
    print("\n--- Per-Volume Statistics ---")
    for vol in range(1, 9):
        result = collection.get(
            where={"volume": vol},
            include=["metadatas"],
        )
        count = len(result["ids"])
        if count > 0:
            stories = set(m["story_title"] for m in result["metadatas"])
            sections = set(m["section_number"] for m in result["metadatas"])
            layers = set(m["aincrad_layer"] for m in result["metadatas"])
            print(f"  Vol {vol}: {count} chunks | "
                  f"sections: {sorted(sections)} | "
                  f"layer: {layers} | "
                  f"stories: {stories}")

    # Sample semantic queries
    print("\n--- Sample Semantic Queries ---")
    queries = [
        "桐人第一次见到亚丝娜",
        "黑暗精灵骑士基滋梅尔",
        "怪物斗技场赌博",
    ]
    for query in queries:
        print(f"\n  Query: \"{query}\"")
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            preview = doc[:80].replace("\n", " ") + "..."
            print(f"    [{i+1}] dist={dist:.4f} | vol={meta['volume']} "
                  f"s{meta['section_number']}c{meta['chunk_index']} "
                  f"| {meta['story_title']}")
            print(f"        {preview}")

    # Metadata completeness
    print("\n--- Metadata Completeness ---")
    sample = collection.get(
        limit=min(50, total),
        include=["metadatas"],
    )
    required_fields = ["volume", "story_title", "section_number", "chunk_index",
                       "total_chunks_in_section", "source_file", "aincrad_layer", "in_game_date"]
    int_fields = {"volume", "section_number", "chunk_index", "total_chunks_in_section", "aincrad_layer"}
    missing = {f: 0 for f in required_fields}
    for meta in sample["metadatas"]:
        for field in required_fields:
            if field not in meta:
                missing[field] += 1
            elif field in int_fields:
                if meta[field] is None:
                    missing[field] += 1
            else:
                if meta[field] in (None, ""):
                    missing[field] += 1

    total_checked = len(sample["metadatas"])
    print(f"  Checked {total_checked} documents:")
    for field, count in missing.items():
        status = "OK" if count == 0 else f"MISSING in {count}/{total_checked}"
        print(f"    {field}: {status}")

    print(f"\nVerification complete.")


if __name__ == "__main__":
    main()
