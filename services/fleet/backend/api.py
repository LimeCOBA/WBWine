from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from ledger.models import Vehicle, Trip
from ledger.web import save_form, form_spec, validated, table, require_action

VEHICLE = ["plate","litres","kg"]
TRIP = ["vehicle","driver","origin","destination","departure","arrival","dedicated","logistic"]


def choices(user):
    return {"vehicle":Vehicle.objects.filter(fleet=user),"driver":get_user_model().objects.filter(assigned_vehicles__fleet=user,is_active=True).distinct()}


def screen(user):
    trips = Trip.objects.filter(vehicle__fleet=user).order_by("departure").select_related("vehicle","origin","destination","driver")
    rows = [(t.vehicle.plate,str(t.driver),str(t.origin),str(t.destination),t.departure,t.arrival) for t in trips]
    return dict(forms=[form_spec(Vehicle,VEHICLE,"vehicle","Добавить машину"),form_spec(Trip,TRIP,"trip","Запланировать рейс",choices(user))],
                tables=[table("Расписание",["Машина","Водитель","Из","В","Отправление","Прибытие"],rows)])


def mutate(user,action,data):
    require_action(action,"vehicle","trip")
    if action=="vehicle":
        save_form(Vehicle,VEHICLE,data,fleet=user)
        return
    trip = validated(Trip,TRIP,data,choices(user))
    if not trip.vehicle.drivers.filter(pk=trip.driver_id).exists() or trip.departure<=timezone.now():
        raise ValidationError("Проверьте назначение водителя и время отправления")
    trip.full_clean()
    trip.save()