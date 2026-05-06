import json
import time
from collections import defaultdict
from datetime import date
from decimal import Decimal

import jwt
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.template.response import TemplateResponse

from django.contrib import admin as django_admin

from .models import CurrencyRate, Expense, MetabaseDashboard

admin_site = django_admin.site


DB = "analytics"


def _db():
    """Return 'analytics' if the DB is available, else 'default'."""
    from django.db import connections
    try:
        conn = connections[DB]
        conn.ensure_connection()
        return DB
    except Exception:
        return "default"


def _get_rates():
    """Return {currency: rate_to_usd} dict, USD=1 always."""
    rates = {"USD": Decimal("1")}
    for cr in CurrencyRate.objects.using("default").all():
        rates[cr.currency] = cr.rate_to_usd
    return rates


def _to_usd(amount, currency, rates):
    rate = rates.get(currency)
    if rate:
        return float(amount * rate)
    return 0.0


def _month_key(dt):
    return dt.strftime("%Y-%m")


@staff_member_required
def pnl_dashboard(request):
    from payments.models import PaymentRecord

    rates = _get_rates()
    db = _db()

    # --- Revenue by month (payment_records) ---
    revenue_qs = (
        PaymentRecord.objects.using(db).filter(status="success")
        .annotate(month=TruncMonth("created_at"))
        .values("month", "currency", "payment_system")
        .annotate(total=Sum("amount"), cnt=Count("id"))
        .order_by("month")
    )

    # Aggregate revenue by month in USD
    revenue_by_month = defaultdict(float)
    revenue_by_system = defaultdict(lambda: defaultdict(float))
    revenue_by_currency = defaultdict(lambda: defaultdict(float))
    total_revenue_usd = 0.0
    total_payments = 0

    for row in revenue_qs:
        mk = _month_key(row["month"])
        usd = _to_usd(row["total"], row["currency"], rates)
        revenue_by_month[mk] += usd
        revenue_by_system[row["payment_system"]][mk] += usd
        revenue_by_currency[row["currency"]][mk] += float(row["total"])
        total_revenue_usd += usd
        total_payments += row["cnt"]

    # --- Expenses by month ---
    # For recurring expenses, spread from period to current month
    expenses_by_month = defaultdict(float)
    expenses_by_category = defaultdict(lambda: defaultdict(float))
    total_expenses_usd = 0.0

    today = date.today()
    current_month_start = today.replace(day=1)

    for exp in Expense.objects.select_related("category").all():
        cat_name = exp.category.name
        amount_usd = _to_usd(exp.amount, exp.currency, rates)

        if exp.is_recurring:
            # Spread recurring expense from its period to current month
            m = exp.period.replace(day=1)
            while m <= current_month_start:
                mk = _month_key(m)
                expenses_by_month[mk] += amount_usd
                expenses_by_category[cat_name][mk] += amount_usd
                total_expenses_usd += amount_usd
                # Next month
                if m.month == 12:
                    m = m.replace(year=m.year + 1, month=1)
                else:
                    m = m.replace(month=m.month + 1)
        else:
            mk = _month_key(exp.period)
            expenses_by_month[mk] += amount_usd
            expenses_by_category[cat_name][mk] += amount_usd
            total_expenses_usd += amount_usd

    # --- Build unified month list ---
    all_months = sorted(set(list(revenue_by_month.keys()) + list(expenses_by_month.keys())))
    if not all_months:
        all_months = [_month_key(date.today())]

    # --- P&L data ---
    pnl_revenue = [round(revenue_by_month.get(m, 0), 2) for m in all_months]
    pnl_expenses = [round(expenses_by_month.get(m, 0), 2) for m in all_months]
    pnl_net = [round(r - e, 2) for r, e in zip(pnl_revenue, pnl_expenses)]

    # --- Revenue by payment system ---
    systems = sorted(revenue_by_system.keys())
    system_datasets = []
    colors_system = {"stripe": "#635BFF", "bepaid": "#28a745"}
    for sys_name in systems:
        system_datasets.append({
            "label": sys_name.capitalize(),
            "data": [round(revenue_by_system[sys_name].get(m, 0), 2) for m in all_months],
            "backgroundColor": colors_system.get(sys_name, "#6c757d"),
        })

    # --- Expenses by category ---
    categories = sorted(expenses_by_category.keys())
    cat_colors = [
        "#dc3545", "#fd7e14", "#ffc107", "#198754",
        "#0dcaf0", "#0d6efd", "#6610f2", "#d63384",
    ]
    category_datasets = []
    for i, cat in enumerate(categories):
        category_datasets.append({
            "label": cat,
            "data": [round(expenses_by_category[cat].get(m, 0), 2) for m in all_months],
            "backgroundColor": cat_colors[i % len(cat_colors)],
        })

    # --- Key metrics ---
    from django.contrib.auth import get_user_model

    User = get_user_model()
    total_users = User.objects.using(db).count()

    # Active subscriptions & MRR
    # MRR = Sum of (annual_subscription_amount / 12) for each active subscriber,
    # converted to USD. For annual plans the full amount is normalized to monthly.
    try:
        from payments.models import RecurringSubscription
        active_subs_qs = RecurringSubscription.objects.using(db).filter(status="active")
        active_subs = active_subs_qs.count()

        # Calculate MRR per-currency then convert to USD
        mrr_by_currency = (
            active_subs_qs.values("currency")
            .annotate(total=Sum("amount"))
        )
        mrr_usd = 0.0
        for row in mrr_by_currency:
            annual_total = row["total"] or 0
            monthly = float(annual_total) / 12
            mrr_usd += _to_usd(Decimal(str(monthly)), row["currency"], rates)
    except Exception:
        active_subs = 0
        mrr_usd = 0

    # Unique paying users
    unique_payers = (
        PaymentRecord.objects.using(db).filter(status="success")
        .values("user_id")
        .distinct()
        .count()
    )

    # Conversion rate
    conversion_rate = round(unique_payers / total_users * 100, 2) if total_users else 0

    net_profit = total_revenue_usd - total_expenses_usd

    context = {
        **admin_site.each_context(request),
        "title": "P&L Dashboard",
        "months_json": json.dumps(all_months),
        "pnl_revenue_json": json.dumps(pnl_revenue),
        "pnl_expenses_json": json.dumps(pnl_expenses),
        "pnl_net_json": json.dumps(pnl_net),
        "system_datasets_json": json.dumps(system_datasets),
        "category_datasets_json": json.dumps(category_datasets),
        # Key metrics
        "total_revenue": round(total_revenue_usd, 2),
        "total_expenses": round(total_expenses_usd, 2),
        "net_profit": round(net_profit, 2),
        "mrr": round(mrr_usd, 2),
        "active_subs": active_subs,
        "unique_payers": unique_payers,
        "total_payments": total_payments,
        "total_users": total_users,
        "conversion_rate": conversion_rate,
        # Info
        "data_source": db,
        "missing_rates": not rates or len(rates) <= 1,
    }

    return TemplateResponse(request, "admin/analytics/pnl_dashboard.html", context)


@staff_member_required
def dashboard_list(request):
    dashboards = MetabaseDashboard.objects.filter(is_active=True)
    return TemplateResponse(
        request,
        "admin/analytics/dashboard_list.html",
        {**admin_site.each_context(request), "dashboards": dashboards, "title": "Дашборды"},
    )


@staff_member_required
def dashboard_embed(request, dashboard_id):
    try:
        dashboard = MetabaseDashboard.objects.get(
            metabase_id=dashboard_id, is_active=True
        )
    except MetabaseDashboard.DoesNotExist:
        raise Http404

    metabase_url = settings.METABASE_SITE_URL
    metabase_key = settings.METABASE_SECRET_KEY

    payload = {
        "resource": {"dashboard": dashboard.metabase_id},
        "params": {},
        "exp": round(time.time()) + 600,
    }
    token = jwt.encode(payload, metabase_key, algorithm="HS256")
    iframe_url = f"{metabase_url}/embed/dashboard/{token}#bordered=true&titled=true"

    return TemplateResponse(
        request,
        "admin/analytics/dashboard_embed.html",
        {
            **admin_site.each_context(request),
            "dashboard": dashboard,
            "iframe_url": iframe_url,
            "title": dashboard.name,
        },
    )
