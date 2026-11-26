"""Versioned offline teaching network. Coordinates in degrees, road weights in km."""
from heapq import heappop, heappush

CITIES = {"Москва": (55.76,37.62), "Владимир": (56.13,40.41),
          "Нижний Новгород": (56.33,44.00), "Чебоксары": (56.14,47.25),
          "Казань": (55.80,49.11), "Йошкар-Ола": (56.63,47.90)}
ROADS = (("Москва","Владимир",190),("Владимир","Нижний Новгород",230),
         ("Нижний Новгород","Чебоксары",245),("Чебоксары","Казань",155),
         ("Чебоксары","Йошкар-Ола",95),("Йошкар-Ола","Казань",145))


def road(start,end):
    if start not in CITIES or end not in CITIES:
        raise ValueError("Город отсутствует в автономном атласе")
    queue = [(0,start,(start,))]
    seen = set()
    while queue:
        km,city,path = heappop(queue)
        if city == end:
            return km,path
        if city in seen:
            continue
        seen.add(city)
        for a,b,length in ROADS:
            if city in (a,b):
                other = b if city==a else a
                if other not in seen:
                    heappush(queue,(km+length,other,path+(other,)))
    raise ValueError("Нет дорожного пути")