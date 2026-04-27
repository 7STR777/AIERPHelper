from llama_cpp import Llama
from pathlib import Path

print("=" * 70)
print("🔍 ТЕСТ GIGACHAT МОДЕЛИ")
print("=" * 70)

# Ваш полный путь к модели
model_path = r"D:\ragproject\rag_test\models\mistral-7b-instruct-v0.3-q4_k_m.gguf"

# Проверяем существование файла
if not Path(model_path).exists():
    print(f"❌ Файл не найден: {model_path}")
    exit(1)

print(f"\n📦 Модель: {Path(model_path).name}")
print(f"📏 Размер: {Path(model_path).stat().st_size / (1024**3):.1f} GB")
print()

print("🔄 Загрузка модели на GPU...")
print("(Если ошибка, попробуем CPU режим)")
print("-" * 50)

try:
    # Пробуем с GPU
    print("1. Пробуем GPU режим (n_gpu_layers=-1)...")
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=8,
        n_gpu_layers=-1,
        n_batch=256,
        verbose=True
    )
    print("\n✅ Модель загружена на GPU!")
    
except Exception as e:
    print(f"\n⚠️ GPU режим не удался: {e}")
    
    try:
        # Пробуем с CPU
        print("\n2. Пробуем CPU режим (n_gpu_layers=0)...")
        llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=8,
            n_gpu_layers=0,
            n_batch=256,
            verbose=True
        )
        print("\n✅ Модель загружена на CPU!")
        
    except Exception as e2:
        print(f"\n❌ Ошибка загрузки: {e2}")
        print("\nМодель не поддерживается текущей версией llama-cpp-python")
        exit(1)

# Тест генерации
print("\n" + "=" * 70)
print("🔄 ТЕСТ ГЕНЕРАЦИИ")
print("=" * 70)

try:
    response = llm(
        "Ответь 'Привет!' одним словом",
        max_tokens=10,
        temperature=0
    )
    print(f"✅ Ответ: {response['choices'][0]['text']}")
    print("\n🎉 Модель работает!")
    
except Exception as e:
    print(f"❌ Ошибка генерации: {e}")