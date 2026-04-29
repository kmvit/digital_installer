from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0007_projectobject_as_built_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128, unique=True, verbose_name="Название")),
            ],
            options={
                "verbose_name": "Город",
                "verbose_name_plural": "Города",
                "db_table": "objects_city",
                "ordering": ("name",),
            },
        ),
        migrations.AlterField(
            model_name="projectobject",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Название"),
        ),
        migrations.AddField(
            model_name="projectobject",
            name="city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="project_objects",
                to="objects.city",
                verbose_name="Город",
            ),
        ),
    ]
