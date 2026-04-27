import json
from vector_db import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer

# ============================================
# 1. ВСТАВИТЬ ВСЕ 96 ЧАНКОВ СЮДА
# Копируйте массив из предыдущего ответа (от chunk_001 до chunk_096)
# ============================================

# Если вы скопировали чанки в JSON файл, можно загрузить оттуда:
with open(r'C:\Users\igorm\OneDrive\Desktop\ragproject\chunks.json', 'r', encoding='utf-8') as f:
    ALL_CHUNKS_96 = json.load(f)

# ============================================
# 2. Подключение к Qdrant
# ============================================
client = QdrantClient(host="localhost", port=6333)
collection_name = "production_preparation_chunks_full"

# Проверяем, существует ли коллекция
collections = client.get_collections().collections
collection_names = [c.name for c in collections]

if collection_name not in collection_names:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE
        )
    )
    print(f"✅ Создана новая коллекция '{collection_name}'")
else:
    print(f"📁 Коллекция '{collection_name}' уже существует, очищаем...")
    client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE
        )
    )
    print(f"✅ Коллекция '{collection_name}' пересоздана")

# ============================================
# 3. Загрузка модели
# ============================================
print("🔄 Загрузка модели эмбеддингов...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Модель загружена")

# ============================================
# 4. Генерация и загрузка чанков
# ============================================
def prepare_text_for_embedding(chunk):
    """Формирует текст для эмбеддинга из всех метаданных"""
    parts = []
    if chunk.get('section'):
        parts.append(f"[Секция: {chunk['section']}]")
    if chunk.get('subsection'):
        parts.append(f"[Подсекция: {chunk['subsection']}]")
    if chunk.get('term'):
        parts.append(f"[Термин: {chunk['term']}]")
    if chunk.get('type'):
        parts.append(f"[Тип: {chunk['type']}]")
    parts.append(chunk.get('text', ''))
    return ' '.join(parts)

print(f"\n📊 Загрузка {len(ALL_CHUNKS_96)} чанков...")
print("-" * 50)

points = []
failed_chunks = []

for i, chunk in enumerate(ALL_CHUNKS_96):
    try:
        # Подготавливаем текст для эмбеддинга
        text_for_embedding = prepare_text_for_embedding(chunk)
        
        # Генерируем вектор
        vector = model.encode(text_for_embedding).tolist()
        
        # Создаем точку
        point = PointStruct(
            id=i,
            vector=vector,
            payload={
                "id": chunk.get("id", f"chunk_{i:03d}"),
                "section": chunk.get("section", ""),
                "subsection": chunk.get("subsection", ""),
                "type": chunk.get("type", ""),
                "term": chunk.get("term", ""),
                "text": chunk.get("text", ""),
                "items": chunk.get("items", []),
                "definition": chunk.get("definition", "")
            }
        )
        points.append(point)
        
        # Прогресс-бар
        if (i + 1) % 10 == 0:
            print(f"  Обработано {i+1}/{len(ALL_CHUNKS_96)} чанков")
            
    except Exception as e:
        failed_chunks.append((i, chunk.get('id', 'unknown'), str(e)))
        print(f"  ❌ Ошибка в чанке {i}: {e}")

# Загружаем пачками по 100 точек (Qdrant recommendation)
batch_size = 100
for i in range(0, len(points), batch_size):
    batch = points[i:i+batch_size]
    client.upsert(
        collection_name=collection_name,
        points=batch
    )
    print(f"  📤 Загружена пачка {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")

print(f"\n✅ Успешно загружено {len(points)} из {len(ALL_CHUNKS_96)} чанков")
if failed_chunks:
    print(f"⚠️ Не удалось загрузить {len(failed_chunks)} чанков:")
    for idx, chunk_id, error in failed_chunks[:5]:
        print(f"   - {chunk_id}: {error}")

# ============================================
# 5. Проверка загруженных данных
# ============================================
collection_info = client.get_collection(collection_name)
print(f"\n📊 Статистика коллекции '{collection_name}':")
print(f"   - Количество точек: {collection_info.points_count}")
print(f"   - Размерность: {collection_info.config.params.vectors.size}")
print(f"   - Метрика: {collection_info.config.params.vectors.distance}")

# ============================================
# 6. Функция поиска (исправленная)
# ============================================
def search(query, limit=5, collection=collection_name):
    """Поиск по коллекции"""
    query_vector = model.encode(query).tolist()
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_payload=True
    )
    return results.points

# ============================================
# 7. Тестовые запросы
# ============================================
print("\n" + "="*60)
print("🔍 ТЕСТОВЫЕ ПОИСКОВЫЕ ЗАПРОСЫ")
print("="*60)

test_queries = [
    "Как создать технологический процесс для детали?",
    "Что такое редакция спецификации?",
    "Какие типы ДСЕ бывают и чем они отличаются?",
    "Как настроить альтернативный техпроцесс?",
    "Что делать, если оборудование не отображается в списке?"
]

for query in test_queries:
    print(f"\n📝 {query}")
    print("-" * 50)
    results = search(query, limit=2)
    
    if results:
        for i, r in enumerate(results, 1):
            print(f"\n  {i}. (score: {r.score:.4f})")
            print(f"     📂 {r.payload.get('section', '')} / {r.payload.get('subsection', '')}")
            print(f"     📄 {r.payload['text'][:150]}...")
    else:
        print("  ⚠️ Результатов не найдено")

print("\n" + "="*60)
print("✅ ГОТОВО! RAG-система настроена.")
print(f"📚 Коллекция '{collection_name}' содержит {collection_info.points_count} векторизованных чанков")
print("💡 Теперь вы можете использовать функцию search() для запросов")