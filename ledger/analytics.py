from datetime import date
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ledger.models import Node, NodeFinance, Parcel, ParcelFinance


class FinanceForm(forms.Form):
    item = forms.ModelChoiceField(queryset=Node.objects.none(), label="Объект")
    revenue = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)
    expenses = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)

    def __init__(self, items, seller, *args):
        super().__init__(*args)
        self.fields["item"].queryset = items
        self.fields["item"].label = "Заказ" if seller else "Пункт выдачи"
        if seller:
            self.fields["item"].label_from_instance = lambda parcel: parcel.reference
        self.fields["revenue"].label = "Выручка, ₽" if seller else "Начисления ПВЗ, ₽"
        self.fields["expenses"].label = "Расходы без логистики, ₽" if seller else "Расходы ПВЗ, ₽"


@login_required(login_url="/login/")
@require_http_methods(["GET", "POST"])
def analytics(request):
    from common import authorized

    if not authorized(request.user):
        return HttpResponseForbidden("Нет доступа к кабинету")

    current_month = timezone.localdate().replace(day=1)
    try:
        month = date.fromisoformat(request.GET.get("month", current_month.strftime("%Y-%m")) + "-01")
    except ValueError:
        month = current_month
    seller = settings.SERVICE == "seller"
    if seller:
        items = Parcel.objects.filter(
            seller=request.user, created__year=month.year, created__month=month.month,
        ).select_related("finance").order_by("-created")
    else:
        items = Node.objects.filter(owner=request.user).order_by("name")
    form = FinanceForm(items, seller, request.POST if request.method == "POST" else None)
    if request.method == "POST":
        with transaction.atomic():
            if form.is_valid():
                item = form.cleaned_data["item"]
                amounts = {key: form.cleaned_data[key] for key in ("revenue", "expenses")}
                if seller:
                    ParcelFinance.objects.update_or_create(parcel=item, defaults=amounts)
                else:
                    NodeFinance.objects.update_or_create(node=item, month=month, defaults=amounts)
                return redirect(f"{reverse('analytics')}?month={month:%Y-%m}")

    node_records = {} if seller else {
        record.node_id: record for record in NodeFinance.objects.filter(node__in=items, month=month)
    }
    rows = []
    for item in items:
        record = getattr(item, "finance", None) if seller else node_records.get(item.pk)
        cost = item.calculation.get("cost", {}) if seller else {}
        logistics = Decimal(str(cost["total"])) if "total" in cost else None
        complete = record is not None and (not seller or logistics is not None)
        total = record.expenses + (logistics if seller else Decimal(0)) if complete else None
        rows.append({
            "label": item.reference if seller else item.name,
            "record": record, "logistics": logistics, "total": total,
            "profit": record.revenue - total if complete else None,
        })
    covered = [row for row in rows if row["profit"] is not None]
    totals = {
        "revenue": sum(row["record"].revenue for row in covered),
        "expenses": sum(row["total"] for row in covered),
        "profit": sum(row["profit"] for row in covered),
    }
    return render(request, "analytics.html", {
        "seller": seller, "month": f"{month:%Y-%m}", "form": form,
        "rows": rows, "covered": covered, "totals": totals, "editing": request.method == "POST",
    })
