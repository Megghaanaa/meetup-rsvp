# Recipe for the app container
FROM python:3.13-slim

WORKDIR /code

# Install packages first so Docker can reuse this layer when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]