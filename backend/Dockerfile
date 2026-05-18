FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    libgl1 \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# openai-whisper's setup.py imports pkg_resources, which setuptools>=81 dropped.
# Constrain setuptools in both the main env and the PEP-517 build-isolation env.
RUN pip install --no-cache-dir --upgrade pip "setuptools<81" wheel
RUN echo "setuptools<81" > /tmp/build-constraints.txt
ENV PIP_CONSTRAINT=/tmp/build-constraints.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
