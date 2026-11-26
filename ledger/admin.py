from django.contrib import admin
from .models import Packaging, Node, Vehicle
# Provision reference data and assignments. Operational records use domain actions.
admin.site.register(Packaging)

@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    fields = ["city","name","owner","workers","hub","active"]
    def has_add_permission(self,request):
        return False

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    fields = ["plate","fleet","drivers"]
    def has_add_permission(self,request):
        return False