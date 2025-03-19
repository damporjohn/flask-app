import mysql.connector
from flask import Flask, request, redirect, url_for, session, render_template, flash, jsonify, logging
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
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
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cursor = conn.cursor(dictionary=True)
                    
                    # Check for admin activation
                    cursor.execute("""
                        SELECT s.id, s.purpose, s.room_number
                        FROM sit_in s
                        WHERE s.student_id = %s 
                        AND s.is_activated = 1 
                        AND s.login_time IS NULL
                        AND s.logout_time IS NULL
                    """, (student['id'],))
                    
                    activation = cursor.fetchone()
                    
                    if not activation:
                        # No active session found
                        flash("Please contact an administrator to activate your session.", "warning")
                        return redirect(url_for('login_dashboard'))
                    
                    # If we have an activation, set up the session
                    session['user_id'] = student['id']
                    session['username'] = student['username']
                    session['firstname'] = student['firstname']
                    session['lastname'] = student['lastname']
                    session['role'] = 'student'
                    
                    # Store activation info and proceed with login
                    session['activation_id'] = activation['id']
                    session['activation_purpose'] = activation['purpose']
                    session['activation_room'] = activation['room_number']
                    session['needs_login'] = True
                    
                    # Update login time
                    cursor.execute("""
                        UPDATE sit_in 
                        SET login_time = NOW()
                        WHERE id = %s
                    """, (activation['id'],))
                    
                    # Decrement remaining sessions
                    cursor.execute("""
                        UPDATE students 
                        SET remaining_sessions = remaining_sessions - 1 
                        WHERE id = %s
                    """, (student['id'],))
                    
                    conn.commit()
                    
                    return redirect(url_for('student_dashboard'))
                
                except mysql.connector.Error as e:
                    flash(f"Database error: {str(e)}", "danger")
                    return redirect(url_for('login_dashboard'))
                finally:
                    cursor.close()
                    conn.close()
                
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
        return jsonify({"success": "Session activated successfully!"})

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
    if session.get('role') != 'admin':  # Add authentication check
        return redirect(url_for('login_dashboard'))
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Get all sit-in records with student information
        cursor.execute("""
            SELECT s.id, s.student_id, s.purpose, s.room_number, 
                   s.login_time, s.logout_time,
                   st.firstname, st.lastname
            FROM sit_in s
            LEFT JOIN students st ON s.student_id = st.id
            ORDER BY s.login_time DESC
        """)
        records = cursor.fetchall()

        return render_template('sit_in.html', records=records)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('admin_dashboard'))

    finally:
        cursor.close()
        conn.close()

@app.route('/sit_in_history', methods=['GET'])
def sit_in_history():
    """Fetch and categorize sit-in reservations for the logged-in student using MySQL."""
    username = session.get('username')  # Ensure the student is logged in
    if not username:
        return jsonify({"error": "Unauthorized"}), 403  # Return error if not logged in

    try:
        # Connect to MySQL database
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="SYSARCH"
        )
        cursor = conn.cursor(dictionary=True)

        # Fetch all reservations of the logged-in student
        cursor.execute("""
            SELECT datetime, lab_id, status 
            FROM reservations 
            WHERE username = %s
            ORDER BY datetime ASC
        """, (username,))
        sit_in_records = cursor.fetchall()

        # Get current timestamp
        now = datetime.now()

        # Categorize reservations into old, ongoing, and upcoming
        old_reservations = []
        ongoing_reservations = []
        upcoming_reservations = []

        for record in sit_in_records:
            record_datetime = record["datetime"]

            reservation_data = {
                "datetime": record_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                "lab_id": record["lab_id"],
                "status": record["status"]
            }

            if record_datetime < now:  # Past reservations
                old_reservations.append(reservation_data)
            elif record_datetime.date() == now.date():  # Same day = Ongoing
                ongoing_reservations.append(reservation_data)
            else:  # Future reservations
                upcoming_reservations.append(reservation_data)

    except mysql.connector.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        # Ensure connection is closed
        cursor.close()
        conn.close()

    return jsonify({
        "old_reservations": old_reservations,
        "ongoing_reservations": ongoing_reservations,
        "upcoming_reservations": upcoming_reservations
    })

@app.route('/make_reservation', methods=['GET', 'POST'])
def make_reservation():
    if 'username' not in session or session.get('role') != 'student':
        flash("Please log in as a student.", "danger")
        return redirect(url_for('login_dashboard'))

    # Check if student has an active session
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id 
            FROM sit_in 
            WHERE student_id = %s 
            AND login_time IS NOT NULL 
            AND logout_time IS NULL
        """, (session['user_id'],))
        
        active_session = cursor.fetchone()
        
        if not active_session:
            flash("You need an active session to make reservations.", "warning")
            return redirect(url_for('student_dashboard'))
            
        # Continue with existing reservation logic...

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('student_dashboard'))

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

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
            lab_id = request.form.get('lab')
            date = request.form.get('date')
            time = request.form.get('time')
            purpose = request.form.get('purpose')  # Get single purpose value

            # Insert reservation request
            cursor.execute("""
                INSERT INTO reservation_requests 
                (student_id, lab_id, purpose, requested_date, requested_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (student['id'], lab_id, purpose, date, time))
            
            conn.commit()
            flash("Reservation request submitted. Waiting for admin approval.", "success")
            return redirect(url_for('student_dashboard'))

        # For GET request, fetch available labs
        cursor.execute("SELECT id, roomNumber, capacity FROM labs WHERE status = 'Available'")
        labs = cursor.fetchall()

        # Get programming languages for purpose dropdown
        programming_languages = PROGRAMMING_LANGUAGES

        return render_template('make_reservation.html', student=student, labs=labs, 
                              programming_languages=programming_languages)

    except mysql.connector.Error as e:
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
                SET status = 'approved', admin_response = NOW()
                WHERE id = %s
            """, (request_id,))
            
            # Get student's remaining sessions
            cursor.execute("""
                SELECT remaining_sessions FROM students
                WHERE id = %s
            """, (reservation['student_id'],))
            
            student = cursor.fetchone()
            
            # If student has remaining sessions, don't decrement
            # This will happen when they actually use the reservation
            
            conn.commit()
            return jsonify({'success': 'Reservation approved successfully'})
            
        elif action == 'reject':
            # Update the reservation status
            cursor.execute("""
                UPDATE reservation_requests 
                SET status = 'rejected', admin_response = NOW()
                WHERE id = %s
            """, (request_id,))
            
            conn.commit()
            return jsonify({'success': 'Reservation rejected successfully'})
        
        else:
            return jsonify({'error': 'Invalid action'})

    except mysql.connector.Error as e:
        return jsonify({'error': str(e)})

    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
def logout():
    if 'user_id' in session and session['role'] == 'student':
        student_id = session['user_id']

        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # Find the latest entry for this student where logout_time is NULL
            update_query = """
                UPDATE sit_in 
                SET logout_time = NOW()
                WHERE student_id = %s AND logout_time IS NULL
                ORDER BY login_time DESC 
                LIMIT 1;
            """
            cursor.execute(update_query, (student_id,))
            conn.commit()

            flash("Logout successful!", "success")

        except mysql.connector.Error as e:
            flash(f"Database error: {e}", "danger")

        finally:
            cursor.close()
            conn.close()

    # Clear session and redirect
    session.clear()
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
        
        cursor.execute("""
            INSERT INTO announcements (title, content)
            VALUES (%s, %s)
        """, (title, content))
        
        conn.commit()
        return jsonify({'success': True})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
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

            # Update student record
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
                   course, yearlevel, email, registration_date, remaining_sessions
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
        # Modified to handle multiple languages per sit-in
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

        # Update the record with logout time
        cursor.execute("""
            UPDATE sit_in 
            SET logout_time = NOW()
            WHERE id = %s
        """, (sitInId,))

        # Clear student's session if they're currently logged in
        cursor.execute("""
            SELECT session_data 
            FROM sessions 
            WHERE user_id = %s AND role = 'student'
        """, (sit_in['student_id'],))
        
        student_session = cursor.fetchone()
        if student_session:
            cursor.execute("""
                DELETE FROM sessions 
                WHERE user_id = %s AND role = 'student'
            """, (sit_in['student_id'],))

        conn.commit()
        return jsonify({
            'success': True, 
            'message': f'Session ended for student {sit_in["firstname"]} {sit_in["lastname"]}'
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
            
        # Create an activation record with NULL login_time
        try:
            # Try with is_activated and activation_time columns
            cursor.execute("""
                INSERT INTO sit_in (student_id, purpose, room_number, is_activated, activation_time)
                VALUES (%s, %s, %s, 1, NOW())
            """, (student_id, purpose, room_number))
        except mysql.connector.Error as e:
            if "Unknown column" in str(e):
                # Fallback if columns don't exist
                cursor.execute("""
                    INSERT INTO sit_in (student_id, purpose, room_number)
                    VALUES (%s, %s, %s)
                """, (student_id, purpose, room_number))
            else:
                raise
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Sit-in activated for student'})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/admin/get_reservations')
def get_reservations():
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                r.id,
                r.student_id,
                s.firstname,
                s.lastname,
                r.purpose,
                l.roomNumber as room_number,
                DATE_FORMAT(r.requested_date, '%Y-%m-%d') as requested_date,
                TIME_FORMAT(r.requested_time, '%H:%i') as requested_time,
                r.status
            FROM reservation_requests r
            JOIN students s ON r.student_id = s.id
            JOIN labs l ON r.lab_id = l.id
            ORDER BY r.created_at DESC
        """)
        
        reservations = cursor.fetchall()
        return jsonify({'reservations': reservations})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500

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
