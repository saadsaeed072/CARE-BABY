# BabyCare - Babysitter Hiring Platform

A comprehensive web-based platform that connects parents in Pakistan with verified, trustworthy babysitters. The system provides a safe, convenient, and efficient way to find, book, and pay for childcare services.

## Features

### For Parents
- **Easy Registration**: Create family profiles with children's ages and special needs
- **Advanced Search**: Filter by location, availability, hourly rate, experience, languages, and special skills
- **Detailed Profiles**: View comprehensive profiles with photos, experience, certifications, background check status, and parent reviews
- **Real-Time Booking**: Book one-time or recurring sessions with instant confirmation
- **In-App Messaging**: Chat with potential sitters before booking
- **Rating System**: Rate and review sitters after each session

### For Babysitters
- **Profile Creation**: Create professional profiles with photos, qualifications, and certifications
- **ID Verification**: Submit national ID for admin verification and get verified badges
- **Availability Calendar**: Set availability for days and times
- **Booking Requests**: Receive instant notifications for new booking requests
- **Earnings Dashboard**: Track earnings in real-time and withdraw funds easily
- **Build Reputation**: Collect ratings and reviews from parents

### For Admin
- **User Management**: Approve or reject user registrations, manage user roles
- **Verification System**: Review and approve babysitter documents
- **Activity Monitoring**: Track all bookings, payments, and user activities
- **Financial Management**: Track transactions and manage payouts
- **Analytics Dashboard**: View key metrics and export reports

## Technology Stack

- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Backend**: Python Flask
- **Database**: MySQL
- **Authentication**: Session-based with Werkzeug password hashing

## Installation

### Prerequisites
- Python 3.8+
- MySQL Server
- pip (Python package manager)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd babycare
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Setup Database
1. Create a MySQL database named `babycare_db`
2. Import the database schema:
```bash
mysql -u root -p babycare < database/schema.sql
```

### Step 5: Configure Database Connection
Edit `app.py` and update the MySQL configuration:
```python
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'babycare_db'
```

### Step 6: Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
babycare/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/               # Custom CSS (if any)
│   └── uploads/           # User uploaded files
└── templates/
    ├── base.html          # Base template
    ├── index.html         # Home page
    ├── about.html         # About page
    ├── how_it_works.html  # How it works page
    ├── search.html        # Search babysitters
    ├── babysitter_profile.html
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── parent/
    │   ├── dashboard.html
    │   ├── profile.html
    │   ├── bookings.html
    │   ├── book.html
    │   ├── messages.html
    │   ├── chat.html
    │   ├── notifications.html
    │   └── review.html
    ├── babysitter/
    │   ├── dashboard.html
    │   ├── profile.html
    │   ├── verification.html
    │   ├── availability.html
    │   ├── bookings.html
    │   ├── earnings.html
    │   ├── messages.html
    │   ├── chat.html
    │   └── notifications.html
    ├── admin/
    │   ├── dashboard.html
    │   ├── users.html
    │   ├── verifications.html
    │   ├── bookings.html
    │   ├── withdrawals.html
    │   ├── analytics.html
    │   ├── settings.html
    │   └── logs.html
```

## Key Features Implemented

1. **User Authentication**: Registration, login, logout with role-based access control
2. **Three User Roles**: Parent, Babysitter, and Admin with different permissions
3. **Profile Management**: Complete profile creation and editing for all user types
4. **Search & Filter**: Advanced search functionality for finding babysitters
5. **Booking System**: Complete booking flow with status tracking
6. **Messaging System**: In-app messaging between parents and babysitters
7. **Rating & Reviews**: Post-session rating and review system
8. **Verification System**: ID verification workflow for babysitters
9. **Earnings Management**: Track earnings and request withdrawals
10. **Admin Panel**: Comprehensive admin dashboard for platform management
11. **Analytics**: View statistics and reports
12. **Responsive Design**: Mobile-friendly Bootstrap 5 interface

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- Role-based access control
- CSRF protection (can be added with Flask-WTF)
- File upload validation
- SQL injection protection via parameterized queries

## Future Enhancements

- Email notifications
- SMS notifications
- Real-time chat with WebSockets
- Mobile app (React Native/Flutter)
- Payment gateway integration
- Advanced search with geolocation
- Subscription plans
- Insurance options

## Support

For support, email saadsaeed07@gmail.com or call 0322-9970667.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
