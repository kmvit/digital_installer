from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workday", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="objectsession",
            name="scheme_photo",
            field=models.ImageField(
                blank=True,
                help_text="Фото рукописной схемы с отмеченными участками выполнения работ.",
                upload_to="workday/scheme/%Y/%m/%d/",
                verbose_name="Схема выполненных работ",
            ),
        ),
    ]
