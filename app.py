import os
import sqlite3
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from datetime import datetime, timedelta
from functools import wraps
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-123' 
DB_NAME = "seating.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table_exists = c.fetchone() is not None
    
    # Faculty table
    c.execute('''CREATE TABLE IF NOT EXISTS faculty (
                faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                designation TEXT CHECK(designation IN ('Professor', 'Associate Professor', 'Assistant Professor', 'Lecturer')) NOT NULL,
                department TEXT NOT NULL,
                total_duties INTEGER DEFAULT 0,
                remaining_duties INTEGER DEFAULT 0,
                is_available BOOLEAN DEFAULT TRUE
            )''')
    
    # Exam halls table
    c.execute('''CREATE TABLE IF NOT EXISTS halls (
                    hall_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hall_name TEXT NOT NULL UNIQUE,
                    capacity INTEGER NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE
                )''')
    
    # Exams table
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
                    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_type TEXT CHECK(exam_type IN ('Mid Term', 'Missed Evaluation', 'End Sem', 'Supplementary Exam')) NOT NULL,
                    date DATE NOT NULL,
                    session TEXT CHECK(session IN ('Forenoon', 'Afternoon')) NOT NULL,
                    invigilators_required INTEGER NOT NULL,
                    course_code TEXT,
                    course_name TEXT,
                    students_count INTEGER NOT NULL DEFAULT 0
                )''')
    
    # Faculty duty allocation table
    c.execute('''CREATE TABLE IF NOT EXISTS faculty_duties (
                    duty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_id INTEGER NOT NULL,
                    exam_id INTEGER NOT NULL,
                    duties_assigned INTEGER DEFAULT 1,
                    FOREIGN KEY (faculty_id) REFERENCES faculty (faculty_id),
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id),
                    UNIQUE(faculty_id, exam_id)
                )''')
    
    # Duty allocation table
    c.execute('''CREATE TABLE IF NOT EXISTS duty_allocations (
                    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    session TEXT NOT NULL,
                    faculty_id INTEGER NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id),
                    FOREIGN KEY (faculty_id) REFERENCES faculty (faculty_id),
                    UNIQUE(exam_id, faculty_id, date, session)
                )''')
    
    # Exam hall allocations table - FIXED: Added UNIQUE constraint
    c.execute('''CREATE TABLE IF NOT EXISTS exam_hall_allocations (
                    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    hall_id INTEGER NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id),
                    FOREIGN KEY (hall_id) REFERENCES halls (hall_id),
                    UNIQUE(exam_id, hall_id)
                )''')
    
    # Users table for authentication
    if not users_table_exists:
        c.execute('''CREATE TABLE users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'admin'
                    )''')
        
        # Default admin user
        c.execute('''INSERT INTO users (username, password, role)
                     VALUES (?, ?, ?)''', ('admin', 'admin123', 'admin'))
        print("Created users table and added default admin user")
    
    # Insert sample data only if tables are empty
    c.execute("SELECT COUNT(*) FROM faculty")
    if c.fetchone()[0] == 0:
        faculty_data = [
            ('Dr. Smith', 'Professor', 'Computer Science', 10, 10, True),
            ('Prof. Johnson', 'Professor', 'Mathematics', 10, 10, True),
            ('Dr. Williams', 'Associate Professor', 'Physics', 12, 12, True),
            ('Prof. Brown', 'Associate Professor', 'Chemistry', 12, 12, True),
            ('Dr. Davis', 'Assistant Professor', 'Computer Science', 15, 15, True),
            ('Prof. Miller', 'Assistant Professor', 'Mathematics', 15, 15, True),
            ('Dr. Wilson', 'Lecturer', 'Physics', 20, 20, True),
            ('Prof. Moore', 'Lecturer', 'Chemistry', 20, 20, True)
        ]
        
        c.executemany('''INSERT INTO faculty (name, designation, department, total_duties, remaining_duties, is_available)
                         VALUES (?, ?, ?, ?, ?, ?)''', faculty_data)
    
    # Check if halls table is empty
    c.execute("SELECT COUNT(*) FROM halls")
    if c.fetchone()[0] == 0:
        halls_data = [
            ('Room 101', 60, True),
            ('Room 102', 60, True),
            ('Room 201', 80, True),
            ('Room 202', 80, True),
            ('Main Hall', 120, True),
            ('Auditorium', 200, True)
        ]
        
        c.executemany('''INSERT INTO halls (hall_name, capacity, is_available)
                         VALUES (?, ?, ?)''', halls_data)
    
    # Check if exams table is empty and add sample exams
    c.execute("SELECT COUNT(*) FROM exams")
    if c.fetchone()[0] == 0:
        # Calculate dates
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        exams_data = [
            ('Mid Term', tomorrow, 'Forenoon', 4, 'CS101', 'Introduction to Programming', 100),
            ('End Sem', tomorrow, 'Afternoon', 6, 'MA201', 'Advanced Mathematics', 180),
            ('Missed Evaluation', day_after, 'Forenoon', 2, 'PH101', 'Physics Fundamentals', 40),
            ('Supplementary Exam', day_after, 'Afternoon', 4, 'CH201', 'Organic Chemistry', 80)
        ]
        
        c.executemany('''INSERT INTO exams (exam_type, date, session, invigilators_required, course_code, course_name, students_count)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', exams_data)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- VALIDATION FUNCTIONS ----------
def validate_date(date_string):
    """Validate date format and ensure it's not in the past"""
    try:
        input_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if input_date < today:
            return False, "Date cannot be in the past"
        
        return True, input_date
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD"

def validate_exam_scheduling(exam_date, session, faculty_ids):
    conn = get_db_connection()
    
    conflict_faculty = []
    for faculty_id in faculty_ids:
        existing_duty = conn.execute("""
            SELECT f.name, e.date, e.session 
            FROM duty_allocations da
            JOIN faculty f ON da.faculty_id = f.faculty_id
            JOIN exams e ON da.exam_id = e.exam_id
            WHERE da.faculty_id = ? AND e.date = ? AND e.session = ?
        """, (faculty_id, exam_date, session)).fetchone()
        
        if existing_duty:
            conflict_faculty.append(existing_duty['name'])
    
    conn.close()
    
    if conflict_faculty:
        return False, f"Faculty members {', '.join(conflict_faculty)} already have duties on {exam_date} ({session})"
    
    return True, "No conflicts"

def validate_students_count(students_count):
    try:
        count = int(students_count)
        if count <= 0:
            return False, "Number of students must be at least 1"
        if count > 1000:
            return False, "Number of students cannot exceed 1000"
        return True, count
    except ValueError:
        return False, "Number of students must be a valid number"

def sanitize_input(text):
    """Basic input sanitization"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    import re
    cleaned = re.sub(r'[;\"\']', '', str(text)).strip()
    return cleaned[:255]  # Limit length

# ---------- UTILITY FUNCTIONS ----------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_invigilators_required(exam_type, students_count):
    """Calculate invigilators required based on exam type and student count"""
    # Base invigilators per student range
    if students_count <= 60:
        base_invigilators = 2
    elif students_count <= 120:
        base_invigilators = 3
    elif students_count <= 200:
        base_invigilators = 4
    else:
        base_invigilators = 5
    
    # Adjust based on exam type
    exam_multipliers = {
        'Mid Term': 1.0,
        'Missed Evaluation': 1.2,
        'End Sem': 1.5,
        'Supplementary Exam': 1.2
    }
    
    multiplier = exam_multipliers.get(exam_type, 1.0)
    return max(2, int(base_invigilators * multiplier))

def calculate_required_halls(students_count, available_halls):
    """Calculate how many halls are needed based on student count"""
    if not available_halls:
        return [], 0
    
    # Sort halls by capacity (descending)
    sorted_halls = sorted(available_halls, key=lambda x: x['capacity'], reverse=True)
    
    assigned_halls = []
    remaining_students = students_count
    
    for hall in sorted_halls:
        if remaining_students <= 0:
            break
        assigned_halls.append(hall)
        remaining_students -= hall['capacity']
    
    total_capacity = sum(hall['capacity'] for hall in assigned_halls)
    return assigned_halls, total_capacity

def get_duty_requirement(exam_type):
    duty_requirements = {
        'Mid Term': 2,
        'Missed Evaluation': 2,
        'End Sem': 1,
        'Supplementary Exam': 2
    }
    return duty_requirements.get(exam_type, 1)

def get_designation_duties(designation):
    designation_duties = {
        'Professor': 10,
        'Associate Professor': 12,
        'Assistant Professor': 15,
        'Lecturer': 20
    }
    return designation_duties.get(designation, 10)

def reset_semester_duties():
    conn = get_db_connection()
    conn.execute('''
        UPDATE faculty 
        SET remaining_duties = total_duties
    ''')
    conn.commit()
    conn.close()
    flash("Semester duties reset successfully!", "success")

def update_faculty_designations():
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        designation_mapping = {
            'Level1': 'Professor',
            'Level2': 'Associate Professor', 
            'Level3': 'Assistant Professor',
            'Level4': 'Lecturer'
        }
        
        for old_designation, new_designation in designation_mapping.items():
            c.execute("UPDATE faculty SET designation = ? WHERE designation = ?", 
                     (new_designation, old_designation))
            updated_count = c.rowcount
            if updated_count > 0:
                print(f"Updated {updated_count} faculty from {old_designation} to {new_designation}")
        
        conn.commit()
        print("Faculty designations updated successfully!")
        
    except Exception as e:
        print(f"Error updating designations: {e}")
        conn.rollback()
    finally:
        conn.close()

def remove_duplicate_faculty():
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Find and remove duplicates
        c.execute("""
            DELETE FROM faculty 
            WHERE faculty_id NOT IN (
                SELECT MIN(faculty_id) 
                FROM faculty 
                GROUP BY name, designation, department
            )
        """)
        
        deleted_count = c.rowcount
        if deleted_count > 0:
            print(f"Removed {deleted_count} duplicate faculty entries")
        
        conn.commit()
        
    except Exception as e:
        print(f"Error removing duplicates: {e}")
        conn.rollback()
    finally:
        conn.close()

# ---------- AUTHENTICATION ROUTES ----------
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = sanitize_input(request.form['password'])
        
        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return render_template('login.html')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == password:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ---------- MAIN ROUTES ----------
@app.route("/")
@login_required
def index():
    conn = get_db_connection()
    
    # Get statistics for dashboard
    faculty_count = conn.execute("SELECT COUNT(*) FROM faculty WHERE is_available = TRUE").fetchone()[0]
    hall_count = conn.execute("SELECT COUNT(*) FROM halls WHERE is_available = TRUE").fetchone()[0]
    upcoming_exams = conn.execute("""
        SELECT COUNT(*) FROM exams 
        WHERE date >= date('now') 
        ORDER BY date LIMIT 5
    """).fetchone()[0]
    
    # Get recent duty allocations
    recent_allocations = conn.execute("""
        SELECT e.exam_type, e.date, e.session, f.name as faculty_name, f.designation
        FROM duty_allocations da
        JOIN exams e ON da.exam_id = e.exam_id
        JOIN faculty f ON da.faculty_id = f.faculty_id
        WHERE e.date >= date('now')
        ORDER BY e.date, e.session
        LIMIT 5
    """).fetchall()
    
    conn.close()
    
    return render_template("index.html", 
                         faculty_count=faculty_count,
                         hall_count=hall_count,
                         upcoming_exams=upcoming_exams,
                         recent_allocations=recent_allocations)

@app.route("/faculty")
@login_required
def faculty():
    remove_duplicate_faculty()
    update_faculty_designations()
    
    conn = get_db_connection()
    faculty = conn.execute("""
        SELECT *, (total_duties - remaining_duties) as duties_completed 
        FROM faculty 
        ORDER BY department, designation, name
    """).fetchall()
    conn.close()
    return render_template("faculty.html", faculty=faculty)

@app.route("/add_faculty", methods=["POST"])
@login_required
def add_faculty():
    try:
        name = sanitize_input(request.form["name"])
        designation = sanitize_input(request.form["designation"])
        department = sanitize_input(request.form["department"])
        
        if not name or not designation or not department:
            flash("All fields are required!", "error")
            return redirect(url_for("faculty"))
        
        total_duties = get_designation_duties(designation)
        
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO faculty (name, designation, department, total_duties, remaining_duties) 
            VALUES (?, ?, ?, ?, ?)
        """, (name, designation, department, total_duties, total_duties))
        conn.commit()
        conn.close()
        
        flash("Faculty member added successfully!", "success")
        return redirect(url_for("faculty"))
        
    except Exception as e:
        flash(f"Error adding faculty: {str(e)}", "error")
        return redirect(url_for("faculty"))

@app.route("/toggle_faculty/<int:faculty_id>")
@login_required
def toggle_faculty(faculty_id):
    try:
        conn = get_db_connection()
        faculty = conn.execute("SELECT * FROM faculty WHERE faculty_id = ?", (faculty_id,)).fetchone()
        
        if not faculty:
            flash("Faculty member not found!", "error")
            return redirect(url_for("faculty"))
            
        new_status = not faculty['is_available']
        
        conn.execute("UPDATE faculty SET is_available = ? WHERE faculty_id = ?", (new_status, faculty_id))
        conn.commit()
        conn.close()
        
        status = "available" if new_status else "unavailable"
        flash(f"Faculty member marked as {status}!", "success")
        return redirect(url_for("faculty"))
        
    except Exception as e:
        flash(f"Error updating faculty status: {str(e)}", "error")
        return redirect(url_for("faculty"))

@app.route("/reset_duties/<int:faculty_id>")
@login_required
def reset_faculty_duties(faculty_id):
    try:
        conn = get_db_connection()
        faculty = conn.execute("SELECT * FROM faculty WHERE faculty_id = ?", (faculty_id,)).fetchone()
        
        if faculty:
            conn.execute("UPDATE faculty SET remaining_duties = total_duties WHERE faculty_id = ?", (faculty_id,))
            conn.commit()
            flash(f"Duties reset for {faculty['name']}!", "success")
        else:
            flash("Faculty member not found!", "error")
        
        conn.close()
        return redirect(url_for("faculty"))
        
    except Exception as e:
        flash(f"Error resetting duties: {str(e)}", "error")
        return redirect(url_for("faculty"))

@app.route("/reset_all_duties")
@login_required
def reset_all_duties():
    try:
        reset_semester_duties()
        return redirect(url_for("faculty"))
    except Exception as e:
        flash(f"Error resetting duties: {str(e)}", "error")
        return redirect(url_for("faculty"))

@app.route("/halls")
@login_required
def halls():
    conn = get_db_connection()
    halls = conn.execute("""
        SELECT h.*, 
               COUNT(eha.exam_id) as upcoming_exams
        FROM halls h
        LEFT JOIN exam_hall_allocations eha ON h.hall_id = eha.hall_id
        LEFT JOIN exams e ON eha.exam_id = e.exam_id AND e.date >= date('now')
        GROUP BY h.hall_id
        ORDER BY h.hall_name
    """).fetchall()
    conn.close()
    return render_template("halls.html", halls=halls)

@app.route("/add_hall", methods=["POST"])
@login_required
def add_hall():
    try:
        hall_name = sanitize_input(request.form["hall_name"])
        capacity = request.form["capacity"]
        
        if not hall_name or not capacity:
            flash("All fields are required!", "error")
            return redirect(url_for("halls"))
        
        capacity = int(capacity)
        if capacity <= 0:
            flash("Capacity must be a positive number!", "error")
            return redirect(url_for("halls"))
        
        conn = get_db_connection()
        conn.execute("INSERT INTO halls (hall_name, capacity) VALUES (?, ?)", (hall_name, capacity))
        conn.commit()
        conn.close()
        
        flash("Hall added successfully!", "success")
        return redirect(url_for("halls"))
        
    except ValueError:
        flash("Capacity must be a valid number!", "error")
        return redirect(url_for("halls"))
    except sqlite3.IntegrityError:
        flash("Hall name already exists!", "error")
        return redirect(url_for("halls"))
    except Exception as e:
        flash(f"Error adding hall: {str(e)}", "error")
        return redirect(url_for("halls"))

@app.route("/toggle_hall/<int:hall_id>")
@login_required
def toggle_hall(hall_id):
    try:
        conn = get_db_connection()
        hall = conn.execute("SELECT * FROM halls WHERE hall_id = ?", (hall_id,)).fetchone()
        
        if not hall:
            flash("Hall not found!", "error")
            return redirect(url_for("halls"))
            
        new_status = not hall['is_available']
        
        conn.execute("UPDATE halls SET is_available = ? WHERE hall_id = ?", (new_status, hall_id))
        conn.commit()
        conn.close()
        
        status = "available" if new_status else "unavailable"
        flash(f"Hall marked as {status}!", "success")
        return redirect(url_for("halls"))
        
    except Exception as e:
        flash(f"Error updating hall status: {str(e)}", "error")
        return redirect(url_for("halls"))

@app.route("/exams")
@login_required
def exams():
    conn = get_db_connection()
    exams = conn.execute("""
        SELECT e.*, 
               COUNT(DISTINCT da.faculty_id) as assigned_invigilators,
               COUNT(DISTINCT eha.hall_id) as assigned_halls,
               SUM(h.capacity) as total_hall_capacity
        FROM exams e 
        LEFT JOIN duty_allocations da ON e.exam_id = da.exam_id 
        LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
        LEFT JOIN halls h ON eha.hall_id = h.hall_id
        GROUP BY e.exam_id 
        ORDER BY e.date, e.session
    """).fetchall()
    conn.close()
    return render_template("exams.html", exams=exams)

@app.route("/add_exam", methods=["POST"])
@login_required
def add_exam():
    try:
        exam_type = sanitize_input(request.form["exam_type"])
        date = sanitize_input(request.form["date"])
        session = sanitize_input(request.form["session"])
        students_count = sanitize_input(request.form["students_count"])
        course_code = sanitize_input(request.form.get("course_code", ""))
        course_name = sanitize_input(request.form.get("course_name", ""))
        
        # Validate required fields
        if not exam_type or not date or not session or not students_count:
            flash("All required fields must be filled!", "error")
            return redirect(url_for("exams"))
        
        # Validate date
        is_valid_date, date_result = validate_date(date)
        if not is_valid_date:
            flash(date_result, "error")
            return redirect(url_for("exams"))
        
        # Validate students count
        is_valid_students, students_result = validate_students_count(students_count)
        if not is_valid_students:
            flash(students_result, "error")
            return redirect(url_for("exams"))
        
        students_count = students_result
        invigilators_required = calculate_invigilators_required(exam_type, students_count)
        
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO exams (exam_type, date, session, invigilators_required, course_code, course_name, students_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (exam_type, date, session, invigilators_required, course_code, course_name, students_count))
        
        exam_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        
        flash(f"Exam added successfully! Required invigilators: {invigilators_required}", "success")
        return redirect(url_for("assign_halls", exam_id=exam_id))
        
    except Exception as e:
        flash(f"Error adding exam: {str(e)}", "error")
        return redirect(url_for("exams"))

@app.route("/assign_invigilators/<int:exam_id>")
@login_required
def assign_invigilators(exam_id):
    try:
        conn = get_db_connection()
        
        # Get exam with hall assignment count
        exam = conn.execute("""
            SELECT e.*, 
                   COUNT(DISTINCT eha.hall_id) as assigned_halls,
                   SUM(h.capacity) as total_hall_capacity
            FROM exams e 
            LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
            LEFT JOIN halls h ON eha.hall_id = h.hall_id
            WHERE e.exam_id = ?
            GROUP BY e.exam_id
        """, (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("exams"))
        
        available_faculty = conn.execute("""
            SELECT f.* FROM faculty f 
            WHERE f.is_available = TRUE 
            AND f.remaining_duties > 0
            AND f.faculty_id NOT IN (
                SELECT da.faculty_id FROM duty_allocations da 
                JOIN exams e ON da.exam_id = e.exam_id 
                WHERE e.date = ? AND e.session = ? AND e.exam_id != ?
            )
            ORDER BY f.designation, f.remaining_duties DESC
        """, (exam['date'], exam['session'], exam_id)).fetchall()
        
        conn.close()
        
        return render_template("assignments.html", 
                             exam=exam, 
                             faculty=available_faculty)
                             
    except Exception as e:
        flash(f"Error loading assignment page: {str(e)}", "error")
        return redirect(url_for("exams"))

@app.route("/make_assignment", methods=["POST"])
@login_required
def make_assignment():
    try:
        exam_id = int(request.form["exam_id"])
        faculty_ids = [int(id) for id in request.form.getlist("faculty_ids")]
        
        if not faculty_ids:
            flash("Please select at least one faculty member!", "error")
            return redirect(url_for("assign_invigilators", exam_id=exam_id))
        
        conn = get_db_connection()
        
        exam = conn.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("exams"))
        
        if len(faculty_ids) < exam['invigilators_required']:
            flash(f"Not enough faculty selected. Required: {exam['invigilators_required']}", "error")
            return redirect(url_for("assign_invigilators", exam_id=exam_id))
        
        # Validate faculty availability
        is_available, availability_message = validate_exam_scheduling(
            exam['date'], exam['session'], faculty_ids
        )
        
        if not is_available:
            flash(availability_message, "error")
            return redirect(url_for("assign_invigilators", exam_id=exam_id))
        
        duty_requirement = get_duty_requirement(exam['exam_type'])
        
        for faculty_id in faculty_ids:
            # Check if faculty has enough remaining duties
            faculty = conn.execute("SELECT * FROM faculty WHERE faculty_id = ?", (faculty_id,)).fetchone()
            if faculty['remaining_duties'] < duty_requirement:
                flash(f"{faculty['name']} doesn't have enough remaining duties!", "error")
                return redirect(url_for("assign_invigilators", exam_id=exam_id))
            
            # Check if faculty is already assigned to this exam
            existing_assignment = conn.execute("""
                SELECT * FROM duty_allocations 
                WHERE exam_id = ? AND faculty_id = ?
            """, (exam_id, faculty_id)).fetchone()
            
            if not existing_assignment:
                conn.execute("""
                    INSERT INTO duty_allocations (exam_id, date, session, faculty_id)
                    VALUES (?, ?, ?, ?)
                """, (exam_id, exam['date'], exam['session'], faculty_id))
            
            # Update faculty duties
            conn.execute("""
                UPDATE faculty 
                SET remaining_duties = remaining_duties - ? 
                WHERE faculty_id = ? AND remaining_duties >= ?
            """, (duty_requirement, faculty_id, duty_requirement))
            
            # Update or insert faculty duties record
            existing_duty = conn.execute("""
                SELECT * FROM faculty_duties 
                WHERE faculty_id = ? AND exam_id = ?
            """, (faculty_id, exam_id)).fetchone()
            
            if existing_duty:
                conn.execute("""
                    UPDATE faculty_duties 
                    SET duties_assigned = ? 
                    WHERE faculty_id = ? AND exam_id = ?
                """, (duty_requirement, faculty_id, exam_id))
            else:
                conn.execute("""
                    INSERT INTO faculty_duties (faculty_id, exam_id, duties_assigned)
                    VALUES (?, ?, ?)
                """, (faculty_id, exam_id, duty_requirement))
        
        conn.commit()
        conn.close()
        
        flash("Invigilators assigned successfully!", "success")
        return redirect(url_for("schedule"))
        
    except Exception as e:
        flash(f"Error assigning invigilators: {str(e)}", "error")
        return redirect(url_for("assign_invigilators", exam_id=exam_id))

@app.route("/assign_halls/<int:exam_id>")
@login_required
def assign_halls(exam_id):
    try:
        conn = get_db_connection()
        
        exam = conn.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("exams"))
        
        # Get already assigned halls with proper capacity calculation
        assigned_halls = conn.execute("""
            SELECT h.* FROM halls h
            JOIN exam_hall_allocations eha ON h.hall_id = eha.hall_id
            WHERE eha.exam_id = ?
        """, (exam_id,)).fetchall()
        
        # Calculate total assigned capacity
        total_assigned_capacity = sum(hall['capacity'] for hall in assigned_halls)
        
        # Get available halls (not assigned to any exam at the same time)
        available_halls = conn.execute("""
            SELECT h.*,
                   CASE 
                       WHEN eha.hall_id IS NOT NULL THEN 1
                       ELSE 0
                   END as already_assigned,
                   CASE 
                       WHEN conflict.conflict_exam IS NOT NULL THEN 'Booked for another exam'
                       ELSE NULL
                   END as conflict
            FROM halls h
            LEFT JOIN exam_hall_allocations eha ON h.hall_id = eha.hall_id AND eha.exam_id = ?
            LEFT JOIN (
                SELECT DISTINCT eha.hall_id, e.exam_type as conflict_exam
                FROM exam_hall_allocations eha
                JOIN exams e ON eha.exam_id = e.exam_id
                WHERE e.date = ? AND e.session = ? AND e.exam_id != ?
            ) conflict ON h.hall_id = conflict.hall_id
            WHERE h.is_available = TRUE
            AND (eha.hall_id IS NOT NULL OR conflict.hall_id IS NULL)
            ORDER BY h.capacity DESC
        """, (exam_id, exam['date'], exam['session'], exam_id)).fetchall()
        
        conn.close()
        
        return render_template("assign_halls.html", 
                             exam=exam, 
                             assigned_halls=assigned_halls,
                             available_halls=available_halls,
                             total_assigned_capacity=total_assigned_capacity)
                             
    except Exception as e:
        flash(f"Error loading hall assignment page: {str(e)}", "error")
        return redirect(url_for("exams"))

@app.route("/make_hall_assignment", methods=["POST"])
@login_required
def make_hall_assignment():
    try:
        exam_id = int(request.form["exam_id"])
        hall_ids = [int(id) for id in request.form.getlist("hall_ids")]
        
        if not hall_ids:
            flash("Please select at least one hall!", "error")
            return redirect(url_for("assign_halls", exam_id=exam_id))
        
        conn = get_db_connection()
        
        exam = conn.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("exams"))
        
        # Calculate total capacity of selected halls
        total_capacity = 0
        for hall_id in hall_ids:
            hall = conn.execute("SELECT capacity FROM halls WHERE hall_id = ?", (hall_id,)).fetchone()
            if hall:
                total_capacity += hall['capacity']
        
        # Check if capacity is sufficient
        if total_capacity < exam['students_count']:
            flash(f"Selected halls capacity ({total_capacity}) is less than required ({exam['students_count']})!", "warning")
        
        # Assign halls
        assigned_count = 0
        for hall_id in hall_ids:
            # Check if hall is already assigned to this exam
            existing = conn.execute("""
                SELECT * FROM exam_hall_allocations 
                WHERE exam_id = ? AND hall_id = ?
            """, (exam_id, hall_id)).fetchone()
            
            if not existing:
                try:
                    conn.execute("""
                        INSERT INTO exam_hall_allocations (exam_id, hall_id)
                        VALUES (?, ?)
                    """, (exam_id, hall_id))
                    assigned_count += 1
                except sqlite3.IntegrityError:
                    # Hall already assigned, skip
                    pass
        
        conn.commit()
        conn.close()
        
        flash(f"{assigned_count} hall(s) assigned successfully! Total capacity: {total_capacity} students", "success")
        return redirect(url_for("assign_invigilators", exam_id=exam_id))
        
    except Exception as e:
        flash(f"Error assigning halls: {str(e)}", "error")
        return redirect(url_for("assign_halls", exam_id=exam_id))

@app.route("/auto_assign_halls/<int:exam_id>")
@login_required
def auto_assign_halls(exam_id):
    try:
        conn = get_db_connection()
        
        exam = conn.execute("SELECT * FROM exams WHERE exam_id = ?", (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("exams"))
        
        # Get available halls (not assigned to any exam at the same time)
        available_halls = conn.execute("""
            SELECT h.*
            FROM halls h
            WHERE h.is_available = TRUE
            AND h.hall_id NOT IN (
                SELECT eha.hall_id 
                FROM exam_hall_allocations eha
                JOIN exams e ON eha.exam_id = e.exam_id
                WHERE e.date = ? AND e.session = ? AND e.exam_id != ?
            )
            ORDER BY h.capacity DESC
        """, (exam['date'], exam['session'], exam_id)).fetchall()
        
        if not available_halls:
            flash("No available halls for auto-assignment!", "warning")
            return redirect(url_for("assign_halls", exam_id=exam_id))
        
        # Auto-assign halls based on capacity using smarter algorithm
        assigned_halls = []
        remaining_students = exam['students_count']
        assigned_count = 0
        total_capacity = 0
        
        # First pass: Try to find halls that can accommodate all students
        for hall in available_halls:
            if hall['capacity'] >= remaining_students:
                # Found a single hall that can accommodate all students
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO exam_hall_allocations (exam_id, hall_id)
                        VALUES (?, ?)
                    """, (exam_id, hall['hall_id']))
                    assigned_halls.append(hall)
                    assigned_count += 1
                    total_capacity += hall['capacity']
                    remaining_students = 0
                    break
                except sqlite3.IntegrityError:
                    continue
        
        # Second pass: If no single hall can accommodate all, use multiple halls
        if remaining_students > 0:
            for hall in available_halls:
                if remaining_students <= 0:
                    break
                
                # Skip if hall is already assigned in first pass
                if any(h['hall_id'] == hall['hall_id'] for h in assigned_halls):
                    continue
                
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO exam_hall_allocations (exam_id, hall_id)
                        VALUES (?, ?)
                    """, (exam_id, hall['hall_id']))
                    assigned_halls.append(hall)
                    assigned_count += 1
                    total_capacity += hall['capacity']
                    remaining_students -= hall['capacity']
                except sqlite3.IntegrityError:
                    continue
        
        conn.commit()
        conn.close()
        
        # Calculate the actual total capacity from assigned halls
        actual_total_capacity = sum(hall['capacity'] for hall in assigned_halls)
        
        if assigned_count > 0:
            if actual_total_capacity >= exam['students_count']:
                flash(f"Auto-assigned {assigned_count} hall(s) successfully! Total capacity: {actual_total_capacity} students (✅ Capacity Satisfied)", "success")
            else:
                flash(f"Auto-assigned {assigned_count} hall(s)! Total capacity: {actual_total_capacity} students. Still need capacity for {exam['students_count'] - actual_total_capacity} more students (⚠️ Insufficient Capacity)", "warning")
        else:
            flash("No halls were auto-assigned. All available halls may already be assigned or have conflicts.", "warning")
        
        return redirect(url_for("assign_halls", exam_id=exam_id))
        
    except Exception as e:
        flash(f"Error auto-assigning halls: {str(e)}", "error")
        return redirect(url_for("assign_halls", exam_id=exam_id))

@app.route("/remove_hall_assignment/<int:exam_id>/<int:hall_id>")
@login_required
def remove_hall_assignment(exam_id, hall_id):
    try:
        conn = get_db_connection()
        
        # Verify the assignment exists
        assignment = conn.execute("""
            SELECT * FROM exam_hall_allocations 
            WHERE exam_id = ? AND hall_id = ?
        """, (exam_id, hall_id)).fetchone()
        
        if assignment:
            conn.execute("""
                DELETE FROM exam_hall_allocations 
                WHERE exam_id = ? AND hall_id = ?
            """, (exam_id, hall_id))
            conn.commit()
            flash("Hall assignment removed successfully!", "success")
        else:
            flash("Hall assignment not found!", "error")
        
        conn.close()
        return redirect(url_for("assign_halls", exam_id=exam_id))
        
    except Exception as e:
        flash(f"Error removing hall assignment: {str(e)}", "error")
        return redirect(url_for("assign_halls", exam_id=exam_id))
@app.route("/schedule")
@login_required
def schedule():
    # Get sorting and filtering parameters
    sort_by = request.args.get('sort_by', 'e.date')
    sort_order = request.args.get('sort_order', 'asc')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    exam_type = request.args.get('exam_type')
    session_filter = request.args.get('session')

    # Build the base query
    base_query = """
        SELECT da.allocation_id, e.exam_id, e.date, e.session, e.exam_type, e.course_code, e.course_name, e.students_count,
               f.faculty_id, f.name as faculty_name, f.designation, f.department,
               fd.duties_assigned,
               GROUP_CONCAT(DISTINCT h.hall_name) as hall_names,
               SUM(h.capacity) as total_hall_capacity
        FROM duty_allocations da
        JOIN faculty f ON da.faculty_id = f.faculty_id
        JOIN exams e ON da.exam_id = e.exam_id
        LEFT JOIN faculty_duties fd ON f.faculty_id = fd.faculty_id AND e.exam_id = fd.exam_id
        LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
        LEFT JOIN halls h ON eha.hall_id = h.hall_id
        WHERE 1=1
    """
    
    params = []
    
    # Add date range filter
    if start_date:
        base_query += " AND e.date >= ?"
        params.append(start_date)
    if end_date:
        base_query += " AND e.date <= ?"
        params.append(end_date)
    
    # Add exam type filter
    if exam_type:
        base_query += " AND e.exam_type = ?"
        params.append(exam_type)
    
    # Add session filter
    if session_filter:
        base_query += " AND e.session = ?"
        params.append(session_filter)
    
    # Add grouping
    base_query += " GROUP BY da.allocation_id"
    
    # Add sorting with table prefixes to avoid ambiguity
    sort_mapping = {
        'date': 'e.date',
        'session': 'e.session',
        'exam_type': 'e.exam_type',
        'faculty_name': 'f.name',
        'department': 'f.department',
        'designation': 'f.designation',
        'course_code': 'e.course_code'
    }
    
    # Get the actual column name with table prefix
    actual_sort_column = sort_mapping.get(sort_by, 'e.date')
    
    # Validate sort order
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'ASC'
    
    base_query += f" ORDER BY {actual_sort_column} {sort_order.upper()}"
    
    conn = get_db_connection()
    schedule_data = conn.execute(base_query, params).fetchall()
    conn.close()
    
    return render_template("schedule.html", schedule=schedule_data)
@app.route("/upload_faculty", methods=["POST"])
@login_required
def upload_faculty():
    try:
        if 'file' not in request.files:
            flash("No file uploaded", "error")
            return redirect(url_for("faculty"))
        
        file = request.files['file']
        if not file or file.filename == '':
            flash("No file selected", "error")
            return redirect(url_for("faculty"))
        
        if not file.filename.endswith('.csv'):
            flash("Please upload a CSV file", "error")
            return redirect(url_for("faculty"))
        
        # Read and validate CSV
        stream = file.stream.read().decode("UTF8")
        csv_data = csv.reader(stream.splitlines())
        
        conn = get_db_connection()
        headers = next(csv_data, None)  # Skip header
        
        if not headers or len(headers) < 3:
            flash("CSV file must have at least 3 columns: Name, Designation, Department", "error")
            return redirect(url_for("faculty"))
        
        success_count = 0
        error_count = 0
        
        for row_num, row in enumerate(csv_data, start=2):
            if len(row) >= 3:
                name = sanitize_input(row[0])
                designation = sanitize_input(row[1])
                department = sanitize_input(row[2])
                
                if name and designation and department:
                    try:
                        total_duties = get_designation_duties(designation)
                        conn.execute("""
                            INSERT OR IGNORE INTO faculty (name, designation, department, total_duties, remaining_duties) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (name, designation, department, total_duties, total_duties))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error importing row {row_num}: {e}")
                else:
                    error_count += 1
        
        conn.commit()
        conn.close()
        
        if success_count > 0:
            flash(f"Faculty data uploaded successfully! {success_count} records imported.", "success")
        if error_count > 0:
            flash(f"{error_count} records failed to import. Please check the CSV format.", "warning")
            
    except Exception as e:
        flash(f"Error uploading file: {str(e)}", "error")
    
    return redirect(url_for("faculty"))
@app.route("/reports")
@login_required
def reports():
    # Get filter parameters
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    department = request.args.get('department', '')
    exam_type = request.args.get('exam_type', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    conn = get_db_connection()
    
    # Faculty Workload with filtering
    faculty_query = """
        SELECT f.faculty_id, f.name, f.designation, f.department,
               f.total_duties, f.remaining_duties,
               (f.total_duties - f.remaining_duties) as duties_completed,
               COUNT(DISTINCT da.exam_id) as exams_assigned
        FROM faculty f
        LEFT JOIN duty_allocations da ON f.faculty_id = da.faculty_id
        LEFT JOIN exams e ON da.exam_id = e.exam_id
        WHERE 1=1
    """
    faculty_params = []
    
    if date_from:
        faculty_query += " AND (e.date >= ? OR e.date IS NULL)"
        faculty_params.append(date_from)
    if date_to:
        faculty_query += " AND (e.date <= ? OR e.date IS NULL)"
        faculty_params.append(date_to)
    if department:
        faculty_query += " AND f.department = ?"
        faculty_params.append(department)
    
    faculty_query += " GROUP BY f.faculty_id"
    
    # Add sorting
    sort_columns = {
        'name': 'f.name',
        'department': 'f.department',
        'designation': 'f.designation',
        'duties_completed': 'duties_completed',
        'utilization': '(f.total_duties - f.remaining_duties) * 100.0 / f.total_duties'
    }
    faculty_query += f" ORDER BY {sort_columns.get(sort_by, 'f.name')} {sort_order.upper()}"
    
    faculty_workload = conn.execute(faculty_query, faculty_params).fetchall()
    
    # Exam Assignments with filtering
    exam_query = """
        SELECT e.exam_id, e.exam_type, e.date, e.session, e.course_code, 
               e.course_name, e.students_count, e.invigilators_required,
               COUNT(DISTINCT da.faculty_id) as faculty_assigned,
               COUNT(DISTINCT eha.hall_id) as halls_assigned,
               SUM(h.capacity) as total_hall_capacity
        FROM exams e
        LEFT JOIN duty_allocations da ON e.exam_id = da.exam_id
        LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
        LEFT JOIN halls h ON eha.hall_id = h.hall_id
        WHERE 1=1
    """
    exam_params = []
    
    if date_from:
        exam_query += " AND e.date >= ?"
        exam_params.append(date_from)
    if date_to:
        exam_query += " AND e.date <= ?"
        exam_params.append(date_to)
    if exam_type:
        exam_query += " AND e.exam_type = ?"
        exam_params.append(exam_type)
    if department:
        # Fixed the multi-line string issue
        exam_query += " AND EXISTS (SELECT 1 FROM duty_allocations da2 JOIN faculty f ON da2.faculty_id = f.faculty_id WHERE da2.exam_id = e.exam_id AND f.department = ?)"
        exam_params.append(department)
    
    exam_query += " GROUP BY e.exam_id ORDER BY e.date DESC, e.session"
    
    exam_assignments = conn.execute(exam_query, exam_params).fetchall()
    
    # Department Statistics
    dept_stats = conn.execute("""
        SELECT department, 
               COUNT(*) as faculty_count,
               SUM(total_duties - remaining_duties) as completed_duties,
               SUM(total_duties) as total_duties,
               ROUND(AVG((total_duties - remaining_duties) * 100.0 / total_duties), 1) as avg_utilization
        FROM faculty 
        GROUP BY department 
        ORDER BY avg_utilization DESC
    """).fetchall()
    
    # Hall Utilization Statistics
    hall_stats = conn.execute("""
        SELECT h.hall_name, h.capacity,
               COUNT(DISTINCT eha.exam_id) as total_exams,
               COUNT(DISTINCT CASE WHEN e.date >= date('now') THEN eha.exam_id END) as upcoming_exams
        FROM halls h
        LEFT JOIN exam_hall_allocations eha ON h.hall_id = eha.hall_id
        LEFT JOIN exams e ON eha.exam_id = e.exam_id
        GROUP BY h.hall_id
        ORDER BY h.capacity DESC
    """).fetchall()
    
    # Monthly Statistics
    monthly_stats = conn.execute("""
        SELECT strftime('%Y-%m', date) as month,
               COUNT(DISTINCT exam_id) as exam_count,
               COUNT(*) as assignment_count,
               SUM(students_count) as total_students
        FROM exams 
        WHERE date >= date('now', '-6 months')
        GROUP BY month 
        ORDER BY month DESC
    """).fetchall()
    
    # Get unique departments for filter dropdown
    departments = conn.execute("SELECT DISTINCT department FROM faculty ORDER BY department").fetchall()
    
    conn.close()
    
    return render_template("reports.html", 
                         faculty_workload=faculty_workload,
                         exam_assignments=exam_assignments,
                         dept_stats=dept_stats,
                         hall_stats=hall_stats,
                         monthly_stats=monthly_stats,
                         departments=departments,
                         filters={
                             'date_from': date_from,
                             'date_to': date_to,
                             'department': department,
                             'exam_type': exam_type,
                             'sort_by': sort_by,
                             'sort_order': sort_order
                         })
@app.route("/export_schedule")
@login_required
def export_schedule():
    conn = get_db_connection()
    schedule_data = conn.execute("""
        SELECT e.date, e.session, e.exam_type, e.course_code, e.course_name, e.students_count,
               f.name as faculty_name, f.designation, f.department,
               fd.duties_assigned,
               GROUP_CONCAT(DISTINCT h.hall_name) as hall_names,
               SUM(h.capacity) as total_hall_capacity
        FROM duty_allocations da
        JOIN faculty f ON da.faculty_id = f.faculty_id
        JOIN exams e ON da.exam_id = e.exam_id
        LEFT JOIN faculty_duties fd ON f.faculty_id = fd.faculty_id AND e.exam_id = fd.exam_id
        LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
        LEFT JOIN halls h ON eha.hall_id = h.hall_id
        GROUP BY da.allocation_id
        ORDER BY e.date, e.session, f.department
    """).fetchall()
    
    conn.close()
    
    def generate():
        data = []
        data.append(['Date', 'Session', 'Exam Type', 'Course Code', 'Course Name', 'Students Count',
                    'Faculty', 'Designation', 'Department', 'Halls', 'Total Capacity', 'Duties Assigned'])
        
        for row in schedule_data:
            data.append([
                row['date'], row['session'], row['exam_type'], row['course_code'],
                row['course_name'], row['students_count'], row['faculty_name'], 
                row['designation'], row['department'], row['hall_names'] or 'Not assigned',
                row['total_hall_capacity'] or 0,
                row['duties_assigned'] or 1
            ])
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(data)
        output.seek(0)
        
        yield output.getvalue()
    
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=invigilation_schedule.csv"}
    )
@app.route("/delete_exam/<int:exam_id>")
@login_required
def delete_exam(exam_id):
    try:
        conn = get_db_connection()
        
        # Get exam details before deleting
        exam = conn.execute("""
            SELECT e.*, 
                   COUNT(DISTINCT da.faculty_id) as faculty_count,
                   COUNT(DISTINCT eha.hall_id) as hall_count
            FROM exams e
            LEFT JOIN duty_allocations da ON e.exam_id = da.exam_id
            LEFT JOIN exam_hall_allocations eha ON e.exam_id = eha.exam_id
            WHERE e.exam_id = ?
            GROUP BY e.exam_id
        """, (exam_id,)).fetchone()
        
        if not exam:
            flash("Exam not found!", "error")
            return redirect(url_for("schedule"))
        
        # Get all faculty assignments for this exam to restore duties
        faculty_assignments = conn.execute("""
            SELECT da.faculty_id, f.name, fd.duties_assigned, e.exam_type
            FROM duty_allocations da
            JOIN faculty f ON da.faculty_id = f.faculty_id
            JOIN exams e ON da.exam_id = e.exam_id
            LEFT JOIN faculty_duties fd ON f.faculty_id = fd.faculty_id AND e.exam_id = fd.exam_id
            WHERE da.exam_id = ?
        """, (exam_id,)).fetchall()
        
        # Restore duties for all assigned faculty
        for assignment in faculty_assignments:
            duty_requirement = get_duty_requirement(assignment['exam_type'])
            duties_to_restore = assignment['duties_assigned'] or duty_requirement
            
            conn.execute("""
                UPDATE faculty 
                SET remaining_duties = remaining_duties + ? 
                WHERE faculty_id = ?
            """, (duties_to_restore, assignment['faculty_id']))
        
        # Delete all related records in correct order (to maintain referential integrity)
        
        # 1. Delete faculty duties records
        conn.execute("DELETE FROM faculty_duties WHERE exam_id = ?", (exam_id,))
        
        # 2. Delete duty allocations
        conn.execute("DELETE FROM duty_allocations WHERE exam_id = ?", (exam_id,))
        
        # 3. Delete hall allocations
        conn.execute("DELETE FROM exam_hall_allocations WHERE exam_id = ?", (exam_id,))
        
        # 4. Finally delete the exam itself
        conn.execute("DELETE FROM exams WHERE exam_id = ?", (exam_id,))
        
        conn.commit()
        conn.close()
        
        flash(f"Exam deleted successfully! Removed {exam['faculty_count']} faculty assignments and {exam['hall_count']} hall allocations.", "success")
        return redirect(url_for("schedule"))
        
    except Exception as e:
        flash(f"Error deleting exam: {str(e)}", "error")
        return redirect(url_for("schedule"))
@app.route("/delete_assignment/<int:allocation_id>")
@login_required
def delete_assignment(allocation_id):
    try:
        conn = get_db_connection()
        
        # Get assignment details before deleting
        assignment = conn.execute("""
            SELECT da.*, e.exam_type, f.name as faculty_name, fd.duties_assigned
            FROM duty_allocations da
            JOIN exams e ON da.exam_id = e.exam_id
            JOIN faculty f ON da.faculty_id = f.faculty_id
            LEFT JOIN faculty_duties fd ON f.faculty_id = fd.faculty_id AND e.exam_id = fd.exam_id
            WHERE da.allocation_id = ?
        """, (allocation_id,)).fetchone()
        
        if not assignment:
            flash("Assignment not found!", "error")
            return redirect(url_for("schedule"))
        
        # Get duty requirement for this exam type
        duty_requirement = get_duty_requirement(assignment['exam_type'])
        duties_to_restore = assignment['duties_assigned'] or duty_requirement
        
        # Delete from duty_allocations
        conn.execute("DELETE FROM duty_allocations WHERE allocation_id = ?", (allocation_id,))
        
        # Delete from faculty_duties
        conn.execute("""
            DELETE FROM faculty_duties 
            WHERE faculty_id = ? AND exam_id = ?
        """, (assignment['faculty_id'], assignment['exam_id']))
        
        # Restore faculty duties
        conn.execute("""
            UPDATE faculty 
            SET remaining_duties = remaining_duties + ? 
            WHERE faculty_id = ?
        """, (duties_to_restore, assignment['faculty_id']))
        
        conn.commit()
        conn.close()
        
        flash(f"Assignment removed successfully! {duties_to_restore} duty/duties restored to {assignment['faculty_name']}.", "success")
        return redirect(url_for("schedule"))
        
    except Exception as e:
        flash(f"Error deleting assignment: {str(e)}", "error")
        return redirect(url_for("schedule"))
@app.route("/database-simple")
@login_required
def database_simple():
    """Simple text-based database display for debugging"""
    conn = get_db_connection()
    
    # Get all table names
    tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """).fetchall()
    
    # Start building the output
    output = "<pre style='font-family: monospace; font-size: 14px; background: #f8f9fa; padding: 20px;'>"
    output += "DATABASE TABLES - INVIGILATION SYSTEM\n"
    output += "=======================================\n\n"
    
    for table in tables:
        table_name = table['name']
        output += f"TABLE: {table_name}\n"
        output += "-" * (len(table_name) + 7) + "\n"
        
        try:
            # Get column information
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            column_names = [col['name'] for col in columns]
            output += f"Columns: {', '.join(column_names)}\n"
            
            # Get the data
            data = conn.execute(f"SELECT * FROM {table_name}").fetchall()
            output += f"Total rows: {len(data)}\n\n"
            
            # Display the data
            if data:
                # Show column headers
                output += "| " + " | ".join(f"{col:15}" for col in column_names) + " |\n"
                output += "|" + "|".join(["-" * 17] * len(column_names)) + "|\n"
                
                # Show each row
                for row in data:
                    row_values = []
                    for col in column_names:
                        value = row[col]
                        if value is None:
                            display_value = "NULL"
                        else:
                            display_value = str(value)
                        # Truncate long values for display
                        if len(display_value) > 15:
                            display_value = display_value[:12] + "..."
                        row_values.append(f"{display_value:15}")
                    output += "| " + " | ".join(row_values) + " |\n"
            else:
                output += "No data in this table\n"
            
        except sqlite3.Error as e:
            output += f"ERROR reading table: {str(e)}\n"
        
        output += "\n" + "="*50 + "\n\n"
    
    conn.close()
    output += "</pre>"
    
    # Add a navigation header
    nav_header = """
    <nav style="background: #343a40; padding: 10px; margin-bottom: 20px;">
        <a href="/" style="color: white; text-decoration: none; margin-right: 15px;">Dashboard</a>
        <a href="/database-simple" style="color: white; text-decoration: none; margin-right: 15px;">Database View</a>
        <a href="/logout" style="color: white; text-decoration: none;">Logout</a>
    </nav>
    """
    
    return nav_header + output


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)