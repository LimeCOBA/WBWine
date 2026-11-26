import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import Group,User
from django.test import Client,TestCase,override_settings
from django.utils import timezone
from ledger.models import Node,Packaging,Parcel,Reservation,Transfer,Trip,Vehicle,Tariff


class Workflow(TestCase):
    def setUp(self):
        self.now=timezone.now().replace(microsecond=0)
        self.user=User.objects.create_user("operator")
        self.user.groups.set(Group.objects.all())
        self.client.force_login(self.user)
        self.a,self.b=[Node.objects.create(name=n,owner=self.user,capacity=10,peak=0) for n in ("A","B")]
        self.a.workers.add(self.user)
        self.b.workers.add(self.user)
        self.pack=Packaging.objects.create(name="box",k=1,stacking=0)
        car=Vehicle.objects.create(fleet=self.user,plate="ABC",litres=10,kg=10)
        self.trip=Trip.objects.create(origin=self.a,destination=self.b,vehicle=car,driver=self.user,departure=self.now+timedelta(hours=1),arrival=self.now+timedelta(hours=2),logistic=3)
        Tariff.objects.create(start=self.now-timedelta(days=1),a=1,b=1,rub=1,handling=0,risk=0)
        self.data=dict(origin=self.a.pk,destination=self.b.pk,packaging=self.pack.pk,length=20,width=20,height=20,kg=2,deadline=(self.now+timedelta(hours=5)).isoformat(),days=1,reference="one",product="books")

    def post(self,role,action,**data):
        with override_settings(SERVICE=role):
            return self.client.post("/api/",json.dumps(dict(action=action,data=data)),content_type="application/json")

    def test_booking_and_delivery(self):
        quote=self.post("seller","quote",**self.data)
        self.assertEqual(quote.status_code,200,quote.content)
        self.assertFalse(Parcel.objects.exists())
        res=self.post("seller","book",**self.data)
        self.assertEqual(res.status_code,200,res.content)
        parcel=Parcel.objects.get()
        transfer=Transfer.objects.get()
        self.assertEqual(parcel.litres,8)
        self.assertEqual(Reservation.objects.filter(released=None).count(),2)
        self.assertEqual(self.post("seller","book",**{**self.data,"reference":"other"}).status_code,400)
        self.assertEqual(self.post("partner","peak",node=self.a.pk,peak=3).status_code,400)
        self.assertEqual(self.post("node","issue",id=parcel.pk).status_code,400)
        self.assertEqual(self.post("node","accept",id=parcel.pk).status_code,200)
        with patch("services.drive.backend.api.timezone.now",return_value=self.trip.departure):
            self.assertEqual(self.post("drive","pickup",id=transfer.pk).status_code,200)
            self.assertEqual(self.post("drive","pickup",id=transfer.pk).status_code,400)
        self.assertEqual(Reservation.objects.filter(released=None).count(),1)
        with patch("services.drive.backend.api.timezone.now",return_value=self.trip.arrival):
            self.assertEqual(self.post("drive","deliver",id=transfer.pk).status_code,200)
        self.assertEqual(self.post("node","issue",id=parcel.pk).status_code,200)
        self.assertFalse(Reservation.objects.filter(released=None).exists())

    def test_access_and_csrf(self):
        other=User.objects.create_user("other")
        self.client.force_login(other)
        self.assertEqual(self.post("partner","peak",node=self.a.pk,peak=5).status_code,403)
        other.groups.add(Group.objects.get(name="partner"))
        self.assertEqual(self.post("partner","peak",node=self.a.pk,peak=5).status_code,404)
        csrf=Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post("/api/",{},content_type="application/json").status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get("/api/").status_code,403)

    def test_no_rate_no_partial_records(self):
        Tariff.objects.all().delete()
        self.assertEqual(self.post("seller","book",**self.data).status_code,400)
        self.assertFalse(Reservation.objects.exists())
        self.assertFalse(Parcel.objects.exists())
    def test_enter_master_data_and_vehicle_assignment(self):
        response = self.post("partner","node",name="New",city="Москва",capacity=80,peak=5,hub=False)
        self.assertEqual(response.status_code,200,response.content)
        new = Node.objects.get(name="New")
        self.assertEqual(new.owner,self.user)
        self.assertEqual(self.post("fleet","vehicle",plate="SECOND",litres=50,kg=20).status_code,200)
        car = Vehicle.objects.get(plate="SECOND")
        data = dict(vehicle=car.pk,driver=self.user.pk,origin=new.pk,destination=self.b.pk,
                    departure=(self.now+timedelta(hours=3)).isoformat(),arrival=(self.now+timedelta(hours=4)).isoformat(),
                    dedicated=True,logistic=7)
        self.assertEqual(self.post("fleet","trip",**data).status_code,400)
        car.drivers.add(self.user)
        res=self.post("fleet","trip",**data)
        self.assertEqual(res.status_code,200,res.content)
        self.assertEqual(self.post("fleet","trip",**data).status_code,400)
        res=self.post("wild","tariff",start=self.now.isoformat(),a=2,b=2,rub=2,handling=1,risk=1)
        self.assertEqual(res.status_code,200,res.content)
        for name in ("seller","partner","atlas","wild","fleet","node","drive"):
            with override_settings(SERVICE=name):
                self.assertEqual(self.client.get("/api/").status_code,200)

    def test_effective_tariff_and_duplicate_reference(self):
        Tariff.objects.create(start=self.now+timedelta(days=1),a=100,b=100,rub=100,handling=100,risk=100)
        data={**self.data,"length":1}
        self.assertEqual(self.post("seller","book",**data).status_code,200)
        self.assertEqual(self.post("seller","book",**data).status_code,400)
        self.assertEqual(Transfer.objects.count(),1)
        saved=Parcel.objects.get().calculation
        self.assertEqual(saved["cost"]["transport"],"3.00")
        self.assertEqual(saved["tariff"],Tariff.objects.earliest("start").pk)
