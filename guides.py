"""RAG part: download Wikivoyage travel guides, split them, and search them."""

import httpx
import re


def fetch_guide(city):
    """Download the Wikivoyage guide for a city as plain text.

    Returns the text, or None if there is no guide with that name.
    """
    response = httpx.get(
        "https://en.wikivoyage.org/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",       # get the article's content...
            "explaintext": 1,         # ...as plain text, not HTML
            "titles": city,
            "redirects": 1,           # follow redirects, e.g. "NYC" → "New York City"
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": "travel-planner-agent/0.1 (student project)"},
        timeout=20,
    )
    response.raise_for_status()
    page = response.json()["query"]["pages"][0]
    if page.get("missing"):
        return None
    return page["extract"]

# Matches heading lines like "== Eat ==" or "=== Budget ==="
HEADING = re.compile(r"^(=+)\s*(.+?)\s*=+$")


def split_sections(text):
    """Split a guide into sections using its == headings ==.

    Returns a list of {"section": "Eat > Budget", "text": "..."}; empty sections are skipped.
    """
    sections = []
    main = "Introduction"   # current main section (== ... ==)
    title = main            # full label for the current section
    lines = []              # lines collected for the current section

    for line in text.splitlines():
        match = HEADING.match(line.strip())
        if match:
            # A new heading: save the section we were collecting (if it has text)
            body = "\n".join(lines).strip()
            if body:
                sections.append({"section": title, "text": body})
            lines = []

            level = len(match.group(1))   # number of "=" signs
            name = match.group(2)         # the heading text, e.g. "Eat"
            if level == 2:
                main = name
                title = name
            else:
                title = f"{main} > {name}"
        else:
            lines.append(line)

    # Save the last section (there's no heading after it to trigger the save)
    body = "\n".join(lines).strip()
    if body:
        sections.append({"section": title, "text": body})
    return sections


def make_chunks(city, max_chars=1200):
    """Download a city's guide and turn it into search-sized chunks.

    Long sections are split at paragraph breaks so no chunk is much longer
    than max_chars. Each chunk keeps its city and section label for citations.
    """
    text = fetch_guide(city)
    if text is None:
        return []

    chunks = []
    for section in split_sections(text):
        piece = ""
        for paragraph in section["text"].split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            # If adding this paragraph would make the piece too long, save the piece first
            if piece and len(piece) + len(paragraph) > max_chars:
                chunks.append({"city": city, "section": section["section"], "text": piece})
                piece = ""
            piece = f"{piece}\n{paragraph}" if piece else paragraph
        if piece:
            chunks.append({"city": city, "section": section["section"], "text": piece})
    return chunks

if __name__ == "__main__":
    chunks = make_chunks("Melbourne")
    print("Chunks:", len(chunks))
    print("Longest:", max(len(c["text"]) for c in chunks), "chars")
    print()
    print(chunks[20])