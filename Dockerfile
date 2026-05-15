FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

WORKDIR /app

# =========================
# System dependencies
# =========================
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    cmake \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Python tooling (CRITICAL)
# =========================
RUN python3 -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN python3 -m pip install --no-cache-dir \
    rank-bm25==0.2.2

RUN python3 -m pip install --no-cache-dir \
    llama-cpp-python==0.3.21 \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124

# =========================
# App source
# =========================
COPY . .

# =========================
# Runtime config
# =========================
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]