# Use an official Python runtime as a parent image
FROM python:3.8-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 3000

# Run app.py when the container launches
CMD ["python", "app.py"]
