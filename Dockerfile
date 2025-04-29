# Dockerfile - Using standard python image

# Use the standard, non-slim image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install only specific libraries potentially still needed, skip build-essential if included
# (You might not even need this apt-get section with the full image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev && \
    # Clean up apt lists
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose the port
EXPOSE 8510

# ENV for headless
ENV STREAMLIT_SERVER_HEADLESS=true

# CMD to run the app
CMD ["streamlit", "run", "app.py", "--server.port=8510", "--server.address=0.0.0.0"]
