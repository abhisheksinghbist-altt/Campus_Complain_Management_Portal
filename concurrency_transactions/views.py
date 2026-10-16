"""
Module 1 Views: Atomic ticket assignment + Staff Workload admin view.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from submission_monitoring.models import Complaint
from automation_auth.models import CampusUser
from .models import StaffWorkload, AssignmentLog


@login_required
def assign_ticket(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if not request.user.is_admin():
        messages.error(request, "Only admins can assign tickets.")
        return redirect("submission_monitoring:list")
    available_staff = CampusUser.objects.filter(role="staff").select_related("workload")
    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        notes    = request.POST.get("notes", "")
        try:
            with transaction.atomic():
                locked_complaint = Complaint.objects.select_for_update().get(id=complaint_id)
                staff = CampusUser.objects.get(id=staff_id, role="staff")
                workload, _ = StaffWorkload.objects.select_for_update().get_or_create(
                    staff=staff, defaults={"active_count": 0, "max_capacity": 5}
                )
                if not workload.is_available():
                    raise ValueError(staff.get_full_name() + " is at full capacity.")
                prev_status = locked_complaint.status
                locked_complaint.assigned_to = staff
                locked_complaint.status = "assigned"
                locked_complaint.save()
                workload.active_count += 1
                workload.save()
                AssignmentLog.objects.create(
                    complaint=locked_complaint, assigned_by=request.user,
                    assigned_to=staff, previous_status=prev_status,
                    new_status="assigned", notes=notes,
                )
            messages.success(request, "Ticket assigned to " + staff.get_full_name() + ".")
            return redirect("submission_monitoring:list")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "Assignment failed and was rolled back: " + str(e))
    return render(request, "concurrency_transactions/assign.html", {
        "complaint": complaint,
        "available_staff": available_staff,
    })


@login_required
def staff_workload_view(request):
    if not request.user.is_admin():
        from django.http import Http404
        raise Http404
    staff_users = CampusUser.objects.filter(role="staff")
    workloads = []
    full_count = 0
    available_count = 0
    for s in staff_users:
        wl, _ = StaffWorkload.objects.get_or_create(
            staff=s, defaults={"active_count": 0, "max_capacity": 5}
        )
        pct = round((wl.active_count / wl.max_capacity) * 100) if wl.max_capacity else 0
        workloads.append({"user": s, "workload": wl, "pct": pct})
        if wl.active_count >= wl.max_capacity:
            full_count += 1
        else:
            available_count += 1
    return render(request, "concurrency_transactions/workload.html", {
        "workloads": workloads,
        "full_count": full_count,
        "available_count": available_count,
    })
