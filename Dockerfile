# Match the Airflow and Python versions used in the course.
ARG AIRFLOW_VERSION=2.9.2
ARG PYTHON_VERSION=3.10

# Start with the ready-made Airflow image from Docker Hub (also works with Podman).
FROM docker.io/apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

# Make the selected build argument available inside this build stage.
ARG AIRFLOW_VERSION

# Airflow's home inside the Linux container, not a Windows directory.
ENV AIRFLOW_HOME=/opt/airflow

# Copy the project's package list into the image filesystem.
COPY requirements.txt /

# Add project packages while keeping Airflow's version; avoid pip's download cache.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt
