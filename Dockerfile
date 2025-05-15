FROM python:3.8-slim-buster
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Добавляем порт, который должен использовать ваш бот
EXPOSE 8443

CMD ["python", "animebot.py"]
