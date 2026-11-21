FROM python:3.11-slim

WORKDIR /app

# System dependencies install karein
RUN apt-get update && apt-get install -y curl procps && \
    curl -fsSL https://ollama.com/install.sh | sh

# Python dependencies copy aur install karein
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki application code copy karein
COPY . .

# Start script ko executable banayein
RUN chmod +x start.sh

# Streamlit ka port expose karein
EXPOSE 8501

# Start script run karein
CMD ["./start.sh"]