"""
Module 2 Views: Secure file upload/download + system log viewer.
"""
import os, mimetypes
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.contrib import messages
from submission_monitoring.models import Complaint
from .models import ComplaintAttachment, SystemLog

ALLOWED_MIME_TYPES = {"image/jpeg","image/png","image/gif","application/pdf","video/mp4"}
MAX_FILE_SIZE = 5 * 1024 * 1024


@login_required
def upload_attachment(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.user != complaint.submitter and not request.user.is_admin():
        raise Http404
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if mime_type not in ALLOWED_MIME_TYPES:
            messages.error(request, "File type not allowed.")
            return redirect("submission_monitoring:detail", complaint_id=complaint_id)
        if uploaded_file.size > MAX_FILE_SIZE:
            messages.error(request, "File exceeds 5 MB limit.")
            return redirect("submission_monitoring:detail", complaint_id=complaint_id)
        attachment = ComplaintAttachment.objects.create(
            complaint=complaint, uploaded_by=request.user,
            file=uploaded_file, original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=mime_type or "application/octet-stream",
        )
        try:
            dir_path = os.path.dirname(attachment.file.path)
            os.chmod(dir_path, 0o750)
            os.chmod(attachment.file.path, 0o640)
        except Exception:
            pass
        SystemLog.objects.create(
            action="file_upload", complaint=complaint, actor=request.user,
            description="File \"" + uploaded_file.name + "\" uploaded for complaint #" + str(complaint_id),
        )
        messages.success(request, "File uploaded successfully.")
    return redirect("submission_monitoring:detail", complaint_id=complaint_id)


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(ComplaintAttachment, id=attachment_id)
    complaint  = attachment.complaint
    user       = request.user
    authorized = (user == complaint.submitter or user == complaint.assigned_to or user.is_admin())
    if not authorized:
        raise Http404
    if not os.path.exists(attachment.file.path):
        raise Http404
    return FileResponse(
        open(attachment.file.path, "rb"),
        as_attachment=True,
        filename=attachment.original_filename,
    )


@login_required
def system_log_view(request):
    if not request.user.is_admin():
        raise Http404
    action_filter = request.GET.get("action", "")
    logs = SystemLog.objects.select_related("actor", "complaint").order_by("-timestamp")
    if action_filter:
        logs = logs.filter(action=action_filter)
    logs = logs[:200]
    return render_logs(request, logs, action_filter)


def render_logs(request, logs, action_filter):
    from django.shortcuts import render
    return render(request, "file_engine/system_logs.html", {
        "logs": logs,
        "action_filter": action_filter,
        "action_choices": SystemLog.ACTION_CHOICES,
    })
