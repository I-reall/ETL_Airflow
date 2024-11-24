# Use the Python 3.9 development container from Microsoft
FROM mcr.microsoft.com/vscode/devcontainers/python:3.9

# Update and install required system packages
RUN apt-get update && apt-get install -y \
    mysql-server \
    libmysqlclient-dev \
    default-libmysqlclient-dev \
    && apt-get clean

# Install Airflow and its MySQL provider
RUN pip install apache-airflow apache-airflow-providers-mysql pyreadstat pandas

# Set up Airflow environment variables
ENV AIRFLOW_HOME=/workspace/airflow

# Initialize Airflow database
RUN airflow db init

# Expose ports for Airflow and MySQL
EXPOSE 8080 3306

# Set MySQL configuration to allow external connections
RUN echo "[mysqld]\nskip-host-cache\nskip-name-resolve\n" >> /etc/mysql/my.cnf

# Start MySQL service when the container starts
CMD service mysql start && airflow webserver --port 8080
