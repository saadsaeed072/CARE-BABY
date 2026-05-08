# BabyCare Platform - Upgrade & Refactoring TODO

This document outlines the recommended technical, architectural, and feature upgrades for the BabyCare platform based on a system audit.

## 1. Architectural Refactoring
- [x] **Implement Flask Blueprints**: `app.py` is currently monolithic (~2,000 lines). Break it down into modular blueprints:
  - `routes/auth.py`
  - `routes/admin.py`
  - `routes/parent.py`
  - `routes/babysitter.py`
  - `routes/public.py`
- [ ] **Migrate to an ORM**: Replace raw `flask_mysqldb` queries with **Flask-SQLAlchemy**. This will protect against SQL injection, simplify complex joins, and make the database portable.
- [ ] **Implement Database Migrations**: Add **Flask-Migrate** to track and version database schema changes.
- [ ] **Sync Schema Documentation**: Ensure `database/schema.sql` is always up-to-date with active migrations.
- [ ] **Database Connection Pooling**: Optimize raw SQL connections or move to a pool-managed ORM connection.

## 2. Security Enhancements
- [x] **Rate Limiting**: Add `Flask-Limiter` to protect login, registration, and contact forms from brute-force and spam attacks.
- [x] **Email Verification**: Implement token-based email verification upon registration before allowing users to book or offer services.
- [ ] **Environment Variable Security**: Remove all hardcoded passwords/secrets from `app.py` and ensure they only reside in `.env`.
- [x] **AJAX CSRF Protection**: Added CSRF meta tags to `base.html` for secure socket and fetch operations.

## 3. UI/UX & Theming
- [x] **Dashboard Theme Consistency**: The public pages have been upgraded to the "Prime Dental" clinical theme. The internal templates in `templates/admin/`, `templates/parent/`, and `templates/babysitter/` need to be audited to ensure they match this new aesthetic (stripping old gradients and glassmorphism).
- [x] **Real-time Notifications**: Replace traditional page-reload alerts with real-time push notifications using `Flask-SocketIO` (for messages and booking updates).

## 4. Feature Additions
- [ ] **Automated Payments Integration**: Integrate actual payment gateway APIs (e.g., JazzCash, EasyPaisa API, or Stripe) instead of relying on manual payment verification.
- [ ] **Interactive Maps**: Integrate Google Maps API for the Babysitter search, allowing parents to see sitters visually on a map based on their city/neighborhood.

## 5. Testing & DevOps
- [ ] **Unit & Integration Testing**: Create a `tests/` directory and write automated tests using `pytest` for critical paths (login, booking flow, payment calculation).
- [ ] **Dockerization**: Create a `Dockerfile` and `docker-compose.yml` to easily spin up the Flask app and MySQL database locally or on a server.
- [ ] **CI/CD Pipeline**: Setup GitHub Actions to automatically lint code and run tests on new commits.
