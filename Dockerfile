FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install uv

RUN uv pip install --system -r requirements.txt

COPY . .

EXPOSE 5007

CMD ["gunicorn", "-w", "1", "--timeout", "300", "-b", "0.0.0.0:5007", "app:app"]
