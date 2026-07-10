# 🛣️ RoadWatch — Community Road Hazard Reporting Platform

> **COMP-8347 | Database Systems & Web Development**
> University of Windsor | Masters of Applied Computing | Summer 2026 | **Group 14**

---

## 📋 Project Overview

RoadWatch is a Django-based community platform where citizens report road hazards (potholes, sinkholes, broken traffic lights, flooding, and more). Reports are **AI-scored for severity**, **prioritized by community upvotes**, and tracked through a **6-stage status pipeline** until the hazard is fixed.

### 🎯 Problem Statement
- Road hazards cause accidents and vehicle damage daily
- Existing 311/city reporting systems are slow and opaque — citizens get **zero feedback**
- No community prioritization — a critical sinkhole queues the same as a minor pothole
- RoadWatch solves this with **crowdsourced detection + AI scoring + real-time city dashboards**

---

## 👥 Team Members — Group 14

| # | Name | Role | Contributions |
|---|------|------|--------------|
| 1 | **Janitha Reddy** | AI Features & Views | AI severity scorer, duplicate detection, upvote/flag views, URL routing, AIInsight model |
| 2 | **Lisa Magnani** | Database & Models | All 9 Django models, migrations, Admin config, JSON fixtures, seed data, status history logging |
| 3 | **Shiv Patel** | Frontend & Templates | 12+ HTML templates, Bootstrap 5, base.html, dark/light theme toggle, CSS animations, responsive layout |
| 4 | **Dhruv Patel** | Auth, Forms & Uploads | Registration, login, logout, forgot password, 3-photo upload, avatar, document upload, sessions/cookies, role-based access |
| 5 | **Hiten Patil** | Dashboards & Search | Citizen/city/super admin dashboards, Q-object search, dropdown filters, pagination, notifications, CSV export, leaderboard |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14 + Django 5.0.7 |
| Frontend | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons |
| Database | SQLite via Django ORM |
| Auth | Django built-in + role-based (UserPassesTestMixin) |
| Sessions | Django sessions + cookie-based visit counter |
| Email | Django email framework (Gmail SMTP) |
| Animations | Pure CSS keyframes + JS micro-interactions |
| Design | Glassmorphism, dark/light themes, CSS variables |
| Version Control | GitHub |

---

## 🗄️ Database — 9 Models

| Model | Purpose |
|-------|---------|
| `Profile` | Extends User — role, city, avatar |
| `HazardReport` | Core entity — title, type, severity, status, GPS |
| `ReportPhoto` | Up to 3 photos per report |
| `StatusHistory` | Full audit trail of status changes |
| `Upvote` | One per user per report |
| `Comment` | Citizen comments |
| `AIInsight` | AI severity score + duplicate detection |
| `Notification` | In-app alerts on status change |
| `Subscription` | Free / Citizen Pro / City Partner plans |

### Status Pipeline
`Open` → `Under Review` → `In Progress` → `Pending Verification` → `Resolved` → `Fixed`

---

## ⚙️ Views — 18 Class-Based Views (CBV)

All views use Django CBVs with `LoginRequiredMixin` and `UserPassesTestMixin` where appropriate.

`IndexView`, `ReportDetailView`, `RegisterView`, `RWLoginView`, `DashboardView`, `ProfileEditView`, `ReportSubmitView`, `UpvoteView`, `CommentSubmitView`, `MarkNotificationsReadView`, `LeaderboardView`, `SubscriptionView`, `ContactView`, `AboutView`, `CityAdminDashboardView`, `UpdateReportStatusView`, `SuperAdminDashboardView`, `CSVExportView`

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/shivpatel6502/RoadWatch---Report-Road-Hazard-makes-Roads-Safer.git
cd RoadWatch---Report-Road-Hazard-makes-Roads-Safer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Load seed data (fixtures)
python manage.py loaddata fixtures/01_users.json
python manage.py loaddata fixtures/02_profiles.json
python manage.py loaddata fixtures/03_hazard_reports.json
python manage.py loaddata fixtures/04_report_photos.json
python manage.py loaddata fixtures/05_status_history.json
python manage.py loaddata fixtures/06_upvotes_comments.json
python manage.py loaddata fixtures/07_aiinsights_notifications.json

# Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`

---

## 🔑 Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `shiv` | `password123` | Citizen |
| `dhruv` | `password123` | Citizen |
| `hiten` | `password123` | Citizen |
| `janitha` | `password123` | Citizen |
| `lisa` | `password123` | Citizen |
| `superadmin` | `password123` | Super Admin |

---

## 🌐 URL Reference

| Page | URL | Access |
|------|-----|--------|
| Homepage | `/` | Public |
| Register | `/register/` | Public |
| Login | `/accounts/login/` | Public |
| Dashboard | `/dashboard/` | Login required |
| Submit Report | `/report/submit/` | Login required |
| Report Detail | `/report/<id>/` | Public |
| Leaderboard | `/leaderboard/` | Public |
| Subscription | `/subscribe/` | Public |
| City Admin | `/city-admin/` | City Admin |
| Super Admin | `/super-admin/` | Super Admin |
| CSV Export | `/reports/export/` | Admin only |

---

## 🎨 Bonus Features

- 🌙 **Dark/Light Theme** — Toggle in navbar, persisted via localStorage
- 🚧 **Loading Animation** — Accident emoji sequence on every page load
- 🏆 **Animated Leaderboard** — Spinning crown, rising podium, 9 stats per user
- 💳 **Subscription Plans** — Free / Citizen Pro $4.99 / City Partner $29/mo
- 📊 **Admin Dashboards** — City + Super Admin KPI analytics
- 📤 **CSV Export** — Admin-filtered report download
- 🔔 **Notification System** — In-app alerts with auto-dismiss
- 🤖 **AI Severity Scoring** — Keyword engine (1–10 scale) + duplicate detection
- 🗺️ **GPS Coordinates** — Lat/long stored per report
- 📧 **Email Password Reset** — Django auth + Gmail SMTP

---

## 📊 Live Database Stats

| Metric | Value |
|--------|-------|
| Registered users | 15 |
| Total hazard reports | 40 |
| Fixed reports | 10 |
| Resolved reports | 7 |
| In-progress reports | 9 |
| Critical severity reports | 13 |
| Community upvotes | 103 |
| Comments | 83 |
| Cities covered | Windsor, Toronto |

---

*COMP-8347 — University of Windsor — Group 14 — Summer 2026*

## Database Models (Lisa Magnani)
All 9 core models designed and implemented by Lisa:
- HazardReport, ReportPhoto, Comment, Upvote
- Profile, Notification, StatusHistory, AIInsight, Subscription
