from django.db import migrations


def groups(apps, schema_editor):
    Group = apps.get_model("auth","Group")
    for role in ("seller","partner","fleet","node","drive","atlas","wild"):
        Group.objects.get_or_create(name=role)


class Migration(migrations.Migration):
    dependencies = [("ledger","0002_parcel_accepted"),("auth","0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(groups,migrations.RunPython.noop)]