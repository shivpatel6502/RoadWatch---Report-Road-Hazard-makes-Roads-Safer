"""
RoadWatch — reports/views.py
All class-based views for auth, report browsing, submission, dashboard, profile, and about.
"""

from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta

from .models import (
    HazardReport, ReportPhoto, StatusHistory, Profile,
    Upvote, Comment, Notification, AIInsight,
    HazardType, SeverityLevel, ReportStatus, UserRole,
)
from .forms import (
    UserRegistrationForm, HazardReportForm,
    UserUpdateForm, ProfileUpdateForm, CommentForm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _track_recently_viewed(request, report_pk):
    """Store up to 5 recently viewed report PKs in the session."""
    recently = request.session.get('recently_viewed', [])
    if report_pk in recently:
        recently.remove(report_pk)
    recently.insert(0, report_pk)
    request.session['recently_viewed'] = recently[:5]


# ---------------------------------------------------------------------------
# 1. Index / Browse (ListView) — homepage + report list
# ---------------------------------------------------------------------------

class IndexView(ListView):
    model = HazardReport
    template_name = 'index.html'
    context_object_name = 'reports'
    paginate_by = 9

    def get_queryset(self):
        qs = HazardReport.objects.filter(is_active=True).select_related('reporter', 'reporter__profile')

        # Keyword search (Q objects across 4 fields)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(city__icontains=q) |
                Q(street__icontains=q)
            )

        # Dropdown filters
        hazard_type = self.request.GET.get('hazard_type', '')
        severity    = self.request.GET.get('severity', '')
        status      = self.request.GET.get('status', '')
        city        = self.request.GET.get('city', '').strip()

        # Fall back to session city preference if no city filter in URL
        if not city:
            city = self.request.session.get('city_preference', '')

        if hazard_type:
            qs = qs.filter(hazard_type=hazard_type)
        if severity:
            qs = qs.filter(severity=severity)
        if status:
            qs = qs.filter(status=status)
        if city:
            qs = qs.filter(city__icontains=city)
            # Persist city preference to session
            self.request.session['city_preference'] = city

        return qs.annotate(upvote_count_ann=Count('upvotes')).order_by('-ai_score', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hazard_types']     = HazardType.choices
        context['severity_levels']  = SeverityLevel.choices
        context['status_choices']   = ReportStatus.choices
        context['in_progress_count']= HazardReport.objects.filter(status__in=['in_progress', 'under_review']).count()
        context['cities']           = sorted(HazardReport.objects.values_list('city', flat=True).distinct())
        context['current_filters']  = {
            'q':           self.request.GET.get('q', ''),
            'hazard_type': self.request.GET.get('hazard_type', ''),
            'severity':    self.request.GET.get('severity', ''),
            'status':      self.request.GET.get('status', ''),
            'city':        self.request.GET.get('city', ''),
        }
        return context


# ---------------------------------------------------------------------------
# 2. Register
# ---------------------------------------------------------------------------

class RegisterView(View):
    template_name = 'registration/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('reports:index')
        return render(request, self.template_name, {'form': UserRegistrationForm()})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set city on the auto-created Profile
            try:
                user.profile.city = form.cleaned_data.get('city', '')
                user.profile.save()
            except Profile.DoesNotExist:
                Profile.objects.create(user=user, city=form.cleaned_data.get('city', ''))

            # Store city preference in session
            request.session['city_preference'] = form.cleaned_data.get('city', '')

            login(request, user)
            messages.success(
                request,
                f'Welcome to RoadWatch, {user.first_name or user.username}! '
                f'Your account has been created successfully.'
            )
            return redirect('reports:dashboard')
        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# 3. Custom Login (overrides template only; Django handles auth logic)
# ---------------------------------------------------------------------------

class RWLoginView(DjangoLoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return reverse_lazy('reports:dashboard')


# ---------------------------------------------------------------------------
# 4. Report Detail (DetailView)
# ---------------------------------------------------------------------------

class ReportDetailView(DetailView):
    model = HazardReport
    template_name = 'reports/detail.html'
    context_object_name = 'report'

    def get_object(self):
        obj = super().get_object()
        _track_recently_viewed(self.request, obj.pk)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = context['report']
        context['photos']         = report.photos.all()
        context['status_history'] = report.status_history.all().order_by('timestamp')
        context['comments']       = report.comments.filter(is_flagged=False).select_related('user', 'user__profile')
        context['comment_form']   = CommentForm()
        context['upvote_count']   = report.upvotes.count()
        context['comment_count']  = report.comments.filter(is_flagged=False).count()

        if self.request.user.is_authenticated:
            context['user_has_upvoted'] = report.upvotes.filter(user=self.request.user).exists()
        else:
            context['user_has_upvoted'] = False

        try:
            context['ai_insight'] = report.ai_insight
        except AIInsight.DoesNotExist:
            context['ai_insight'] = None

        return context


# ---------------------------------------------------------------------------
# 5. Report Submission (LoginRequired)
# ---------------------------------------------------------------------------

class ReportSubmitView(LoginRequiredMixin, View):
    template_name = 'reports/submit.html'
    login_url = '/accounts/login/'

    def get(self, request):
        initial = {'city': request.session.get('city_preference', '')}
        return render(request, self.template_name, {'form': HazardReportForm(initial=initial)})

    def post(self, request):
        form = HazardReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()

            # Save city preference to session
            request.session['city_preference'] = report.city

            # Save up to 3 photos
            for i in range(1, 4):
                photo_file = request.FILES.get(f'photo{i}')
                if photo_file:
                    ReportPhoto.objects.create(report=report, image=photo_file)

            # Create initial StatusHistory entry
            StatusHistory.objects.create(
                report=report,
                old_status='',
                new_status='open',
                changed_by=request.user,
                note='Report submitted by citizen.',
            )

            # Create stub AIInsight (real scoring wired in Phase 3)
            AIInsight.objects.create(
                report=report,
                severity_score=0,
                raw_response={'stub': True, 'note': 'To be scored by AI service in Phase 3'},
            )

            messages.success(
                request,
                '✅ Your hazard report has been submitted! Thank you for making roads safer.'
            )
            return redirect('reports:detail', pk=report.pk)

        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# 6. Citizen Dashboard (LoginRequired)
# ---------------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        my_reports = HazardReport.objects.filter(reporter=user, is_active=True)
        context['my_reports']       = my_reports.order_by('-created_at')[:8]
        context['my_report_count']  = my_reports.count()
        context['my_fixed_count']   = my_reports.filter(status='fixed').count()
        context['my_open_count']    = my_reports.filter(status='open').count()
        context['my_upvotes_given'] = Upvote.objects.filter(user=user).count()
        context['my_in_progress']   = my_reports.filter(status__in=['in_progress', 'under_review']).count()

        # ── Analytics: Status breakdown (for donut chart) ──────────────────
        all_active = HazardReport.objects.filter(is_active=True)
        status_breakdown = (
            all_active.values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        status_labels  = []
        status_counts  = []
        status_display = dict(ReportStatus.choices)
        for item in status_breakdown:
            status_labels.append(status_display.get(item['status'], item['status']))
            status_counts.append(item['count'])
        context['status_labels'] = status_labels
        context['status_counts'] = status_counts

        # ── Analytics: Severity breakdown ──────────────────────────────────
        severity_breakdown = (
            all_active.values('severity')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        severity_labels  = []
        severity_counts  = []
        severity_display = dict(SeverityLevel.choices)
        for item in severity_breakdown:
            severity_labels.append(severity_display.get(item['severity'], item['severity']).split('—')[0].strip())
            severity_counts.append(item['count'])
        context['severity_labels'] = severity_labels
        context['severity_counts'] = severity_counts

        # ── Analytics: Hazard type breakdown (for bar chart) ────────────────
        hazard_breakdown = (
            all_active.values('hazard_type')
            .annotate(count=Count('id'))
            .order_by('-count')[:6]
        )
        hazard_labels  = []
        hazard_counts  = []
        hazard_display = dict(HazardType.choices)
        for item in hazard_breakdown:
            hazard_labels.append(hazard_display.get(item['hazard_type'], item['hazard_type']))
            hazard_counts.append(item['count'])
        context['hazard_labels'] = hazard_labels
        context['hazard_counts'] = hazard_counts

        # ── Platform-wide stats ──────────────────────────────────────────────
        total = all_active.count() or 1
        fixed = all_active.filter(status='fixed').count()
        context['platform_total']          = all_active.count()
        context['platform_fixed']          = fixed
        context['platform_open']           = all_active.filter(status='open').count()
        context['platform_in_progress']    = all_active.filter(status__in=['in_progress','under_review']).count()
        context['resolution_rate']         = round((fixed / total) * 100, 1)
        context['platform_critical']       = all_active.filter(severity='critical').count()

        # ── My reports: severity progress bars ───────────────────────────────
        my_total = my_reports.count() or 1
        context['my_severity_data'] = [
            {'label': 'Critical', 'count': my_reports.filter(severity='critical').count(), 'color': '#f75a5a', 'pct': round(my_reports.filter(severity='critical').count() / my_total * 100)},
            {'label': 'High',     'count': my_reports.filter(severity='high').count(),     'color': '#f59e0b', 'pct': round(my_reports.filter(severity='high').count()     / my_total * 100)},
            {'label': 'Medium',   'count': my_reports.filter(severity='medium').count(),   'color': '#7c5af7', 'pct': round(my_reports.filter(severity='medium').count()   / my_total * 100)},
            {'label': 'Low',      'count': my_reports.filter(severity='low').count(),      'color': '#64748b', 'pct': round(my_reports.filter(severity='low').count()      / my_total * 100)},
        ]

        # ── Recent 7-day activity (daily report counts) ──────────────────────
        today = timezone.now().date()
        daily_labels = []
        daily_counts = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily_labels.append(d.strftime('%b %d'))
            daily_counts.append(
                HazardReport.objects.filter(
                    created_at__date=d, is_active=True
                ).count()
            )
        context['daily_labels'] = daily_labels
        context['daily_counts'] = daily_counts

        # ── Recently viewed ──────────────────────────────────────────────────
        rv_ids = self.request.session.get('recently_viewed', [])
        if rv_ids:
            rv_qs   = HazardReport.objects.filter(pk__in=rv_ids, is_active=True)
            id_order = {pk: i for i, pk in enumerate(rv_ids)}
            context['recently_viewed'] = sorted(rv_qs, key=lambda r: id_order.get(r.pk, 999))
        else:
            context['recently_viewed'] = []

        # ── Notifications ────────────────────────────────────────────────────
        context['notifications']  = Notification.objects.filter(user=user).order_by('-created_at')[:10]
        context['unread_count']   = Notification.objects.filter(user=user, is_read=False).count()

        # ── Daily visit cookie ────────────────────────────────────────────────
        try:
            context['daily_visits'] = int(self.request.COOKIES.get('rw_daily_visits', 1))
        except (ValueError, TypeError):
            context['daily_visits'] = 1

        # ── City preference ───────────────────────────────────────────────────
        context['city_preference'] = self.request.session.get('city_preference', '')

        return context


# ---------------------------------------------------------------------------
# 6b. About Us page
# ---------------------------------------------------------------------------

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_active = HazardReport.objects.filter(is_active=True)
        total = all_active.count() or 1
        fixed = all_active.filter(status='fixed').count()
        context['platform_total']    = all_active.count()
        context['platform_fixed']    = fixed
        context['resolution_rate']   = round((fixed / total) * 100, 1)
        context['platform_cities']   = HazardReport.objects.values('city').distinct().count()
        return context


# ---------------------------------------------------------------------------
# 7. Profile Edit (LoginRequired)
# ---------------------------------------------------------------------------

class ProfileEditView(LoginRequiredMixin, View):
    template_name = 'profile_edit.html'
    login_url = '/accounts/login/'

    def get(self, request):
        return render(request, self.template_name, {
            'user_form':    UserUpdateForm(instance=request.user),
            'profile_form': ProfileUpdateForm(instance=request.user.profile),
        })

    def post(self, request):
        user_form    = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile = profile_form.save()
            if profile.city:
                request.session['city_preference'] = profile.city
            messages.success(request, '✅ Your profile has been updated successfully!')
            return redirect('reports:dashboard')

        return render(request, self.template_name, {
            'user_form':    user_form,
            'profile_form': profile_form,
        })


# ---------------------------------------------------------------------------
# 8. Upvote Toggle (LoginRequired, POST only)
# ---------------------------------------------------------------------------

class UpvoteView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def post(self, request, pk):
        report = get_object_or_404(HazardReport, pk=pk, is_active=True)
        upvote, created = Upvote.objects.get_or_create(report=report, user=request.user)
        if not created:
            upvote.delete()
            messages.info(request, 'Upvote removed.')
        else:
            messages.success(request, '👍 Report upvoted!')
        return redirect('reports:detail', pk=pk)


# ---------------------------------------------------------------------------
# 9. Comment Submit (LoginRequired, POST only)
# ---------------------------------------------------------------------------

class CommentSubmitView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def post(self, request, pk):
        report = get_object_or_404(HazardReport, pk=pk, is_active=True)
        form   = CommentForm(request.POST)
        if form.is_valid():
            comment        = form.save(commit=False)
            comment.report = report
            comment.user   = request.user
            comment.save()
            messages.success(request, '💬 Comment posted!')
        else:
            messages.error(request, 'Comment could not be posted. Please try again.')
        return redirect('reports:detail', pk=pk)


# ---------------------------------------------------------------------------
# 10. Mark notifications read
# ---------------------------------------------------------------------------

class MarkNotificationsReadView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('reports:dashboard')


# ---------------------------------------------------------------------------
# 9. Leaderboard
# ---------------------------------------------------------------------------
class LeaderboardView(TemplateView):
    template_name = 'leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth.models import User
        from django.utils import timezone
        top_users = []
        for user in User.objects.filter(is_active=True).select_related('profile'):
            reports     = HazardReport.objects.filter(reporter=user, is_active=True)
            total       = reports.count()
            if not total:
                continue
            fixed       = reports.filter(status='fixed').count()
            resolved    = reports.filter(status='resolved').count()
            in_progress = reports.filter(status='in_progress').count()
            under_review= reports.filter(status='under_review').count()
            open_count  = reports.filter(status='open').count()
            critical    = reports.filter(severity='critical').count()
            high        = reports.filter(severity='high').count()
            upvotes     = Upvote.objects.filter(report__reporter=user).count()
            comments    = Comment.objects.filter(user=user).count()
            cities      = reports.values('city').distinct().count()
            last_rpt    = reports.order_by('-created_at').first()
            days_ago    = (timezone.now() - last_rpt.created_at).days if last_rpt else 99
            res_rate    = round((fixed + resolved) / total * 100) if total else 0
            score       = (fixed * 3) + (resolved * 2) + (total * 1) + (upvotes * 2) + (critical * 1)
            top_users.append({
                'user':         user,
                'total':        total,
                'fixed':        fixed,
                'resolved':     resolved,
                'in_progress':  in_progress,
                'under_review': under_review,
                'open_count':   open_count,
                'critical':     critical,
                'high':         high,
                'upvotes':      upvotes,
                'comments':     comments,
                'cities':       cities,
                'days_ago':     days_ago,
                'res_rate':     res_rate,
                'score':        score,
            })
        top_users.sort(key=lambda x: x['score'], reverse=True)
        context['leaderboard'] = top_users[:15]
        all_active = HazardReport.objects.filter(is_active=True)
        total_all  = all_active.count() or 1
        context['platform_fixed']    = all_active.filter(status='fixed').count()
        context['platform_total']    = all_active.count()
        context['platform_critical'] = all_active.filter(severity='critical').count()
        context['resolution_rate']   = round(all_active.filter(status__in=['fixed','resolved']).count() / total_all * 100, 1)
        return context


# ---------------------------------------------------------------------------
# 10. Subscription page
# ---------------------------------------------------------------------------
class SubscriptionView(TemplateView):
    template_name = 'subscription.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            from .models import Subscription, SubscriptionPlan
            sub, _ = Subscription.objects.get_or_create(
                user=self.request.user,
                defaults={'plan': 'free'}
            )
            context['current_plan'] = sub.plan
        else:
            context['current_plan'] = 'free'
        return context

    def post(self, request):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('/accounts/login/')
        from .models import Subscription
        plan = request.POST.get('plan', 'free')
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        sub.plan = plan
        sub.is_active = True
        sub.save()
        messages.success(request, f'🎉 Successfully subscribed to {sub.get_plan_display()} plan!')
        return redirect('reports:subscription')

# ---------------------------------------------------------------------------
# 11. Contact page
# ---------------------------------------------------------------------------
class ContactView(TemplateView):
    template_name = 'contact.html'

    def post(self, request):
        name    = request.POST.get('name', '')
        email   = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        if name and email and message:
            messages.success(request, f'✅ Thank you {name}! Your message has been received. We will get back to you within 24 hours.')
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('reports:contact')

# ---------------------------------------------------------------------------
# 12. City Admin Dashboard
# ---------------------------------------------------------------------------
from django.contrib.auth.mixins import UserPassesTestMixin

class CityAdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'city_admin_dashboard.html'
    login_url = '/accounts/login/'

    def test_func(self):
        return self.request.user.profile.is_city_admin or self.request.user.profile.is_super_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        city = user.profile.city
        city_reports = HazardReport.objects.filter(is_active=True)
        if not user.profile.is_super_admin:
            city_reports = city_reports.filter(city__iexact=city)
        context['city_reports']    = city_reports.order_by('-ai_score', '-created_at')[:30]
        context['city_total']      = city_reports.count()
        context['city_open']       = city_reports.filter(status='open').count()
        context['city_in_progress']= city_reports.filter(status='in_progress').count()
        context['city_fixed']      = city_reports.filter(status='fixed').count()
        context['city_critical']   = city_reports.filter(severity='critical').count()
        context['city_name']       = city or 'All Cities'
        return context

class UpdateReportStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/accounts/login/'

    def test_func(self):
        return self.request.user.profile.is_city_admin or self.request.user.profile.is_super_admin

    def post(self, request, pk):
        report = get_object_or_404(HazardReport, pk=pk)
        new_status = request.POST.get('status')
        note       = request.POST.get('note', '')
        if new_status and new_status != report.status:
            old_status = report.status
            StatusHistory.objects.create(
                report=report,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                note=note,
            )
            report.status = new_status
            report.save()
            # Notify reporter
            if report.reporter and report.reporter != request.user:
                Notification.objects.create(
                    user=report.reporter,
                    report=report,
                    message=f'Your report "{report.title}" status changed to {report.get_status_display()}.'
                )
            messages.success(request, f'Status updated to {report.get_status_display()}.')
        return redirect('reports:city_admin_dashboard')

# ---------------------------------------------------------------------------
# 13. Super Admin Dashboard
# ---------------------------------------------------------------------------
class SuperAdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'super_admin_dashboard.html'
    login_url = '/accounts/login/'

    def test_func(self):
        return self.request.user.profile.is_super_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth.models import User
        all_active = HazardReport.objects.filter(is_active=True)
        context['all_reports']     = all_active.order_by('-created_at')[:20]
        context['platform_total']  = all_active.count()
        context['platform_fixed']  = all_active.filter(status='fixed').count()
        context['platform_open']   = all_active.filter(status='open').count()
        context['platform_critical'] = all_active.filter(severity='critical').count()
        total = all_active.count() or 1
        context['resolution_rate'] = round(all_active.filter(status='fixed').count() / total * 100, 1)
        context['total_users']     = User.objects.count()
        context['city_breakdown']  = (
            all_active.values('city')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )
        return context

# ---------------------------------------------------------------------------
# 14. CSV Export
# ---------------------------------------------------------------------------
import csv
from django.http import HttpResponse

class CSVExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/accounts/login/'

    def test_func(self):
        return self.request.user.profile.is_city_admin or self.request.user.profile.is_super_admin

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="roadwatch_reports.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID','Title','Hazard Type','Severity','Status','City','Street','Reporter','AI Score','Upvotes','Created'])
        reports = HazardReport.objects.filter(is_active=True)
        if not request.user.profile.is_super_admin:
            reports = reports.filter(city__iexact=request.user.profile.city)
        for r in reports:
            writer.writerow([
                r.pk, r.title, r.get_hazard_type_display(), r.get_severity_display(),
                r.get_status_display(), r.city, r.street,
                r.reporter.username if r.reporter else 'anon',
                r.ai_score,
                Upvote.objects.filter(report=r).count(),
                r.created_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response
