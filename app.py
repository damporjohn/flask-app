import mysql.connector
from flask import Flask, request, redirect, url_for, session, render_template, flash, jsonify, logging
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
import pymysql
import os
from werkzeug.utils import secure_filename
registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Add this at the top of your app.py with your other constants
PROGRAMMING_LANGUAGES = [
    "Python", "Java", "C++", "JavaScript", "PHP", "C#", 
    "Ruby", "Swift", "Kotlin", "Go", "Rust", "TypeScript",
    "HTML/CSS", "SQL", "R", "MATLAB"
]

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "SYSARCH",
    "port": 3306
}

# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_photos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Index route
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'login' in request.form:
            return redirect(url_for('login_dashboard'))
        elif 'register' in request.form:
            return redirect(url_for('register_user'))

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_dashboard():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            # Check admins table (plural)
            cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
            admin = cursor.fetchone()
            
            # Check staffs table (plural)
            cursor.execute("SELECT * FROM staffs WHERE username = %s", (username,))
            staff = cursor.fetchone()
            
            # Check students table (plural)
            cursor.execute("SELECT * FROM students WHERE username = %s", (username,))
            student = cursor.fetchone()
            
            if admin and check_password_hash(admin['password'], password):
                session['user_id'] = admin['id']
                session['username'] = admin['username']
                session['firstname'] = admin['firstname']
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
                
            elif staff and check_password_hash(staff['password'], password):
                session['user_id'] = staff['id']
                session['username'] = staff['username']
                session['firstname'] = staff['firstname']
                session['role'] = 'staff'
                return redirect(url_for('staff_dashboard'))
                
            elif student and check_password_hash(student['password'], password):
                # Set up student session directly without activation check
                session['user_id'] = student['id']
                session['username'] = student['username']
                session['firstname'] = student['firstname']
                session['lastname'] = student['lastname']
                session['role'] = 'student'
                return redirect(url_for('student_dashboard'))
            
            else:
                return render_template('login.html', error="Invalid username or password")
                
        except mysql.connector.Error as e:
            return render_template('login.html', error=f"Database error: {e}")
            
        finally:
            cursor.close()
            conn.close()
            
    return render_template('login.html')

@app.route('/registeruser')
def register_user():
    return render_template("registeruser.html")  # Render registration page

@app.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    database_map = {
        "admin": "admins",
        "staff": "staffs",
        "student": "students"
    }

    if role not in database_map:
        flash("Invalid role.", 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        midname = request.form.get('midname', '')
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match.", 'danger')
            return redirect(url_for('register', role=role))

        conn = None
        cursor = None

        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # 🔹 Check if email exists in any table
            query_email_check = """
                SELECT email FROM admins WHERE email = %s
                UNION 
                SELECT email FROM staffs WHERE email = %s
                UNION 
                SELECT email FROM students WHERE email = %s
            """
            cursor.execute(query_email_check, (email, email, email))
            existing_email = cursor.fetchone()

            if existing_email:
                flash("Email already exists. Please use a different email.", 'danger')
                return redirect(url_for('register', role=role))

            # 🔹 If email is unique, proceed with registration
            hashed_password = generate_password_hash(password)
            registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            table_name = database_map[role]

            if role == "student":
                course = request.form.get('course', '')
                yearlevel = request.form.get('yearlevel', '')
                remaining_sessions = 30  # Default session count for students

                query = f'''
                    INSERT INTO {table_name} 
                    (username, password, firstname, lastname, midname, course, yearlevel, email, registration_date, remaining_sessions) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                values = (username, hashed_password, firstname, lastname, midname, 
                          course, yearlevel, email, registration_date, remaining_sessions)
            
            else:  # 🔹 Admins & Staff (no course or yearlevel)
                query = f'''
                    INSERT INTO {table_name} 
                    (username, password, firstname, lastname, midname, email, registration_date) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                '''
                values = (username, hashed_password, firstname, lastname, midname, email, registration_date)

            cursor.execute(query, values)
            conn.commit()

            new_id = cursor.lastrowid  # Auto-generated ID

            flash(f"Successfully registered as {role}! Your ID is {new_id}.", 'success')
            return redirect(url_for('login_dashboard'))

        except mysql.connector.Error as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('register', role=role))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template(f'register_{role}.html')  # Render role-specific form




#MGA DASHBOARDS

#ADMIN
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login_dashboard'))
    
    current_term = "1st Semester" # You can make this dynamic
    
    return render_template('admin_dashboard.html', 
                         current_term=current_term)


@app.route('/get_students', methods=['GET'])
def get_students():
    search_query = request.args.get('search_query', '').strip()
    students = []
    
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                    SELECT id, username, firstname, midname, lastname, email, registration_date
                    FROM students
                """
                params = []

                if search_query:
                    query += " WHERE id LIKE %s OR username LIKE %s OR firstname LIKE %s "
                    query += "OR midname LIKE %s OR lastname LIKE %s OR email LIKE %s"
                    wildcard_search = f"%{search_query}%"
                    params = [wildcard_search] * 6
                
                cursor.execute(query, params)
                students = cursor.fetchall()
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    return jsonify({'students': students})

@app.route('/submit_sit_in_form', methods=['POST'])
def submit_sit_in_form():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    student_id = request.form.get('student_id')
    purpose = request.form.get('purpose')
    room_number = request.form.get('roomNumber')

    if not student_id:
        return jsonify({"error": "Student ID is missing!"})

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO sit_in 
            (student_id, purpose, room_number, is_activated, activation_time) 
            VALUES (%s, %s, %s, 1, NOW())
        """, (student_id, purpose, room_number))
        
        conn.commit()

        # Get updated statistics after inserting new session
        cursor.execute("""
            SELECT 
                SUBSTRING_INDEX(SUBSTRING_INDEX(purpose, ',', numbers.n), ',', -1) language,
                COUNT(*) as count
            FROM
                sit_in
                CROSS JOIN (
                    SELECT 1 + ones.n + tens.n * 10 as n
                    FROM
                        (SELECT 0 as n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) ones
                        CROSS JOIN
                        (SELECT 0 as n UNION SELECT 1) tens
                    ORDER BY n
                ) numbers
            WHERE
                numbers.n <= 1 + (LENGTH(sit_in.purpose) - LENGTH(REPLACE(sit_in.purpose, ',', '')))
                AND SUBSTRING_INDEX(SUBSTRING_INDEX(purpose, ',', numbers.n), ',', -1) != ''
            GROUP BY language
            ORDER BY count DESC
        """)
        purpose_stats = cursor.fetchall()
        
        return jsonify({
            "success": "Session activated successfully!",
            "purpose_stats": purpose_stats
        })

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    finally:
        cursor.close()
        conn.close()

@app.route('/get_labs', methods=['GET'])
def get_labs():
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT roomNumber FROM labs WHERE status = 'Available'")
                labs = cursor.fetchall()
        return jsonify({'labs': labs})
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/update_all_remaining_sessions', methods=['POST'])
def update_all_remaining_sessions():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Update remaining_sessions for all students
        cursor.execute("UPDATE students SET remaining_sessions = 25")
        conn.commit()

        return jsonify({'success': 'Remaining sessions updated to 25 for all students'})

    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/submit_sit_in_form_mysql', methods=['POST'])
def submit_sit_in_form_mysql():
    if 'student_id' not in session:
        return redirect(url_for('login_dashboard'))

    student_id = session['student_id']
    student_full_name = session.get('student_full_name', '')

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        purposes = request.form.getlist('purpose')  # Gets multiple selected values
        purpose_str = ','.join(purposes)  # Join them with commas
        room_number = request.form.get('roomNumber')

        # Fetch the remaining sessions of the student
        cursor.execute("SELECT remaining_sessions FROM students WHERE id = %s", (student_id,))
        student_data = cursor.fetchone()

        if not student_data:
            return jsonify({'error': 'Student not found.'}), 400

        remaining_sessions = student_data["remaining_sessions"]

        if remaining_sessions <= 0:
            return jsonify({'error': 'No remaining sessions available.'}), 400

        # Insert the new sit-in record into the sitin table
        cursor.execute("""
            INSERT INTO sitin (student_id, student_name, purpose, room_number, remaining_sessions)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, student_full_name, purpose_str, room_number, remaining_sessions - 1))

        # Deduct 1 from the student's remaining sessions
        cursor.execute("""
            UPDATE students SET remaining_sessions = remaining_sessions - 1 WHERE id = %s
        """, (student_id,))

        conn.commit()

        return jsonify({'success': 'Sit-in form submitted successfully. Session deducted.'})

    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'An error occurred while submitting the form.'}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/sit_in_records')
def sit_in_records():
    if session.get('role') != 'admin':  # Authentication check
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Get only today's sit-in records
        cursor.execute("""
            SELECT s.id, s.student_id, s.purpose, s.room_number, 
                   s.login_time, s.logout_time,
                   st.firstname, st.lastname
            FROM sit_in s
            LEFT JOIN students st ON s.student_id = st.id
            WHERE DATE(s.login_time) = CURDATE()
            ORDER BY 
                CASE 
                    WHEN s.logout_time IS NULL THEN 1 
                    ELSE 0 
                END DESC, 
                s.logout_time DESC
        """)
        records = cursor.fetchall()

        return render_template('sit_in_records.html', records=records)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('admin_dashboard'))

    finally:
        cursor.close()
        conn.close()

@app.route('/sit_in_history', methods=['GET'])
def sit_in_history():
    """Fetch sit-in history for the logged-in student from the sit_in table."""
    if 'username' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('login_dashboard'))
    
    username = session.get('username')
    student_id = session.get('user_id')  # Should be storing the student ID in session
    
    if not student_id:
        # If user_id is not in session, try to get it from the database
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT id FROM students WHERE username = %s", (username,))
            student = cursor.fetchone()
            
            if student:
                student_id = student['id']
            else:
                flash("Student record not found.", "danger")
                return redirect(url_for('student_dashboard'))
                
        except mysql.connector.Error as e:
            flash(f"Database error: {e}", "danger")
            return redirect(url_for('student_dashboard'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    try:
        # Connect to MySQL database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Fetch all sit-in records for the logged-in student
        cursor.execute("""
            SELECT id, student_id, purpose, room_number, login_time, logout_time, is_activated, activation_time 
            FROM sit_in 
            WHERE student_id = %s
            ORDER BY login_time DESC
        """, (student_id,))
        
        history = cursor.fetchall()
        
        return render_template('sit_in_history.html', history=history)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        # Ensure connection is closed
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/create_reservation_table')
def create_reservation_table():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create the reservation_requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservation_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                lab_id VARCHAR(50) NOT NULL,
                purpose VARCHAR(255) NOT NULL,
                requested_date DATE NOT NULL,
                requested_time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Reservation table created successfully'})

    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/make_reservation', methods=['GET', 'POST'])
def make_reservation():
    if 'username' not in session or session.get('role') != 'student':
        flash("Please log in as a student.", "danger")
        return redirect(url_for('login_dashboard'))

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Get student information
        cursor.execute("""
            SELECT id, firstname, lastname 
            FROM students 
            WHERE username = %s
        """, (session['username'],))
        student = cursor.fetchone()

        if request.method == 'POST':
            room_number = request.form.get('room')
            date = request.form.get('date')
            time = request.form.get('time')
            purpose = request.form.get('purpose')

            if not all([room_number, date, time, purpose]):
                flash("All fields are required.", "danger")
                return redirect(url_for('make_reservation'))

            # Verify that the room exists in labs table
            cursor.execute("SELECT roomNumber FROM labs WHERE roomNumber = %s", (room_number,))
            if not cursor.fetchone():
                flash("Invalid room number selected.", "danger")
                return redirect(url_for('make_reservation'))

            try:
                # Insert the reservation with default values for new columns
                cursor.execute("""
                    INSERT INTO reservation_requests 
                    (student_id, room_number, purpose, requested_date, requested_time, status, created_at, used)
                    VALUES (%s, %s, %s, %s, %s, 'pending', NOW(), 0)
                """, (student['id'], room_number, purpose, date, time))
                
                conn.commit()
                flash("Reservation request sent successfully!", "success")
                return redirect(url_for('student_dashboard'))
                
            except mysql.connector.Error as e:
                print(f"Error in make_reservation: {str(e)}")  # Add logging
                flash(f"Error saving reservation: {str(e)}", "danger")
                return redirect(url_for('make_reservation'))

        # For GET request, fetch available labs
        cursor.execute("SELECT roomNumber FROM labs WHERE status = 'Available'")
        labs = cursor.fetchall()

        return render_template('make_reservation.html', 
                            student=student, 
                            labs=labs, 
                            programming_languages=PROGRAMMING_LANGUAGES)

    except mysql.connector.Error as e:
        print(f"Database error in make_reservation: {str(e)}")  # Add logging
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/admin/handle_reservation/<int:request_id>/<string:action>', methods=['POST'])
def handle_reservation(request_id, action):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # First check if the reservation exists and is pending
        cursor.execute("""
            SELECT * FROM reservation_requests 
            WHERE id = %s AND status = 'pending'
        """, (request_id,))
        
        reservation = cursor.fetchone()
        if not reservation:
            return jsonify({'error': 'Reservation not found or already processed'})
        
        if action == 'approve':
            # Update the reservation status
            cursor.execute("""
                UPDATE reservation_requests 
                SET status = 'approved', 
                    admin_response = NOW(),
                    used = 0
                WHERE id = %s
            """, (request_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Reservation approved successfully'})
            
        elif action == 'reject':
            # Update the reservation status
            cursor.execute("""
                UPDATE reservation_requests 
                SET status = 'rejected', 
                    admin_response = NOW(),
                    used = 1
                WHERE id = %s
            """, (request_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Reservation rejected successfully'})
        
        else:
            return jsonify({'error': 'Invalid action'})

    except mysql.connector.Error as e:
        print(f"Database error in handle_reservation: {str(e)}")  # Add logging
        return jsonify({'error': str(e)})

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.clear()
        flash("Logout successful!", "success")
    return redirect(url_for('login_dashboard'))

@app.route('/post_announcement', methods=['POST'])
def post_announcement():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # First, ensure the announcements table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Now insert the announcement
        cursor.execute("""
            INSERT INTO announcements (title, content)
            VALUES (%s, %s)
        """, (title, content))
        
        conn.commit()
        return jsonify({'success': True})
        
    except mysql.connector.Error as e:
        print(f"Database error in post_announcement: {str(e)}")  # Add logging
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get_announcements')
def get_announcements():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, title, content, created_at, updated_at 
            FROM announcements 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        announcements = cursor.fetchall()
        return jsonify({'announcements': announcements})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()

@app.route('/student_dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student':  
        flash("You need to log in first.", "danger")
        return redirect(url_for('login_dashboard'))

    username = session['username']

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Get student information
        cursor.execute('''
            SELECT id, username, firstname, midname, lastname, 
                   course, yearlevel, email, registration_date, remaining_sessions
            FROM students WHERE username = %s
        ''', (username,))
        student = cursor.fetchone()

        if not student:
            flash("Student record not found.", "danger")
            return redirect(url_for('login_dashboard'))

        return render_template('student_dashboard.html', student=student)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('login_dashboard'))

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/edit_student_record', methods=['GET', 'POST'])
def edit_student_record():
    if 'username' not in session or session.get('role') != 'student':
        flash("You need to log in first.", "danger")
        return redirect(url_for('login_dashboard'))

    username = session['username']

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            # Get form data
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            midname = request.form.get('midname')
            course = request.form.get('course')
            yearlevel = request.form.get('yearlevel')
            email = request.form.get('email')

            # Handle photo upload
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo and photo.filename and allowed_file(photo.filename):
                    try:
                        # Create a unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = secure_filename(f"{username}_{timestamp}_{photo.filename}")
                        
                        # Ensure the upload directory exists
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        # Full path for saving the file
                        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        
                        # Save the file
                        photo.save(save_path)
                        
                        # Store the relative path in the database
                        photo_path = os.path.join('static', 'uploads', 'profile_photos', filename)
                        
                        print(f"Photo saved at: {save_path}")
                        print(f"Photo path stored in DB: {photo_path}")
                        
                        # Update student record with new photo path
                        cursor.execute("""
                            UPDATE students 
                            SET firstname=%s, lastname=%s, midname=%s, 
                                course=%s, yearlevel=%s, email=%s, photo_path=%s
                            WHERE username=%s
                        """, (firstname, lastname, midname, course, yearlevel, email, photo_path, username))
                    except Exception as e:
                        print(f"Error saving photo: {e}")
                        flash(f"Error saving photo: {e}", "danger")
                        # Update without changing photo
                        cursor.execute("""
                            UPDATE students 
                            SET firstname=%s, lastname=%s, midname=%s, 
                                course=%s, yearlevel=%s, email=%s
                            WHERE username=%s
                        """, (firstname, lastname, midname, course, yearlevel, email, username))
                else:
                    # Update without changing photo
                    cursor.execute("""
                        UPDATE students 
                        SET firstname=%s, lastname=%s, midname=%s, 
                            course=%s, yearlevel=%s, email=%s
                        WHERE username=%s
                    """, (firstname, lastname, midname, course, yearlevel, email, username))
            else:
                # Update without changing photo
                cursor.execute("""
                    UPDATE students 
                    SET firstname=%s, lastname=%s, midname=%s, 
                        course=%s, yearlevel=%s, email=%s
                    WHERE username=%s
                """, (firstname, lastname, midname, course, yearlevel, email, username))
            
            conn.commit()
            flash("Your record has been updated successfully!", "success")
            return redirect(url_for('student_dashboard'))

        # GET request - fetch student data
        cursor.execute("""
            SELECT id, username, firstname, lastname, midname,
                   course, yearlevel, email, registration_date, remaining_sessions,
                   photo_path
            FROM students 
            WHERE username = %s
        """, (username,))
        
        student = cursor.fetchone()

        if not student:
            flash("Student record not found.", "danger")
            return redirect(url_for('student_dashboard'))

        return render_template('edit_student_record.html', student=student)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/sit_in_rules')
def sit_in_rules():
    if 'username' not in session or session.get('role') != 'student':
        flash("You need to log in first.", "danger")
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get student information for the sidebar
        cursor.execute("""
            SELECT id, username, firstname, lastname 
            FROM students 
            WHERE username = %s
        """, (session['username'],))
        
        student = cursor.fetchone()
        
        if not student:
            flash("Student record not found.", "danger")
            return redirect(url_for('login_dashboard'))
            
        return render_template('sit_in_rules.html', student=student)
        
    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/lab_rules')
def lab_rules():
    if 'username' not in session or session.get('role') != 'student':
        flash("You need to log in first.", "danger")
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get student information for the sidebar
        cursor.execute("""
            SELECT id, username, firstname, lastname 
            FROM students 
            WHERE username = %s
        """, (session['username'],))
        
        student = cursor.fetchone()
        
        if not student:
            flash("Student record not found.", "danger")
            return redirect(url_for('login_dashboard'))
            
        return render_template('lab_rules_&_regulation.html', student=student)
        
    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get_admin_statistics')
def get_admin_statistics():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get total registered students
        cursor.execute("SELECT COUNT(*) as total FROM students")
        total_students = cursor.fetchone()['total']
        
        # Get currently active sit-ins
        cursor.execute("SELECT COUNT(*) as active FROM sit_in WHERE logout_time IS NULL")
        active_sitins = cursor.fetchone()['active']
        
        # Get total sit-ins
        cursor.execute("SELECT COUNT(*) as total FROM sit_in")
        total_sitins = cursor.fetchone()['total']
        
        # Get purpose statistics for pie chart
        cursor.execute("""
            SELECT purpose, COUNT(*) as count
            FROM sit_in
            WHERE purpose IS NOT NULL AND purpose != ''
            GROUP BY purpose
            ORDER BY count DESC
        """)
        
        raw_stats = cursor.fetchall()
        
        # Process the statistics to handle multiple languages per purpose
        language_counts = {}
        for stat in raw_stats:
            # Split multiple languages if they exist
            languages = [lang.strip() for lang in stat['purpose'].split(',')]
            for lang in languages:
                if lang in PROGRAMMING_LANGUAGES:  # Only count valid programming languages
                    language_counts[lang] = language_counts.get(lang, 0) + stat['count']
        
        # Convert to the format expected by the chart
        purpose_stats = [
            {'language': lang, 'count': count}
            for lang, count in language_counts.items()
        ]
        
        # Sort by count in descending order
        purpose_stats.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            'total_students': total_students,
            'active_sitins': active_sitins,
            'total_sitins': total_sitins,
            'purpose_stats': purpose_stats
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()

@app.route('/get_programming_languages')
def get_programming_languages():
    return jsonify({'languages': PROGRAMMING_LANGUAGES})

@app.route('/current_sit_in')
def current_sit_in():
    if 'role' not in session or session['role'] != 'admin':
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get active sit-in sessions (both pending login and active)
        query = """
            SELECT 
                s.id as sit_in_id,
                s.student_id,
                st.firstname,
                st.lastname,
                st.course,
                s.purpose,
                s.room_number,
                DATE_FORMAT(s.login_time, '%Y-%m-%d %H:%i:%s') as login_time
            FROM sit_in s
            JOIN students st ON s.student_id = st.id
            WHERE s.is_activated = 1 AND s.logout_time IS NULL
            ORDER BY s.login_time DESC
        """
        cursor.execute(query)
        active_sessions = cursor.fetchall()
        
        return render_template(
            'current_sit_in.html',
            sit_ins=active_sessions,
            total=len(active_sessions),
            PROGRAMMING_LANGUAGES=PROGRAMMING_LANGUAGES
        )
        
    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/end_sit_in_session/<int:sitInId>', methods=['POST'])
def end_sit_in_session(sitInId):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # First check if the session exists and is active
        cursor.execute("""
            SELECT s.id, s.student_id, s.login_time, s.logout_time,
                   st.username, st.firstname, st.lastname
            FROM sit_in s
            JOIN students st ON s.student_id = st.id
            WHERE s.id = %s
        """, (sitInId,))
        
        sit_in = cursor.fetchone()
        
        if not sit_in:
            return jsonify({'error': 'Session not found'}), 404
            
        if sit_in['logout_time']:
            return jsonify({'error': 'Session already ended'}), 400

        # Deduct one session from the student's remaining sessions
        cursor.execute("""
            UPDATE students 
            SET remaining_sessions = remaining_sessions - 1 
            WHERE id = %s 
            AND remaining_sessions > 0
        """, (sit_in['student_id'],))

        # Update the record with logout time
        cursor.execute("""
            UPDATE sit_in 
            SET logout_time = NOW()
            WHERE id = %s
        """, (sitInId,))

        conn.commit()
        return jsonify({
            'success': True, 
            'message': f'Session ended for student {sit_in["firstname"]} {sit_in["lastname"]} and remaining sessions deducted'
        })

    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/sit_in_reports')
def sit_in_reports():
    if session.get('role') != 'admin':
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get all sit-in records with student information
        cursor.execute("""
            SELECT 
                s.id,
                s.student_id,
                st.firstname,
                st.lastname,
                st.course,
                s.purpose,
                s.room_number,
                s.login_time,
                s.logout_time,
                TIMEDIFF(COALESCE(s.logout_time, NOW()), s.login_time) as duration
            FROM sit_in s
            JOIN students st ON s.student_id = st.id
            ORDER BY s.login_time DESC
        """)
        
        records = cursor.fetchall()
        return render_template('sit_in_reports.html', 
                             records=records,
                             PROGRAMMING_LANGUAGES=PROGRAMMING_LANGUAGES)
        
    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/register_sitin', methods=['POST'])
def admin_register_sitin():
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        student_id = request.form.get('student_id')
        purpose = request.form.get('purpose')
        room_number = request.form.get('room_number')
        
        if not all([student_id, purpose, room_number]):
            return jsonify({'error': 'All fields are required'}), 400
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Check if student exists
        cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
            
        # Check if student already has an active session
        cursor.execute("""
            SELECT id FROM sit_in 
            WHERE student_id = %s AND logout_time IS NULL
        """, (student_id,))
        active_session = cursor.fetchone()
        if active_session:
            return jsonify({'error': 'Student already has an active session'}), 400
            
        # Register new sit-in session
        cursor.execute("""
            INSERT INTO sit_in (student_id, purpose, room_number, login_time)
            VALUES (%s, %s, %s, NOW())
        """, (student_id, purpose, room_number))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Sit-in session registered successfully'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/admin/activate_sitin', methods=['POST'])
def admin_activate_sitin():
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        student_id = request.form.get('student_id')
        purpose = request.form.get('purpose')
        room_number = request.form.get('room_number')
        reservation_id = request.form.get('reservation_id')
        
        if not all([student_id, purpose, room_number]):
            return jsonify({'error': 'All fields are required'}), 400
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Check if student exists
        cursor.execute("SELECT id, firstname, lastname FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
            
        # Check if student already has an active session
        cursor.execute("""
            SELECT id FROM sit_in 
            WHERE student_id = %s AND logout_time IS NULL
        """, (student_id,))
        active_session = cursor.fetchone()
        if active_session:
            return jsonify({'error': 'Student already has an active session'}), 400
            
        # Validate programming languages
        languages = [lang.strip() for lang in purpose.split(',')]
        valid_languages = [lang for lang in languages if lang in PROGRAMMING_LANGUAGES]
        
        if not valid_languages:
            return jsonify({'error': 'No valid programming languages selected'}), 400
            
        # Create an activation record
        cursor.execute("""
            INSERT INTO sit_in (
                student_id, 
                purpose, 
                room_number, 
                is_activated, 
                activation_time,
                reservation_id
            ) VALUES (%s, %s, %s, 1, NOW(), %s)
        """, (student_id, ','.join(valid_languages), room_number, reservation_id))
        
        # If this was from a reservation, mark it as used
        if reservation_id:
            cursor.execute("""
                UPDATE reservation_requests 
                SET used = 1 
                WHERE id = %s
            """, (reservation_id,))
        
        conn.commit()
        return jsonify({
            'success': True, 
            'message': f'Session activated for {student["firstname"]} {student["lastname"]}'
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/student/login_sitin', methods=['POST'])
def student_login_sitin():
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        student_id = session.get('user_id')
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Check if there's an activated sit-in for this student
        cursor.execute("""
            SELECT id FROM sit_in 
            WHERE student_id = %s AND is_activated = 1 AND login_time IS NULL
        """, (student_id,))
        
        activation = cursor.fetchone()
        if not activation:
            return jsonify({'error': 'No active sit-in found for this student'}), 404
            
        # Update the record with login time
        cursor.execute("""
            UPDATE sit_in 
            SET login_time = NOW()
            WHERE id = %s
        """, (activation['id'],))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Successfully logged in to sit-in session'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/student/logout_sitin', methods=['POST'])
def student_logout_sitin():
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        student_id = session.get('user_id')
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Update the record with logout time
        cursor.execute("""
            UPDATE sit_in 
            SET logout_time = NOW(),
                is_activated = 0  # Deactivate the session
            WHERE student_id = %s 
            AND login_time IS NOT NULL 
            AND logout_time IS NULL
        """, (student_id,))
        
        # Clear all session data
        session.clear()
        
        return jsonify({
            'success': True, 
            'message': 'Successfully logged out. Please contact an administrator for your next session.'
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/get_pending_activations')
def get_pending_activations():
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                s.id,
                s.student_id,
                st.firstname,
                st.lastname,
                st.course,
                s.purpose,
                s.room_number,
                DATE_FORMAT(s.activation_time, '%Y-%m-%d %H:%i:%s') as activation_time
            FROM sit_in s
            JOIN students st ON s.student_id = st.id
            WHERE s.is_activated = 1 AND s.login_time IS NULL
            ORDER BY s.activation_time DESC
        """)
        
        activations = cursor.fetchall()
        return jsonify({'activations': activations})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/admin/cancel_activation/<int:activation_id>', methods=['POST'])
def cancel_activation(activation_id):
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sit_in 
            WHERE id = %s AND is_activated = 1 AND login_time IS NULL
        """, (activation_id,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': 'Activation cancelled successfully'})
        else:
            return jsonify({'error': 'Activation not found or already used'})
            
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/student/acknowledge_login', methods=['POST'])
def acknowledge_login():
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Clear the login notification flag
    session.pop('needs_login', None)
    
    return jsonify({'success': True})

@app.route('/get_reservations')
def get_reservations():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Get all reservations that haven't been used yet
        cursor.execute("""
            SELECT 
                r.id, 
                r.student_id, 
                r.room_number, 
                r.purpose, 
                DATE_FORMAT(r.requested_date, '%Y-%m-%d') as requested_date,
                TIME_FORMAT(r.requested_time, '%H:%i') as requested_time,
                r.status, 
                r.created_at,
                r.used,
                s.firstname, 
                s.lastname
            FROM reservation_requests r
            JOIN students s ON r.student_id = s.id
            WHERE (r.used = 0 OR r.used IS NULL)
            ORDER BY r.created_at DESC
        """)
        
        reservations = cursor.fetchall()
        
        # Convert datetime objects to string format for JSON serialization
        for reservation in reservations:
            if isinstance(reservation['created_at'], datetime):
                reservation['created_at'] = reservation['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'reservations': reservations})

    except mysql.connector.Error as e:
        print(f"Database error in get_reservations: {str(e)}")  # Add logging
        return jsonify({'error': str(e)}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/admin/add_used_column', methods=['GET'])
def add_used_column():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'reservation_requests'
            AND COLUMN_NAME = 'used'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        if result[0] == 0:
            # Add the column if it doesn't exist
            cursor.execute("""
                ALTER TABLE reservation_requests
                ADD COLUMN used TINYINT(1) DEFAULT 0
            """)
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Column added successfully'})
        else:
            return jsonify({'success': True, 'message': 'Column already exists'})
            
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/add_reservation_id_column', methods=['GET'])
def add_reservation_id_column():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'sit_in'
            AND COLUMN_NAME = 'reservation_id'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        if result[0] == 0:
            # Add the column if it doesn't exist
            cursor.execute("""
                ALTER TABLE sit_in
                ADD COLUMN reservation_id INT,
                ADD FOREIGN KEY (reservation_id) REFERENCES reservation_requests(id)
            """)
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Column added successfully'})
        else:
            return jsonify({'success': True, 'message': 'Column already exists'})
            
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/student/check_session_status')
def check_session_status():
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'ended': True})
        
    try:
        student_id = session.get('user_id')
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id 
            FROM sit_in 
            WHERE student_id = %s 
            AND login_time IS NOT NULL 
            AND logout_time IS NULL
        """, (student_id,))
        
        active_session = cursor.fetchone()
        return jsonify({'ended': not bool(active_session)})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/activate_reservation/<int:reservation_id>', methods=['POST'])
def activate_reservation(reservation_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get reservation details
        cursor.execute("""
            SELECT r.*, s.firstname, s.lastname
            FROM reservation_requests r
            JOIN students s ON r.student_id = s.id
            WHERE r.id = %s AND r.status = 'approved' AND r.used = 0
        """, (reservation_id,))
        
        reservation = cursor.fetchone()
        if not reservation:
            return jsonify({'error': 'Reservation not found or already used'}), 404
            
        # Create sit-in session from reservation
        try:
            cursor.execute("""
                INSERT INTO sit_in 
                (student_id, purpose, room_number, is_activated, activation_time, reservation_id)
                VALUES (%s, %s, %s, 1, NOW(), %s)
            """, (reservation['student_id'], reservation['purpose'], 
                  reservation['room_number'], reservation_id))
        except mysql.connector.Error as e:
            if "Unknown column 'reservation_id'" in str(e):
                # If reservation_id column doesn't exist, add it first
                cursor.execute("""
                    ALTER TABLE sit_in
                    ADD COLUMN reservation_id INT,
                    ADD FOREIGN KEY (reservation_id) REFERENCES reservation_requests(id)
                """)
                conn.commit()
                
                # Try the insert again
                cursor.execute("""
                    INSERT INTO sit_in 
                    (student_id, purpose, room_number, is_activated, activation_time, reservation_id)
                    VALUES (%s, %s, %s, 1, NOW(), %s)
                """, (reservation['student_id'], reservation['purpose'], 
                      reservation['room_number'], reservation_id))
            else:
                raise
        
        # Mark reservation as used
        cursor.execute("""
            UPDATE reservation_requests 
            SET used = 1 
            WHERE id = %s
        """, (reservation_id,))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'Session activated for {reservation["firstname"]} {reservation["lastname"]}'
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/get_student_remaining_sessions/<int:student_id>')
def get_student_remaining_sessions(student_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT remaining_sessions 
            FROM students 
            WHERE id = %s
        """, (student_id,))
        
        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
            
        return jsonify({'remaining_sessions': student['remaining_sessions']})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Get programming languages count from the database
def get_language_data():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    query = "SELECT purpose FROM sit_in"
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Normalize data
    language_count = {lang: 0 for lang in PROGRAMMING_LANGUAGES}
    
    for row in results:
        purpose = row[0].strip().lower()
        for lang in PROGRAMMING_LANGUAGES:
            if lang.lower() in purpose:
                language_count[lang] += 1
                break

    cursor.close()
    conn.close()
    return language_count

@app.route('/get_data')
def get_data():
    return jsonify(get_language_data())

@app.route('/get_today_stats')
def get_today_stats():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get programming languages used today
        cursor.execute("""
            SELECT 
                SUBSTRING_INDEX(SUBSTRING_INDEX(purpose, ',', numbers.n), ',', -1) as language,
                COUNT(*) as count
            FROM
                sit_in
                CROSS JOIN (
                    SELECT 1 + ones.n + tens.n * 10 as n
                    FROM
                        (SELECT 0 as n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) ones
                        CROSS JOIN
                        (SELECT 0 as n UNION SELECT 1) tens
                    ORDER BY n
                ) numbers
            WHERE
                DATE(login_time) = CURDATE()
                AND numbers.n <= 1 + (LENGTH(sit_in.purpose) - LENGTH(REPLACE(sit_in.purpose, ',', '')))
                AND SUBSTRING_INDEX(SUBSTRING_INDEX(purpose, ',', numbers.n), ',', -1) != ''
            GROUP BY language
            ORDER BY count DESC
        """)
        languages = cursor.fetchall()
        
        # Get labs used today
        cursor.execute("""
            SELECT 
                room_number,
                COUNT(*) as count
            FROM sit_in
            WHERE DATE(login_time) = CURDATE()
            GROUP BY room_number
            ORDER BY count DESC
        """)
        labs = cursor.fetchall()
        
        return jsonify({
            'languages': languages,
            'labs': labs
        })
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
        conn.close()

@app.route('/reservations')
def reservations():
    if session.get('role') != 'admin':
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login_dashboard'))
    return render_template('reservations.html')

@app.route('/create_announcements_table')
def create_announcements_table():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create the announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Announcements table created successfully'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/create_reports_table')
def create_reports_table():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create the reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                report_text TEXT NOT NULL,
                rating INT CHECK (rating >= 1 AND rating <= 5),
                room_number VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'unread',
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Reports table created successfully'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/submit_report', methods=['POST'])
def submit_report():
    if 'user_id' not in session or session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        report_text = request.form.get('report_text')
        rating = request.form.get('rating')
        room_number = request.form.get('room_number')
        
        if not report_text or not rating or not room_number:
            return jsonify({'error': 'Report text, rating, and room number are required'}), 400
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reports (student_id, report_text, rating, room_number)
            VALUES (%s, %s, %s, %s)
        """, (session['user_id'], report_text, rating, room_number))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Report submitted successfully'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/get_reports')
def get_reports():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT r.*, s.firstname, s.lastname
            FROM reports r
            JOIN students s ON r.student_id = s.id
            ORDER BY r.created_at DESC
        """)
        
        reports = cursor.fetchall()
        
        # Convert datetime objects to string for JSON serialization
        for report in reports:
            report['created_at'] = report['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
        return jsonify({'reports': reports})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/feedback_reports')
def feedback_reports():
    if session.get('role') != 'admin':
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login_dashboard'))
    return render_template('feedback_reports.html')

@app.route('/registered_students')
def registered_students():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, firstname, lastname, midname, course, yearlevel, email, registration_date 
            FROM students 
            ORDER BY registration_date DESC
        """)
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('all_registered_students.html', students=students)
    except Exception as e:
        print(f"Error fetching students: {e}")
        return "Error fetching student data", 500

@app.route('/test_upload', methods=['GET', 'POST'])
def test_upload():
    if request.method == 'POST':
        if 'photo' not in request.files:
            return 'No file part'
        
        photo = request.files['photo']
        if photo.filename == '':
            return 'No selected file'
        
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            photo.save(save_path)
            return f'File uploaded successfully to {save_path}'
    
    return '''
    <!doctype html>
    <title>Test Upload</title>
    <h1>Test File Upload</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=photo>
      <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print('Shutting down gracefully...')
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the application with threaded=False to avoid threading issues
    app.run(debug=True, port=3306, threaded=False)