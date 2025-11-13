#!/bin/bash

# Build and start the Docker containers
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting containers..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

echo ""
echo "Checking service health..."
docker-compose ps

echo ""
echo "========================================="
echo "Data Dictionary is now running!"
echo "========================================="
echo ""
echo "Public view:  http://localhost:8000"
echo "Admin view:   http://localhost:8000/admin/"
echo "API:          http://localhost:5001/api"
echo ""
echo "To view logs:    docker-compose logs -f"
echo "To stop:         docker-compose down"
echo "========================================="
