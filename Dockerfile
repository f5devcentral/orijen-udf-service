FROM python:3.10.14-slim
LABEL org.opencontainers.image.description Orijen UDF Service for F5XC

WORKDIR /app
COPY app .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./app.py"]
