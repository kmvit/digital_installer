from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0003_alter_pricelistitem_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkType",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(blank=True, help_text="Название раздела (например, «Раздел 1. ...»).", max_length=255, verbose_name="Раздел")),
                ("name", models.CharField(max_length=512, verbose_name="Наименование вида работ")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("price_list", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="work_types", to="pricing.pricelist", verbose_name="База расценок")),
            ],
            options={
                "verbose_name": "Вид работ",
                "verbose_name_plural": "Виды работ",
                "db_table": "core_worktype",
                "ordering": ("price_list_id", "order", "name"),
                "unique_together": {("price_list", "name")},
            },
        ),
        migrations.AddField(
            model_name="pricelistitem",
            name="work_type",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="items",
                to="pricing.worktype",
                verbose_name="Вид работ",
            ),
        ),
    ]
