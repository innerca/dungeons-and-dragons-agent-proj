#!/usr/bin/env python3
"""Convert EPUB files in asset/ directory to txt format."""

import os
import glob
import tempfile
import zipfile
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def clean_text(raw_text):
    """Clean up excessive blank lines from extracted text."""
    lines = raw_text.split("\n")
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if not prev_blank:
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(stripped)
            prev_blank = False
    return "\n".join(cleaned_lines)


def epub_to_text_ebooklib(epub_path):
    """Extract text using ebooklib (preferred)."""
    book = epub.read_epub(epub_path, options={"ignore_ncx": True})
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            chapters.append(clean_text(text))
    return "\n\n".join(chapters)


def epub_to_text_fallback(epub_path):
    """Extract text by directly reading HTML files from the EPUB zip (fallback for corrupted EPUBs)."""
    chapters = []
    with zipfile.ZipFile(epub_path, "r") as zf:
        for name in sorted(zf.namelist()):
            if name.lower().endswith((".xhtml", ".html", ".htm")):
                try:
                    data = zf.read(name)
                    soup = BeautifulSoup(data, "html.parser")
                    text = soup.get_text(separator="\n")
                    cleaned = clean_text(text)
                    if cleaned.strip():
                        chapters.append(cleaned)
                except Exception:
                    print(f"    Skipping unreadable entry: {name}")
    return "\n\n".join(chapters)


def epub_to_text(epub_path):
    """Extract text content from an EPUB file."""
    try:
        return epub_to_text_ebooklib(epub_path)
    except Exception:
        print("    ebooklib failed, using fallback zip extraction...")
        return epub_to_text_fallback(epub_path)


def main():
    asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asset")
    # Recursively find all epub files in asset/ directory
    epub_files = glob.glob(os.path.join(asset_dir, "**", "*.epub"), recursive=True)

    if not epub_files:
        print("No EPUB files found in asset/ directory.")
        return

    print(f"Found {len(epub_files)} EPUB file(s).")

    for epub_path in sorted(epub_files):
        basename = os.path.splitext(os.path.basename(epub_path))[0]
        # Clean up filename for output
        txt_filename = basename + ".txt"
        # Output txt file in the same directory as the epub file
        txt_path = os.path.join(os.path.dirname(epub_path), txt_filename)

        print(f"Converting: {epub_path} -> {txt_filename}")
        try:
            text = epub_to_text(epub_path)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  Done. Output size: {len(text)} chars")
        except Exception as e:
            print(f"  Error: {e}")

    print("\nAll conversions complete.")


if __name__ == "__main__":
    main()
