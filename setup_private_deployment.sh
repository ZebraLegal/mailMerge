#!/bin/bash
# setup_private_deployment.sh - Complete setup script for private Docker deployment

set -e

echo "🚀 Setting up private Mail Merge deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp env.template .env
    echo "⚠️  Please edit .env file and set your MAILMERGE_PASSWORD"
    echo "   nano .env"
    read -p "Press Enter after you've set the password..."
fi

# Create output directory
echo "📁 Creating output directory..."
mkdir -p output

# Build and start the application
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting Mail Merge application..."
docker-compose up -d

# Wait for the application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is running
if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
    echo "✅ Mail Merge application is running!"
    echo "🌐 Access your application at: http://localhost:8501"
    echo "🔐 Use the password you set in the .env file"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker-compose logs -f"
    echo "   Stop app:  docker-compose down"
    echo "   Restart:   docker-compose restart"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
fi







