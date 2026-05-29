FROM python:3.11-slim
WORKDIR /ydays_project_agent
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .