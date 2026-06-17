# ASRS Aviation Incident RAG System

This project is a complete Retrieval-Augmented Generation system. It acts as an artificial intelligence diagnostic assistant for aviation safety records. It searches through real flight data to answer technical questions safely and accurately.

## System Architecture
The system uses a modern microservice design to separate the different parts of the application.

* Frontend: A user interface built with Node.js to handle user inputs and display live responses.
* Backend API: A Flask application that controls the data flow and connects the database to the interface.
* Vector Database: Qdrant runs in a Docker container to store and search 38,655 embedded flight incident reports.
* Language Model: Llama 3 runs locally via Ollama. The system is designed to bypass Docker constraints and use the native host graphics card for maximum generation speed.
* CI/CD Pipeline: GitHub Actions automatically tests the system environment and code quality on every push.

## Key Features
* Live text streaming for instant user feedback.
* Automated system health testing using pytest.
* Mathematical evaluation of the artificial intelligence using sentence transformers to prevent hallucinations.
* Full dockerization for easy setup on any new machine.

## How to Run the Project
1. Install Docker and Ollama on your computer.
2. Download the local model by running `ollama run llama3` in your terminal.
3. Start the application by running `docker compose up --build` in the project folder.
4. Open your web browser to the local port shown in the terminal.
