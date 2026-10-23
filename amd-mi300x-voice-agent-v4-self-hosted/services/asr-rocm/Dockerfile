FROM rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.10.0

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    openai-whisper

COPY main.py /app/main.py

ENV WHISPER_MODEL=small
ENV PYTHONUNBUFFERED=1

EXPOSE 9000

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
