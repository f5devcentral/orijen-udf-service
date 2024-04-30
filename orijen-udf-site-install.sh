#!/bin/bash

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit
fi

# Check for docker and install if it's missing
if ! command -v docker &> /dev/null; then
    echo "Docker could not be found, updating repositories and installing..."
    apt-get update --quiet
    apt-get install --quiet --yes docker.io
fi

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Variable Declarations
IMAGE="ghcr.io/f5devcentral/orijen-udf-service/orijen-udf-site:dev"
SERVICE="orijen-udf-site.service"
CONTAINER="orijen-udf-site"

# Create the systemd service file
cat <<EOF >/etc/systemd/system/$SERVICE
[Unit]
Description=Orijen UDF Site Service
Requires=docker.service
After=docker.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop $CONTAINER
ExecStartPre=-/usr/bin/docker rm $CONTAINER
ExecStartPre=/usr/bin/docker pull $IMAGE
ExecStart=/usr/bin/docker run --rm --name $CONTAINER $IMAGE
ExecStop=/usr/bin/docker stop $CONTAINER

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd manager configuration
systemctl daemon-reload

# Enable the service
systemctl enable $SERVICE

echo "$SERVICE has been installed and enabled."