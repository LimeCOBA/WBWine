from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelform_factory


def require_action(action,*allowed):
    if action not in allowed:
        raise ValidationError("Неизвестная операция")


def table(title,columns,rows):
    return dict(title=title,columns=columns,rows=list(rows))


def make_form(model,fields,data=None,choices=None):
    form = modelform_factory(model,fields=fields)(data)
    for key,query in (choices or {}).items():
        form.fields[key].queryset = query
    return form


def form_spec(model,fields,action,label,choices=None):
    items = []
    for name,f in make_form(model,fields,choices=choices).fields.items():
        item = dict(name=name,label=f.label,required=f.required,type="text")
        if isinstance(f,forms.ModelChoiceField):
            item.update(type="select",options=[(obj.pk,str(obj)) for obj in f.queryset])
        elif isinstance(f,forms.ChoiceField):
            item.update(type="select",options=[(v,t) for v,t in f.choices if v])
        elif isinstance(f,forms.DateTimeField):
            item["type"]="datetime-local"
        elif isinstance(f,forms.BooleanField):
            item["type"]="checkbox"
        elif isinstance(f,forms.DecimalField):
            item["type"]="number"
        items.append(item)
    return dict(action=action,label=label,fields=items)


def validated(model,fields,data,choices=None):
    form = make_form(model,fields,data,choices)
    if not form.is_valid():
        raise ValidationError([str(msg) for errors in form.errors.values() for msg in errors])
    return form.save(commit=False)


def save_form(model,fields,data,choices=None,**attributes):
    obj = validated(model,fields,data,choices)
    for key,value in attributes.items():
        setattr(obj,key,value)
    obj.full_clean()
    obj.save()
    return obj