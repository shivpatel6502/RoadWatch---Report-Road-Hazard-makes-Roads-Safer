"""
RoadWatch — reports/admin.py
Django Admin registration for all 8 models with rich list/filter/search config.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Profile, HazardReport, ReportPhoto,
    StatusHistory, Upvote, Comment,
    AIInsight, Notification,
)


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class ReportPhotoInline(admin.TabularInline):
    model = ReportPhoto
    extra = 0
    max_num = 3
    readonly_fields = ('uploaded_at', 'image_preview')
    fields = ('image', 'image_preview', 'caption', 'uploaded_at')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:4px;">', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'timestamp', 'note')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('user', 'text', 'created_at', 'is_flagged')
    can_delete = True


# ---------------------------------------------------------------------------
# 1. Profile
# ---------------------------------------------------------------------------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'city', 'created_at', 'avatar_preview')
    list_filter   = ('role', 'city')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'city')
    readonly_fields = ('created_at', 'avatar_preview')

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="height:48px;width:48px;border-radius:50%;object-fit:cover;">', obj.avatar.url)
        return '—'
    avatar_preview.short_description = 'Avatar'


# ---------------------------------------------------------------------------
# 2. HazardReport
# ---------------------------------------------------------------------------

@admin.register(HazardReport)
class HazardReportAdmin(admin.ModelAdmin):
    list_display  = (
        'id', 'title', 'hazard_type', 'severity',
        'status_badge', 'city', 'reporter',
        'upvote_count', 'ai_score', 'created_at',
    )
    list_filter   = ('status', 'hazard_type', 'severity', 'city', 'is_flagged', 'is_active')
    search_fields = ('title', 'description', 'city', 'street', 'reporter__username')
    readonly_fields = ('created_at', 'updated_at', 'ai_score')
    date_hierarchy = 'created_at'
    inlines = [ReportPhotoInline, StatusHistoryInline, CommentInline]

    fieldsets = (
        ('Report Details', {
            'fields': ('title', 'description', 'hazard_type', 'severity', 'status'),
        }),
        ('Location', {
            'fields': ('city', 'street', 'latitude', 'longitude'),
        }),
        ('Reporter & AI', {
            'fields': ('reporter', 'ai_score', 'document'),
        }),
        ('Flags & Timestamps', {
            'fields': ('is_flagged', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colours = {
            'open':           '#6c757d',
            'under_review':   '#0d6efd',
            'in_progress':    '#fd7e14',
            'pending_verify': '#ffc107',
            'resolved':       '#20c997',
            'fixed':          '#198754',
        }
        colour = colours.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{}</span>',
            colour, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def upvote_count(self, obj):
        return obj.upvotes.count()
    upvote_count.short_description = '👍'


# ---------------------------------------------------------------------------
# 3. ReportPhoto
# ---------------------------------------------------------------------------

@admin.register(ReportPhoto)
class ReportPhotoAdmin(admin.ModelAdmin):
    list_display  = ('id', 'report', 'caption', 'uploaded_at', 'image_preview')
    list_filter   = ('uploaded_at',)
    search_fields = ('report__title', 'caption')
    readonly_fields = ('uploaded_at', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:4px;">', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'


# ---------------------------------------------------------------------------
# 4. StatusHistory
# ---------------------------------------------------------------------------

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display  = ('report', 'old_status', 'new_status', 'changed_by', 'timestamp')
    list_filter   = ('old_status', 'new_status')
    search_fields = ('report__title', 'changed_by__username', 'note')
    readonly_fields = ('report', 'old_status', 'new_status', 'changed_by', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False   # status history is system-generated, not manually added


# ---------------------------------------------------------------------------
# 5. Upvote
# ---------------------------------------------------------------------------

@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'report', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('user__username', 'report__title')
    readonly_fields = ('created_at',)


# ---------------------------------------------------------------------------
# 6. Comment
# ---------------------------------------------------------------------------

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'report', 'short_text', 'is_flagged', 'created_at')
    list_filter   = ('is_flagged', 'created_at')
    search_fields = ('user__username', 'text', 'report__title')
    readonly_fields = ('created_at',)
    actions = ['flag_comments', 'unflag_comments']

    def short_text(self, obj):
        return obj.text[:80] + ('…' if len(obj.text) > 80 else '')
    short_text.short_description = 'Comment'

    @admin.action(description='Flag selected comments')
    def flag_comments(self, request, queryset):
        queryset.update(is_flagged=True)

    @admin.action(description='Unflag selected comments')
    def unflag_comments(self, request, queryset):
        queryset.update(is_flagged=False)


# ---------------------------------------------------------------------------
# 7. AIInsight
# ---------------------------------------------------------------------------

@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display  = ('report', 'severity_score', 'is_duplicate_of', 'computed_at')
    list_filter   = ('severity_score',)
    search_fields = ('report__title',)
    readonly_fields = ('computed_at',)


# ---------------------------------------------------------------------------
# 8. Notification
# ---------------------------------------------------------------------------

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'short_message', 'report', 'is_read', 'created_at')
    list_filter   = ('is_read', 'created_at')
    search_fields = ('user__username', 'message', 'report__title')
    readonly_fields = ('created_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    def short_message(self, obj):
        return obj.message[:80] + ('…' if len(obj.message) > 80 else '')
    short_message.short_description = 'Message'

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


# ---------------------------------------------------------------------------
# Customise Admin site header
# ---------------------------------------------------------------------------
admin.site.site_header  = 'RoadWatch Administration'
admin.site.site_title   = 'RoadWatch Admin'
admin.site.index_title  = 'Road Hazard Reporting Platform'
