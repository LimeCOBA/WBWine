"""WB Wine units: centimetres, litres, days, Berry and RUB."""
from dataclasses import dataclass
from decimal import Decimal as D, ROUND_CEILING, ROUND_HALF_UP

CENT = D(".01")


def occupied_litres(length, width, height, k, stacking):
    if min(length, width, height) <= 0 or not (0 < k <= 1 and 0 <= stacking <= 1):
        raise ValueError("Проверьте размеры и коэффициенты упаковки")
    box = length * width * height / D(1000)
    return (box * (1 - stacking * (1 - k))).quantize(D(".001"), rounding=ROUND_CEILING)


@dataclass(frozen=True)
class Rates:
    a: D
    b: D
    rub: D
    handling: D
    risk: D

    def __post_init__(self):
        if min(self.a,self.b,self.handling,self.risk) < 0 or self.rub <= 0:
            raise ValueError("Недопустимый тариф")

    def charge(self, logistic, days, litres, transfers):
        if min(logistic,days,litres,transfers) < 0:
            raise ValueError("Отрицательная величина")
        transport = self.a * logistic
        storage = self.b * days * litres
        berries = storage
        parts = {"transport": transport, "storage": storage*self.rub,
                 "handling": self.handling*transfers, "risk": self.risk*transfers}
        parts = {key: v.quantize(CENT,rounding=ROUND_HALF_UP) for key,v in parts.items()}
        return dict(**parts, berries=berries, total=sum(parts.values()))