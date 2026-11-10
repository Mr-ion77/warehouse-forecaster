# Use the official lightweight Python image
FROM python:3.12-slim

WORKDIR /app

# Install the package and app dependencies
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir ".[app]"

# App entrypoint and data
COPY scripts/streamlit_app.py scripts/
COPY data/synthetic_inventory.csv data/

# Cloud Run expects the app to listen on port 8080
EXPOSE 8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "scripts/streamlit_app.py", "--browser.serverAddress=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
