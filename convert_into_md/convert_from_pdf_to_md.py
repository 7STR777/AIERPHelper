import pymupdf4llm
from pathlib import Path

md = pymupdf4llm.to_markdown("D:\\ragproject\\convert_into_md\\Подготовка производства (wiki).pdf")
Path("D:\\ragproject\\convert_into_md\\output.md").write_bytes(md.encode())