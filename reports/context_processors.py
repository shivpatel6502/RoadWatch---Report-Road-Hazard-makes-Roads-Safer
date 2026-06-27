"""
RoadWatch — reports/context_processors.py
Injects global context (unread notifications, platform stats) into every template.
"""

from .models import Notification, HazardReport


def global_context(request):
    """Available in every template as template context variables."""
    ctx = {
        'fixed_reports_total': HazardReport.objects.filter(status='fixed').count(),
        'total_reports':       HazardReport.objects.filter(is_active=True).count(),
    }
    if request.user.is_authenticated:
        ctx['unread_notifications'] = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        ctx['latest_notifications'] = Notification.objects.filter(
            user=request.user
        ).select_related('report').order_by('-created_at')[:5]
    else:
        ctx['unread_notifications'] = 0
        ctx['latest_notifications'] = []
    return ctx
