# Use lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy everything into container
COPY . .

# Install dependencies (from src folder)
RUN pip install --no-cache-dir -r src/requirements.txt

# Expose port (Cloud Run uses 8080)
EXPOSE 8080

# Start app using gunicorn
CMD ["gunicorn", "src.app:server", "--bind", "0.0.0.0:8001"]
