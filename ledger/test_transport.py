from unittest import TestCase
from django.contrib.auth.models import Group, User
from django.test import TestCase as DatabaseTest, override_settings
from domain.roads import road
from domain.transport import allocate


class TransportTests(TestCase):
    def test_roads_and_exact_optimum(self):
        self.assertEqual(road("Москва","Нижний Новгород"),(420,("Москва","Владимир","Нижний Новгород")))
        stock={"Москва":2,"Чебоксары":3}
        demand={"Владимир":3,"Казань":2}
        exact=allocate(stock,demand,"simplex")
        # Two Moscow units to Vladimir, one Cheboksary unit to Vladimir and two to Kazan.
        self.assertEqual(exact["work"],2*190+475+2*155)
        learned=allocate(stock,demand,"ai")
        self.assertGreaterEqual(learned["work"],exact["work"])
        for plan in (exact,learned):
            outbound,inbound={},{}
            for path,count,_ in plan["rows"]:
                cities=path.split(" → ")
                outbound[cities[0]]=outbound.get(cities[0],0)+count
                inbound[cities[-1]]=inbound.get(cities[-1],0)+count
            self.assertEqual((outbound,inbound),(stock,demand))

    def test_invalid_and_local(self):
        self.assertRaises(ValueError,allocate,{"Москва":1},{"Казань":2},"simplex")
        self.assertRaises(ValueError,allocate,{"Вымышленная нода":1},{"Казань":1},"ai")
        self.assertEqual(allocate({"Москва":1},{"Москва":1},"simplex")["work"],0)


@override_settings(SERVICE="atlas")
class AtlasEndpoint(DatabaseTest):
    def test_modes(self):
        user=User.objects.create_user("planner")
        user.groups.add(Group.objects.get(name="atlas"))
        self.client.force_login(user)
        for mode in ("simplex","ai"):
            res=self.client.post("/api/",{"action":"allocate","data":{"stockМосква":"2","needsКазань":"2","mode":mode}},content_type="application/json")
            self.assertEqual(res.status_code,200,res.content)
            self.assertEqual(res.json()["result"]["work"],1640)