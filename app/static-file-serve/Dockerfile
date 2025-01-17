# Use minimal Python image
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Copy application code
COPY app.py /app/
COPY .env /app/

# Install runtime dependencies
RUN apk add --no-cache python3-dev libffi-dev gcc musl-dev \
    && pip install --no-cache-dir python-dotenv \
    && apk del gcc musl-dev

# Expose the port
EXPOSE 6002

# Run the server
CMD ["python", "/app/app.py"]
