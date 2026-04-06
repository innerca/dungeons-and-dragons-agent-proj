"""Text chunker for splitting novel sections into embedding-sized chunks.

Splits text by paragraph boundaries first, then by sentence boundaries,
maintaining overlap between chunks for context continuity.
"""

import re


def chunk_section(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """Split a section's text into chunks suitable for embedding.

    Strategy:
    1. If text is short enough, return as single chunk
    2. Split by paragraph boundaries (double newline)
    3. Greedily merge paragraphs up to max_chars
    4. For oversized paragraphs, split by sentence boundaries
    5. Maintain overlap between consecutive chunks

    Args:
        text: The section text to chunk.
        max_chars: Maximum characters per chunk (target ~800, Chinese 1 char ≈ 1-1.5 tokens).
        overlap: Characters of overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    # Split into paragraphs (by blank lines)
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [text]

    # Split oversized paragraphs by sentences
    split_paragraphs = []
    for para in paragraphs:
        if len(para) <= max_chars:
            split_paragraphs.append(para)
        else:
            # Split by sentence-ending punctuation
            sentences = re.split(r"(?<=[。！？」）\)\.])\s*", para)
            sentences = [s.strip() for s in sentences if s.strip()]
            split_paragraphs.extend(sentences)

    # Greedily merge into chunks
    chunks = []
    current = ""

    for para in split_paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If single paragraph exceeds max, force-split it
            if len(para) > max_chars:
                forced = _force_split(para, max_chars)
                chunks.extend(forced[:-1])
                current = forced[-1] if forced else ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply overlap between chunks
    if overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, overlap)

    # Filter out tiny chunks (merge into previous)
    min_chars = 200
    merged = []
    for chunk in chunks:
        if merged and len(chunk) < min_chars:
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)

    return merged


def _force_split(text: str, max_chars: int) -> list[str]:
    """Force-split a long text that has no good split points."""
    # Try splitting by single newlines first
    lines = text.split("\n")
    chunks = []
    current = ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = line
    if current:
        chunks.append(current)

    # If still oversized, hard split by character
    result = []
    for chunk in chunks:
        while len(chunk) > max_chars:
            # Find a good split point (sentence boundary)
            split_pos = max_chars
            for punct in ["。", "！", "？", "」", "）", ".", "\n"]:
                pos = chunk.rfind(punct, 0, max_chars)
                if pos > max_chars // 2:
                    split_pos = pos + 1
                    break
            result.append(chunk[:split_pos].strip())
            chunk = chunk[split_pos:].strip()
        if chunk:
            result.append(chunk)

    return result


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Add overlap text from previous chunk to the beginning of next chunk."""
    if len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        # Take the last `overlap` characters from previous chunk
        overlap_text = prev[-overlap:] if len(prev) > overlap else prev
        # Find a clean break point (start of a sentence or paragraph)
        clean_start = 0
        for j, ch in enumerate(overlap_text):
            if ch in "。！？\n":
                clean_start = j + 1
                break
        overlap_text = overlap_text[clean_start:]
        if overlap_text:
            result.append(overlap_text.strip() + "\n\n" + chunks[i])
        else:
            result.append(chunks[i])

    return result
