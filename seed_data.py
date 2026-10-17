"""
Seed script — clears non-admin users and complaints, then inserts
realistic campus data with varied statuses, staff assignments, and
status history.

Run:  python manage.py shell < seed_data.py
"""
import os, django, random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_portal.settings")
django.setup()

from django.utils import timezone
from datetime import timedelta
from automation_auth.models import CampusUser
from submission_monitoring.models import Complaint, Category
from status_caching.models import StatusUpdate
from concurrency_transactions.models import StaffWorkload, AssignmentLog
from file_engine.models import SystemLog

# ── 1. WIPE old non-admin data ────────────────────────────────────────────────
print("Clearing old data...")
SystemLog.objects.all().delete()
AssignmentLog.objects.all().delete()
StatusUpdate.objects.all().delete()
Complaint.objects.all().delete()
StaffWorkload.objects.all().delete()
CampusUser.objects.exclude(username="admin").delete()
print("  ✓ old records removed")

# ── 2. USERS ──────────────────────────────────────────────────────────────────
print("Creating users...")

staff_data = [
    ("ravi.kumar",   "Ravi",    "Kumar",    "Electrical",  "9812345001"),
    ("meena.singh",  "Meena",   "Singh",    "Plumbing",    "9812345002"),
    ("arjun.nair",   "Arjun",   "Nair",     "IT Support",  "9812345003"),
]
student_data = [
    ("priya.sharma",    "Priya",    "Sharma",   "Computer Science", "B"),
    ("rohit.verma",     "Rohit",    "Verma",    "Mechanical",       "A"),
    ("ankita.das",      "Ankita",   "Das",      "Electronics",      "C"),
    ("suresh.pillai",   "Suresh",   "Pillai",   "Civil",            "D"),
    ("divya.menon",     "Divya",    "Menon",    "Computer Science", "B"),
]
faculty_data = [
    ("prof.thomas",  "Thomas",  "George",   "Computer Science"),
    ("prof.reddy",   "Sunita",  "Reddy",    "Electronics"),
]

staff_users  = []
student_users = []
faculty_users = []

for uname, fn, ln, dept, phone in staff_data:
    u = CampusUser.objects.create_user(
        username=uname, password="Staff@2025",
        first_name=fn, last_name=ln,
        email=f"{uname}@campus.edu",
        role="staff", department=dept, phone=phone,
    )
    staff_users.append(u)
    print(f"  staff   → {u}")

for uname, fn, ln, dept, block in student_data:
    u = CampusUser.objects.create_user(
        username=uname, password="Student@2025",
        first_name=fn, last_name=ln,
        email=f"{uname}@campus.edu",
        role="student", department=dept, hostel_block=block,
    )
    student_users.append(u)
    print(f"  student → {u}")

for uname, fn, ln, dept in faculty_data:
    u = CampusUser.objects.create_user(
        username=uname, password="Faculty@2025",
        first_name=fn, last_name=ln,
        email=f"{uname}@campus.edu",
        role="faculty", department=dept,
    )
    faculty_users.append(u)
    print(f"  faculty → {u}")

admin_user = CampusUser.objects.get(username="admin")

# ── 3. STAFF WORKLOAD INIT ────────────────────────────────────────────────────
for s in staff_users:
    StaffWorkload.objects.get_or_create(staff=s, defaults={"active_count": 0, "max_capacity": 5})

# ── 4. CATEGORIES (ensure they exist) ────────────────────────────────────────
cat_map = {name: Category.objects.get_or_create(name=name)[0]
           for name in ["Electrical", "Plumbing", "IT Support", "Housekeeping", "Furniture", "Network"]}

# ── 5. COMPLAINTS ─────────────────────────────────────────────────────────────
print("Creating complaints...")
now = timezone.now()

complaints_data = [
    # (title, desc, cat, location, loc_detail, submitter, status, days_ago, staff_idx, rating)
    ("Flickering lights in Lab 3",
     "The fluorescent lights in Lab 3 keep flickering and have been causing headaches during practicals.",
     "Electrical", "lab", "Lab 3, Block A", student_users[0], "resolved", 14, 0, 5),

    ("Water leakage in hostel bathroom",
     "There is a continuous water leak under the sink in Room 204, Block B. Water is pooling on the floor.",
     "Plumbing", "hostel", "Room 204, Block B", student_users[1], "resolved", 10, 1, 4),

    ("Projector not working in Room 101",
     "The ceiling-mounted projector in Classroom 101 stopped displaying anything. Cable and connections checked.",
     "IT Support", "classroom", "Room 101, Main Block", student_users[2], "closed", 20, 2, 5),

    ("Broken bench in Canteen",
     "One of the long benches near the south wall of the canteen has a broken leg and is a safety hazard.",
     "Furniture", "canteen", "South wall, Main Canteen", student_users[3], "in_progress", 3, 0, None),

    ("Wi-Fi not working in Library",
     "The Wi-Fi access point in the reading hall of the library has been offline for two days.",
     "Network", "library", "Reading Hall, Central Library", faculty_users[0], "in_progress", 5, 2, None),

    ("Power socket sparking in Office 12",
     "The wall socket near the door in Admin Office 12 sparks when plugging in devices. Urgent safety issue.",
     "Electrical", "office", "Admin Office 12", faculty_users[1], "assigned", 2, 0, None),

    ("Clogged drain in hostel corridor",
     "The floor drain in the ground floor corridor of Block C is clogged causing water accumulation.",
     "Plumbing", "hostel", "Ground floor, Block C", student_users[4], "assigned", 1, 1, None),

    ("Keyboard missing from Lab 2 PC",
     "Station 7 in Computer Lab 2 is missing its keyboard. Students cannot use that workstation.",
     "IT Support", "lab", "Lab 2, Station 7", student_users[0], "pending", 0, None, None),

    ("Dustbins overflowing near hostel entrance",
     "The dustbins near the Block D entrance have not been emptied for 3 days and are overflowing.",
     "Housekeeping", "hostel", "Block D entrance", student_users[1], "pending", 0, None, None),

    ("Broken window in Classroom 204",
     "The window latch in Classroom 204 is broken. The window cannot be closed properly causing disturbance.",
     "Furniture", "classroom", "Room 204, Second Floor", student_users[2], "resolved", 7, 1, 3),

    ("Network cable loose in server room",
     "A patch cable connecting Switch-2 is loose causing intermittent connectivity drops for Block E.",
     "Network", "office", "Server Room, Admin Block", faculty_users[0], "resolved", 12, 2, 5),

    ("AC not cooling in Staff Room",
     "The air conditioner in the main staff room runs but does not cool. Temperature stays above 30°C.",
     "Electrical", "office", "Main Staff Room", faculty_users[1], "in_progress", 4, 0, None),
]

created_complaints = []
for (title, desc, cat_name, loc, loc_detail, submitter,
     status, days_ago, staff_idx, rating) in complaints_data:

    submitted_at = now - timedelta(days=days_ago, hours=random.randint(0, 8))
    resolved_at  = None
    assigned_to  = staff_users[staff_idx] if staff_idx is not None else None

    if status in ("resolved", "closed"):
        resolved_at = submitted_at + timedelta(hours=random.randint(4, 48))

    c = Complaint(
        title=title, description=desc,
        category=cat_map[cat_name],
        location=loc, location_detail=loc_detail,
        submitter=submitter,
        assigned_to=assigned_to,
        status=status,
        rating=rating,
    )
    c.submitted_at = submitted_at          # auto_now_add — set after init
    c.save()

    # Force submitted_at because auto_now_add ignores assignment after save
    Complaint.objects.filter(pk=c.pk).update(submitted_at=submitted_at)
    if resolved_at:
        Complaint.objects.filter(pk=c.pk).update(resolved_at=resolved_at)

    created_complaints.append(c)
    print(f"  [{status.upper():12}] {title[:55]}")

# ── 6. STATUS HISTORY ────────────────────────────────────────────────────────
print("Creating status histories...")

def add_status(complaint, old_s, new_s, actor, delta_hours, note=""):
    ts = complaint.submitted_at + timedelta(hours=delta_hours)
    StatusUpdate.objects.create(
        complaint=complaint, updated_by=actor,
        old_status=old_s, new_status=new_s,
        note=note, timestamp=ts,
    )

for c in created_complaints:
    s = c.status
    staff = c.assigned_to

    if s in ("assigned", "in_progress", "resolved", "closed"):
        add_status(c, "pending", "assigned", admin_user, 1,
                   "Assigned to maintenance team.")

    if s in ("in_progress", "resolved", "closed"):
        add_status(c, "assigned", "in_progress", staff, 3,
                   "Work started. Parts/tools being arranged.")

    if s in ("resolved", "closed"):
        add_status(c, "in_progress", "resolved", staff, random.randint(8, 40),
                   "Issue resolved. Area inspected and cleared.")

    if s == "closed":
        add_status(c, "resolved", "closed", admin_user, random.randint(48, 72),
                   "Ticket closed after student confirmation.")

# ── 7. ASSIGNMENT LOGS ───────────────────────────────────────────────────────
def active_count(staff):
    return Complaint.objects.filter(
        assigned_to=staff, status__in=["assigned", "in_progress"]
    ).count()

print("Creating assignment logs...")
for c in created_complaints:
    if c.assigned_to:
        AssignmentLog.objects.create(
            complaint=c,
            assigned_by=admin_user,
            assigned_to=c.assigned_to,
            previous_status="pending",
            new_status="assigned",
        )

for s in staff_users:
    StaffWorkload.objects.filter(staff=s).update(active_count=active_count(s))

# ── DONE ─────────────────────────────────────────────────────────────────────
print("\n✅ Seed complete!")
print(f"   Staff    : {CampusUser.objects.filter(role='staff').count()}")
print(f"   Students : {CampusUser.objects.filter(role='student').count()}")
print(f"   Faculty  : {CampusUser.objects.filter(role='faculty').count()}")
print(f"   Complaints: {Complaint.objects.count()}")
print(f"   Status updates: {StatusUpdate.objects.count()}")
print(f"   Assignment logs: {AssignmentLog.objects.count()}")
print("\nLogin credentials:")
print("  admin     / admin123")
print("  ravi.kumar / Staff@2025  (staff)")
print("  priya.sharma / Student@2025  (student)")
