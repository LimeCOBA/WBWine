from django.core.exceptions import ValidationError
from domain.wild import Rates
from ledger.models import Tariff


def current(now):
    row = Tariff.objects.filter(start__lte=now).order_by("-start").first()
    if row is None:
        raise ValidationError("На дату расчёта нет тарифа Wild")
    return row, Rates(row.a,row.b,row.rub,row.handling,row.risk)


def screen(user):
    from ledger.web import form_spec, table
    return dict(forms=[form_spec(Tariff,["start","a","b","rub","handling","risk"],"tariff","Добавить тариф")],
                tables=[table("Тарифы",["Действует с","Множитель перевозки","Berry / (л·сут)","₽ / Berry","Обработка, ₽","Риск, ₽"],Tariff.objects.order_by("-start").values_list("start","a","b","rub","handling","risk"))])


def mutate(user,action,data):
    from ledger.web import save_form, require_action
    require_action(action,"tariff")
    save_form(Tariff,["start","a","b","rub","handling","risk"],data)