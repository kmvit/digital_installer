from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0009_available_works"),
        ("pricing", "0004_worktype"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="projectobject",
            name="available_works",
        ),
        migrations.AddField(
            model_name="projectobject",
            name="available_work_types",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Виды работ из базы расценок, разрешённые для этого объекта. "
                    "Если пусто — доступны все виды/работы из привязанной базы."
                ),
                related_name="available_for_objects",
                to="pricing.worktype",
                verbose_name="Виды работ для объекта",
            ),
        ),
    ]
