from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


CABINETS = {
    "seller": (8100, "Продавец"),
    "node": (8101, "Сотрудник ноды"),
    "partner": (8102, "Владелец ноды"),
    "drive": (8103, "Водитель"),
    "fleet": (8104, "Перевозчик"),
    "atlas": (8105, "Планировщик Atlas"),
    "wild": (8106, "Специалист по тарифам Wild"),
}
VERIFICATION_REQUIRED = {"partner", "fleet", "drive", "node", "atlas", "wild"}


def verify_application(application):
    """Локальная заглушка: возвращает копию заявления без внешней проверки."""
    return application.copy()


def cabinet_context():
    role = settings.SERVICE
    return {
        "role_name": CABINETS[role][1],
        "simulated": role in VERIFICATION_REQUIRED,
        "other_roles": [(name, f"http://127.0.0.1:{port}/register/")
                        for key, (port, name) in CABINETS.items() if key != role],
    }


@require_http_methods(["GET", "POST"])
def register(request):
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        role = settings.SERVICE
        application = {"username": form.cleaned_data["username"], "role": role}
        if role in VERIFICATION_REQUIRED and verify_application(application) != application:
            form.add_error(None, "Заявление не подтверждено")
        else:
            try:
                with transaction.atomic():
                    user = form.save()
                    user.groups.add(Group.objects.get(name=role))
            except IntegrityError:
                form.add_error("username", "Это имя уже занято")
            else:
                login(request, user)
                return redirect("/")
    return render(request, "register.html", {"form": form, **cabinet_context()})
