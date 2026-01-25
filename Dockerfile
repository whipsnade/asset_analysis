# Stage 1: Build frontend
FROM registry.npmmirror.com/node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install --registry=https://registry.npmmirror.com

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build


# Stage 2: Python backend
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy backend source
COPY backend/app ./app

# Copy frontend build to static folder
COPY --from=frontend-builder /app/frontend/dist ./static

# Expose port
EXPOSE 80

# Environment variables
ENV DATABASE_URL="mysql+pymysql://income:Vk7#a3DfGtYhJkL9@118.195.236.243:53890/income"
ENV DEEPSEEK_API_KEY="sk-0d58e31989a2447daec86f84d4f11dec"
ENV DEEPSEEK_API_URL="https://api.deepseek.com/v1"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
