"""
Module 5 Views: Submit a complaint + process health check endpoint.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Complaint, Category


@login_required
def submit_complaint(request):
    """
    Handles the complaint submission form.
    DBMS: Uses a safe INSERT via Django ORM (parameterized — no SQL injection).
    """
    categories = Category.objects.all().order_by('priority')

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        location    = request.POST.get('location', 'other')
        location_detail = request.POST.get('location_detail', '').strip()

        if not all([title, description, category_id]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            complaint = Complaint.objects.create(
                title=title,
                description=description,
                category_id=category_id,
                location=location,
                location_detail=location_detail,
                submitter=request.user,
                status='pending',
            )
            messages.success(request, f'Complaint #{complaint.id} submitted successfully.')
            return redirect('status_caching:track', complaint_id=complaint.id)

    return render(request, 'submission_monitoring/submit.html', {
        'categories': categories,
    })


@login_required
def complaint_list(request):
    """Lists all complaints — filtered by role."""
    user = request.user
    if user.is_admin():
        complaints = Complaint.objects.select_related('category', 'submitter', 'assigned_to').all()
    elif user.is_staff_member():
        complaints = Complaint.objects.filter(assigned_to=user).select_related('category', 'submitter')
    else:
        complaints = Complaint.objects.filter(submitter=user).select_related('category')

    return render(request, 'submission_monitoring/list.html', {'complaints': complaints})


def health_check(request):
    """
    OS Concept: Process monitoring endpoint.
    Returns DB and server status. Called by the health-check bash script.
    """
    from django.db import connection
    from django.http import JsonResponse
    import time

    status = {'server': 'ok', 'db': 'unknown', 'timestamp': time.time()}
    try:
        connection.ensure_connection()
        status['db'] = 'ok'
    except Exception as e:
        status['db'] = f'error: {str(e)}'
    return JsonResponse(status)
