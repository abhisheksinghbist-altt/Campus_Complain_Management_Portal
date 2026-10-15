"""
Module 6 Views: Status tracking with file-based cache.
DBMS: SELECT/WHERE for per-student complaint history.
OS: File-based cache to reduce DB queries — demonstrates memory vs disk I/O.
"""
import time
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from submission_monitoring.models import Complaint
from .models import StatusUpdate, CacheMetric


@login_required
def track_complaint(request, complaint_id):
    """
    Student views real-time status of one complaint.
    All status history fetched from DB with a WHERE clause on complaint_id.
    """
    complaint = get_object_or_404(
        Complaint.objects.select_related('category', 'submitter', 'assigned_to'),
        id=complaint_id
    )
    # Only submitter, assigned staff, or admin can view
    user = request.user
    if user != complaint.submitter and user != complaint.assigned_to and not user.is_admin():
        from django.http import Http404
        raise Http404

    # SELECT WHERE complaint_id = ? — per-student data isolation
    status_history = StatusUpdate.objects.filter(
        complaint=complaint
    ).select_related('updated_by').order_by('timestamp')

    return render(request, 'status_caching/track.html', {
        'complaint': complaint,
        'status_history': status_history,
    })


@login_required
def my_complaints(request):
    """
    Student's own complaint history — isolated with a WHERE submitter = ?
    OS Caching: caches the total count to avoid repeated COUNT(*) queries.
    """
    user = request.user
    cache_key = f'complaint_count_user_{user.id}'

    # --- Cache lookup (OS: file-based memory cache) ---
    t_start = time.monotonic()
    cached_count = cache.get(cache_key)
    t_end = time.monotonic()
    latency = round((t_end - t_start) * 1000, 3)

    if cached_count is not None:
        CacheMetric.objects.create(key=cache_key, hit=True, latency_ms=latency)
        total_count = cached_count
    else:
        # --- Cache miss: query DB then store result ---
        t_start = time.monotonic()
        total_count = Complaint.objects.filter(submitter=user).count()
        t_end = time.monotonic()
        latency = round((t_end - t_start) * 1000, 3)

        cache.set(cache_key, total_count, timeout=300)
        CacheMetric.objects.create(key=cache_key, hit=False, latency_ms=latency)

    complaints = (
        Complaint.objects
        .filter(submitter=user)          # WHERE submitter = ?
        .select_related('category')
        .order_by('-submitted_at')
    )

    return render(request, 'status_caching/my_complaints.html', {
        'complaints':   complaints,
        'total_count':  total_count,
    })


@login_required
def update_status(request, complaint_id):
    """
    Staff member updates complaint status.
    Triggers a cache invalidation for affected users.
    """
    from django.contrib import messages
    from django.shortcuts import redirect

    complaint = get_object_or_404(Complaint, id=complaint_id)
    user = request.user

    if user != complaint.assigned_to and not user.is_admin():
        messages.error(request, 'You are not authorized to update this complaint.')
        return redirect('status_caching:my_complaints')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        note       = request.POST.get('note', '')
        old_status = complaint.status

        if new_status and new_status != old_status:
            from django.utils import timezone

            complaint.status = new_status
            if new_status == 'resolved':
                complaint.resolved_at = timezone.now()
            complaint.save()

            StatusUpdate.objects.create(
                complaint=complaint,
                updated_by=user,
                old_status=old_status,
                new_status=new_status,
                note=note,
            )

            # Invalidate submitter's cached count
            cache.delete(f'complaint_count_user_{complaint.submitter_id}')

            # If staff resolved it, decrement workload
            if new_status == 'resolved' and complaint.assigned_to:
                from concurrency_transactions.models import StaffWorkload
                try:
                    wl = StaffWorkload.objects.get(staff=complaint.assigned_to)
                    if wl.active_count > 0:
                        wl.active_count -= 1
                        wl.save()
                except StaffWorkload.DoesNotExist:
                    pass

            messages.success(request, f'Status updated to "{new_status}".')
        return redirect('status_caching:track', complaint_id=complaint_id)

    from submission_monitoring.models import Complaint as C
    status_choices = C.STATUS_CHOICES
    return render(request, 'status_caching/update_status.html', {
        'complaint': complaint,
        'status_choices': status_choices,
    })
