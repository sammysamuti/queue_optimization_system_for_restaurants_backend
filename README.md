# QueueOpt - Restaurant Queue Optimization System (Backend)

Django REST Framework backend API for restaurant queue optimization simulations using M/M/c queuing theory.

## Prerequisites

- Docker & Docker Compose

## Setup and Running

**Build and start the backend:**

```bash
docker-compose down
docker-compose up --build -d
```

The API will be available at `http://localhost:4400/api`

## API Endpoints

### Authentication

- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login
- `POST /api/auth/token/refresh/` - Refresh access token
- `GET /api/auth/me/` - Get current user info

### Restaurants

- `GET /api/restaurants/` - List user's restaurants
- `POST /api/restaurants/` - Create restaurant
- `GET /api/restaurants/{id}/` - Get restaurant details
- `PATCH /api/restaurants/{id}/` - Update restaurant
- `DELETE /api/restaurants/{id}/` - Delete restaurant

### Simulations

- `POST /api/simulation/run/` - Run authenticated simulation (saves to DB)
- `POST /api/simulation/run-guest/` - Run guest simulation (no save)
- `GET /api/simulations/` - List user's simulations
- `GET /api/simulations/{simulation_id}/` - Get simulation details
- `PATCH /api/simulations/{simulation_id}/` - Update simulation
- `DELETE /api/simulations/{simulation_id}/delete/` - Delete simulation

### Health

- `GET /api/health/` - Health check

## Data Isolation

- **Each user only sees their own restaurants and simulations**
- All endpoints require authentication (except guest simulation)
- Restaurant ownership is automatically set to the authenticated user
- Simulations are linked to restaurants and filtered by owner

## Database Models

- **Restaurant**: User-owned restaurant profiles
- **SimulationResult**: Simulation runs linked to restaurants
- **SimulationConfig**: Saved simulation configurations
- **Experiment**: Scenario comparison experiments
- **Recommendation**: Optimization recommendations

## Project Structure

```
queueopt-backend/
  ├── config/              # Django settings
  │   ├── settings.py
  │   └── urls.py
  ├── simulation/          # Main app
  │   ├── models.py        # Database models
  │   ├── views.py         # API views
  │   ├── serializers.py   # Request/response serializers
  │   ├── urls.py          # URL routing
  │   └── services/        # Business logic
  └── requirements.txt     # Python dependencies
```

## Tech Stack

- **Django 4.x** - Web framework
- **Django REST Framework** - API framework
- **django-cors-headers** - CORS handling
- **djangorestframework-simplejwt** - JWT authentication
- **PostgreSQL** - Database (recommended)

## Important Notes

- **User Isolation**: All data is scoped to the authenticated user
- **Owner Required**: Every restaurant must have an owner (set automatically)
- **Cascade Delete**: Deleting a user deletes their restaurants and simulations
- **CORS**: Configured to allow all origins in development (update for production)

## Development

- Default port: `4400`
- API base URL: `http://localhost:4400/api`
- Admin panel: `http://localhost:4400/admin` (if enabled)
- Health check: `http://localhost:4400/api/health/`
