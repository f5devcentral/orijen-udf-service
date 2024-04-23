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
IMAGE=ghcr.io/f5devcentral/orijen-udf-service/orijen-udf-site:latest
SERVICE=orijen-udf-site.service

# Create the systemd service file
sudo bash -c "cat > /etc/systemd/system/$SERVICE <<EOF
[Unit]
Description=Orijen Site Registration Service
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStartPre=/usr/bin/docker pull $IMAGE
ExecStart=/usr/bin/docker run --rm $IMAGE
RemainAfterExit=no
SuccessExitStatus=0

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable and start your app service
sudo systemctl enable $SERVICE
sudo systemctl start $SERVICE

echo "$SERVICE has been installed and started as a systemd service."