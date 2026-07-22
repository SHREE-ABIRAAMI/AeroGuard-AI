# Use the official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user

# Create a non-root user for security (Hugging Face requires UID 1000)
RUN useradd -m -u 1000 user

# Set up working directory inside the user's home
WORKDIR $HOME/app

# Install system dependencies needed for compiling ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for caching
COPY --chown=user:user requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application files with correct ownership
COPY --chown=user:user . .

# Set container user to 1000
USER user

# Expose Hugging Face's default port
EXPOSE 7860

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
