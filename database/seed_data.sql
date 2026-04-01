-- Seed data for BabyCare platform

-- Insert demo users
INSERT INTO users (email, password_hash, full_name, phone, city, address, user_type, is_verified, is_active) VALUES
('parent@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Ahmed Khan', '0300-1234567', 'Karachi', '123 Main Street, Karachi', 'parent', TRUE, TRUE),
('sitter@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Fatima Ali', '0301-2345678', 'Lahore', '456 Garden Town, Lahore', 'babysitter', TRUE, TRUE),
('admin@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Admin User', '0302-3456789', 'Islamabad', 'Admin Office, Islamabad', 'admin', TRUE, TRUE);

-- Insert parent profile
INSERT INTO parent_profiles (user_id, family_name, number_of_children, children_ages, special_needs, emergency_contact_name, emergency_contact_phone) VALUES
(1, 'Khan Family', 2, '5, 8', 'No allergies', 'Sara Khan', '0303-4567890');

-- Insert babysitter profile
INSERT INTO babysitter_profiles (user_id, date_of_birth, gender, cnic_number, hourly_rate, years_of_experience, about_me, education, languages, special_skills, certifications, has_cpr, has_first_aid, background_check_status, verification_status, total_bookings, total_earnings, rating_average, rating_count) VALUES
(2, '1995-05-15', 'female', '35201-1234567-8', 800.00, 5, 'Experienced babysitter with a passion for childcare. I have worked with children of all ages and specialize in creating engaging educational activities. I am patient, caring, and dedicated to providing a safe and nurturing environment for your children.', 'Bachelor in Early Childhood Education', 'Urdu, English, Punjabi', 'Cooking, Art & Craft, Storytelling, Homework Help', 'CPR Certified, First Aid Certified', TRUE, TRUE, 'approved', 'verified', 15, 45000.00, 4.8, 12);

-- Insert availability for babysitter
INSERT INTO availability (babysitter_id, day_of_week, start_time, end_time, is_available) VALUES
(1, 1, '09:00:00', '17:00:00', TRUE),
(1, 2, '09:00:00', '17:00:00', TRUE),
(1, 3, '09:00:00', '17:00:00', TRUE),
(1, 4, '09:00:00', '17:00:00', TRUE),
(1, 5, '09:00:00', '17:00:00', TRUE),
(1, 6, '10:00:00', '14:00:00', TRUE);

-- Insert more sample babysitters
INSERT INTO users (email, password_hash, full_name, phone, city, address, user_type, is_verified, is_active) VALUES
('sitter2@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Ayesha Siddiqui', '0304-5678901', 'Karachi', '789 Clifton Block 5, Karachi', 'babysitter', TRUE, TRUE),
('sitter3@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Maria Hassan', '0305-6789012', 'Islamabad', '321 F-10 Sector, Islamabad', 'babysitter', TRUE, TRUE),
('sitter4@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'Zainab Ahmed', '0306-7890123', 'Lahore', '654 DHA Phase 5, Lahore', 'babysitter', TRUE, TRUE);

INSERT INTO babysitter_profiles (user_id, date_of_birth, gender, hourly_rate, years_of_experience, about_me, languages, special_skills, has_cpr, has_first_aid, verification_status, total_bookings, rating_average, rating_count) VALUES
(4, '1990-08-20', 'female', 600.00, 8, 'Professional nanny with extensive experience in childcare. I love working with children and helping them learn and grow.', 'Urdu, English', 'Cooking, Cleaning, Homework Help', TRUE, FALSE, 'verified', 25, 4.9, 20),
(5, '1993-12-10', 'female', 1000.00, 7, 'Certified childcare professional with expertise in early childhood development. I provide a stimulating and safe environment for children.', 'Urdu, English, Pashto', 'Early Education, Music, Art', TRUE, TRUE, 'verified', 18, 4.7, 15),
(6, '1997-03-25', 'female', 500.00, 3, 'Enthusiastic and caring babysitter. I enjoy playing games, reading stories, and engaging children in creative activities.', 'Urdu, Punjabi', 'Games, Storytelling, Arts & Crafts', FALSE, TRUE, 'verified', 10, 4.5, 8);

-- Insert availability for additional babysitters
INSERT INTO availability (babysitter_id, day_of_week, start_time, end_time, is_available) VALUES
(2, 0, '10:00:00', '18:00:00', TRUE),
(2, 1, '10:00:00', '18:00:00', TRUE),
(2, 2, '10:00:00', '18:00:00', TRUE),
(2, 3, '10:00:00', '18:00:00', TRUE),
(2, 4, '10:00:00', '18:00:00', TRUE),
(2, 5, '10:00:00', '16:00:00', TRUE),
(2, 6, '10:00:00', '16:00:00', TRUE),
(3, 1, '08:00:00', '16:00:00', TRUE),
(3, 2, '08:00:00', '16:00:00', TRUE),
(3, 3, '08:00:00', '16:00:00', TRUE),
(3, 4, '08:00:00', '16:00:00', TRUE),
(3, 5, '08:00:00', '14:00:00', TRUE),
(4, 1, '14:00:00', '20:00:00', TRUE),
(4, 2, '14:00:00', '20:00:00', TRUE),
(4, 3, '14:00:00', '20:00:00', TRUE),
(4, 4, '14:00:00', '20:00:00', TRUE),
(4, 5, '14:00:00', '20:00:00', TRUE),
(4, 6, '10:00:00', '18:00:00', TRUE);

-- Insert sample bookings
INSERT INTO bookings (parent_id, babysitter_id, booking_date, start_time, end_time, number_of_children, children_ages, special_instructions, total_hours, hourly_rate, total_amount, platform_fee, babysitter_earnings, status, payment_status) VALUES
(1, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '13:00:00', 2, '5, 8', 'Please help with homework', 4, 800.00, 3200.00, 320.00, 2880.00, 'confirmed', 'paid'),
(1, 1, DATE_ADD(CURDATE(), INTERVAL 3 DAY), '10:00:00', '14:00:00', 2, '5, 8', '', 4, 800.00, 3200.00, 320.00, 2880.00, 'pending', 'pending'),
(1, 2, DATE_SUB(CURDATE(), INTERVAL 5 DAY), '09:00:00', '17:00:00', 2, '5, 8', 'Prepare lunch for kids', 8, 600.00, 4800.00, 480.00, 4320.00, 'completed', 'paid');

-- Insert sample reviews
INSERT INTO reviews (booking_id, parent_id, babysitter_id, rating, review_text, is_visible) VALUES
(3, 1, 2, 5, 'Fatima was amazing with my children! She was punctual, professional, and my kids loved her. Will definitely book again.', TRUE);

-- Insert sample notifications
INSERT INTO notifications (user_id, title, message, type, is_read) VALUES
(1, 'Booking Confirmed', 'Your booking for tomorrow has been confirmed by Fatima Ali.', 'booking', FALSE),
(2, 'New Booking Request', 'You have a new booking request from Ahmed Khan.', 'booking', FALSE),
(2, 'New Review', 'You received a 5-star review from Ahmed Khan!', 'booking', TRUE);

-- Update babysitter stats
UPDATE babysitter_profiles SET total_bookings = 2, total_earnings = 7200.00, rating_average = 5.0, rating_count = 1 WHERE id = 2;
