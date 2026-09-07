FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del proyecto
COPY . .

# Directorios de ejecución
RUN mkdir -p data

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
