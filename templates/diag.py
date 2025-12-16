from graphviz import Digraph

# Initialize Digraph
dot = Digraph(name="ERD", format="png")
dot.attr(rankdir="LR", size="10")

# Entities with attributes
entities = {
    "Faculty": [
        "faculty_id (PK)",
        "name",
        "email (Unique)",
        "department_id (FK)",
        "designation",
        "max_hours_per_week",
        "total_assigned_hours (Calc)",
        "is_available"
    ],
    "Department": [
        "department_id (PK)",
        "department_code (Unique)",
        "department_name"
    ],
    "Course": [
        "course_id (PK)",
        "course_code (Unique)",
        "course_name",
        "department_id (FK)"
    ],
    "Exam": [
        "exam_id (PK)",
        "exam_type",
        "course_id (FK)",
        "date",
        "start_time",
        "duration_minutes",
        "session (Calc)",
        "invigilators_required",
        "exam_series_id (FK, Nullable)"
    ],
    "ExamSeries": [
        "exam_series_id (PK)",
        "name",
        "start_date",
        "end_date",
        "default_session"
    ],
    "Hall": [
        "hall_id (PK)",
        "hall_name (Unique)",
        "capacity",
        "is_available"
    ],
    "Assignment": [
        "assignment_id (PK)",
        "exam_id (FK)",
        "hall_id (FK)",
        "faculty_id (FK)",
        "assigned_duty_minutes",
        "status"
    ],
    "LeaveRequest": [
        "leave_request_id (PK)",
        "faculty_id (FK)",
        "start_date",
        "end_date",
        "reason",
        "status"
    ]
}

# Add entities as tables
for entity, attrs in entities.items():
    label = f"<<TABLE BORDER='1' CELLBORDER='1' CELLSPACING='0'>"
    label += f"<TR><TD BGCOLOR='lightblue'><B>{entity}</B></TD></TR>"
    for attr in attrs:
        label += f"<TR><TD ALIGN='LEFT'>{attr}</TD></TR>"
    label += "</TABLE>>"
    dot.node(entity, label=label, shape="plaintext")

# Relationships
relations = [
    ("Department", "Faculty", "1", "∞"),
    ("Department", "Course", "1", "∞"),
    ("Course", "Exam", "1", "∞"),
    ("ExamSeries", "Exam", "1", "∞"),
    ("Faculty", "LeaveRequest", "1", "∞"),
    ("Exam", "Assignment", "1", "∞"),
    ("Faculty", "Assignment", "1", "∞"),
    ("Hall", "Assignment", "1", "∞")
]

for parent, child, card1, card2 in relations:
    dot.edge(parent, child, label=f"{card1}:{card2}")

# Render diagram to file
file_path = "/mnt/data/elaborated_erd"
dot.render(file_path, format="png", cleanup=True)

file_path + ".png"
