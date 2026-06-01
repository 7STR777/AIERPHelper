import fitz  # PyMuPDF
from typing import Optional

class PDFProcessor:
    """Извлекает текст из PDF с сохранением структуры"""
    
    @staticmethod
    def extract_text(pdf_path: str) -> Optional[str]:
        """Извлекает текст со структурой страниц и абзацев"""
        try:
            doc = fitz.open(pdf_path)
            full_text = []
            
            for page_num, page in enumerate(doc, 1):
                # Извлекаем текст с позициями блоков
                blocks = page.get_text("blocks")
                page_text = []
                
                for block in blocks:
                    text = block[4].strip()
                    if len(text) > 20:  # Игнорируем короткие строки
                        page_text.append(text)
                
                if page_text:
                    full_text.append(f"\n{'='*60}\nСтраница {page_num}\n{'='*60}\n")
                    full_text.append("\n\n".join(page_text))
            
            doc.close()
            return "\n".join(full_text)
        
        except Exception as e:
            print(f"[pdf] error extracting text: {e}")
            return None
    
    @staticmethod
    def extract_metadata(pdf_path: str) -> dict:
        """Извлекает метаданные PDF"""
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            doc.close()
            return {
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "pages": len(doc),
                "file_size": Path(pdf_path).stat().st_size
            }
        except Exception as e:
            print(f"[pdf] error extracting metadata: {e}")
            return {}