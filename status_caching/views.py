"""
Module 6 Views: Status tracking, caching, cache stats.
"""
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from submission_monitoring.models import Complaint
from .models import StatusUpdate, CacheMetric


@login_required
def track_complaint(request, complaint_id):
    complaint = get_object_or_404(
        Complaint.objects.select_related("category", "submitter", "assigned_to"),
        id=complaint_id
    )
    user = request.user
    if user != complaint.submitter and user != complaint.assigned_to and not user.is_admin():
        from django.http import Http404
        raise Http404
    status_history = StatusUpdate.objects.filter(
        complaint=complaint
    ).select_related("updated_by").order_by("timestamp")
    return render(request, "status_caching/track.html", {
        "complaint": complaint,
        "status_history": status_history,
    })


@login_required
def my_complaints(request):
    user = request.user
    cache_key = "complaint_count_user_" + str(user.id)
    t_start = time.monotonic()
    cached_count = cache.get(cache_key)
    latency = round((time.monotonic() - t_start) * 1000, 3)
    if cached_count is not None:
        CacheMetric.objects.create(key=cache_key, hit=True, latency_ms=latency)
        total_count = cached_count
    else:
        t_start = time.monotonic()
        total_count = Complaint.objects.filter(submitter=user).count()
        latency = round((time.monotonic() - t_start) * 1000, 3)
        cache.set(cache_key, total_count, timeout=300)
        CacheMetric.objects.create(key=cache_key, hit=False, latency_ms=latency)

    complaints = (
        Complaint.objects
        .filter(submitter=user)
        .select_related("category")
        .order_by("-submitted_at")
    )
    pending_count  = complaints.filter(status="pending").count()
    active_count   = complaints.filter(status__in=["assigned", "in_progress"]).count()
    resolved_count = complaints.filter(status="resolved").count()
    return render(request, "status_caching/my_complaints.html", {
        "complaints":     complaints,
        "total_count":    total_count,
        "pending_count":  pending_count,
        "active_count":   active_count,
        "resolved_count": resolved_count,
    })


@login_required
def update_status(request, complaint_id):
    from django.contrib import messages
    complaint = get_object_or_404(Complaint, id=complaint_id)
    user = request.user
    if user != complaint.assigned_to and not user.is_admin():
        messages.error(request, "You are not authorized to update this complaint.")
        return redirect("status_caching:my_complaints")
    if request.method == "POST":
        new_status = request.POST.get("status")
        note       = request.POST.get("note", "")
        old_status = complaint.status
        if new_status and new_status != old_status:
            from django.utils import timezone
            complaint.status = new_status
            if new_status == "resolved":
                complaint.resolved_at = timezone.now()
            complaint.save()
            StatusUpdate.objects.create(
                complaint=complaint, updated_by=user,
                old_status=old_status, new_status=new_status, note=note,
            )
            cache.delete("complaint_count_user_" + str(complaint.submitter_id))
            if new_status == "resolved" and complaint.assigned_to:
                from concurrency_transactions.models import StaffWorkload
                try:
                    wl = StaffWorkload.objects.get(staff=complaint.assigned_to)
                    if wl.active_count > 0:
                        wl.active_count -= 1
                        wl.save()
                except StaffWorkload.DoesNotExist:
                    pass
            messages.success(request, "Status updated to \"" + new_status + "\".")
        return redirect("status_caching:track", complaint_id=complaint_id)
    status_choices = Complaint.STATUS_CHOICES
    return render(request, "status_caching/update_status.html", {
        "complaint": complaint,
        "status_choices": status_choices,
    })


@login_required
def cache_stats(request):
    if not request.user.is_admin():
        from django.http import Http404
        raise Http404
    from .models import CacheMetric
    from django.db.models import Avg
    metrics = CacheMetric.objects.all()
    total  = metrics.count()
    hits   = metrics.filter(hit=True).count()
    misses = metrics.filter(hit=False).count()
    hit_rate = round((hits / total) * 100, 1) if total else 0
    recent = metrics.order_by("-timestamp")[:50]
    avg_hit_ms  = metrics.filter(hit=True).aggregate(a=Avg("latency_ms"))["a"] or 0
    avg_miss_ms = metrics.filter(hit=False).aggregate(a=Avg("latency_ms"))["a"] or 0
    return render(request, "status_caching/cache_stats.html", {
        "total": total, "hits": hits, "misses": misses,
        "hit_rate": hit_rate, "recent": recent,
        "avg_hit_ms": round(avg_hit_ms, 3),
        "avg_miss_ms": round(avg_miss_ms, 3),
    })
