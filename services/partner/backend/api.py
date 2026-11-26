from django.core.exceptions import ValidationError
from ledger.models import Node
from ledger.web import save_form, form_spec, validated, table, require_action
from services.atlas.backend.api import available

FIELDS = ["city","name","hub","capacity","peak"]


def screen(user):
    nodes = Node.objects.filter(owner=user)
    free = available()
    rows = [(n.name,n.capacity,n.peak,free.get(n.pk,"Закрыта")) for n in nodes]
    peak = form_spec(Node,["peak"],"peak","Изменить внешнюю загрузку")
    peak["fields"].insert(0,dict(type="select",name="node",label="Нода",required=True,options=[(n.pk,n.name) for n in nodes]))
    return dict(forms=[form_spec(Node,FIELDS,"node","Открыть ноду"),peak],
                tables=[table("Мои ноды",["Адрес","Ёмкость, л","Внешняя загрузка, л","Свободно, л"],rows)])


def mutate(user,action,data):
    require_action(action,"node","peak")
    if action == "node":
        save_form(Node,FIELDS,data,owner=user)
        return
    node = Node.objects.get(pk=data.get("node"),owner=user,active=True)
    peak = validated(Node,["peak"],data).peak
    if peak > available()[node.pk]+node.peak:
        raise ValidationError("Этот объём уже зарезервирован отправлениями")
    node.peak = peak
    node.save(update_fields=["peak"])