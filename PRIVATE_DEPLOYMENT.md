# Private Deployment Guide

## Option 1: Docker + Your Own Server
```bash
# Build the Docker image
docker build -t mailmerge-private .

# Run with authentication
docker run -p 8501:8501 -e MAILMERGE_PASSWORD="your_password" mailmerge-private
```

## Option 2: Local Network Deployment
```bash
# Run on your local network (accessible to team)
streamlit run mailMerge_with_auth.py --server.address=0.0.0.0 --server.port=8501
```

## Option 3: Cloud VPS (DigitalOcean, Linode, etc.)
- Deploy on a $5-10/month VPS
- Use Docker or direct Python installation
- Configure firewall for team access only

## Option 4: Corporate Network
- Deploy on your company's internal network
- Use VPN for remote access
- Complete privacy and control

