# ---- Builder Stage ----
# This stage installs all dependencies and downloads the model.
FROM python:3.13-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and activate a virtual environment
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Download and save the SentenceTransformer model
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); model.save('./models/all-MiniLM-L6-v2')"

# Copy the application source code into the builder stage.
COPY . .

# ---- Final Stage ----
# This stage copies the application, the venv, and the model from the builder.
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the model path environment variable for the application
ENV MODEL_PATH /app/models/all-MiniLM-L6-v2

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code and the downloaded model from the builder stage
COPY --from=builder /app /app

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port and run the application
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
