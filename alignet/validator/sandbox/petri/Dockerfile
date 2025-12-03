FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Petri from AstrowareAI/astro-petri repo
# Clone to /opt to avoid conflicts with /sandbox volume mount
WORKDIR /opt
RUN git clone https://github.com/AstrowareAI/astro-petri.git && \
    cd astro-petri && \
    git checkout alignet && \
    pip install --no-cache-dir -e .

# Set working directory for runtime
WORKDIR /sandbox

# Copy run.sh script into the image
COPY run.sh /sandbox/run.sh
RUN chmod +x /sandbox/run.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run the run.sh script
CMD ["/bin/bash", "/sandbox/run.sh"]