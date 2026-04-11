# Market Screener

AI-powered stock screening API with PostgreSQL backend and React frontend. Screener AI augmented.

Comprehensive project reference (architecture, deployment, operations, and latest changes): [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)

## Features

- **Dynamic Stock Screening**: Filter stocks by fundamental, technical, and AI-based criteria
- **TradingView-style Filters**: Region, cap bucket, 52w distance, above/below moving averages
- **PostgreSQL Database**: Reliable, scalable relational database with connection pooling
- **FastAPI Backend**: Modern, fast Python API framework with automatic Swagger documentation
- **React Frontend**: Interactive user interface with real-time updates
- **Airflow Scheduling**: Intraday and nightly DAGs for timed multi-pass refresh
- **Docker Compose**: Complete containerized stack for easy local development and deployment
- **Health Checks**: Built-in service health monitoring and graceful shutdown
- **Async Database Operations**: Non-blocking I/O with connection pooling and recycling
- **Comprehensive Logging**: Structured logging for debugging and monitoring
- **Environment Configuration**: 12-factor app compliance with `.env` file support

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Setup & Run

1. Clone or download the repository
2. Copy the environment template:

```bash
cp .env.example .env
```

3. Start the application stack:

```bash
docker compose up --build
```

This will automatically:
- Pull PostgreSQL 16 Alpine image
- Build the backend FastAPI service
- Build the frontend React service with multi-stage build
- Start Airflow (init + scheduler + webserver)
- Create and initialize the database
- Seed initial stock data
- Perform health checks on all services

### Access the Application

Once all services report as "healthy" (check with `docker compose ps`):

- **Frontend UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health
- **PostgreSQL**: localhost:5432 (for database tools)
- **Airflow UI**: http://localhost:8088 (`admin` / `admin`)

### Airflow On VPN

Airflow can be restricted to a VPN address instead of being exposed on all interfaces.

Set these variables in [.env](.env):

```bash
AIRFLOW_BIND_HOST=127.0.0.1
AIRFLOW_PORT=8088
```

If you use a VPN such as Tailscale or WireGuard, replace `127.0.0.1` with the VPN IP of the host, for example:

```bash
AIRFLOW_BIND_HOST=100.x.y.z
AIRFLOW_PORT=8088
```

Then restart Airflow:

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

With this setup, Airflow listens only on the VPN IP and is not exposed on the public interface.

Local test recommendation:

- Keep `AIRFLOW_BIND_HOST=127.0.0.1` for local development.
- Use the OVH deployment env file (`deploy/scripts/env.ovh`) for VPS production, where `AIRFLOW_BIND_HOST` is your VPN IP (for example OpenVPN `10.8.0.1`).

## Configuration

### Environment Variables

Edit `.env` to customize settings. Available variables:

```bash
# PostgreSQL
POSTGRES_DB=market_screener
POSTGRES_USER=screener_user
POSTGRES_PASSWORD=screener_password_dev
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Backend
# Optional override. Leave empty to auto-build from POSTGRES_* values.
DATABASE_URL=
PYTHONUNBUFFERED=1
ENVIRONMENT=development
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_DATA_BASE_URL=https://data.alpaca.markets
STARTUP_MIN_REQUIRED=8
STARTUP_FETCH_MIN_VALID=40
STARTUP_PROVIDER_RETRIES=2
STARTUP_PROVIDER_RETRY_DELAY_SECONDS=3.0
STARTUP_INCLUDE_ALPACA_FALLBACK=true
STARTUP_ENABLE_TECHNICAL_FALLBACK=true
FUNDAMENTALS_ENABLED=true
FUNDAMENTALS_BOOTSTRAP_ROUNDS=8
FUNDAMENTALS_BOOTSTRAP_INITIAL_DELAY_SECONDS=300
FUNDAMENTALS_BOOTSTRAP_INTERVAL_SECONDS=120
FUNDAMENTALS_MAINTENANCE_INTERVAL_SECONDS=1800
FUNDAMENTALS_ROUND_LIMIT=120
FUNDAMENTALS_ONLY_MISSING=true

# Frontend
VITE_API_URL=http://localhost:8000/api/v1

# Airflow
AIRFLOW_UID=50000
AIRFLOW_BIND_HOST=127.0.0.1
AIRFLOW_PORT=8088
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=change-me-local
AIRFLOW_ADMIN_FIRSTNAME=Market
AIRFLOW_ADMIN_LASTNAME=Screener
AIRFLOW_ADMIN_EMAIL=admin@local.dev
```

Startup multi-pass behavior:

- `STARTUP_MIN_REQUIRED`: minimum valid rows required to accept provider update
- `STARTUP_FETCH_MIN_VALID`: target rows to collect during startup fetch passes
- `STARTUP_PROVIDER_RETRIES`: number of startup passes
- `STARTUP_PROVIDER_RETRY_DELAY_SECONDS`: pause between passes

Dedicated fundamentals enrichment behavior:

- Aggressive bootstrap rounds after startup, then lighter recurring passes every 30 minutes.
- Manual trigger endpoint: `POST /api/v1/admin/fundamentals/enrich`

### Production Deployment

For production:

1. Update `.env`:

```bash
ENVIRONMENT=production
POSTGRES_PASSWORD=<generate-strong-password>
VITE_API_URL=https://api.yourdomain.com/api/v1
```

2. Update CORS origins in `backend/app/main.py`:

```python
cors_origins = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

3. Enable HTTPS with reverse proxy (Nginx, Caddy)
4. Use secrets management for passwords
5. Consider adding authentication (JWT, OAuth)

Production stack file for OVH: use [deploy/docker-compose.ovh.yml](deploy/docker-compose.ovh.yml) with the base compose file.

For the OVH VPS deployment workflow and scripts, including Apache + Certbot autoconfig and minimal rollback, see [scripts/DEPLOYMENT_GUIDE.md](scripts/DEPLOYMENT_GUIDE.md).

For a complete consolidated technical recap (local + OVH + OpenVPN + Airflow + retries/fallback), see [DEPLOYMENT_OVH_AIRFLOW_PIPELINE.md](DEPLOYMENT_OVH_AIRFLOW_PIPELINE.md).

## Architecture

### Backend (FastAPI + SQLAlchemy + PostgreSQL)

```
backend/
├── app/
│   ├── main.py           # FastAPI application with lifespan events
│   ├── config.py         # Pydantic settings with environment loading
│   ├── database.py       # SQLAlchemy async engine with pooling
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic request/response models
│   ├── routes.py         # FastAPI route handlers
│   ├── screener.py       # Stock screening business logic
│   ├── ai_analysis.py    # AI analysis service
│   ├── seed.py           # Database seeding
│   └── __init__.py
├── requirements.txt      # Python dependencies
└── Dockerfile            # Multi-stage build (production-ready)
```

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── App.jsx           # Main React component
│   └── main.jsx          # React entry point
├── public/               # Static assets
├── index.html            # HTML template
├── vite.config.js        # Vite build configuration
├── package.json          # Node.js dependencies
└── Dockerfile            # Multi-stage build for production
```

### Services Orchestration

```
docker-compose.yml
├── postgres          # PostgreSQL 16 Alpine
├── backend           # FastAPI uvicorn server
└── frontend          # Node serve for production build
```

## API Documentation

### Auto-Generated Documentation

- **Swagger UI**: http://localhost:8000/docs - Interactive API testing
- **ReDoc**: http://localhost:8000/redoc - Alternative API documentation

### Health & Monitoring

```
GET /health                           # Service health status with version
GET /                                 # API information and available endpoints
```

### Screening Endpoints

```
POST /api/v1/screen                   # Advanced screening with all filters
GET  /api/v1/screen/quick             # Quick screening with basic filters
GET  /api/v1/filters                  # Available filter options
GET  /api/v1/stock/{ticker}           # Get stock details by ticker
GET  /api/v1/ai/analyze/{ticker}      # Get AI analysis for a stock
```

### Presets & Saved Screens

```
GET  /api/v1/presets                  # Get screening presets
GET  /api/v1/saved-screens            # Get user's saved screens
POST /api/v1/saved-screens            # Create and save a screen
POST /api/v1/admin/refresh-yahoo      # Force refresh (Yahoo first, Alpaca fallback if configured)
POST /api/v1/admin/pipeline/run       # Multi-pass multi-source refresh with local calculations
GET  /api/v1/admin/pipeline/profiles  # Recommended scheduling profiles for Airflow

### External Data Providers

- Primary provider: Yahoo Finance (no key required)
- Fallback provider: Alpaca Data API (optional key-based)
- Local calculations: technical and derived metrics are computed in backend pipeline passes

If Yahoo is rate-limited and Alpaca credentials are configured, the backend attempts Alpaca fallback automatically.

### Airflow DAG Schedules

- `market_screener_intraday_pipeline` cron: `10 * * * 1-5`
- `market_screener_nightly_pipeline` cron: `15 2 * * 1-5`

Both DAGs call the backend pipeline endpoint and run post-refresh quality checks.

Pipeline resilience:

- Provider fetch is retried automatically (`provider_retries`, `provider_retry_delay_seconds`).
- If provider data is incomplete, technical indicators are completed with automatic local fallback calculations (`enable_technical_fallback=true`).

### Advanced Filters (TradingView-like)

- Region: `north_america`, `europe`, `asia_pacific`, `world`
- Market cap bucket: `micro`, `small`, `mid`, `large`, `mega`
- Trend booleans: `above_mm50`, `above_mm200`
- 52-week proximity booleans: `near_52w_high`, `near_52w_low`
- Distance ranges: `dist_52w_high`, `dist_52w_low`
- Momentum ranges: `change_3m`, `change_6m`
```

## Development

### Local Development (Without Docker)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on http://localhost:5173 with HMR enabled.

### Database

#### Connection String Format

PostgreSQL async:
```
postgresql+asyncpg://user:password@host:port/database
```

#### Connection Pool

- **Pool Size**: 20 connections
- **Max Overflow**: 10 additional connections
- **Recycle Time**: 3600 seconds (1 hour)
- **Pre-ping**: Enabled (verifies connection before use)

#### Schema Creation

Tables are automatically created on application startup via SQLAlchemy `metadata.create_all()`.

For more advanced migrations, consider Alembic:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Monitoring & Logging

### Log Format

All logs follow a standard format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
2026-04-08 12:00:00,123 - app.main - INFO - 🚀 Starting Market Screener API...
```

### Viewing Logs

Real-time logs from services:

```bash
docker compose logs -f              # All services
docker compose logs -f backend      # Only backend
docker compose logs -f frontend     # Only frontend
docker compose logs -f postgres     # Only database
```

### Health Checks

All services have built-in health checks:

```bash
# View service status
docker compose ps

# Check manually
curl http://localhost:8000/health
curl http://localhost:3000
```

## Performance Optimization

### Database

- **Connection Pooling**: Reuses database connections to reduce overhead
- **Pre-ping**: Detects and removes stale connections automatically
- **Connection Recycling**: Prevents long-lived session issues
- **Async Operations**: Non-blocking I/O for concurrent requests

### API

- **FastAPI**: ASGI framework optimized for performance
- **Uvicorn**: Production-grade ASGI server
- **CORS Middleware**: Efficient origin matching

### Frontend

- **Vite**: Next-generation build tool with instant HMR
- **React**: Component-based efficient rendering
- **Production Build**: Optimized bundle with tree-shaking

## Security Best Practices

### Current Implementation

- ✅ Environment variables for secrets
- ✅ PostgreSQL credentials in .env
- ✅ CORS origin validation
- ✅ HTTP status code appropriate error handling
- ✅ Async database with connection pooling
- ✅ Structured logging without sensitive data

### Recommended for Production

- ⚠️ Add authentication (JWT, OAuth2)
- ⚠️ Implement rate limiting
- ⚠️ Enable HTTPS/TLS
- ⚠️ Use secrets management (AWS Secrets, HashiCorp Vault)
- ⚠️ Add API key authentication
- ⚠️ Implement comprehensive input validation
- ⚠️ Add request logging and audit trails
- ⚠️ Use environment-specific configurations
- ⚠️ Regular dependency updates and security scanning
- ⚠️ SQL injection prevention (already using parameterized queries)

## Troubleshooting

### Services won't start

```bash
# Check status
docker compose ps

# View full logs
docker compose logs

# Restart services
docker compose restart

# Force rebuild
docker compose down -v
docker compose up --build
```

### Database connection refused

```bash
# Verify PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify connection string in .env
cat .env | grep DATABASE_URL
```

### Frontend can't reach API

1. Check API is running: `curl http://localhost:8000/health`
2. Check VITE_API_URL in .env
3. Check browser console for CORS errors
4. Verify firewall allows port 8000

### Port already in use

```bash
# Change ports in docker-compose.yml
# Or kill existing process
lsof -i :3000
lsof -i :8000
lsof -i :5432
```

## Project Structure

```
market_screener/
├── .dockerignore         # Docker build ignore patterns
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── docker-compose.yml   # Service orchestration
├── README.md            # This file
│
├── backend/
│   ├── Dockerfile       # Multi-stage production build
│   ├── requirements.txt  # Python dependencies
│   └── app/
│       ├── __init__.py
│       ├── main.py      # FastAPI application
│       ├── config.py    # Configuration management
│       ├── database.py  # Database setup
│       ├── models.py    # SQLAlchemy models
│       ├── schemas.py   # Pydantic schemas
│       ├── routes.py    # API endpoints
│       ├── screener.py  # Screening logic
│       ├── ai_analysis.py# AI service
│       └── seed.py      # Data seeding
│
└── frontend/
    ├── Dockerfile       # Multi-stage production build
    ├── package.json     # Node dependencies
    ├── vite.config.js   # Vite configuration
    ├── index.html       # HTML template
    ├── public/          # Static assets
    └── src/
        ├── main.jsx     # React entry
        └── App.jsx      # Main component
```

## Deployment Examples

### Docker Production

```bash
docker compose -f docker-compose.yml up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
```

### Docker Swarm

```bash
docker stack deploy -c docker-compose.yml market-screener
```

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes following the code style
3. Test locally: `docker compose down -v && docker compose up --build`
4. Submit a pull request

## License

Proprietary License - Copyright (c) Doctum Consilium. All rights reserved.

See LICENSE for full terms.

## Support & Issues

Report issues, request features, or ask questions on the project repository.
