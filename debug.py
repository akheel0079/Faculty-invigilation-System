import os
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "seating.db"

def clear_database():
    """Completely clear all data from the database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        print("🔧 Starting database reset...")
        
        # Get counts before deletion
        tables = [
            'faculty', 'halls', 'exams', 'duty_allocations', 
            'faculty_duties', 'exam_hall_allocations', 'users'
        ]
        
        print("\n📊 Current database status:")
        for table in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"   {table:20} : {count} records")
            except:
                print(f"   {table:20} : Table doesn't exist")
        
        # Delete all data from tables (in correct order to maintain referential integrity)
        print("\n🗑️  Deleting data...")
        
        # 1. Delete dependent tables first
        c.execute("DELETE FROM duty_allocations")
        print("   ✅ duty_allocations cleared")
        
        c.execute("DELETE FROM faculty_duties")
        print("   ✅ faculty_duties cleared")
        
        c.execute("DELETE FROM exam_hall_allocations")
        print("   ✅ exam_hall_allocations cleared")
        
        # 2. Delete main tables
        c.execute("DELETE FROM exams")
        print("   ✅ exams cleared")
        
        c.execute("DELETE FROM halls")
        print("   ✅ halls cleared")
        
        c.execute("DELETE FROM faculty")
        print("   ✅ faculty cleared")
        
        # 3. Keep users table but reset if needed
        c.execute("DELETE FROM users WHERE username != 'admin'")
        print("   ✅ non-admin users cleared")
        
        # Reset admin password to default
        c.execute("UPDATE users SET password = 'admin123' WHERE username = 'admin'")
        print("   ✅ admin password reset")
        
        conn.commit()
        print("\n✅ Database cleared successfully!")
        
        # Show empty status
        print("\n📊 Database status after reset:")
        for table in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"   {table:20} : {count} records")
            except:
                print(f"   {table:20} : Table doesn't exist")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")

def recreate_sample_data():
    """Recreate sample data for testing"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        print("\n🎯 Creating sample data...")
        
        # Sample faculty data
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
        print("   ✅ Sample faculty created")
        
        # Sample halls data
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
        print("   ✅ Sample halls created")
        
        # Sample exams data
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
        print("   ✅ Sample exams created")
        
        conn.commit()
        conn.close()
        
        print("✅ Sample data created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")

def reset_faculty_duties():
    """Reset all faculty duties to their maximum"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        print("\n🔄 Resetting faculty duties...")
        
        # Reset duties based on designation
        c.execute("""
            UPDATE faculty 
            SET remaining_duties = CASE 
                WHEN designation = 'Professor' THEN 10
                WHEN designation = 'Associate Professor' THEN 12
                WHEN designation = 'Assistant Professor' THEN 15
                WHEN designation = 'Lecturer' THEN 20
                ELSE 10
            END,
            total_duties = CASE 
                WHEN designation = 'Professor' THEN 10
                WHEN designation = 'Associate Professor' THEN 12
                WHEN designation = 'Assistant Professor' THEN 15
                WHEN designation = 'Lecturer' THEN 20
                ELSE 10
            END
        """)
        
        updated_count = c.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Reset duties for {updated_count} faculty members")
        
    except Exception as e:
        print(f"❌ Error resetting faculty duties: {e}")

def show_database_status():
    """Show current database status"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        print("\n📈 DATABASE STATUS REPORT")
        print("=" * 50)
        
        # Table counts
        tables = [
            'faculty', 'halls', 'exams', 'duty_allocations', 
            'faculty_duties', 'exam_hall_allocations', 'users'
        ]
        
        for table in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"📊 {table:20} : {count:3} records")
            except:
                print(f"📊 {table:20} : Table doesn't exist")
        
        # Faculty status
        print("\n👥 FACULTY STATUS:")
        c.execute("""
            SELECT designation, COUNT(*), 
                   SUM(remaining_duties), AVG(remaining_duties)
            FROM faculty 
            GROUP BY designation
        """)
        for row in c.fetchall():
            print(f"   {row[0]:20} : {row[1]:2} faculty, {row[2]:3} total duties remaining")
        
        # Exam status
        print("\n📅 EXAM STATUS:")
        c.execute("""
            SELECT exam_type, COUNT(*), SUM(students_count)
            FROM exams 
            GROUP BY exam_type
        """)
        for row in c.fetchall():
            print(f"   {row[0]:20} : {row[1]:2} exams, {row[2]:4} total students")
        
        # Hall status
        print("\n🏛️  HALL STATUS:")
        c.execute("""
            SELECT 
                COUNT(*) as total_halls,
                SUM(capacity) as total_capacity,
                AVG(capacity) as avg_capacity
            FROM halls 
            WHERE is_available = 1
        """)
        row = c.fetchone()
        print(f"   Available Halls      : {row[0]} halls")
        print(f"   Total Capacity       : {row[1]} students")
        print(f"   Average Capacity     : {row[2]:.1f} students")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing database status: {e}")

def backup_database():
    """Create a backup of the current database"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"seating_backup_{timestamp}.db"
        
        # Simple file copy for backup
        if os.path.exists(DB_NAME):
            with open(DB_NAME, 'rb') as original:
                with open(backup_name, 'wb') as backup:
                    backup.write(original.read())
            print(f"✅ Database backed up as: {backup_name}")
        else:
            print("❌ Database file not found for backup")
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")

def main():
    """Main menu for debug operations"""
    print("🔧 FACULTY INVIGILATION SYSTEM - DEBUG TOOL")
    print("=" * 50)
    
    while True:
        print("\nPlease select an option:")
        print("1. 📊 Show Database Status")
        print("2. 🗑️  Clear All Data (Reset Database)")
        print("3. 🎯 Clear & Create Sample Data")
        print("4. 🔄 Reset Faculty Duties Only")
        print("5. 💾 Backup Current Database")
        print("6. 🚪 Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            show_database_status()
            
        elif choice == '2':
            confirm = input("❌ WARNING: This will DELETE ALL DATA! Type 'YES' to confirm: ")
            if confirm.upper() == 'YES':
                backup_database()  # Backup first
                clear_database()
            else:
                print("❌ Operation cancelled.")
                
        elif choice == '3':
            confirm = input("🔄 This will DELETE ALL DATA and create sample data. Type 'YES' to confirm: ")
            if confirm.upper() == 'YES':
                backup_database()  # Backup first
                clear_database()
                recreate_sample_data()
                show_database_status()
            else:
                print("❌ Operation cancelled.")
                
        elif choice == '4':
            reset_faculty_duties()
            show_database_status()
            
        elif choice == '5':
            backup_database()
            
        elif choice == '6':
            print("👋 Exiting debug tool. Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    # Check if database exists
    if not os.path.exists(DB_NAME):
        print("❌ Database file not found!")
        print("💡 Please make sure your Flask app has created the database first.")
    else:
        main()