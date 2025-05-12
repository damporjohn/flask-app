from flask import Flask, jsonify, render_template, session, redirect, url_for, flash, request
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "notification_test_key"

# Database connection configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "SYSARCH",
    "port": 3306
}

# Login route for testing (admin)
@app.route('/login/admin', methods=['GET'])
def login_admin():
    session['user_id'] = 1  # Sample admin ID
    session['username'] = 'admin'
    session['role'] = 'admin'
    return redirect(url_for('notification_test'))

# Login route for testing (student)
@app.route('/login/student/<int:student_id>', methods=['GET'])
def login_student(student_id):
    session['user_id'] = student_id
    session['username'] = 'student'
    session['role'] = 'student'
    return redirect(url_for('notification_test'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('notification_test'))

# Test page with notification bell
@app.route('/')
def notification_test():
    role = session.get('role', 'guest')
    user_id = session.get('user_id', None)
    return render_template('notification_test.html', role=role, user_id=user_id)

# Admin notification routes
@app.route('/admin/notification_count')
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

# Route to add a test notification
@app.route('/add_test_notification/<notification_type>', methods=['POST'])
def add_test_notification(notification_type):
    if notification_type not in ['admin', 'student']:
        return jsonify({'error': 'Invalid notification type'}), 400
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        now = datetime.now()
        
        if notification_type == 'admin':
            cursor.execute("""
                INSERT INTO admin_notifications 
                (type, title, message, reference_id, is_read, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ('test', 'Test Admin Notification', 'This is a test admin notification', 
                999, 0, now))
            notification_id = cursor.lastrowid
            
        else:  # student notification
            student_id = request.form.get('student_id')
            if not student_id:
                return jsonify({'error': 'Student ID is required'}), 400
                
            cursor.execute("""
                INSERT INTO student_notifications 
                (student_id, type, title, message, reference_id, is_read, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (student_id, 'test', 'Test Student Notification', 
                'This is a test student notification', 999, 0, now))
            notification_id = cursor.lastrowid
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Created new {notification_type} notification with ID: {notification_id}'
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000) 