FROM python:3.10.14-slim
LABEL org.opencontainers.image.description Orijen UDF Service for F5XC

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5123/tcp

CMD ["python", "./app.py"]
