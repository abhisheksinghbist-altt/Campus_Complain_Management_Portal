"""
Module 1 Views: Ticket assignment with ACID transaction + mutex pattern.
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
    """
    Atomically assigns a complaint to a staff member.

    ACID Transaction:
      1. Lock the complaint row (SELECT FOR UPDATE — acts as a mutex).
      2. Lock the staff workload row.
      3. Update complaint status + assigned_to.
      4. Increment staff active_count.
      5. Write AssignmentLog entry.
      If ANY step raises an exception → entire transaction rolls back.

    OS Concept: SELECT FOR UPDATE mimics a mutex/semaphore —
    prevents two admins from simultaneously assigning the same ticket.
    """
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if not request.user.is_admin():
        messages.error(request, 'Only admins can assign tickets.')
        return redirect('submission_monitoring:list')

    available_staff = CampusUser.objects.filter(
        role='staff'
    ).select_related('workload')

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        notes    = request.POST.get('notes', '')

        try:
            with transaction.atomic():
                # Mutex: lock both rows before any modification
                locked_complaint = Complaint.objects.select_for_update().get(id=complaint_id)
                staff = CampusUser.objects.get(id=staff_id, role='staff')
                workload, _ = StaffWorkload.objects.select_for_update().get_or_create(
                    staff=staff,
                    defaults={'active_count': 0, 'max_capacity': 5}
                )

                if not workload.is_available():
                    raise ValueError(f'{staff.get_full_name()} is at full capacity.')

                prev_status = locked_complaint.status

                # Atomic updates
                locked_complaint.assigned_to = staff
                locked_complaint.status = 'assigned'
                locked_complaint.save()

                workload.active_count += 1
                workload.save()

                AssignmentLog.objects.create(
                    complaint=locked_complaint,
                    assigned_by=request.user,
                    assigned_to=staff,
                    previous_status=prev_status,
                    new_status='assigned',
                    notes=notes,
                )

            messages.success(request, f'Ticket assigned to {staff.get_full_name()}.')
            return redirect('submission_monitoring:list')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Assignment failed and was rolled back: {str(e)}')

    return render(request, 'concurrency_transactions/assign.html', {
        'complaint': complaint,
        'available_staff': available_staff,
    })
