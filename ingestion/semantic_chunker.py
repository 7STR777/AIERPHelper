import re
import json
import uuid
from pathlib import Path

# ==========================================================
# CONFIG
# ==========================================================
INPUT_FILE = "Подготовка производства.md"
OUTPUT_FILE = "chunks_output_v2.json"

MAX_TOKENS = 420          # безопасный размер чанка
MIN_TOKENS = 80
OVERLAP_SENTENCES = 1

# ==========================================================
# HELPERS
# ==========================================================

def estimate_tokens(text: str) -> int:
    # грубо: 1 токен ~ 0.75 слова
    words = text.split()
    return int(len(words) * 1.3)


def clean_text(text: str) -> str:
    """
    Очистка markdown мусора
    """

    # удалить ссылки markdown [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # удалить mk:@MSITStore мусор
    text = re.sub(r'mk:@MSITStore:[^\s)]+', '', text)

    # удалить изображения
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'images\/[^\s)]+', '', text)

    # удалить html anchor
    text = re.sub(r'<a name=.*?</a>', '', text)

    # убрать мусорные slash continuation
    text = text.replace("\\", " ")

    # лишние пробелы
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def remove_ui_noise(text: str) -> str:
    """
    Удаляем UI инструкции
    """
    bad_patterns = [
        r'нажмите клавишу .*',
        r'щелкните мышкой .*',
        r'пиктограмм.*',
        r'клавишу <.*?>',
        r'нажать <.*?>',
        r'Alt',
        r'Esc',
        r'F\d+',
    ]

    lines = text.splitlines()
    clean_lines = []

    for line in lines:
        skip = False
        for p in bad_patterns:
            if re.search(p, line, re.IGNORECASE):
                skip = True
                break
        if not skip:
            clean_lines.append(line)

    return "\n".join(clean_lines)


def split_sentences(text: str):
    sents = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sents if s.strip()]


# ==========================================================
# PARSE HEADERS
# ==========================================================

def parse_sections(md_text: str):
    """
    Делим по # ## ###
    """
    lines = md_text.splitlines()

    sections = []
    current = {
        "h1": "",
        "h2": "",
        "h3": "",
        "content": []
    }

    for line in lines:
        if line.startswith("# "):
            if current["content"]:
                sections.append(current)

            current = {
                "h1": line[2:].strip(),
                "h2": "",
                "h3": "",
                "content": []
            }

        elif line.startswith("## "):
            if current["content"]:
                sections.append(current)

            current = {
                "h1": current["h1"],
                "h2": line[3:].strip(),
                "h3": "",
                "content": []
            }

        elif line.startswith("### "):
            if current["content"]:
                sections.append(current)

            current = {
                "h1": current["h1"],
                "h2": current["h2"],
                "h3": line[4:].strip(),
                "content": []
            }

        else:
            current["content"].append(line)

    if current["content"]:
        sections.append(current)

    return sections


# ==========================================================
# CHUNKING
# ==========================================================

def chunk_text(section):
    text = "\n".join(section["content"]).strip()

    if not text:
        return []

    text = clean_text(text)
    text = remove_ui_noise(text)

    sentences = split_sentences(text)

    chunks = []
    current = []

    for sent in sentences:
        test = " ".join(current + [sent])

        if estimate_tokens(test) > MAX_TOKENS:
            if current:
                chunks.append(" ".join(current))

                # overlap
                current = current[-OVERLAP_SENTENCES:]
                current.append(sent)
            else:
                chunks.append(sent)
                current = []
        else:
            current.append(sent)

    if current:
        chunks.append(" ".join(current))

    # фильтр мелких
    final_chunks = []
    for c in chunks:
        if estimate_tokens(c) >= MIN_TOKENS:
            final_chunks.append(c)

    return final_chunks


# ==========================================================
# GLOSSARY EXTRACTION
# ==========================================================

def extract_glossary(md_text):
    glossary = []

    pattern = r'\*\*(.*?)\*\*\s*-\s*(.*)'
    matches = re.findall(pattern, md_text)

    for term, desc in matches:
        if len(term) < 50:
            glossary.append({
                "id": str(uuid.uuid4()),
                "type": "glossary",
                "title": term.strip(),
                "text": desc.strip()
            })

    return glossary


# ==========================================================
# MAIN
# ==========================================================

def build_chunks():
    md = Path(INPUT_FILE).read_text(encoding="utf-8")

    sections = parse_sections(md)

    all_chunks = []
    idx = 1

    for sec in sections:
        chunks = chunk_text(sec)

        for c in chunks:
            title_parts = [sec["h1"], sec["h2"], sec["h3"]]
            title = " / ".join([x for x in title_parts if x])

            all_chunks.append({
                "id": f"chunk_{idx:04}",
                "type": "content",
                "title": title,
                "section_h1": sec["h1"],
                "section_h2": sec["h2"],
                "section_h3": sec["h3"],
                "tokens": estimate_tokens(c),
                "text": c
            })

            idx += 1

    glossary = extract_glossary(md)

    all_chunks.extend(glossary)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print("Saved:", OUTPUT_FILE)
    print("Total chunks:", len(all_chunks))


if __name__ == "__main__":
    build_chunks()