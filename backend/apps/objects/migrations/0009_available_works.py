from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0008_city"),
        ("pricing", "0003_alter_pricelistitem_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectobject",
            name="available_works",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Перечень работ из базы расценок, разрешённых для этого объекта. "
                    "Если пусто — доступны все работы из привязанной базы."
                ),
                related_name="available_for_objects",
                to="pricing.pricelistitem",
                verbose_name="Состав работ для объекта",
            ),
        ),
    ]
