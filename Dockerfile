# Dockerfile
FROM mcr.microsoft.com/playwright:v1.52.0-noble

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Railway provides $PORT; default to 8000 if not set
ENV PORT=8000

# Start the Flask app
CMD ["python", "app.py"]
