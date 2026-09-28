FROM python:3.11-slim

# Project Midas — Base Container Image
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------

WORKDIR /app

# Install system dependencies required by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyyaml>=6.0 python-pptx>=1.0.0 langgraph-checkpoint-sqlite>=1.0.0

COPY . .

# Outputs directory — generated .docx and .xlsx files land here
RUN mkdir -p /app/outputs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
