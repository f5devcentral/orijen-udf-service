#!/bin/bash

# Update apt
sudo DEBIAN_FRONTEND=noninteractive apt-get update --yes

# Check if Docker is installed, install it if it's not
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found, installing..."
    sudo apt-get install -y docker.io
fi

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Variable Declarations
IMAGE=ghcr.io/kreynoldsf5/orijen-udf-service:latest
SERVICE=orijen-udf.service
CONTAINER=orijen-udf

# Create the systemd service file
sudo bash -c "cat > /etc/systemd/system/$SERVICE <<EOF
[Unit]
Description=Orijen UDF Service
Requires=docker.service
After=docker.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop $IMAGE
ExecStartPre=-/usr/bin/docker rm $IMAGE
ExecStartPre=/usr/bin/docker pull $IMAGE
ExecStart=/usr/bin/docker run --rm --name $CONTAINER $IMAGE
ExecStop=/usr/bin/docker stop $CONTAINER

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable and start your app service
sudo systemctl enable $SERVICE
sudo systemctl start $SERVICE

echo "$SERVICE has been installed and started as a systemd service."
