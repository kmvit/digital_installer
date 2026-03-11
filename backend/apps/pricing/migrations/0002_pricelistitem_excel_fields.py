from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pricelistitem",
            old_name="section",
            new_name="item_number",
        ),
        migrations.RenameField(
            model_name="pricelistitem",
            old_name="short_description",
            new_name="composition",
        ),
        migrations.RenameField(
            model_name="pricelistitem",
            old_name="rate",
            new_name="base_rate",
        ),
        migrations.AlterField(
            model_name="pricelistitem",
            name="item_number",
            field=models.CharField(blank=True, max_length=64, verbose_name="№ п/п"),
        ),
        migrations.AlterField(
            model_name="pricelistitem",
            name="name",
            field=models.CharField(max_length=500, verbose_name="Наименование работ"),
        ),
        migrations.AlterField(
            model_name="pricelistitem",
            name="composition",
            field=models.TextField(blank=True, verbose_name="Состав работ"),
        ),
        migrations.AlterField(
            model_name="pricelistitem",
            name="unit",
            field=models.CharField(blank=True, max_length=100, verbose_name="Единица измерения"),
        ),
        migrations.AlterField(
            model_name="pricelistitem",
            name="base_rate",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=14,
                verbose_name="Удельная стоимость за единицу без НДС, руб.",
            ),
        ),
        migrations.AddField(
            model_name="pricelistitem",
            name="note",
            field=models.TextField(blank=True, verbose_name="Примечание"),
        ),
        migrations.AddField(
            model_name="pricelistitem",
            name="smr_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="в том числе стоимость СМР (работ), руб.",
            ),
        ),
        migrations.AddField(
            model_name="pricelistitem",
            name="materials_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="в том числе стоимость кабеля, материалов, руб.",
            ),
        ),
        migrations.AddField(
            model_name="pricelistitem",
            name="pir_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="в том числе стоимость ПИР, руб.",
            ),
        ),
        migrations.AlterModelOptions(
            name="pricelistitem",
            options={
                "ordering": ("item_number", "name"),
                "verbose_name": "Позиция расценки",
                "verbose_name_plural": "Позиции расценок",
            },
        ),
    ]
