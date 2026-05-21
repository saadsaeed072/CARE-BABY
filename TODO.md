# BabyCare Platform - Status & TODO

This document outlines the current status of the project, recent improvements, and remaining tasks based on the latest system audit.

## ✅ Recent Improvements
- **Maps Removal**: Successfully removed all Google Maps related code, UI elements, and API configurations to simplify the platform and reduce external dependencies.
- **Dependency Management**: Updated `requirements.txt` with missing extensions (`Flask-Limiter`, `Flask-SocketIO`, `eventlet`).
- **Configuration Security**: Moved hardcoded fallbacks for `MAIL` and `MYSQL` settings to use environment variables from `.env`.
- **Schema Synchronization**: Updated `database/schema.sql` to include missing columns for Email Verification and Password Reset systems used in the code.

## 🛠️ Pending Tasks & Suggestions

### 1. Architectural Improvements
- [ ] **Migrate to an ORM**: Replace raw `flask_mysqldb` queries with **Flask-SQLAlchemy** for better security (SQL injection protection) and cleaner code.
- [ ] **Implement Database Migrations**: Add **Flask-Migrate** to track and version database changes properly.
- [x] **Folder Cleanup**:
    - [x] Delete `app_old_backup.py` (Verified obsolete - Ready for manual deletion).
    - [x] Delete `fix_csrf.py` (Verified: All forms now have CSRF tokens - Ready for manual deletion).

### 2. Security & Validation
- [x] **Production Secret Management**: Ensure that `.env` is never committed to version control and that different secrets are used for production.
- [ ] **Babysitter Verification Flow**: Audit the babysitter registration and verification flow to ensure CNIC images are stored securely and only accessible by admins.

### 3. UI/UX & Theming
- [x] **Theme Audit**: Continue auditing internal templates (`templates/admin/`, `templates/parent/`, etc.) to ensure they follow the "Prime Dental" clinical aesthetic consistently.
- [x] **Empty States**: Add better "No results found" or "No messages yet" designs to dashboards.

### 4. Technical Debt
- [ ] **Lint Fixes**: Resolve false-positive lint errors related to `socketio.emit` by ensuring the IDE recognizes the installed `Flask-SocketIO` package.
- [ ] **Error Handling**: Implement a global error handler for 404 and 500 errors to provide a professional user experience.

### 5. Testing
- [x] **Unit Testing**: Implement basic tests for authentication and booking logic using `pytest`.

### 6. Dependency Upgrades & Tech Stack Modernization
- [ ] **Migrate from Eventlet**: Replace the deprecated `eventlet` library with `gevent` or standard `asyncio` for WebSocket connections via `Flask-SocketIO` to ensure long-term support.
- [ ] **Configure Redis for Rate Limiting**: Set up a Redis cache for `Flask-Limiter` in production to prevent memory leaks and scale horizontally, moving away from in-memory tracking.
- [ ] **Update MySQL Library**: Address `Flask-MySQLdb` deprecation warnings (`_app_ctx_stack`) by either updating the library (once maintainers patch it) or fast-tracking the migration to `Flask-SQLAlchemy` (see Architectural Improvements).
