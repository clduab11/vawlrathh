FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for HF Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Copy application code with correct ownership
COPY --chown=user . $HOME/app
WORKDIR $HOME/app

# Create data directory for SQLite
RUN mkdir -p $HOME/app/data

# Set API host for Docker (binds to all interfaces)
ENV API_HOST=0.0.0.0

# Expose FastAPI port (HF Spaces default is 7860)
EXPOSE 7860

# Expose MCP protocol port
EXPOSE 8001

# Run the application
# Launch app.py which contains the combined Gradio+FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
