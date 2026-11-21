#!/bin/bash
# Ollama ko background mein start karein
ollama serve &

# Ollama ke ready hone ka intezar karein
sleep 5

# Model pull karein (config.py wala naam yahan daalein)
ollama pull llama3.2:latest

# Streamlit ko cloud ke liye sahi port aur address par start karein
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true