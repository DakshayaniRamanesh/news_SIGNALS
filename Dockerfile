FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Colombo \
    SCHEDULER_AUTOSTART=true

# Set work directory
WORKDIR /app

# Install system dependencies
# gcc/python3-dev/musl-dev might be needed for some python packages like wordcloud or others if added
# libxml2-dev libxslt-dev are often needed for xhtml2pdf or similar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Colombo /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (Stopwords and VADER) to a global location
RUN python -m nltk.downloader stopwords vader_lexicon -d /usr/local/share/nltk_data

# Download Spacy model
RUN python -m spacy download en_core_web_sm

# Copy project files
COPY . .

# Create directory for data persistence if not exists
RUN mkdir -p data

# Expose the port
EXPOSE 5000

# Run with Gunicorn
# Users should mount 'data' volume to persist data
# Using 1 worker because the scheduler runs in the app process (Simple Mode)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "wsgi:app"]
