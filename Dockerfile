FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY data/vault ./data/vault
ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "notesqa"]
