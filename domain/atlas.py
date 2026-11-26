"""Search simple paths on a timetable. No framework or persistence dependencies."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Leg:
    id: int
    start: int
    end: int
    departure: datetime
    arrival: datetime
    litres: Decimal
    kg: Decimal
    logistic: Decimal


def cheapest(legs, free, start, end, ready, deadline, litres, kg, holding_days, rates, via=None):
    if start == end or deadline <= ready or min(litres,kg) <= 0 or holding_days < 0:
        raise ValueError("РџСЂРѕРІРµСЂСЊС‚Рµ СѓР·Р»С‹, СЃСЂРѕРє Рё РїР°СЂР°РјРµС‚СЂС‹ РїРѕСЃС‹Р»РєРё")
    if free.get(start,0) < litres:
        return None
    outgoing = {}
    for leg in legs:
        if leg.arrival > leg.departure and leg.arrival <= deadline and leg.litres >= litres and leg.kg >= kg and free.get(leg.end,0) >= litres:
            outgoing.setdefault(leg.start,[]).append(leg)
    best = None
    pending = [(start,ready,(),{start},Decimal(0),Decimal(0))]
    while pending:
        node, time, path, visited, logistic, wait = pending.pop()
        if node == end and (via is None or visited & via):
            cost = rates.charge(logistic, holding_days + wait, litres, len(path))
            rank = (cost["total"],time,path)
            if best is None or rank < best[0]:
                best = (rank,path,cost)
            continue
        for leg in outgoing.get(node,()):
            if leg.end in visited or leg.departure < time:
                continue
            days = Decimal(str((leg.departure-time).total_seconds())) / 86400
            pending.append((leg.end,leg.arrival,path+(leg.id,),visited|{leg.end},logistic+leg.logistic,wait+days))
    return (best[1],best[2]) if best else None
