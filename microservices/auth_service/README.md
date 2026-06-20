# Auth Service Developer Guide

This service provides username/password authentication and RBAC authorization backed by Redis.

## What this service does

- Stores user credentials in Redis
- Hashes passwords with bcrypt
- Issues short-lived bearer tokens
- Stores RBAC permissions in Redis sets
- Validates authorization for protected actions

## API Endpoints

- `GET /health` - Service health check
- `POST /api/login` - Authenticate username/password and return bearer token + refresh token
- `POST /api/refresh` - Exchange a refresh token for a new access token/refresh token pair
- `POST /api/logout` - Revoke the current access token and/or refresh token
- `POST /api/authorize` - Validate a bearer token for a permission
- `POST /api/users` - Create a new user (admin only)
- `GET /api/users/{username}` - Get user roles and metadata
- `GET /api/roles/{role}` - Get a role's permissions
- `POST /api/roles/{role}/permissions` - Add permissions to a role (admin only)

## Run locally

```bash
cd microservices/auth-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8005
```

## Local defaults

- Port: `8005`
- Redis URL: `redis://redis:6379/0`
- Default admin user: `ADMIN_USERNAME` / `ADMIN_PASSWORD`

## Notes

- The service seeds default RBAC roles and a default admin user on startup if none exist.
- For production, set `ADMIN_PASSWORD` using a secure secret.
