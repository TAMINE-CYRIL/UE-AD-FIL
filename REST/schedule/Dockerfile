FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schedule/ .

EXPOSE 3202

CMD ["python", "schedule.py"]
