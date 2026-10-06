FROM python:3.12-slim

WORKDIR /app

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt

COPY relay ./relay
COPY server.py .

EXPOSE 8000

CMD ["python", "server.py"]