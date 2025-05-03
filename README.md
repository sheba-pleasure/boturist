# Boturist - Scalable Telegram Bot Platform

## Overview
Boturist is a scalable Telegram bot platform built with Python, Django, and various modern technologies. It provides a robust foundation for building and managing Telegram bots with features like CRM integration, analytics, and multi-platform support.

## Technologies
- Python 3.11+
- Django 5.0+
- PostgreSQL 15
- Redis 7
- MongoDB 6
- Docker & Docker Compose
- Prometheus & Grafana for monitoring

## Prerequisites
- Docker and Docker Compose
- Git
- Make (optional, for using Makefile commands)

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/sheba-pleasure/boturist.git
cd boturist
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Build and start services:
```bash
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

5. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

## Project Structure
```
boturist/
├── bot/            # Telegram bot core
├── web/            # Django web interface
├── parsers/        # Data parsing services
├── worker/         # Background tasks worker
├── config/         # Configuration files
├── scripts/        # Utility scripts
└── tests/          # Test suite
```

## Development

### Setting Up Development Environment
1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

### Running Tests
```bash
pytest
```

### Code Style
The project uses:
- Black for code formatting
- Flake8 for linting
- isort for import sorting
- mypy for type checking

## Deployment

### Production Deployment
1. Set up production server:
   - Install Docker and Docker Compose
   - Configure firewall rules
   - Set up SSL certificates

2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update all sensitive information
   - Set `DEBUG=False`

3. Deploy using Docker Compose:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Backup and Restore

#### Creating Backups
Run the backup script:
```bash
./scripts/backup.sh
```

Backups are stored in `/backup` directory with timestamp.

#### Restoring Backups
1. PostgreSQL:
```bash
gunzip -c backup_file.sql.gz | docker exec -i container_name psql -U username dbname
```

2. MongoDB:
```bash
docker exec -i container_name mongorestore --archive < backup_file.archive.gz
```

## Monitoring

### Accessing Monitoring Tools
- Prometheus: http://your-domain:9090
- Grafana: http://your-domain:3000
- Node Exporter: http://your-domain:9100
- PostgreSQL Exporter: http://your-domain:9187

### Health Checks
Health endpoint: http://your-domain:8000/health/

## Maintenance

### Log Management
Logs are stored in the `logs/` directory:
- Application logs: `django.log`
- Bot logs: `bot.log`
- Error logs: `bot_error.log`

### Regular Maintenance Tasks
1. Check logs for errors
2. Monitor disk space
3. Verify backup integrity
4. Update dependencies
5. Review security alerts

### Updating the Application
1. Pull latest changes:
```bash
git pull origin main
```

2. Update dependencies:
```bash
docker-compose build
```

3. Apply migrations:
```bash
docker-compose exec web python manage.py migrate
```

4. Restart services:
```bash
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Common Issues
1. Database connection errors:
   - Check database credentials
   - Verify network connectivity
   - Check database logs

2. Redis connection issues:
   - Verify Redis is running
   - Check Redis configuration
   - Monitor Redis memory usage

3. Bot API errors:
   - Verify Telegram token
   - Check API request limits
   - Review bot logs

### Support
For issues and support, please open an issue on GitHub.

## Security

### Best Practices
1. Regular security updates
2. Proper access control
3. Secure communication
4. Regular security audits
5. Backup verification

### Security Measures
- HTTPS enforcement
- Rate limiting
- Input validation
- Regular dependency updates
- Access control implementation

## License
[Your License Here] 

mkdir -p logs 

chmod +x scripts/backup.sh 
