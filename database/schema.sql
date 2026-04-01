-- BabyCare Platform Database Schema
-- MySQL Database for Babysitter Hiring Platform

CREATE DATABASE IF NOT EXISTS babycare_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE babycare_db;

-- Users table (base table for all user types)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    city VARCHAR(50) NOT NULL,
    address TEXT,
    user_type ENUM(
        'parent',
        'babysitter',
        'admin'
    ) NOT NULL,
    profile_image VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- Parents profile table
CREATE TABLE parent_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    family_name VARCHAR(100),
    number_of_children INT DEFAULT 0,
    children_ages VARCHAR(100),
    special_needs TEXT,
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Babysitters profile table
CREATE TABLE babysitter_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date_of_birth DATE,
    gender ENUM('male', 'female', 'other'),
    cnic_number VARCHAR(15),
    cnic_front_image VARCHAR(255),
    cnic_back_image VARCHAR(255),
    hourly_rate DECIMAL(10, 2) DEFAULT 500.00,
    years_of_experience INT DEFAULT 0,
    about_me TEXT,
    education VARCHAR(100),
    languages VARCHAR(255),
    special_skills TEXT,
    certifications TEXT,
    has_cpr BOOLEAN DEFAULT FALSE,
    has_first_aid BOOLEAN DEFAULT FALSE,
    background_check_status ENUM(
        'pending',
        'in_progress',
        'approved',
        'rejected'
    ) DEFAULT 'pending',
    background_check_notes TEXT,
    verification_status ENUM(
        'unverified',
        'pending',
        'verified',
        'rejected'
    ) DEFAULT 'unverified',
    total_bookings INT DEFAULT 0,
    total_earnings DECIMAL(12, 2) DEFAULT 0.00,
    rating_average DECIMAL(2, 1) DEFAULT 0.0,
    rating_count INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Availability schedule for babysitters
CREATE TABLE availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    babysitter_id INT NOT NULL,
    day_of_week TINYINT NOT NULL COMMENT '0=Sunday, 6=Saturday',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (babysitter_id) REFERENCES babysitter_profiles (id) ON DELETE CASCADE,
    UNIQUE KEY unique_availability (
        babysitter_id,
        day_of_week,
        start_time
    )
);

-- Blocked dates for babysitters
CREATE TABLE blocked_dates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    babysitter_id INT NOT NULL,
    blocked_date DATE NOT NULL,
    reason VARCHAR(255),
    FOREIGN KEY (babysitter_id) REFERENCES babysitter_profiles (id) ON DELETE CASCADE
);

-- Bookings table
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parent_id INT NOT NULL,
    babysitter_id INT NOT NULL,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    number_of_children INT DEFAULT 1,
    children_ages VARCHAR(100),
    special_instructions TEXT,
    total_hours DECIMAL(4, 1) NOT NULL,
    hourly_rate DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    platform_fee DECIMAL(10, 2) DEFAULT 0.00,
    babysitter_earnings DECIMAL(10, 2) NOT NULL,
    status ENUM(
        'pending',
        'confirmed',
        'in_progress',
        'completed',
        'cancelled',
        'rejected'
    ) DEFAULT 'pending',
    payment_status ENUM(
        'pending',
        'paid',
        'refunded',
        'failed'
    ) DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    cancelled_by ENUM(
        'parent',
        'babysitter',
        'admin'
    ) NULL,
    cancellation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (babysitter_id) REFERENCES babysitter_profiles (id) ON DELETE CASCADE
);

-- Reviews and ratings
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    parent_id INT NOT NULL,
    babysitter_id INT NOT NULL,
    rating TINYINT NOT NULL CHECK (
        rating >= 1
        AND rating <= 5
    ),
    review_text TEXT,
    is_visible BOOLEAN DEFAULT TRUE,
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (babysitter_id) REFERENCES babysitter_profiles (id) ON DELETE CASCADE,
    UNIQUE KEY unique_review (booking_id)
);

-- Messages table for in-app messaging
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    booking_id INT NULL,
    message_text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE SET NULL
);

-- Notifications table
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    type ENUM(
        'booking',
        'message',
        'verification',
        'payment',
        'system'
    ) DEFAULT 'system',
    reference_id INT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Wallet/Transactions for babysitters
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    booking_id INT NULL,
    transaction_type ENUM(
        'earning',
        'withdrawal',
        'bonus',
        'penalty',
        'refund'
    ) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description TEXT,
    status ENUM(
        'pending',
        'completed',
        'failed',
        'cancelled'
    ) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE SET NULL
);

-- Withdrawal requests
CREATE TABLE withdrawal_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    babysitter_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    bank_name VARCHAR(100),
    account_number VARCHAR(50),
    account_title VARCHAR(100),
    easypaisa_number VARCHAR(15),
    jazzcash_number VARCHAR(15),
    status ENUM(
        'pending',
        'approved',
        'rejected',
        'completed'
    ) DEFAULT 'pending',
    admin_notes TEXT,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    FOREIGN KEY (babysitter_id) REFERENCES babysitter_profiles (id) ON DELETE CASCADE
);

-- Admin activity log
CREATE TABLE admin_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id INT,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Site settings
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50) UNIQUE NOT NULL,
    setting_value TEXT,
    description VARCHAR(255)
);

-- Contact messages from visitors
CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    subject VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    admin_reply TEXT,
    replied_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT INTO
    settings (
        setting_key,
        setting_value,
        description
    )
VALUES (
        'platform_fee_percent',
        '10',
        'Platform commission percentage'
    ),
    (
        'min_hourly_rate',
        '300',
        'Minimum hourly rate for babysitters'
    ),
    (
        'max_hourly_rate',
        '2000',
        'Maximum hourly rate for babysitters'
    ),
    (
        'withdrawal_min_amount',
        '1000',
        'Minimum withdrawal amount'
    ),
    (
        'booking_cancellation_hours',
        '24',
        'Hours before booking for free cancellation'
    ),
    (
        'support_phone',
        '0300-1234567',
        'Customer support phone number'
    ),
    (
        'support_email',
        'support@babycare.pk',
        'Customer support email'
    );

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users (email);

CREATE INDEX idx_users_type ON users (user_type);

CREATE INDEX idx_bookings_parent ON bookings (parent_id);

CREATE INDEX idx_bookings_babysitter ON bookings (babysitter_id);

CREATE INDEX idx_bookings_status ON bookings (status);

CREATE INDEX idx_bookings_date ON bookings (booking_date);

CREATE INDEX idx_messages_sender ON messages (sender_id);

CREATE INDEX idx_messages_receiver ON messages (receiver_id);

CREATE INDEX idx_reviews_babysitter ON reviews (babysitter_id);

CREATE INDEX idx_availability_babysitter ON availability (babysitter_id);

CREATE INDEX idx_notifications_user ON notifications (user_id);

CREATE INDEX idx_transactions_user ON transactions (user_id);

CREATE INDEX idx_contact_messages_email ON contact_messages (email);

CREATE INDEX idx_contact_messages_read ON contact_messages (is_read);