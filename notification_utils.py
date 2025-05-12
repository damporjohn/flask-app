import mysql.connector
from datetime import datetime

# Database connection configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "SYSARCH",
    "port": 3306
}

def create_admin_notification(notification_type, title, message, reference_id=0):
    """
    Create a notification for admins.
    
    Args:
        notification_type (str): Type of notification (e.g., 'reservation', 'feedback')
        title (str): Notification title
        message (str): Notification message
        reference_id (int, optional): Reference ID if applicable (e.g., reservation ID)
    
    Returns:
        int: ID of the created notification or None if error
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO admin_notifications 
            (type, title, message, reference_id, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (notification_type, title, message, reference_id, 0, now))
        
        notification_id = cursor.lastrowid
        conn.commit()
        
        return notification_id
        
    except mysql.connector.Error as e:
        print(f"Error creating admin notification: {e}")
        return None
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def create_student_notification(student_id, notification_type, title, message, reference_id=0):
    """
    Create a notification for a specific student.
    
    Args:
        student_id (int): ID of the student to receive the notification
        notification_type (str): Type of notification (e.g., 'reservation', 'feedback')
        title (str): Notification title
        message (str): Notification message
        reference_id (int, optional): Reference ID if applicable (e.g., reservation ID)
    
    Returns:
        int: ID of the created notification or None if error
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO student_notifications 
            (student_id, type, title, message, reference_id, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (student_id, notification_type, title, message, reference_id, 0, now))
        
        notification_id = cursor.lastrowid
        conn.commit()
        
        return notification_id
        
    except mysql.connector.Error as e:
        print(f"Error creating student notification: {e}")
        return None
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def create_reservation_notifications(reservation_id, student_id, student_name, room, date, time):
    """
    Create notifications for a new reservation.
    
    Args:
        reservation_id (int): ID of the reservation
        student_id (int): ID of the student making the reservation
        student_name (str): Name of the student
        room (str): Room number
        date (str): Reservation date
        time (str): Reservation time
    
    Returns:
        tuple: (admin_notification_id, student_notification_id)
    """
    # Create admin notification
    admin_title = "New Reservation Request"
    admin_message = f"{student_name} has requested a reservation for Lab {room} on {date} at {time}"
    admin_notif_id = create_admin_notification('reservation', admin_title, admin_message, reservation_id)
    
    # Create student notification
    student_title = "Reservation Submitted"
    student_message = f"Your reservation request for Lab {room} on {date} at {time} has been submitted"
    student_notif_id = create_student_notification(student_id, 'reservation', student_title, student_message, reservation_id)
    
    return (admin_notif_id, student_notif_id)

def create_reservation_status_notification(reservation_id, student_id, student_name, status, room, date, time, admin_message=None):
    """
    Create notifications when a reservation status is updated.
    
    Args:
        reservation_id (int): ID of the reservation
        student_id (int): ID of the student who made the reservation
        student_name (str): Name of the student
        status (str): New status ('approved', 'rejected', 'cancelled')
        room (str): Room number
        date (str): Reservation date
        time (str): Reservation time
        admin_message (str, optional): Admin's message/reason for approval/rejection
    
    Returns:
        int: ID of the student notification
    """
    status_word = status.capitalize()
    
    # Create student notification
    student_title = f"Reservation {status_word}"
    student_message = f"Your reservation for Lab {room} on {date} at {time} has been {status.lower()}"
    
    if admin_message:
        student_message += f". Message: {admin_message}"
    
    student_notif_id = create_student_notification(student_id, 'reservation', student_title, student_message, reservation_id)
    
    return student_notif_id

def create_feedback_notifications(feedback_id, student_id, student_name, lab_room, feedback_type, details=None):
    """
    Create notifications for new feedback or report.
    
    Args:
        feedback_id (int): ID of the feedback/report
        student_id (int): ID of the student submitting the feedback
        student_name (str): Name of the student
        lab_room (str): Lab room number
        feedback_type (str): Type of feedback ('issue', 'suggestion', 'complaint')
        details (str, optional): Brief summary of the feedback
    
    Returns:
        int: ID of the admin notification
    """
    # Create admin notification
    admin_title = f"New {feedback_type.capitalize()} Report"
    
    if details and len(details) > 50:
        short_details = details[:47] + "..."
    else:
        short_details = details if details else "No details provided"
    
    admin_message = f"{student_name} submitted a {feedback_type} report for Lab {lab_room}: {short_details}"
    
    admin_notif_id = create_admin_notification('feedback', admin_title, admin_message, feedback_id)
    
    return admin_notif_id 