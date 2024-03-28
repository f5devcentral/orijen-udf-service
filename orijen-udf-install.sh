#!/bin/bash

# Update the system
sudo apt-get update
sudo apt-get upgrade -y

# Check if Docker is installed, install it if it's not
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found, installing..."
    sudo apt-get install -y docker.io
fi

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Load the Docker image
sudo docker pull orijen-udf-service:latest

# Create the systemd service file
sudo bash -c 'cat > /etc/systemd/system/orijen-udf-service.service <<EOF
[Unit]
Description=Orijen UDF Service
Requires=docker.service
After=docker.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop orijen-udf-service
ExecStartPre=-/usr/bin/docker rm orijen-udf-service
ExecStartPre=/usr/bin/docker pull ghcr.io/kreynoldsf5/orijen-udf-service:latest
ExecStart=/usr/bin/docker run --rm --name orijen-udf-service orijen-udf-service:latest
ExecStop=/usr/bin/docker stop orijen-udf-service

[Install]
WantedBy=multi-user.target
EOF'

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable and start your app service
sudo systemctl enable orijen-udf-service.service
sudo systemctl start orijen-udf-service.service

echo "Orijen UDF service has been installed and started as a systemd service."
