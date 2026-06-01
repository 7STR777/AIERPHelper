import pymupdf4llm
from pathlib import Path

md = pymupdf4llm.to_markdown(r"D:\erphelper\Back\convert_into_md\Подготовка производства (wiki).pdf")
Path(r"D:\erphelper\Back\convert_into_md\Подготовка производства (wiki).md").write_bytes(md.encode())