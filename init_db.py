import sqlite3
import os
from datetime import datetime, timedelta

DB_NAME = "seating.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check if users table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table_exists = c.fetchone() is not None
    
    # Faculty table - matches app.py
    c.execute('''CREATE TABLE IF NOT EXISTS faculty (
                    faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    designation TEXT CHECK(designation IN ('Professor', 'Assistant Professor', 'Associate Professor', 'Lecturer')) NOT NULL,
                    department TEXT NOT NULL,
                    total_duties INTEGER DEFAULT 0,
                    remaining_duties INTEGER DEFAULT 0,
                    is_available BOOLEAN DEFAULT TRUE
                )''')
    
    # Halls table - matches app.py
    c.execute('''CREATE TABLE IF NOT EXISTS halls (
                    hall_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hall_name TEXT NOT NULL UNIQUE,
                    capacity INTEGER NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE
                )''')
    
    # Exams table - UPDATED to match app.py structure (removed rooms_required, added students_count)
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
    
    # Faculty duties table - matches app.py
    c.execute('''CREATE TABLE IF NOT EXISTS faculty_duties (
                    duty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_id INTEGER NOT NULL,
                    exam_id INTEGER NOT NULL,
                    duties_assigned INTEGER DEFAULT 1,
                    FOREIGN KEY (faculty_id) REFERENCES faculty (faculty_id),
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id)
                )''')
    
    # Duty allocations table - matches app.py
    c.execute('''CREATE TABLE IF NOT EXISTS duty_allocations (
                    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    session TEXT NOT NULL,
                    faculty_id INTEGER NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id),
                    FOREIGN KEY (faculty_id) REFERENCES faculty (faculty_id)
                )''')
    
    # Exam hall allocations table - ADDED to match app.py
    c.execute('''CREATE TABLE IF NOT EXISTS exam_hall_allocations (
                    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    hall_id INTEGER NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams (exam_id),
                    FOREIGN KEY (hall_id) REFERENCES halls (hall_id),
                    UNIQUE(exam_id, hall_id)
                )''')
    
    # Users table - FIXED: Use CREATE TABLE IF NOT EXISTS
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'admin'
                )''')
    
    # Always ensure admin user exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    admin_exists = c.fetchone()[0] > 0
    
    if not admin_exists:
        c.execute('''INSERT INTO users (username, password, role)
                     VALUES (?, ?, ?)''', ('admin', 'admin123', 'admin'))
        print("Added default admin user")
    else:
        print("Admin user already exists")
    
    # Insert sample faculty data only if table is empty
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
            ('Prof. Moore', 'Lecturer', 'Chemistry', 20, 20, True),
            ('Dr. Taylor', 'Professor', 'Electronics', 10, 10, True),
            ('Prof. Anderson', 'Associate Professor', 'Mechanical', 12, 12, True)
        ]
        
        c.executemany('''INSERT INTO faculty (name, designation, department, total_duties, remaining_duties, is_available)
                         VALUES (?, ?, ?, ?, ?, ?)''', faculty_data)
        print("Inserted sample faculty data")
    
    # Insert sample halls data only if table is empty
    c.execute("SELECT COUNT(*) FROM halls")
    if c.fetchone()[0] == 0:
        halls_data = [
            ('Room 101', 60, True),
            ('Room 102', 60, True),
            ('Room 201', 80, True),
            ('Room 202', 80, True),
            ('Main Hall', 120, True),
            ('Auditorium', 200, True),
            ('Lab A', 40, True),
            ('Lab B', 40, True)
        ]
        
        c.executemany('''INSERT INTO halls (hall_name, capacity, is_available)
                         VALUES (?, ?, ?)''', halls_data)
        print("Inserted sample halls data")
    
    # Insert sample exams data only if table is empty - UPDATED to match app.py structure
    c.execute("SELECT COUNT(*) FROM exams")
    if c.fetchone()[0] == 0:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        exams_data = [
            # exam_type, date, session, invigilators_required, course_code, course_name, students_count
            ('Mid Term', tomorrow, 'Forenoon', 4, 'CS101', 'Introduction to Programming', 100),
            ('End Sem', tomorrow, 'Afternoon', 6, 'MA201', 'Advanced Mathematics', 180),
            ('Missed Evaluation', day_after, 'Forenoon', 2, 'PH101', 'Physics Fundamentals', 40),
            ('Supplementary Exam', day_after, 'Afternoon', 4, 'CH201', 'Organic Chemistry', 80)
        ]
        
        c.executemany('''INSERT INTO exams (exam_type, date, session, invigilators_required, course_code, course_name, students_count)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', exams_data)
        print("Inserted sample exams data")
    
    conn.commit()
    conn.close()
    print("Database initialization completed successfully!")

def get_designation_duties(designation):
    designation_duties = {
        'Professor': 10,
        'Associate Professor': 12,
        'Assistant Professor': 15,
        'Lecturer': 20
    }
    return designation_duties.get(designation, 10)

def reset_all_duties():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    faculty = c.execute("SELECT faculty_id, designation FROM faculty").fetchall()
    
    for faculty_id, designation in faculty:
        total_duties = get_designation_duties(designation)
        c.execute("UPDATE faculty SET total_duties = ?, remaining_duties = ? WHERE faculty_id = ?",
                 (total_duties, total_duties, faculty_id))
    
    c.execute("DELETE FROM duty_allocations")
    c.execute("DELETE FROM faculty_duties")
    
    conn.commit()
    conn.close()
    print("All duties reset successfully!")

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

def view_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n--- {table_name} ---")
        try:
            c.execute(f"SELECT * FROM {table_name}")
            rows = c.fetchall()
            if rows:
                col_names = [description[0] for description in c.description]
                print("Columns:", col_names)
                for row in rows:
                    print(row)
            else:
                print("No data")
        except sqlite3.Error as e:
            print(f"Error reading table {table_name}: {e}")
    
    conn.close()

def verify_admin_user():
    """Verify that admin user exists and credentials are correct"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_user = c.fetchone()
    
    if admin_user:
        print(f"Admin user found: Username: {admin_user['username']}, Password: {admin_user['password']}, Role: {admin_user['role']}")
    else:
        print("Admin user NOT found!")
    
    conn.close()
    return admin_user

if __name__ == "__main__":
    print("Initializing database...")
    
    # Delete existing database to start fresh
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("Removed existing database file")
    
    init_db()
    
    print("\nVerifying admin user...")
    verify_admin_user()
    
    print("\nDatabase contents:")
    view_tables()
    
    print("\nLogin credentials:")
    print("Username: admin")
    print("Password: admin123")