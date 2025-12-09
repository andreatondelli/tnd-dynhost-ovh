FROM python:3.12-alpine

RUN pip install requests

WORKDIR /app
COPY update.py .

ENTRYPOINT ["python", "update.py"]
