FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y gcc build-essential rustc cargo ffmpeg 

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]