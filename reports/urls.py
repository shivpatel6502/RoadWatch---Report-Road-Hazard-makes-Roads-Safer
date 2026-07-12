"""
RoadWatch — reports/urls.py
Full URL routing for all citizen-facing views.
"""

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Homepage / browse
    path('', views.IndexView.as_view(), name='index'),

    # Auth
    path('register/', views.RegisterView.as_view(), name='register'),
    path('accounts/login/', views.RWLoginView.as_view(), name='login'),

    # Dashboard & profile
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),

    # Reports
    path('report/submit/', views.ReportSubmitView.as_view(), name='submit'),
    path('report/<int:pk>/', views.ReportDetailView.as_view(), name='detail'),
    path('report/<int:pk>/upvote/', views.UpvoteView.as_view(), name='upvote'),
    path('report/<int:pk>/comment/', views.CommentSubmitView.as_view(), name='comment'),

    # Notifications
    path('notifications/mark-read/', views.MarkNotificationsReadView.as_view(), name='mark_notifications_read'),

    # About Us
    path('about/', views.AboutView.as_view(), name='about'),

    # Leaderboard
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    # Subscription
    path('subscribe/', views.SubscriptionView.as_view(), name='subscription'),
    # Contact
    path('contact/', views.ContactView.as_view(), name='contact'),
    # City Admin
    path('city-admin/', views.CityAdminDashboardView.as_view(), name='city_admin_dashboard'),
    path('report/<int:pk>/update-status/', views.UpdateReportStatusView.as_view(), name='update_status'),
    # Super Admin
    path('super-admin/', views.SuperAdminDashboardView.as_view(), name='super_admin_dashboard'),
    # CSV Export
    path('reports/export/', views.CSVExportView.as_view(), name='csv_export'),
]
