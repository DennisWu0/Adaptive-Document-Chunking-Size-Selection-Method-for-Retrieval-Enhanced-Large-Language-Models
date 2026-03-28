FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y git \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
 && pip install uv

RUN uv pip install --system -r requirements.txt

COPY . .

EXPOSE 5007

CMD ["gunicorn", "-w", "1", "--timeout", "300", "-b", "0.0.0.0:5007", "app:app"]

# FROM python:3.12-slim

# WORKDIR /app

# RUN pip install --no-cache-dir virtualenv

# RUN python -m venv venv

# COPY requirements.txt .
# RUN venv/bin/pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 5007

# CMD ["venv/bin/gunicorn", "-w", "4", "-b", "0.0.0.0:5007", "app:app"]
