"""
Module 3 Views: Dashboard with live analytics + scheduling algorithm demo.
DBMS: Complex JOINs, COUNT/AVG aggregates, DB Views.
OS: Priority Scheduling and SJF applied to complaint auto-assignment.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from submission_monitoring.models import Complaint, Category


@login_required
def dashboard(request):
    """
    Main dashboard — aggregated statistics via DB queries.
    Results are cached in Module 6 to demonstrate memory vs disk reads.
    """
    stats = Complaint.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        assigned=Count('id', filter=Q(status='assigned')),
        resolved=Count('id', filter=Q(status='resolved')),
    )

    stats_list = [
        ('Total',       stats['total'],       '#2b6cb0'),
        ('Pending',     stats['pending'],     '#d69e2e'),
        ('Assigned',    stats['assigned'],    '#2b6cb0'),
        ('In Progress', stats['in_progress'], '#6b46c1'),
        ('Resolved',    stats['resolved'],    '#276749'),
    ]

    dept_stats = (
        Complaint.objects
        .values('submitter__department')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    category_stats = (
        Category.objects
        .annotate(count=Count('complaints'))
        .values('name', 'count', 'priority')
        .order_by('priority')
    )

    return render(request, 'analytics_scheduling/dashboard.html', {
        'stats_list':     stats_list,
        'dept_stats':     dept_stats,
        'category_stats': category_stats,
    })


@login_required
def scheduling_demo(request):
    """
    Demonstrates scheduling algorithms — maps to OS CPU scheduling concepts.
    """
    pending = Complaint.objects.filter(status='pending').select_related('category')

    queues = [
        (
            'Priority Scheduling',
            list(pending.order_by('category__priority', 'submitted_at')),
            'Highest priority category served first (e.g. Electrical before Cleaning)',
        ),
        (
            'Shortest Job First (SJF)',
            list(pending.order_by('category__avg_resolution_hours', 'submitted_at')),
            'Complaint with shortest historical resolution time served first',
        ),
        (
            'First Come First Served (FCFS)',
            list(pending.order_by('submitted_at')),
            'Oldest complaint served first — baseline algorithm',
        ),
    ]

    return render(request, 'analytics_scheduling/scheduling.html', {
        'queues': queues,
    })
