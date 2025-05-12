from flask import Flask, jsonify, request, session
import mysql.connector
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "notification_api_key"

# Database connection configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "SYSARCH",
    "port": 3306
}

# Login status mock for testing
MOCK_SESSION = {
    'role': 'admin',
    'user_id': 1
}

# Mock login required decorator for testing
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Using mock session for testing
        session.update(MOCK_SESSION)
        return f(*args, **kwargs)
    return decorated_function

# Create notification tables if they don't exist
@app.route('/create_tables')
def create_notification_tables():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create admin notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                reference_id INT,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create student notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                reference_id INT,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return jsonify({"success": True, "message": "Notification tables created successfully!"})
    
    except mysql.connector.Error as e:
        return jsonify({"success": False, "error": str(e)})
    
    finally:
        cursor.close()
        conn.close()

# Admin notification routes
@app.route('/admin/notification_count')
@login_required
def admin_notification_count():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM admin_notifications WHERE is_read = 0")
        result = cursor.fetchone()
        
        return jsonify({'count': result['count'] if result else 0})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT * FROM admin_notifications 
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        notifications = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for notification in notifications:
            if notification['created_at']:
                notification['created_at'] = notification['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({'notifications': notifications})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def admin_mark_notification_read(notification_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE admin_notifications SET is_read = 1 WHERE id = %s", (notification_id,))
        conn.commit()
        
        return jsonify({'success': True})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/mark_all_notifications_read', methods=['POST'])
@login_required
def admin_mark_all_notifications_read():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE admin_notifications SET is_read = 1")
        conn.commit()
        
        return jsonify({'success': True})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

# Student notification routes
@app.route('/student/notification_count')
@login_required
def student_notification_count():
    if session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student_id = session.get('user_id')
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT COUNT(*) as count 
            FROM student_notifications 
            WHERE student_id = %s AND is_read = 0
        ''', (student_id,))
        result = cursor.fetchone()
        
        return jsonify({'count': result['count'] if result else 0})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/student/notifications')
@login_required
def student_notifications():
    if session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student_id = session.get('user_id')
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT * FROM student_notifications 
            WHERE student_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        ''', (student_id,))
        notifications = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for notification in notifications:
            if notification['created_at']:
                notification['created_at'] = notification['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({'notifications': notifications})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/student/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def student_mark_notification_read(notification_id):
    if session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student_id = session.get('user_id')
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verify this notification belongs to the current student
        cursor.execute('''
            SELECT id FROM student_notifications 
            WHERE id = %s AND student_id = %s
        ''', (notification_id, student_id))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Notification not found'}), 404
        
        cursor.execute("UPDATE student_notifications SET is_read = 1 WHERE id = %s", (notification_id,))
        conn.commit()
        
        return jsonify({'success': True})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/student/mark_all_notifications_read', methods=['POST'])
@login_required
def student_mark_all_notifications_read():
    if session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student_id = session.get('user_id')
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE student_notifications SET is_read = 1 WHERE student_id = %s", (student_id,))
        conn.commit()
        
        return jsonify({'success': True})
    
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5050) 