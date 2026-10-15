"""
Module 2 Views: Secure file upload + download for complaint attachments.
"""
import os
import mimetypes
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.contrib import messages
from django.conf import settings
from submission_monitoring.models import Complaint
from .models import ComplaintAttachment, SystemLog


ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf',
    'video/mp4',
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@login_required
def upload_attachment(request, complaint_id):
    """
    Handles secure file uploads for a complaint.

    OS Concepts demonstrated:
    - Directory permissions: each complaint gets its own sub-directory (0o750)
    - File permissions: uploaded files get 0o640 (owner read/write, group read)
    - MIME type validation prevents disguised executable uploads
    """
    complaint = get_object_or_404(Complaint, id=complaint_id)

    # Only the submitter or admin can attach files
    if request.user != complaint.submitter and not request.user.is_admin():
        raise Http404

    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)

        # Validate file type and size
        if mime_type not in ALLOWED_MIME_TYPES:
            messages.error(request, 'File type not allowed.')
            return redirect('submission_monitoring:list')
        if uploaded_file.size > MAX_FILE_SIZE:
            messages.error(request, 'File exceeds 5 MB limit.')
            return redirect('submission_monitoring:list')

        attachment = ComplaintAttachment.objects.create(
            complaint=complaint,
            uploaded_by=request.user,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=mime_type or 'application/octet-stream',
        )

        # Set restrictive directory permissions (OS concept)
        dir_path = os.path.dirname(attachment.file.path)
        os.chmod(dir_path, 0o750)
        os.chmod(attachment.file.path, 0o640)

        SystemLog.objects.create(
            action='file_upload',
            complaint=complaint,
            actor=request.user,
            description=f'File "{uploaded_file.name}" uploaded for complaint #{complaint_id}',
        )
        messages.success(request, 'File uploaded successfully.')

    return redirect('submission_monitoring:list')


@login_required
def download_attachment(request, attachment_id):
    """
    Serves a file only to the complaint's submitter, assigned staff, or admin.
    OS Concept: Access control check before I/O — mirrors filesystem permissions.
    """
    attachment = get_object_or_404(ComplaintAttachment, id=attachment_id)
    complaint = attachment.complaint
    user = request.user

    authorized = (
        user == complaint.submitter or
        user == complaint.assigned_to or
        user.is_admin()
    )
    if not authorized:
        raise Http404

    if not os.path.exists(attachment.file.path):
        raise Http404

    return FileResponse(
        open(attachment.file.path, 'rb'),
        as_attachment=True,
        filename=attachment.original_filename,
    )
