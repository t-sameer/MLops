# Minimal Python image
FROM python:3.10-slim

WORKDIR /app

# Install Streamlit and requests library
RUN pip install streamlit requests

# Copy frontend code
COPY . /app/

# Expose Streamlit default port
EXPOSE 8501

# Start the Streamlit server
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]