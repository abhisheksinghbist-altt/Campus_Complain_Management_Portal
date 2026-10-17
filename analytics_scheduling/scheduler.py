"""
analytics_scheduling/scheduler.py

Core scheduling engine. Implements three OS CPU-scheduling algorithms
applied to complaint queues, plus:
  - bulk_auto_assign : assign all pending complaints via one algorithm
  - select_best_algorithm : run all 3 algorithms on a complaint, score
                            each one, return the winner + full reasoning
  - smart_auto_assign : on-submit assignment using the best algorithm
"""

from django.db import transaction
from submission_monitoring.models import Complaint
from automation_auth.models import CampusUser
from concurrency_transactions.models import StaffWorkload, AssignmentLog


# ---------------------------------------------------------------------------
# Queue ordering functions
# ---------------------------------------------------------------------------

def get_pending_complaints():
    return list(
        Complaint.objects
        .filter(status="pending")
        .select_related("category", "submitter")
        .order_by("id")
    )


def priority_queue(complaints):
    """Priority Scheduling: lower priority number = more urgent."""
    return sorted(complaints, key=lambda c: (c.category.priority, c.submitted_at))


def sjf_queue(complaints):
    """Shortest Job First: lowest avg_resolution_hours first."""
    return sorted(complaints, key=lambda c: (c.category.avg_resolution_hours, c.submitted_at))


def fcfs_queue(complaints):
    """First Come First Served: oldest submission first."""
    return sorted(complaints, key=lambda c: c.submitted_at)


ALGORITHMS = {
    "priority": ("Priority Scheduling",      priority_queue,
                 "Highest-priority category served first (1=Critical)"),
    "sjf":      ("Shortest Job First (SJF)", sjf_queue,
                 "Complaint with shortest historical resolution time first"),
    "fcfs":     ("First Come First Served",  fcfs_queue,
                 "Oldest complaint served first"),
}


def build_all_queues(complaints):
    """Return (key, label, desc, ordered_list) for all three algorithms."""
    results = []
    for key, (label, fn, desc) in ALGORITHMS.items():
        results.append((key, label, desc, fn(list(complaints))))
    return results


# ---------------------------------------------------------------------------
# Staff helpers
# ---------------------------------------------------------------------------

def get_available_staff():
    """Return list of (CampusUser, StaffWorkload) with remaining capacity."""
    available = []
    for user in CampusUser.objects.filter(role="staff"):
        workload, _ = StaffWorkload.objects.get_or_create(
            staff=user,
            defaults={"active_count": 0, "max_capacity": 5}
        )
        if workload.is_available():
            available.append((user, workload))
    return available


def get_least_loaded_staff(staff_pool):
    """From a pool of (user, workload) pick the one with fewest active tasks."""
    if not staff_pool:
        return None, None
    return min(staff_pool, key=lambda x: x[1].active_count)


# ---------------------------------------------------------------------------
# Smart algorithm selector
# ---------------------------------------------------------------------------

def select_best_algorithm(complaint):
    """
    Run all three algorithms on the current pending queue,
    score each one for THIS specific complaint, and return
    the algorithm key that best serves this complaint.

    Scoring rules (higher = better fit):
      Priority:
        +40 if category.priority == 1  (Critical)
        +25 if category.priority == 2  (High)
        +10 if category.priority == 3  (Medium)
         +0 if category.priority == 4  (Low)

      SJF:
        +40 if avg_resolution_hours <= 4   (very quick fix)
        +25 if avg_resolution_hours <= 8
        +10 if avg_resolution_hours <= 16
         +0 otherwise
        +10 bonus if staff utilisation < 60% (capacity available to process quick jobs)

      FCFS:
        +30 if complaint is the oldest pending (position 1 in FCFS queue)
        +20 if in top 25% of the queue
        +10 if in top 50%
        +15 bonus if staff utilisation >= 80% (fair distribution when overloaded)

    The algorithm with the highest score wins.
    Returns a dict with full reasoning for display.
    """
    pending      = get_pending_complaints()
    staff_pool   = get_available_staff()
    total_staff  = CampusUser.objects.filter(role="staff").count()

    # Staff utilisation (0-100%)
    total_active = sum(wl.active_count for _, wl in staff_pool)
    total_cap    = sum(wl.max_capacity for _, wl in staff_pool) or 1
    utilisation  = round((total_active / total_cap) * 100, 1)

    # FCFS position of this complaint in the queue
    fcfs_ordered = fcfs_queue(pending)
    fcfs_pos     = next((i + 1 for i, c in enumerate(fcfs_ordered) if c.id == complaint.id), len(pending))
    queue_len    = len(pending) or 1
    fcfs_pct     = fcfs_pos / queue_len  # 0 = first, 1 = last

    priority_val = complaint.category.priority
    avg_hrs      = complaint.category.avg_resolution_hours

    # --- Score Priority ---
    if priority_val == 1:
        p_score = 40
        p_reason = "Category is Critical (P1) — must jump the queue"
    elif priority_val == 2:
        p_score = 25
        p_reason = "Category is High priority (P2) — elevated urgency"
    elif priority_val == 3:
        p_score = 10
        p_reason = "Category is Medium priority (P3)"
    else:
        p_score = 0
        p_reason = "Category is Low priority (P4) — not urgent by priority"

    # --- Score SJF ---
    if avg_hrs <= 4:
        s_score = 40
        s_reason = "Avg resolution <= 4h — very fast fix"
    elif avg_hrs <= 8:
        s_score = 25
        s_reason = "Avg resolution <= 8h — reasonably quick"
    elif avg_hrs <= 16:
        s_score = 10
        s_reason = "Avg resolution <= 16h — moderate"
    else:
        s_score = 0
        s_reason = "Avg resolution > 16h — long job, SJF penalises it"

    if utilisation < 60:
        s_score  += 10
        s_reason += " + staff underloaded (<60% utilisation, ideal for SJF)"

    # --- Score FCFS ---
    if fcfs_pos == 1:
        f_score = 30
        f_reason = "This is the oldest pending complaint — FCFS serves it first"
    elif fcfs_pct <= 0.25:
        f_score = 20
        f_reason = "In top 25% of the queue by arrival time"
    elif fcfs_pct <= 0.50:
        f_score = 10
        f_reason = "In top 50% of the queue by arrival time"
    else:
        f_score = 0
        f_reason = "Newer complaint — FCFS would make it wait"

    if utilisation >= 80:
        f_score  += 15
        f_reason += " + staff heavily loaded (>=80%), FCFS ensures fairness"

    scores = {
        "priority": {"score": p_score, "reason": p_reason, "label": "Priority Scheduling"},
        "sjf":      {"score": s_score, "reason": s_reason, "label": "Shortest Job First"},
        "fcfs":     {"score": f_score, "reason": f_reason, "label": "First Come First Served"},
    }

    best_key = max(scores, key=lambda k: scores[k]["score"])

    return {
        "best":       best_key,
        "scores":     scores,
        "utilisation": utilisation,
        "queue_len":  queue_len,
        "fcfs_pos":   fcfs_pos,
        "staff_available": len(staff_pool),
        "total_staff": total_staff,
        "avg_hrs":    avg_hrs,
        "priority_val": priority_val,
    }


# ---------------------------------------------------------------------------
# Smart on-submit assignment
# ---------------------------------------------------------------------------

def smart_auto_assign(complaint, system_user):
    """
    Called immediately after a complaint is submitted.
    Runs select_best_algorithm, then atomically assigns the complaint
    to the least-loaded available staff member.

    Returns a result dict:
      {
        "success":     bool,
        "algorithm":   key of winning algorithm,
        "selection":   full dict from select_best_algorithm,
        "assigned_to": staff name or None,
        "reason":      human-readable explanation,
        "scores":      per-algorithm score breakdown,
      }
    """
    selection = select_best_algorithm(complaint)
    best_key  = selection["best"]
    label     = ALGORITHMS[best_key][0]

    staff_pool = get_available_staff()
    if not staff_pool:
        return {
            "success":     False,
            "algorithm":   best_key,
            "selection":   selection,
            "assigned_to": None,
            "reason":      "No staff available — complaint stays pending",
            "scores":      selection["scores"],
        }

    # Pick least-loaded staff for the assignment
    staff_user, workload = get_least_loaded_staff(staff_pool)

    try:
        with transaction.atomic():
            locked = Complaint.objects.select_for_update().get(id=complaint.id)
            if locked.status != "pending":
                return {
                    "success":     False,
                    "algorithm":   best_key,
                    "selection":   selection,
                    "assigned_to": None,
                    "reason":      "Complaint already processed by another request",
                    "scores":      selection["scores"],
                }

            wl = StaffWorkload.objects.select_for_update().get_or_create(
                staff=staff_user,
                defaults={"active_count": 0, "max_capacity": 5}
            )[0]

            if not wl.is_available():
                return {
                    "success":     False,
                    "algorithm":   best_key,
                    "selection":   selection,
                    "assigned_to": None,
                    "reason":      staff_user.get_full_name() + " hit capacity at assignment time",
                    "scores":      selection["scores"],
                }

            locked.assigned_to = staff_user
            locked.status      = "assigned"
            locked.save()

            wl.active_count += 1
            wl.save()

            AssignmentLog.objects.create(
                complaint=locked,
                assigned_by=system_user,
                assigned_to=staff_user,
                previous_status="pending",
                new_status="assigned",
                notes="Smart auto-assign: " + label + " selected as best algorithm",
            )

        return {
            "success":     True,
            "algorithm":   best_key,
            "selection":   selection,
            "assigned_to": staff_user.get_full_name(),
            "reason":      "Assigned by " + label,
            "scores":      selection["scores"],
        }

    except Exception as exc:
        return {
            "success":     False,
            "algorithm":   best_key,
            "selection":   selection,
            "assigned_to": None,
            "reason":      "Assignment failed: " + str(exc),
            "scores":      selection["scores"],
        }


# ---------------------------------------------------------------------------
# Bulk auto-assign (existing)
# ---------------------------------------------------------------------------

def bulk_auto_assign(algorithm, assigned_by_user):
    """
    Build ordered queue then atomically assign each complaint
    to an available staff member using round-robin distribution.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError("Unknown algorithm: " + algorithm)

    label, queue_fn, _ = ALGORITHMS[algorithm]
    ordered = queue_fn(get_pending_complaints())

    results = {
        "algorithm": algorithm,
        "label":     label,
        "total":     len(ordered),
        "assigned":  0,
        "skipped":   0,
        "no_staff":  0,
        "details":   [],
    }

    if not ordered:
        return results

    rr_index = 0

    for complaint in ordered:
        pool = [u for u, _ in get_available_staff()]
        if not pool:
            results["no_staff"] += 1
            results["details"].append({
                "complaint": complaint,
                "status": "no_staff",
                "assigned_to": "",
                "reason": "All staff at full capacity",
            })
            continue

        staff_user = pool[rr_index % len(pool)]
        rr_index  += 1

        try:
            with transaction.atomic():
                locked = Complaint.objects.select_for_update().get(id=complaint.id)
                if locked.status != "pending":
                    results["skipped"] += 1
                    results["details"].append({
                        "complaint": complaint,
                        "status": "skipped",
                        "assigned_to": "",
                        "reason": "Already " + locked.status,
                    })
                    continue

                workload, _ = StaffWorkload.objects.select_for_update().get_or_create(
                    staff=staff_user,
                    defaults={"active_count": 0, "max_capacity": 5}
                )

                if not workload.is_available():
                    results["skipped"] += 1
                    results["details"].append({
                        "complaint": complaint,
                        "status": "skipped",
                        "assigned_to": "",
                        "reason": staff_user.get_full_name() + " hit capacity",
                    })
                    continue

                prev = locked.status
                locked.assigned_to = staff_user
                locked.status      = "assigned"
                locked.save()
                workload.active_count += 1
                workload.save()

                AssignmentLog.objects.create(
                    complaint=locked,
                    assigned_by=assigned_by_user,
                    assigned_to=staff_user,
                    previous_status=prev,
                    new_status="assigned",
                    notes="Auto-assigned via " + label,
                )

            results["assigned"] += 1
            results["details"].append({
                "complaint": complaint,
                "status": "assigned",
                "assigned_to": staff_user.get_full_name(),
                "reason": "Assigned via " + label,
            })
        except Exception as exc:
            results["skipped"] += 1
            results["details"].append({
                "complaint": complaint,
                "status": "error",
                "assigned_to": "",
                "reason": str(exc),
            })

    return results
