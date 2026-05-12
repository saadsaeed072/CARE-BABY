-- Migration to add password reset support
-- Execute in MySQL: mysql -u root babycare_db < database/add_password_reset.sql

ALTER TABLE users
  ADD COLUMN reset_code VARCHAR(6) NULL,
  ADD COLUMN reset_code_expires_at TIMESTAMP NULL;
