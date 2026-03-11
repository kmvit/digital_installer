# Generated manually to move models from apps.core to apps.objects state
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ProjectObject",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=255, unique=True, verbose_name="Название объекта")),
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                        ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
                        (
                            "price_list",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="objects",
                                to="pricing.pricelist",
                                verbose_name="База расценок",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Объект",
                        "verbose_name_plural": "Объекты",
                        "ordering": ("name",),
                        "db_table": "core_projectobject",
                    },
                ),
            ],
        ),
    ]
