## 🐳 Docker Microservices Guestbook
A cloud-ready, containerized Guestbook application built with Flask and PostgreSQL, fully orchestrated using Docker Compose.
This project demonstrates how to build, containerize, and orchestrate a multi-container microservices application in a clean and production-like setup.


## 🚀 Purpose
The goal of this project is to showcase:

• Containerization: Running isolated environments using Docker.

• Orchestration: Managing multi-container applications with Docker Compose.

• Database Persistence: Handling relational data with PostgreSQL.

• Fast Caching: Implementing Redis to handle real-time counters.

• Error Handling: Building robust retry mechanisms for database connectivity.

## 🏗️ Architecture
The system consists of three main services:

• Web App: A Flask-based RESTful API and UI.

• Database (DB): PostgreSQL 13 used to store guest messages.

• Cache: Redis 8.6 used to track real-time page views.

## 🛠️ Tech Stack
•Language: Python 3.9

• Framework: Flask 3.0

• Databases: PostgreSQL, Redis

• Server: Gunicorn (Production-ready WSGI)

• DevOps: Docker, Docker Compose

## 🚦 Getting Started
### Prerequisites

• Docker Desktop installed on your machine.

• Git (to clone the repo).

### Installation & Deployment
#### 1. Clone the repository:
```bash
git clone https://github.com/selinkaraman/docker-microservices-guestbook.git
cd docker-microservices-guestbook
```
#### 2. Run the services:
Docker Compose will build the image, pull required databases, and set up the networking automatically.
```bash
docker compose up --build
```

#### 3. Access the application:
Open your browser and navigate to:

• URL: ```http://localhost:5001``` 

## 📂 Project Structure

```bash
├── Dockerfile               # Instructions to build the Flask image
├── docker-compose.yml       # Orchestration file for app, db, and redis
├── app.py                   # Main application logic & DB initialization
├── requirements.txt         # Python dependencies
└── .dockerignore            # Files to exclude from the container
```






