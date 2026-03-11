# Generated manually to move state from core to domain apps
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_projectobject"),
        ("pricing", "0001_initial"),
        ("objects", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="PriceListItem"),
                migrations.DeleteModel(name="ProjectObject"),
                migrations.DeleteModel(name="PriceList"),
            ],
        ),
    ]
