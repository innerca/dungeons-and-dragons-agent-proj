"""SAO Progressive novel parser.

Parses 8 SAO Progressive TXT files into structured sections.
Uses a global-scan approach: finds all standalone number lines,
filters out TOC clusters, and treats the rest as content sections.
"""

import re
from dataclasses import dataclass
from pathlib import Path

# Chinese number to int mapping
CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def cn_to_int(cn: str) -> int:
    """Convert Chinese number string to int."""
    cn = cn.strip()
    if cn in CN_NUM:
        return CN_NUM[cn]
    if cn.startswith("十"):
        return 10 + CN_NUM.get(cn[1:], 0)
    if "十" in cn:
        parts = cn.split("十")
        tens = CN_NUM.get(parts[0], 0)
        ones = CN_NUM.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    return 0


@dataclass
class Section:
    """A parsed section from a novel."""
    volume: int
    story_title: str
    section_number: int
    text: str
    aincrad_layer: int = 0
    in_game_date: str = ""
    source_file: str = ""


# Per-volume configuration
VOLUME_CONFIG = [
    {
        "volume": 1,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][01](1).txt",
        "stories": [
            {"title": "无星夜的咏叹调", "default_layer": 1},
            {"title": "幻眬剑之回旋曲", "default_layer": 2},
        ],
        "section_format": "number",
    },
    {
        "volume": 2,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][02](1).txt",
        "stories": [{"title": "黑白协奏曲", "default_layer": 3}],
        "section_format": "title_number",
    },
    {
        "volume": 3,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][03](1).txt",
        "stories": [{"title": "泡影的船歌", "default_layer": 4}],
        "section_format": "number",
    },
    {
        "volume": 4,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][04](1).txt",
        "stories": [{"title": "阴沉薄暮的诙谐曲", "default_layer": 5}],
        "section_format": "number",
    },
    {
        "volume": 5,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][05](1).txt",
        "stories": [{"title": "黄金定律的卡农（上）", "default_layer": 6}],
        "section_format": "number",
    },
    {
        "volume": 6,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][06](1).txt",
        "stories": [{"title": "黄金定律的卡农（下）", "default_layer": 6}],
        "section_format": "number",
    },
    {
        "volume": 7,
        "file_pattern": "[台版][川原砾]][刀剑神域][进击篇-Progressive][07](1).txt",
        "stories": [{"title": "赤色焦热的狂想曲（上）", "default_layer": 7}],
        "section_format": "number",
    },
    {
        "volume": 8,
        "file_pattern": "SAO刀剑神域_Progressive_8(1).txt",
        "stories": [{"title": "赤色焦热的狂想曲（下）", "default_layer": 7}],
        "section_format": "number",
    },
]

# Metadata keywords that indicate a false-positive section (制作信息 area)
_METADATA_KEYWORDS = re.compile(r"录入|作者：|插画：|仅供个人学习|禁作商业|轻之国度|天使动漫")

LAYER_PATTERN = re.compile(r"艾恩葛朗特第(.+?)层")
DATE_PATTERN = re.compile(r"(二[〇○０]二[二三]年.+?月)")


def _find_all_number_lines(lines: list[str]) -> list[tuple[int, int]]:
    """Find all standalone number lines (1-2 digit numbers alone on a line)."""
    results = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^\d{1,2}$", stripped):
            results.append((i, int(stripped)))
    return results


def _filter_toc_clusters(number_lines: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Remove TOC clusters from number lines.

    TOC clusters: 3+ consecutive number lines where each gap is <= 4 lines.
    Content sections have large gaps (typically 50+ lines) between numbers.
    """
    if len(number_lines) <= 2:
        return number_lines

    # Build adjacency groups
    in_cluster = [False] * len(number_lines)
    i = 0
    while i < len(number_lines):
        j = i
        while (j + 1 < len(number_lines) and
               number_lines[j + 1][0] - number_lines[j][0] <= 3):
            j += 1

        cluster_size = j - i + 1
        if cluster_size >= 3:
            for k in range(i, j + 1):
                in_cluster[k] = True
        i = j + 1

    return [nl for nl, is_toc in zip(number_lines, in_cluster) if not is_toc]


def _find_title_number_sections(lines: list[str], story_title: str) -> list[tuple[int, int]]:
    """Find sections in 'title N' format (used by volume 2)."""
    pattern = re.compile(rf"^{re.escape(story_title)}\s+(\d+)$")
    results = []
    for i, line in enumerate(lines):
        m = pattern.match(line.strip())
        if m:
            results.append((i, int(m.group(1))))
    return results


def _extract_layer_and_date(lines: list[str], search_start: int, search_end: int) -> tuple[int, str]:
    """Extract Aincrad layer and in-game date from a range of lines."""
    layer = 0
    date = ""
    end = min(search_end, len(lines))
    for i in range(search_start, end):
        text = lines[i].strip()
        if not layer:
            m = LAYER_PATTERN.search(text)
            if m:
                layer = cn_to_int(m.group(1))
        if not date:
            m = DATE_PATTERN.search(text)
            if m:
                date = m.group(1)
        if layer and date:
            break
    return layer, date


def _assign_story_titles(markers: list[tuple[int, int]], stories: list[dict],
                         lines: list[str]) -> dict[int, str]:
    """Map marker line index -> story title.

    For multi-story volumes (vol 1), detect story boundaries by looking for
    story title lines that are followed by a layer marker or section number.
    For single-story volumes, all sections get the same title.
    """
    result: dict[int, str] = {}

    if len(stories) == 1:
        title = stories[0]["title"]
        for line_idx, _ in markers:
            result[line_idx] = title
        return result

    # Multi-story: find content-start boundaries for each story
    all_titles = [s["title"] for s in stories]
    story_boundaries: list[tuple[int, str]] = []

    for title in all_titles:
        for i, line in enumerate(lines):
            if line.strip() == title:
                # Verify it's a content boundary (has layer marker or content nearby)
                for j in range(i + 1, min(i + 15, len(lines))):
                    stripped = lines[j].strip()
                    if LAYER_PATTERN.search(stripped) or len(stripped) > 30:
                        story_boundaries.append((i, title))
                        break

    story_boundaries.sort(key=lambda x: x[0])

    for line_idx, _ in markers:
        assigned = stories[0]["title"]
        for boundary_line, boundary_title in story_boundaries:
            if line_idx >= boundary_line:
                assigned = boundary_title
        result[line_idx] = assigned

    return result


def parse_novel(file_path: Path, volume_config: dict) -> list[Section]:
    """Parse a single novel TXT file into sections."""
    volume = volume_config["volume"]
    stories = volume_config["stories"]
    section_format = volume_config["section_format"]
    source_file = file_path.name

    text = file_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Step 1: Find all section markers
    if section_format == "title_number":
        markers = _find_title_number_sections(lines, stories[0]["title"])
    else:
        all_numbers = _find_all_number_lines(lines)
        markers = _filter_toc_clusters(all_numbers)

    if not markers:
        print(f"  WARNING: No section markers found in {source_file}")
        return []

    # Step 2: Assign story titles to each marker
    title_map = _assign_story_titles(markers, stories, lines)

    # Step 3: Extract text between consecutive markers, filter non-content
    sections: list[Section] = []
    for i, (marker_line, section_num) in enumerate(markers):
        text_start = marker_line + 1
        text_end = markers[i + 1][0] if i + 1 < len(markers) else len(lines)

        raw_lines = lines[text_start:text_end]
        section_text = "\n".join(raw_lines).strip()

        # Skip sections with very little actual content (false positives from
        # isolated numbers in metadata/afterword areas)
        content_lines = [l for l in raw_lines if len(l.strip()) > 10]
        if len(content_lines) < 3:
            continue

        # Skip metadata sections (制作信息, credits, etc.)
        # Only check the first 30 lines: real content starts with story text,
        # while false-positive sections are entirely metadata.
        head = raw_lines[:30]
        metadata_hits = sum(1 for l in head if _METADATA_KEYWORDS.search(l))
        if metadata_hits >= 2:
            continue

        sections.append(Section(
            volume=volume,
            story_title=title_map.get(marker_line, stories[0]["title"]),
            section_number=section_num,
            text=section_text,
            source_file=source_file,
        ))

    # Step 4: Extract layer and date per story group
    story_groups: dict[str, tuple[int, list[Section]]] = {}
    for idx, (marker_line, _) in enumerate(markers):
        for s in sections:
            if s.section_number == markers[idx][1] and s.story_title == title_map.get(marker_line):
                if s.story_title not in story_groups:
                    story_groups[s.story_title] = (marker_line, [])
                story_groups[s.story_title][1].append(s)
                break

    # Simpler approach: group by story_title, find layer/date near first section
    seen_titles: dict[str, int] = {}  # title -> first marker line
    for marker_line, _ in markers:
        title = title_map.get(marker_line, "")
        if title and title not in seen_titles:
            seen_titles[title] = marker_line

    # Build default_layer lookup from stories config
    default_layers: dict[str, int] = {}
    for s in stories:
        if "default_layer" in s:
            default_layers[s["title"]] = s["default_layer"]

    for title, first_line in seen_titles.items():
        search_start = max(0, first_line - 80)
        layer, date = _extract_layer_and_date(lines, search_start, first_line + 10)
        # Fall back to configured default_layer if auto-detection fails
        if not layer:
            layer = default_layers.get(title, 0)
        for s in sections:
            if s.story_title == title:
                s.aincrad_layer = layer
                s.in_game_date = date

    return sections


def parse_all_novels(asset_dir: Path) -> list[Section]:
    """Parse all 8 SAO Progressive novels from the asset/sao/ directory."""
    sao_dir = asset_dir / "sao"
    all_sections: list[Section] = []

    for config in VOLUME_CONFIG:
        file_path = sao_dir / config["file_pattern"]
        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            continue

        print(f"Parsing volume {config['volume']}: {file_path.name}")
        sections = parse_novel(file_path, config)
        print(f"  Found {len(sections)} sections")
        all_sections.extend(sections)

    print(f"\nTotal sections parsed: {len(all_sections)}")
    return all_sections
