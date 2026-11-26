from django.core.exceptions import ValidationError
from django.utils import timezone
from ledger.models import Transfer, Reservation
from ledger.web import table, require_action


def screen(user):
    rows,buttons = [], []
    for t in Transfer.objects.filter(trip__driver=user).select_related("parcel","trip__origin","trip__destination").order_by("trip__departure"):
        rows.append((t.parcel.reference,str(t.trip.origin),str(t.trip.destination),t.trip.departure,"Доставлено" if t.delivered else "В пути" if t.picked else "Ожидает"))
        if not t.delivered:
            buttons.append(dict(action="deliver" if t.picked else "pickup",id=t.pk,label=("Передать" if t.picked else "Забрать")+" · "+t.parcel.reference+" · "+str(t.trip.origin)))
    return dict(forms=[],buttons=buttons,tables=[table("Мои перевозки",["Заказ","Откуда","Куда","По расписанию","Состояние"],rows)])


def mutate(user,action,data):
    require_action(action,"pickup","deliver")
    t = Transfer.objects.select_related("trip").get(pk=data.get("id"),trip__driver=user)
    now = timezone.now()
    if action=="pickup":
        if not t.parcel.accepted or t.picked or t.trip.departure>now or Transfer.objects.filter(parcel=t.parcel,sequence__lt=t.sequence,delivered=None).exists():
            raise ValidationError("Сначала нужны приёмка, начало рейса и доставка предыдущего плеча")
        t.picked = now
        Reservation.objects.filter(parcel=t.parcel,node=t.trip.origin,released=None).update(released=now)
    else:
        if not t.picked or t.delivered or now < t.picked:
            raise ValidationError("Проверьте статус перевозки")
        t.delivered = now
    t.save()