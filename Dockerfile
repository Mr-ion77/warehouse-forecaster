# Use the official lightweight Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code and data into the container
COPY app.py .
COPY synthetic_inventory.csv .

# Cloud Run expects the app to listen on port 8080
EXPOSE 8080

# Tell Streamlit to run on port 8080 and disable the annoying setup prompts
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# The command to run your app
CMD ["streamlit", "run", "app.py", "--browser.serverAddress=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]