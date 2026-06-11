"""
RoadWatch — reports/models.py
All 8 data models for the platform.
  1. Profile          — extends User with role, city, avatar
  2. HazardReport     — core entity (title, type, severity, 6-stage status, location, AI score)
  3. ReportPhoto      — up to 3 photos per HazardReport
  4. StatusHistory    — full audit trail of every status change
  5. Upvote           — one per user per report (unique_together)
  6. Comment          — citizen comments on reports
  7. AIInsight        — caches AI severity score & duplicate detection result
  8. Notification     — in-app alerts when a followed report changes status
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ---------------------------------------------------------------------------
# Shared choice tuples
# ---------------------------------------------------------------------------

class HazardType(models.TextChoices):
    POTHOLE          = 'pothole',         'Pothole'
    DAMAGED_SIGN     = 'damaged_sign',    'Damaged Sign'
    BROKEN_LIGHT     = 'broken_light',    'Broken Street Light'
    ROAD_CRACK       = 'road_crack',      'Road Crack / Sinkhole'
    FLOODING         = 'flooding',        'Flooding / Standing Water'
    DEBRIS           = 'debris',          'Debris on Road'
    GUARDRAIL        = 'guardrail',       'Damaged Guardrail'
    BRIDGE_DAMAGE    = 'bridge_damage',   'Bridge Damage'
    OTHER            = 'other',           'Other'


class SeverityLevel(models.TextChoices):
    LOW      = 'low',      'Low — Minor inconvenience'
    MEDIUM   = 'medium',   'Medium — Noticeable hazard'
    HIGH     = 'high',     'High — Dangerous'
    CRITICAL = 'critical', 'Critical — Immediate danger'


class ReportStatus(models.TextChoices):
    OPEN            = 'open',           'Open'
    UNDER_REVIEW    = 'under_review',   'Under Review'
    IN_PROGRESS     = 'in_progress',    'In Progress'
    PENDING_VERIFY  = 'pending_verify', 'Pending Verification'
    RESOLVED        = 'resolved',       'Resolved'
    FIXED           = 'fixed',          'Fixed'


class UserRole(models.TextChoices):
    CITIZEN     = 'citizen',     'Citizen'
    CITY_ADMIN  = 'city_admin',  'City Admin'
    SUPER_ADMIN = 'super_admin', 'Super Admin'


# ---------------------------------------------------------------------------
# 1. Profile — extends Django's User
# ---------------------------------------------------------------------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CITIZEN,
    )
    city = models.CharField(max_length=100, blank=True, default='')
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text='Profile picture (optional)',
    )
    bio = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_role_display()})'

    @property
    def is_city_admin(self):
        return self.role == UserRole.CITY_ADMIN

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_citizen(self):
        return self.role == UserRole.CITIZEN


# ---------------------------------------------------------------------------
# 2. HazardReport — the core entity
# ---------------------------------------------------------------------------

class HazardReport(models.Model):
    # Basic info
    title = models.CharField(max_length=200)
    description = models.TextField()
    hazard_type = models.CharField(
        max_length=30,
        choices=HazardType.choices,
        default=HazardType.POTHOLE,
    )
    severity = models.CharField(
        max_length=10,
        choices=SeverityLevel.choices,
        default=SeverityLevel.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
    )

    # Location
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=200)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        help_text='GPS latitude (optional)',
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        help_text='GPS longitude (optional)',
    )

    # Relationships
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports',
    )

    # AI scoring (populated by ai/services.py; 0 = not yet scored)
    ai_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text='AI severity score 1–10 (0 = not yet scored)',
    )

    # Supporting document (e.g. council letter, PDF)
    document = models.FileField(
        upload_to='documents/',
        blank=True,
        null=True,
        help_text='Optional supporting document (PDF, DOCX, etc.)',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft-delete / moderation flag
    is_flagged = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Hazard Report'
        verbose_name_plural = 'Hazard Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_status_display()}] {self.title} — {self.city}'

    @property
    def upvote_count(self):
        return self.upvotes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def photo_count(self):
        return self.photos.count()


# ---------------------------------------------------------------------------
# 3. ReportPhoto — up to 3 photos per HazardReport
# ---------------------------------------------------------------------------

class ReportPhoto(models.Model):
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='photos',
    )
    image = models.ImageField(upload_to='report_photos/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report Photo'
        verbose_name_plural = 'Report Photos'
        ordering = ['uploaded_at']

    def __str__(self):
        return f'Photo for Report #{self.report.pk} — {self.uploaded_at:%Y-%m-%d}'


# ---------------------------------------------------------------------------
# 4. StatusHistory — full audit trail of every status transition
# ---------------------------------------------------------------------------

class StatusHistory(models.Model):
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    old_status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        blank=True,
        default='',
    )
    new_status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes',
    )
    timestamp = models.DateTimeField(default=timezone.now)
    note = models.TextField(
        blank=True,
        default='',
        help_text='Official admin response or reason for this status change',
    )

    class Meta:
        verbose_name = 'Status History'
        verbose_name_plural = 'Status Histories'
        ordering = ['timestamp']

    def __str__(self):
        return (
            f'Report #{self.report.pk}: '
            f'{self.old_status or "—"} → {self.new_status} '
            f'at {self.timestamp:%Y-%m-%d %H:%M}'
        )


# ---------------------------------------------------------------------------
# 5. Upvote — one per user per report
# ---------------------------------------------------------------------------

class Upvote(models.Model):
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='upvotes',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='upvotes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Upvote'
        verbose_name_plural = 'Upvotes'
        unique_together = ('report', 'user')   # one upvote per user per report

    def __str__(self):
        return f'{self.user.username} ↑ Report #{self.report.pk}'


# ---------------------------------------------------------------------------
# 6. Comment — citizen comments on a report
# ---------------------------------------------------------------------------

class Comment(models.Model):
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_flagged = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} on Report #{self.report.pk} ({self.created_at:%Y-%m-%d})'


# ---------------------------------------------------------------------------
# 7. AIInsight — caches AI severity scoring and duplicate detection
# ---------------------------------------------------------------------------

class AIInsight(models.Model):
    report = models.OneToOneField(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='ai_insight',
    )
    severity_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text='AI-computed severity 1–10 (0 = stub / not yet computed)',
    )
    is_duplicate_of = models.ForeignKey(
        HazardReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates',
        help_text='If set, this report is likely a duplicate of another report',
    )
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        help_text='Full raw JSON response from the AI API',
    )
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Insight'
        verbose_name_plural = 'AI Insights'

    def __str__(self):
        dup = f' (dup of #{self.is_duplicate_of.pk})' if self.is_duplicate_of else ''
        return f'AIInsight for Report #{self.report.pk} — score={self.severity_score}{dup}'


# ---------------------------------------------------------------------------
# 8. Notification — in-app alerts for status changes on followed reports
# ---------------------------------------------------------------------------

class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    report = models.ForeignKey(
        HazardReport,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        status = 'read' if self.is_read else 'unread'
        return f'Notification → {self.user.username} | {self.message[:60]} [{status}]'


# ---------------------------------------------------------------------------
# 9. Subscription — user plan (Free / Citizen Pro / City Partner)
# ---------------------------------------------------------------------------

class SubscriptionPlan(models.TextChoices):
    FREE      = 'free',       'Free'
    CITIZEN   = 'citizen',    'Citizen Pro'
    CITY      = 'city',       'City Partner'

class Subscription(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan          = models.CharField(max_length=20, choices=SubscriptionPlan.choices, default=SubscriptionPlan.FREE)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active     = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} — {self.plan}"
