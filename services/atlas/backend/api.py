from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils import timezone
from domain.roads import CITIES, ROADS, road
from domain.atlas import Leg, cheapest
from domain.wild import occupied_litres
from ledger.models import Node, Reservation, Trip, Transfer
from services.wild.backend.api import current


def available():
    occupied = dict(Reservation.objects.filter(released=None).values_list("node_id").annotate(total=Sum("parcel__litres")))
    return {n.pk:n.capacity-n.peak-occupied.get(n.pk,0) for n in Node.objects.filter(active=True)}


def calculate(parcel):
    now = timezone.now()
    tariff,rates = current(now)
    pack = parcel.packaging
    litres = occupied_litres(parcel.length,parcel.width,parcel.height,pack.k,pack.stacking)
    used = {r["trip_id"]:r for r in Transfer.objects.values("trip_id").annotate(volume=Sum("parcel__litres"),mass=Sum("parcel__kg"))}
    trips = Trip.objects.select_related("vehicle","origin","destination").filter(departure__gte=now,arrival__lte=parcel.deadline)
    legs, records = [], {}
    for trip in trips:
        load = used.get(trip.pk,{})
        if trip.dedicated and load:
            continue
        records[trip.pk] = trip
        legs.append(Leg(trip.pk,trip.origin_id,trip.destination_id,trip.departure,trip.arrival,
                        trip.vehicle.litres-load.get("volume",0),trip.vehicle.kg-load.get("mass",0),trip.logistic))
    args = (available(),parcel.origin_id,parcel.destination_id,now,parcel.deadline,litres,parcel.kg,parcel.days,rates)
    result = cheapest(legs,*args)
    if result is None:
        raise ValidationError("Нет доступной цепочки рейсов. Проверьте расписание, срок, массу и свободный объём машины и узлов.")
    ids,cost = result
    hubs = set(Node.objects.filter(hub=True).values_list("pk",flat=True))
    # Baseline must include a hub, even when the optimal path also visits one.
    baseline = cheapest(legs,*args,via=hubs)
    trips = [records[i] for i in ids]
    snapshot = dict(tariff=tariff.pk, rates={name:str(getattr(rates,name)) for name in ("a","b","rub","handling","risk")},k=str(pack.k),stacking=str(pack.stacking),litres=str(litres),
                    route=[str(parcel.origin)]+[str(t.destination) for t in trips],
                    roads=[road(t.origin.city,t.destination.city) if t.origin.city and t.destination.city else None for t in trips],
                    cost={k:str(v) for k,v in cost.items()},hub_total=str(baseline[1]["total"]) if baseline else None)
    return trips,litres,snapshot


def screen(user):
    from services.seller.backend.api import planner
    fields = [dict(name="mode",label="Метод",type="select",required=True,options=[("simplex","Двойственный симплекс"),("ai","Обученное дерево решений")])]
    for city in CITIES:
        for prefix,label in (("stock","Запас"),("needs","Потребность")):
            fields.append(dict(name=prefix+city,label=f"{city} · {label}, ед.",type="number",required=False))
    return dict(cities=CITIES,roads=ROADS,forms=[dict(action="allocate",label="Распределить партию",fields=fields),planner("quote","Рассчитать рейсы посылки")],tables=[])


def mutate(user,action,data):
    from services.seller.backend.api import process
    from ledger.web import require_action
    if action=="allocate":
        from domain.transport import allocate
        def quantities(prefix):
            values = {city:int(data[prefix+city]) for city in CITIES if data.get(prefix+city) not in ("",None)}
            return {city:v for city,v in values.items() if v}
        return allocate(quantities("stock"),quantities("needs"),data.get("mode"))
    require_action(action,"quote")
    return process(user,action,data)