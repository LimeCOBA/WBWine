from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from unittest import TestCase
from domain.wild import Rates, occupied_litres
from domain.atlas import Leg, cheapest


class WildTests(TestCase):
    def test_volume_and_limits(self):
        dims = (D(10),D(20),D(30))
        self.assertEqual(occupied_litres(*dims,D(".7"),D(".5")),D("5.1"))
        self.assertEqual(occupied_litres(*dims,D(".7"),0),6)
        self.assertEqual(occupied_litres(*dims,D(".7"),1),D("4.2"))
        self.assertRaises(ValueError,occupied_litres,*dims,2,1)

    def test_berry_and_money(self):
        rates=Rates(D(2),D(".5"),D(3),D(7),D(4))
        cost=rates.charge(D(12),D(2),D(5),2)
        self.assertEqual(cost,dict(berries=D(5),transport=D(24),storage=D(15),handling=D(14),risk=D(8),total=D(61)))


class AtlasTests(TestCase):
    def test_schedule_capacity_weight_deadline_and_hub(self):
        now=datetime.now(timezone.utc)
        def leg(pk,start,end,h1,h2,fee):
            return Leg(pk,start,end,now+timedelta(hours=h1),now+timedelta(hours=h2),10,3,D(fee))
        network=[leg(1,1,2,1,3,2),leg(2,2,3,4,5,2),leg(3,1,3,0,2,9),leg(4,2,3,2,3,0)]
        def route(free=10,kg=3,deadline=6,via=None):
            return cheapest(network,{1:10,2:free,3:10},1,3,now,now+timedelta(hours=deadline),10,kg,0,Rates(D(1),D(0),D(1),D(0),D(0)),via)
        self.assertEqual(route()[0],(1,2))
        self.assertEqual(route(free=9)[0],(3,))
        self.assertEqual(route(deadline=3)[0],(3,))
        self.assertIsNone(route(kg=4))
        self.assertIsNone(route(free=9,via={2}))