from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F

USER = settings.AUTH_USER_MODEL


def number(label, minimum="0.001", maximum=None):
    validators = [MinValueValidator(Decimal(minimum))]
    if maximum:
        validators.append(MaxValueValidator(Decimal(maximum)))
    return models.DecimalField(label,max_digits=14,decimal_places=3,validators=validators)


from domain.roads import CITIES

class Node(models.Model):
    city = models.CharField("Город",max_length=50,choices=[(c,c) for c in CITIES],null=True)
    name = models.CharField("Населённый пункт и адрес",max_length=180,unique=True)
    hub = models.BooleanField("Распределительный центр",default=False)
    owner = models.ForeignKey(USER,on_delete=models.PROTECT,related_name="owned_nodes")
    workers = models.ManyToManyField(USER,blank=True,related_name="work_nodes")
    capacity = number("Ёмкость, л")
    peak = number("Занято вне системы, л","0")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(peak__gte=0,capacity__gte=F("peak")),name="node_capacity")]


class Packaging(models.Model):
    name = models.CharField("Упаковка",max_length=80,unique=True)
    k = number("Коэффициент заполнения k","0.001","1")
    stacking = number("Укладываемость l","0","1")

    def __str__(self):
        return self.name


class Tariff(models.Model):
    start = models.DateTimeField("Действует с",unique=True)
    a = number("a, множитель цены перевозки","0")
    b = number("b, Berry за литр в сутки","0")
    rub = number("Рублей за Berry")
    handling = number("Обработка на плече, ₽","0")
    risk = number("Резерв риска на плече, ₽","0")

    def __str__(self):
        return str(self.start)


class Vehicle(models.Model):
    fleet = models.ForeignKey(USER,on_delete=models.PROTECT,related_name="vehicles")
    drivers = models.ManyToManyField(USER,blank=True,related_name="assigned_vehicles")
    plate = models.CharField("Госномер",max_length=16,unique=True)
    litres = number("Объём кузова, л")
    kg = number("Грузоподъёмность, кг")

    def __str__(self):
        return self.plate


class Trip(models.Model):
    vehicle = models.ForeignKey(Vehicle,verbose_name="Машина",on_delete=models.PROTECT)
    driver = models.ForeignKey(USER,verbose_name="Водитель",on_delete=models.PROTECT)
    origin = models.ForeignKey(Node,verbose_name="Откуда",on_delete=models.PROTECT,related_name="+")
    destination = models.ForeignKey(Node,verbose_name="Куда",on_delete=models.PROTECT,related_name="+")
    departure = models.DateTimeField("Отправление")
    arrival = models.DateTimeField("Прибытие")
    dedicated = models.BooleanField("Отдельный рейс для одного заказа",default=False)
    logistic = number("Цена отдельного рейса или доплата за попутный груз, ₽","0")

    def clean(self):
        if self.origin_id and self.origin_id == self.destination_id:
            raise ValidationError("Начальная и конечная ноды совпадают")
        if self.departure and self.arrival:
            if self.departure >= self.arrival:
                raise ValidationError("Прибытие должно быть позже отправления")
            overlap = Trip.objects.exclude(pk=self.pk).filter(departure__lt=self.arrival,arrival__gt=self.departure)
            if overlap.filter(Q(vehicle_id=self.vehicle_id)|Q(driver_id=self.driver_id)).exists():
                raise ValidationError("Водитель или машина уже заняты в это время")


class Parcel(models.Model):
    seller = models.ForeignKey(USER,on_delete=models.PROTECT)
    reference = models.CharField("Номер заказа",max_length=64)
    product = models.CharField("Содержимое",max_length=140)
    origin = models.ForeignKey(Node,verbose_name="Пункт приёмки",on_delete=models.PROTECT,related_name="+")
    destination = models.ForeignKey(Node,verbose_name="Пункт выдачи",on_delete=models.PROTECT,related_name="+")
    packaging = models.ForeignKey(Packaging,verbose_name="Упаковка",on_delete=models.PROTECT)
    length = number("Длина, см")
    width = number("Ширина, см")
    height = number("Высота, см")
    kg = number("Масса, кг")
    deadline = models.DateTimeField("Доставить до")
    days = number("Хранение после доставки, сутки","0")
    litres = number("Расчётный объём, л")
    calculation = models.JSONField()
    accepted = models.DateTimeField(null=True,blank=True)
    issued = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["seller","reference"],name="seller_reference")]


class Transfer(models.Model):
    parcel = models.ForeignKey(Parcel,on_delete=models.PROTECT,related_name="transfers")
    trip = models.ForeignKey(Trip,on_delete=models.PROTECT)
    sequence = models.PositiveIntegerField()
    picked = models.DateTimeField(null=True,blank=True)
    delivered = models.DateTimeField(null=True,blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["parcel","sequence"],name="parcel_sequence")]


class Reservation(models.Model):
    parcel = models.ForeignKey(Parcel,on_delete=models.PROTECT)
    node = models.ForeignKey(Node,on_delete=models.PROTECT)
    released = models.DateTimeField(null=True,blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["parcel","node"],name="parcel_node")]
