#!/bin/bash
# start_server.sh - Script to start the mail merge application on a server

# Activate virtual environment (if using one)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Streamlit with custom configuration
streamlit run mailMerge.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false

