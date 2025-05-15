FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Изменить на 8080 для соответствия настройкам Back4App
EXPOSE 8080
CMD ["python", "animebot.py"]
