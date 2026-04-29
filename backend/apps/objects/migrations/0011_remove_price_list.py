from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0010_available_work_types"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="projectobject",
            name="price_list",
        ),
    ]
