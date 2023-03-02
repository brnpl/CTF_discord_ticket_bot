# syntax=docker/dockerfile:1

FROM python:3.8.16-slim-buster

WORKDIR /app

COPY . .
RUN pip3 install discord.py python-dotenv

CMD ["python3", "bot.py"]
