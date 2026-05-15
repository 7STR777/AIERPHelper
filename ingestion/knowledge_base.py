import json
import hashlib
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

class KnowledgeBaseManager:
    """Управляет chunks.json с поддержкой дедупликации"""
    
    def __init__(self, chunks_path: str = "chunks.json"):
        self.chunks_path = Path(chunks_path)
        self.chunks = self._load()
        
    def _load(self) -> List[Dict]:
        """Загружает существующие чанки"""
        if self.chunks_path.exists():
            with open(self.chunks_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _compute_hash(self, text: str) -> str:
        """Вычисляет хэш текста для дедупликации"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]
    
    def find_new_chunks(self, new_chunks: List[Dict]) -> List[Dict]:
        """Возвращает только уникальные чанки"""
        existing_hashes = {self._compute_hash(c["text"]) for c in self.chunks}
        
        unique_chunks = []
        for chunk in new_chunks:
            chunk_hash = self._compute_hash(chunk["text"])
            if chunk_hash not in existing_hashes:
                chunk["hash"] = chunk_hash
                chunk["created_at"] = datetime.now().isoformat()
                unique_chunks.append(chunk)
        
        print(f"[kb] found {len(unique_chunks)} new chunks out of {len(new_chunks)}")
        return unique_chunks
    
    def add_chunks(self, chunks: List[Dict]) -> int:
        """Добавляет новые чанки в базу знаний"""
        new_chunks = self.find_new_chunks(chunks)
        
        if new_chunks:
            self.chunks.extend(new_chunks)
            self._save()
            print(f"[kb] added {len(new_chunks)} chunks to knowledge base")
        
        return len(new_chunks)
    
    def _save(self):
        """Сохраняет обновлённые чанки"""
        with open(self.chunks_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
    
    def get_all_chunks(self) -> List[Dict]:
        """Возвращает все чанки"""
        return self.chunks
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику по базе знаний"""
        return {
            "total_chunks": len(self.chunks),
            "sources": list(set(c.get("source", "unknown") for c in self.chunks)),
            "avg_chunk_size": sum(len(c["text"]) for c in self.chunks) // len(self.chunks) if self.chunks else 0,
            "last_updated": datetime.fromtimestamp(self.chunks_path.stat().st_mtime).isoformat() if self.chunks_path.exists() else None
        }