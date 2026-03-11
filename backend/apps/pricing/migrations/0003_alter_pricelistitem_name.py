from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pricing", "0002_pricelistitem_excel_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pricelistitem",
            name="name",
            field=models.TextField(verbose_name="Наименование работ"),
        ),
    ]
