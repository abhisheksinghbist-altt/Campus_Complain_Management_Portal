"""
Module 5 Views: Submit, list, detail, rate complaints + health check.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Complaint, Category


@login_required
def submit_complaint(request):
    categories = Category.objects.all().order_by("priority")
    if request.method == "POST":
        title           = request.POST.get("title", "").strip()
        description     = request.POST.get("description", "").strip()
        category_id     = request.POST.get("category")
        location        = request.POST.get("location", "other")
        location_detail = request.POST.get("location_detail", "").strip()

        if not all([title, description, category_id]):
            messages.error(request, "Please fill in all required fields.")
        else:
            complaint = Complaint.objects.create(
                title=title, description=description,
                category_id=category_id, location=location,
                location_detail=location_detail,
                submitter=request.user, status="pending",
            )

            # Smart auto-assignment: run all 3 algorithms, pick the best one
            try:
                from analytics_scheduling.scheduler import smart_auto_assign
                result = smart_auto_assign(complaint, request.user)
                # Store result in session so the result page can display it
                request.session["smart_result_" + str(complaint.id)] = {
                    "success":     result["success"],
                    "algorithm":   result["algorithm"],
                    "assigned_to": result["assigned_to"],
                    "reason":      result["reason"],
                    "scores": {
                        k: {"score": v["score"], "reason": v["reason"], "label": v["label"]}
                        for k, v in result["scores"].items()
                    },
                    "utilisation":     result["selection"]["utilisation"],
                    "queue_len":       result["selection"]["queue_len"],
                    "staff_available": result["selection"]["staff_available"],
                    "total_staff":     result["selection"]["total_staff"],
                    "priority_val":    result["selection"]["priority_val"],
                    "avg_hrs":         result["selection"]["avg_hrs"],
                }
                return redirect("dashboard:smart_result", complaint_id=complaint.id)
            except Exception as e:
                messages.success(request, "Complaint #" + str(complaint.id) + " submitted.")
                return redirect("status_caching:track", complaint_id=complaint.id)

    return render(request, "submission_monitoring/submit.html", {"categories": categories})


@login_required
def complaint_list(request):
    user = request.user
    if user.is_admin():
        qs = Complaint.objects.select_related("category", "submitter", "assigned_to").all()
    elif user.is_staff_member():
        qs = Complaint.objects.filter(assigned_to=user).select_related("category", "submitter")
    else:
        qs = Complaint.objects.filter(submitter=user).select_related("category")

    q        = request.GET.get("q", "").strip()
    status   = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    if q:
        qs = qs.filter(title__icontains=q)
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category_id=category)

    categories = Category.objects.all()
    return render(request, "submission_monitoring/list.html", {
        "complaints": qs, "categories": categories,
    })


@login_required
def detail_complaint(request, complaint_id):
    complaint = get_object_or_404(
        Complaint.objects.select_related("category", "submitter", "assigned_to"),
        id=complaint_id
    )
    user = request.user
    if user != complaint.submitter and user != complaint.assigned_to and not user.is_admin():
        from django.http import Http404
        raise Http404
    from status_caching.models import StatusUpdate
    from file_engine.models import ComplaintAttachment
    status_history = StatusUpdate.objects.filter(
        complaint=complaint
    ).select_related("updated_by").order_by("timestamp")
    attachments = ComplaintAttachment.objects.filter(complaint=complaint)
    return render(request, "submission_monitoring/detail.html", {
        "complaint":      complaint,
        "status_history": status_history,
        "attachments":    attachments,
    })


@login_required
def rate_complaint(request, complaint_id):
    complaint = get_object_or_404(
        Complaint, id=complaint_id, submitter=request.user, status="resolved"
    )
    if request.method == "POST":
        try:
            rating = int(request.POST.get("rating", 0))
            if 1 <= rating <= 5:
                complaint.rating = rating
                complaint.save(update_fields=["rating"])
                messages.success(request, "Thank you for your feedback!")
            else:
                messages.error(request, "Rating must be between 1 and 5.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value.")
    return redirect("status_caching:track", complaint_id=complaint_id)


def health_check(request):
    from django.db import connection
    from django.http import JsonResponse
    import time
    status = {"server": "ok", "db": "unknown", "timestamp": time.time()}
    try:
        connection.ensure_connection()
        status["db"] = "ok"
    except Exception as e:
        status["db"] = "error: " + str(e)
    return JsonResponse(status)
