from ledger.models import Parcel, Reservation, Transfer, Node
from ledger.web import form_spec, validated, table, require_action
from services.atlas.backend.api import calculate

FIELDS = ["reference","product","origin","destination","packaging","length","width","height","kg","deadline","days"]


def planner(action,label):
    return form_spec(Parcel,FIELDS,action,label,choices={"origin":Node.objects.filter(active=True),"destination":Node.objects.filter(active=True)})


def process(user,action,data):
    require_action(action,"quote","book")
    parcel = validated(Parcel,FIELDS,data)
    parcel.seller = user
    trips,parcel.litres,parcel.calculation = calculate(parcel)
    if action == "book":
        parcel.full_clean()
        parcel.save()
        for index,trip in enumerate(trips):
            Reservation.objects.create(parcel=parcel,node=trip.origin)
            Transfer.objects.create(parcel=parcel,trip=trip,sequence=index)
        Reservation.objects.create(parcel=parcel,node=parcel.destination)
    return parcel.calculation


mutate = process


def screen(user):
    rows = [(p.reference,p.product," → ".join(p.calculation["route"]),p.calculation["cost"]["total"],"Выдан" if p.issued else "В работе") for p in Parcel.objects.filter(seller=user).order_by("-created")]
    return dict(forms=[planner("book","Оформить отправление")],tables=[table("Мои отправления",["Заказ","Содержимое","Путь","Стоимость, ₽","Статус"],rows)])