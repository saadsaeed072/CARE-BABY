-- Run this migration to add email verification support
-- Execute in MySQL: mysql -u root babycare_db < database/migrate_email_verification.sql

ALTER TABLE users
ADD COLUMN is_email_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN email_verification_token VARCHAR(200) NULL,
ADD COLUMN email_verification_sent_at TIMESTAMP NULL,
ADD INDEX idx_email_verification_token (email_verification_token);

-- Set existing admin/already-active users as verified so they're not locked out
UPDATE users SET is_email_verified = TRUE WHERE user_type = 'admin';