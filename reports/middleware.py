"""
RoadWatch — reports/middleware.py
Tracks the user's daily visit count via a cookie (COMP-8347 requirement).
"""

from datetime import date


class VisitCounterMiddleware:
    """
    Reads/writes two cookies:
      - rw_daily_visits     : integer visit count for today
      - rw_last_visit_date  : ISO date of last recorded visit
    Resets to 1 at midnight when the date changes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        today = date.today().isoformat()
        last_visit_date = request.COOKIES.get('rw_last_visit_date', '')

        try:
            daily_count = int(request.COOKIES.get('rw_daily_visits', 0))
        except (ValueError, TypeError):
            daily_count = 0

        if last_visit_date != today:
            daily_count = 1           # new day — reset counter
        else:
            daily_count += 1          # same day — increment

        response.set_cookie('rw_daily_visits',    daily_count, max_age=86400, samesite='Lax')
        response.set_cookie('rw_last_visit_date', today,       max_age=86400, samesite='Lax')

        return response
