FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY . .

# Install the package in editable mode
RUN pip install -e .

# Expose port for web UI
EXPOSE 7860

# Default command: launch web UI (user can override for CLI)
CMD ["ragcli", "web"]
