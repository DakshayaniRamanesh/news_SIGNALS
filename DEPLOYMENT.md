# Deployment Guide for Server Environment

This guide explains how to deploy the News Signals application in a production server environment using Docker.

## Prerequisites
- A server (VPS or Dedicated) running Linux (Ubuntu/Debian recommended).
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

## 1. Setup

Clone your repository or upload the project files to the server.

```bash
# Example if using git
git clone <your-repo-url>
cd news_SIGNALS
```

Ensure the following files are present:
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `wsgi.py`
- `subscribers.txt` (Create an empty file if it doesn't exist: `touch subscribers.txt`)

## 2. Configuration

### Timezone
The `Dockerfile` and `docker-compose.yml` are pre-configured for **Asia/Colombo** time. If you need to change this, edit the `TZ` environment variable in `docker-compose.yml`.

### Data Persistence
The `docker-compose.yml` mounts the `./data` directory to the container. 
- All scraped news and history (`final_data.csv`, `news_history.json`) will be saved in the `data/` folder on your host machine.
- `subscribers.txt` is also mounted to persist subscriber data.

## 3. Build and Run

Run the following command to build the image and start the container in detached mode (background):

```bash
docker-compose up -d --build
```

- **Build**: This might take a few minutes the first time (installing Python packages).
- **Start**: The server will start on Port **5000**.

## 4. Verify Deployment

Check if the container is running:
```bash
docker ps
```

Check the logs to ensure the scheduler started and models are loading:
```bash
docker-compose logs -f
```
*Note: The first run might be slower as it downloads the sentence-transformer models.*

## 5. Accessing the Application

- **Local/Intranet**: `http://<server-ip>:5000`
- **Public Internet**: 
  - If you have a firewall (UFW), allow port 5000: `sudo ufw allow 5000`
  - Ideally, set up a **Reverse Proxy** (Nginx/Apache) to serve it on port 80/443 with a domain name.

### Typical Nginx Config (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 6. Management

- **Stop the server**:
  ```bash
  docker-compose down
  ```
- **Update the app**:
  1. Pull new code or edit files.
  2. Rebuild and restart:
     ```bash
     docker-compose up -d --build
     ```
- **Manual Data Backup**:
  Simply copy the `data/` directory and `subscribers.txt` to a safe location.

## Troubleshooting

- **Server Error (500)**: Check logs with `docker-compose logs --tail=100`.
- **Scheduler not running**: Ensure `SCHEDULER_AUTOSTART=true` is set in `docker-compose.yml`.
- **Models download loop**: If the container restarts frequently, check memory usage. NLP models need RAM. Ensure your server has at least 2GB RAM (4GB recommended).
