#!/bin/bash

# Create SSL directory if it doesn't exist
mkdir -p config/ssl

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout config/ssl/key.pem \
    -out config/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set proper permissions
chmod 600 config/ssl/key.pem
chmod 644 config/ssl/cert.pem

echo "Self-signed SSL certificate has been generated."
echo "Note: For production, replace these with valid SSL certificates from a trusted CA." 