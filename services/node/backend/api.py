from django.core.exceptions import ValidationError
from django.utils import timezone
from ledger.models import Parcel, Reservation
from ledger.web import table, require_action


def screen(user):
    reservations = Reservation.objects.filter(node__workers=user,released=None).select_related("parcel","node")
    rows = [(r.node.name,r.parcel.reference,r.parcel.litres,r.parcel.calculation["cost"]["berries"]) for r in reservations]
    parcels = Parcel.objects.filter(destination__workers=user,issued=False).exclude(transfers__delivered=None)
    incoming = Parcel.objects.filter(origin__workers=user,accepted=None)
    accept = [dict(action="accept",id=p.pk,label="Принять · "+p.reference) for p in incoming]
    return dict(forms=[],buttons=accept+[dict(action="issue",id=p.pk,label="Выдать · "+p.reference) for p in parcels],
                tables=[table("Резервы моих нод",["Нода","Заказ","Зарезервировано, л","Хранение по заказу, Berry"],rows)])


def mutate(user,action,data):
    require_action(action,"accept","issue")
    if action=="accept":
        p = Parcel.objects.get(pk=data.get("id"),origin__workers=user,accepted=None)
        p.accepted = timezone.now()
        p.save(update_fields=["accepted"])
        return
    p = Parcel.objects.get(pk=data.get("id"),destination__workers=user,issued=False)
    if p.transfers.filter(delivered=None).exists():
        raise ValidationError("Посылка ещё в пути")
    p.issued=True
    p.save(update_fields=["issued"])
    Reservation.objects.filter(parcel=p,node=p.destination,released=None).update(released=timezone.now())