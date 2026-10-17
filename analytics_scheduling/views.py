"""
Module 3 Views: Dashboard + scheduling algorithm demos.
DBMS: Complex JOINs, COUNT/AVG aggregates, DB Views.
OS: Priority Scheduling, SJF, FCFS applied to complaint auto-assignment.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from submission_monitoring.models import Complaint, Category
from .scheduler import (
    ALGORITHMS,
    build_all_queues,
    bulk_auto_assign,
    get_pending_complaints,
    get_available_staff,
)


@login_required
def dashboard(request):
    """Main dashboard with aggregated statistics."""
    stats = Complaint.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        assigned=Count("id", filter=Q(status="assigned")),
        resolved=Count("id", filter=Q(status="resolved")),
    )
    stats_list = [
        ("Total",       stats["total"],       "#2b6cb0"),
        ("Pending",     stats["pending"],     "#d69e2e"),
        ("Assigned",    stats["assigned"],    "#2b6cb0"),
        ("In Progress", stats["in_progress"], "#6b46c1"),
        ("Resolved",    stats["resolved"],    "#276749"),
    ]
    dept_stats = (
        Complaint.objects
        .values("submitter__department")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    category_stats = (
        Category.objects
        .annotate(count=Count("complaints"))
        .values("name", "count", "priority")
        .order_by("priority")
    )
    return render(request, "analytics_scheduling/dashboard.html", {
        "stats_list":     stats_list,
        "dept_stats":     dept_stats,
        "category_stats": category_stats,
    })


@login_required
def scheduling_demo(request):
    """Original scheduling demo page."""
    pending = Complaint.objects.filter(status="pending").select_related("category")
    queues = [
        ("Priority Scheduling",
         list(pending.order_by("category__priority", "submitted_at")),
         "Highest priority category served first"),
        ("Shortest Job First (SJF)",
         list(pending.order_by("category__avg_resolution_hours", "submitted_at")),
         "Complaint with shortest historical resolution time first"),
        ("First Come First Served (FCFS)",
         list(pending.order_by("submitted_at")),
         "Oldest complaint served first"),
    ]
    return render(request, "analytics_scheduling/scheduling.html", {"queues": queues})


# ---------------------------------------------------------------------------
# NEW VIEW 1: Bulk Auto-Assignment
# ---------------------------------------------------------------------------

@login_required
def bulk_assign(request):
    """
    Admin selects an algorithm and clicks Run.
    The system processes ALL pending complaints in that algorithm order
    and atomically assigns each one to an available staff member.
    Uses SELECT FOR UPDATE (mutex) from Module 1 for each assignment.
    """
    if not request.user.is_admin():
        messages.error(request, "Only admins can run bulk assignment.")
        return redirect("dashboard:home")

    pending_count  = Complaint.objects.filter(status="pending").count()
    staff_pool     = get_available_staff()
    results        = None

    if request.method == "POST":
        algorithm = request.POST.get("algorithm", "priority")
        results   = bulk_auto_assign(algorithm, request.user)
        if results["assigned"] > 0:
            n = results["assigned"]
            lbl = results["label"]
            messages.success(request, str(n) + " complaint(s) assigned via " + lbl + ".")
        else:
            messages.warning(request, "No complaints were assigned.")

    return render(request, "analytics_scheduling/bulk_assign.html", {
        "algorithms":    list(ALGORITHMS.items()),
        "pending_count": pending_count,
        "staff_count":   len(staff_pool),
        "results":       results,
    })


# ---------------------------------------------------------------------------
# NEW VIEW 2: Live Queue Processor
# ---------------------------------------------------------------------------

@login_required
def queue_processor(request):
    """
    Shows all pending complaints ordered by the selected algorithm.
    Lets the admin step through and assign one at a time, or run all.
    Each assignment uses the atomic transaction from Module 1.
    """
    if not request.user.is_admin():
        messages.error(request, "Only admins can access the queue processor.")
        return redirect("dashboard:home")

    algorithm  = request.GET.get("algorithm", "priority")
    if algorithm not in ALGORITHMS:
        algorithm = "priority"

    pending    = get_pending_complaints()
    _, queue_fn, desc = ALGORITHMS[algorithm]
    ordered    = queue_fn(pending)
    staff_pool = get_available_staff()

    # Annotate each complaint with its queue position and candidate staff
    queue_items = []
    rr = 0
    for pos, complaint in enumerate(ordered, start=1):
        pool = [u for u, _ in staff_pool]
        candidate = pool[rr % len(pool)].get_full_name() if pool else "No staff available"
        rr += 1
        queue_items.append({
            "position":  pos,
            "complaint": complaint,
            "candidate": candidate,
        })

    return render(request, "analytics_scheduling/queue_processor.html", {
        "algorithm":    algorithm,
        "algo_label":   ALGORITHMS[algorithm][0],
        "algo_desc":    desc,
        "algorithms":   list(ALGORITHMS.items()),
        "queue_items":  queue_items,
        "staff_pool":   staff_pool,
        "total":        len(ordered),
    })


# ---------------------------------------------------------------------------
# NEW VIEW 3: Algorithm Comparison
# ---------------------------------------------------------------------------

@login_required
def comparison(request):
    """
    Side-by-side comparison of all three algorithms on the same
    set of pending complaints. Shows how ordering differs.
    No assignments are made here -- read-only view.
    """
    complaints = get_pending_complaints()
    queues     = build_all_queues(complaints)
    staff_pool = get_available_staff()

    return render(request, "analytics_scheduling/comparison.html", {
        "queues":        queues,
        "total_pending": len(complaints),
        "staff_count":   len(staff_pool),
    })


# ---------------------------------------------------------------------------
# NEW VIEW 4: Smart Algorithm Result
# ---------------------------------------------------------------------------

@login_required
def smart_result(request, complaint_id):
    """
    Shown immediately after complaint submission.
    Displays which algorithm was chosen, why, and the score breakdown.
    """
    from submission_monitoring.models import Complaint
    complaint = get_object_or_404(Complaint, id=complaint_id)

    session_key = "smart_result_" + str(complaint_id)
    result = request.session.pop(session_key, None)

    # If session expired or direct URL access, rebuild scores read-only
    if result is None:
        from .scheduler import select_best_algorithm
        sel = select_best_algorithm(complaint)
        result = {
            "success":         complaint.status == "assigned",
            "algorithm":       sel["best"],
            "assigned_to":     complaint.assigned_to.get_full_name() if complaint.assigned_to else None,
            "reason":          "Score reconstructed from current queue state",
            "scores":          {k: {"score": v["score"], "reason": v["reason"], "label": v["label"]}
                                for k, v in sel["scores"].items()},
            "utilisation":     sel["utilisation"],
            "queue_len":       sel["queue_len"],
            "staff_available": sel["staff_available"],
            "total_staff":     sel["total_staff"],
            "priority_val":    sel["priority_val"],
            "avg_hrs":         sel["avg_hrs"],
        }

    # Sort scores highest first for display
    sorted_scores = sorted(
        result["scores"].items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )
    max_score = sorted_scores[0][1]["score"] if sorted_scores else 1

    return render(request, "analytics_scheduling/smart_result.html", {
        "complaint":    complaint,
        "result":       result,
        "sorted_scores": sorted_scores,
        "max_score":    max_score,
    })
