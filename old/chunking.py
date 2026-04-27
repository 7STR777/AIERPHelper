from unstructured.partition.pdf import partition_pdf
import json

elements = partition_pdf(r"D:\ragproject\Подготовка производства без изображений.md")

chunks = []
chunk_id = 1

for el in elements:
    text = el.text.strip()
    if not text:
        continue

    chunk_type = str(type(el))

    if "Title" in chunk_type:
        section = text
        continue

    elif "ListItem" in chunk_type:
        chunks.append({
            "id": f"chunk_{chunk_id:03}",
            "section": section,
            "type": "list_item",
            "text": text
        })

    else:
        chunks.append({
            "id": f"chunk_{chunk_id:03}",
            "section": section,
            "type": "paragraph",
            "text": text
        })

    chunk_id += 1

with open("good_chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)