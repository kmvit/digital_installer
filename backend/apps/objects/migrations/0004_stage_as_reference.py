"""Refactor stages: Stage as a reference table, ObjectStage links Stage to ProjectObject."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


DEFAULT_STAGES = [
    (0, "Обследовать"),
    (1, "Строить"),
    (2, "Завершен"),
    (3, "Завершен и оплачен"),
    (4, "Гарантия"),
]


def seed_stages(apps, schema_editor):
    Stage = apps.get_model("objects", "Stage")
    for order, name in DEFAULT_STAGES:
        Stage.objects.get_or_create(name=name, defaults={"order": order})


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0003_fix_brigade_related_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Убираем FK current_stage (пока указывает на старый ObjectStage)
        migrations.RemoveField(
            model_name="projectobject",
            name="current_stage",
        ),

        # 2. Удаляем старую таблицу ObjectStage
        migrations.DeleteModel(
            name="ObjectStage",
        ),

        # 3. Создаём справочник Stage
        migrations.CreateModel(
            name="Stage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Название")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")),
            ],
            options={
                "db_table": "objects_stage",
                "verbose_name": "Стадия",
                "verbose_name_plural": "Стадии",
                "ordering": ("order",),
            },
        ),

        # 4. Создаём ObjectStage (привязка стадии к объекту)
        migrations.CreateModel(
            name="ObjectStage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("planned_date", models.DateField(blank=True, null=True, verbose_name="Плановая дата")),
                ("actual_date", models.DateField(blank=True, null=True, verbose_name="Фактическая дата")),
                (
                    "project_object",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="object_stages",
                        to="objects.projectobject",
                        verbose_name="Объект",
                    ),
                ),
                (
                    "stage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="object_stages",
                        to="objects.stage",
                        verbose_name="Стадия",
                    ),
                ),
            ],
            options={
                "db_table": "objects_objectstage",
                "verbose_name": "Стадия объекта",
                "verbose_name_plural": "Стадии объектов",
                "ordering": ("stage__order",),
                "unique_together": {("project_object", "stage")},
            },
        ),

        # 5. Возвращаем current_stage — теперь FK на Stage
        migrations.AddField(
            model_name="projectobject",
            name="current_stage",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="objects.stage",
                verbose_name="Текущая стадия",
            ),
        ),

        # 6. Заполняем справочник дефолтными стадиями
        migrations.RunPython(seed_stages, migrations.RunPython.noop),
    ]
