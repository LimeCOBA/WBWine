from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ledger.models import Node, Packaging, Parcel, Tariff, Trip, Vehicle
from services.seller.backend.api import process


PEOPLE = {
    "seller": "Артём",
    "node": "Андрей",
    "partner": "Мария",
    "drive": "Иван",
    "fleet": "Елена",
    "atlas": "Ольга",
    "wild": "Дмитрий",
}


class Command(BaseCommand):
    help = "Заполняет локальную базу согласованным тестовым сценарием WB Wine."

    @transaction.atomic
    def handle(self, *args, **options):
        users = get_user_model().objects
        usernames = {role: f"wb_demo_{role}" for role in PEOPLE}
        if Parcel.objects.filter(
            seller__username=usernames["seller"], reference="WB-DEMO-001"
        ).exists():
            self.stdout.write("Тестовый сценарий уже загружен.")
            return
        if users.filter(username__in=usernames.values()).exists():
            raise CommandError("Логины тестового сценария уже заняты.")

        accounts = {}
        for role, name in PEOPLE.items():
            user = users.create_user(
                username=usernames[role], first_name=name, password="WBWine-demo!2026"
            )
            user.groups.add(Group.objects.get(name=role))
            accounts[role] = user

        nodes = []
        for city, label, hub in (
            ("Москва", "Приёмка", False),
            ("Владимир", "Распределительный центр", True),
            ("Нижний Новгород", "Выдача", False),
        ):
            node = Node.objects.create(
                name=f"WB Demo · {city} · {label}", city=city, hub=hub,
                owner=accounts["partner"], capacity=Decimal("500"), peak=Decimal("40"),
            )
            node.workers.add(accounts["node"])
            nodes.append(node)

        packaging = Packaging.objects.create(
            name="WB Demo · коробка", k=Decimal("0.8"), stacking=Decimal("0.2")
        )
        now = timezone.now().replace(microsecond=0)
        if not Tariff.objects.filter(start__lte=now).exists():
            Tariff.objects.create(
                start=now, a=Decimal("1"), b=Decimal("0.1"), rub=Decimal("2"),
                handling=Decimal("15"), risk=Decimal("5"),
            )

        vehicle = Vehicle.objects.create(
            plate="WB-DEMO-01", fleet=accounts["fleet"],
            litres=Decimal("200"), kg=Decimal("100"),
        )
        vehicle.drivers.add(accounts["drive"])
        for origin, destination, departure, arrival in (
            (nodes[0], nodes[1], 24, 28),
            (nodes[1], nodes[2], 30, 35),
        ):
            trip = Trip(
                origin=origin, destination=destination, vehicle=vehicle, driver=accounts["drive"],
                departure=now + timedelta(hours=departure), arrival=now + timedelta(hours=arrival),
                logistic=Decimal("120"),
            )
            trip.full_clean()
            trip.save()

        process(accounts["seller"], "book", {
            "reference": "WB-DEMO-001", "product": "Набор бокалов",
            "origin": nodes[0].pk, "destination": nodes[-1].pk, "packaging": packaging.pk,
            "length": "30", "width": "20", "height": "20", "kg": "2.5", "days": "1",
            "deadline": (now + timedelta(hours=48)).isoformat(),
        })
        self.stdout.write(self.style.SUCCESS("Тестовый сценарий загружен."))