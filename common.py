import json
from ledger.analytics import analytics
from ledger.registration import register, cabinet_context
from importlib import import_module
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.staticfiles.views import serve
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse, JsonResponse, HttpResponse
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods


def authorized(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=settings.SERVICE).exists())


@login_required(login_url="/login/")
@ensure_csrf_cookie
def index(request):
    analytics_link = '<aside style="position:fixed;right:1rem;bottom:1rem;background:white;padding:.6rem;border-radius:.5rem"><a href="/analytics/">Аналитика стоимости и прибыли</a></aside>' if settings.SERVICE in {"seller", "partner"} else ''
    return HttpResponse('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WB Wine · '+settings.SERVICE+'</title><link rel="stylesheet" href="/app.css"><div id="root"></div>'+analytics_link+'<script src="/app.js"></script></html>')


@require_http_methods(["GET","POST"])
def api(request):
    if not authorized(request.user):
        return JsonResponse({"error":"Требуется вход и доступ к кабинету"},status=403)
    app = import_module(f"services.{settings.SERVICE}.backend.api")
    try:
        if request.method=="GET":
            return JsonResponse({**app.screen(request.user),"username":request.user.get_username()})
        if request.content_type!="application/json":
            return JsonResponse({"error":"Требуется JSON"},status=415)
        payload=json.loads(request.body)
        if not isinstance(payload,dict) or not isinstance(payload.get("data"),dict):
            raise ValidationError("Некорректный запрос")
        with transaction.atomic():
            result=app.mutate(request.user,payload.get("action"),payload["data"])
        return JsonResponse({"result":result})
    except (ValidationError,ValueError,TypeError,ArithmeticError) as exc:
        message=" · ".join(exc.messages) if isinstance(exc,ValidationError) else "Некорректные параметры"
        return JsonResponse({"error":message},status=400)
    except ObjectDoesNotExist:
        return JsonResponse({"error":"Объект недоступен"},status=404)
    except IntegrityError:
        return JsonResponse({"error":"Конфликт данных"},status=409)


def asset(request,name):
    return FileResponse(open(settings.ROOT/"services"/settings.SERVICE/"frontend/dist"/name,"rb"),content_type="text/css" if name.endswith("css") else "application/javascript")


class CabinetLoginView(LoginView):
    template_name = "login.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **cabinet_context(self.request)}


def auth_style(request):
    return FileResponse((settings.ROOT / "ui" / "style.css").open("rb"), content_type="text/css")


urlpatterns=[path("auth.css",auth_style),path("",index),path("api/",api),path("register/",register),path("login/",CabinetLoginView.as_view()),
             path("logout/",LogoutView.as_view()),path("app.js",asset,{"name":"app.js"}),path("app.css",asset,{"name":"app.css"})]
if settings.SERVICE in {"seller", "partner"}:
    urlpatterns += [path("analytics/", analytics, name="analytics")]
if settings.SERVICE=="partner":
    urlpatterns += [path("admin/",admin.site.urls),path("static/<path:path>",serve,{"insecure":True})]