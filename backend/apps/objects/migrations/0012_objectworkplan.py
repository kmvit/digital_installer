from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0011_remove_price_list"),
        ("pricing", "0004_worktype"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObjectWorkPlan",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("planned_volume", models.DecimalField(decimal_places=3, max_digits=14, verbose_name="Плановый объём")),
                ("planned_start", models.DateField(blank=True, null=True, verbose_name="План: старт")),
                ("planned_end", models.DateField(blank=True, null=True, verbose_name="План: завершение")),
                ("notes", models.TextField(blank=True, verbose_name="Примечания")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                ("project_object", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="work_plans",
                    to="objects.projectobject",
                    verbose_name="Объект",
                )),
                ("work_type", models.ForeignKey(
                    on_delete=models.deletion.PROTECT,
                    related_name="object_plans",
                    to="pricing.worktype",
                    verbose_name="Вид работ",
                )),
            ],
            options={
                "verbose_name": "Плановый объём работ",
                "verbose_name_plural": "Плановые объёмы работ",
                "db_table": "objects_objectworkplan",
                "ordering": ("planned_start", "id"),
                "unique_together": {("project_object", "work_type")},
            },
        ),
    ]
