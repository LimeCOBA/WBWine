from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from ledger.registration import CABINETS


class RegistrationTests(TestCase):
    def test_all_cabinets(self):
        for role in CABINETS:
            with self.subTest(role=role), override_settings(SERVICE=role):
                client = Client(enforce_csrf_checks=True)
                page = client.get("/register/")
                self.assertEqual(page.status_code, 200)
                data = dict(username="new_"+role, password1="Frost!79-maple", password2="Frost!79-maple", is_superuser=True, role="wild")
                self.assertEqual(client.post("/register/", data).status_code, 403)
                data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
                self.assertRedirects(client.post("/register/", data), "/")
                user = User.objects.get(username=data["username"])
                self.assertEqual(list(user.groups.values_list("name",flat=True)), [role])
                self.assertFalse(user.is_staff or user.is_superuser)
                self.assertEqual(client.get("/api/").status_code, 200)
                data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
                self.assertEqual(client.post("/register/", data).status_code, 200)
                self.assertEqual(User.objects.filter(username=data["username"]).count(), 1)
<<<<<<< HEAD


    def test_registration_links_preserve_host_and_scheme(self):
        for role, (port, _) in CABINETS.items():
            with self.subTest(role=role), override_settings(SERVICE=role):
                response = self.client.get(
                    "/register/", secure=True, HTTP_HOST=f"localhost:{port}"
                )
                for other_role, (other_port, _) in CABINETS.items():
                    link = f'https://localhost:{other_port}/register/'
                    if other_role == role:
                        self.assertNotContains(response, link)
                    else:
                        self.assertContains(response, link)
=======
>>>>>>> efe3e3ea7df955d5c5b458e21e424acd9812bff4
