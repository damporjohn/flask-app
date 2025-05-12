# Notification System Guide

This document explains how to use the notification system for the Computer Lab Management System.

## Overview

The notification system consists of:

1. A standalone notification API running on port 5050
2. Database tables for admin and student notifications
3. JavaScript code in the templates for displaying notifications
4. Utility scripts for testing and managing notifications

## Running the Notification API

The notification API runs separately from the main application:

```
python notification_api.py
```

This starts a server on port 5050 that handles all notification-related requests.

## Adding Notifications

### From Command Line

You can add notifications using the command line tool:

```
# Add admin notification
python create_notification.py admin "Notification Title" "Notification Message"

# Add student notification (requires student ID)
python create_notification.py student "Notification Title" "Notification Message" --student-id 123456
```

### From Python Code

You can add notifications from your Python code:

```python
from create_notification import create_notification

# Create admin notification
create_notification('admin', 'New Request', 'There is a new reservation request')

# Create student notification
create_notification('student', 'Reservation Approved', 'Your reservation has been approved', recipient_id=123456)
```

## Notification API Endpoints

### Admin Notifications

- `GET /admin/notification_count` - Get count of unread admin notifications
- `GET /admin/notifications` - Get all admin notifications
- `POST /admin/mark_notification_read/{notification_id}` - Mark specific notification as read
- `POST /admin/mark_all_notifications_read` - Mark all admin notifications as read

### Student Notifications

- `GET /student/notification_count` - Get count of unread student notifications
- `GET /student/notifications` - Get all student notifications for current student
- `POST /student/mark_notification_read/{notification_id}` - Mark specific notification as read
- `POST /student/mark_all_notifications_read` - Mark all notifications as read for current student

## Notification Types

The notification system supports different types of notifications:

- `reservation` - For reservation-related notifications
- `feedback` - For feedback and report-related notifications
- `system` - For system messages
- `test` - For testing purposes

## Testing the System

You can use these scripts to test the notification system:

- `notification_api.py` - Runs the notification API
- `test_notification_api.py` - Tests the notification API endpoints
- `create_notification.py` - Creates test notifications
- `test_notif.py` - Tests adding and retrieving notifications

## Troubleshooting

If notifications aren't appearing in the UI:

1. Make sure the notification API is running (`python notification_api.py`)
2. Check that notifications exist in the database (`python test_notif.py`)
3. Verify the frontend is correctly configured to use `http://localhost:5050` instead of relative paths
4. Check browser console for any JavaScript errors

## Integration with Main Application

To fully integrate the notification system with events in the main application (e.g., creating notifications when reservations are made), add code like this to the appropriate routes:

```python
from create_notification import create_notification

# When a new reservation is created
@app.route('/create_reservation', methods=['POST'])
def create_reservation():
    # ... existing reservation code ...
    
    # Create admin notification
    create_notification(
        'admin', 
        'New Reservation Request', 
        f'Student {student_name} has requested a reservation for {date} at {time}'
    )
    
    # Create student notification
    create_notification(
        'student', 
        'Reservation Submitted', 
        f'Your reservation request for {date} at {time} has been submitted',
        recipient_id=student_id
    )
    
    # ... rest of the code ...
``` 