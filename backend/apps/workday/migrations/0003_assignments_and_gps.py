from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workday", "0002_scheme_photo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="completedwork",
            name="volume",
            field=models.DecimalField(decimal_places=3, max_digits=12, verbose_name="Объём (фактический)"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="planned_volume",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name="Объём (плановый)"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="status",
            field=models.CharField(
                choices=[("assigned", "Назначена"), ("in_progress", "В работе"), ("completed", "Выполнена")],
                db_index=True,
                default="completed",
                max_length=16,
                verbose_name="Статус",
            ),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="assigned_works",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Назначена монтажнику",
            ),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="assigned_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="given_works",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Назначил",
            ),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Начата"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="started_photo",
            field=models.ImageField(blank=True, upload_to="workday/work_started/%Y/%m/%d/", verbose_name="Фото начала"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="started_latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="GPS широта (начало)"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="started_longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="GPS долгота (начало)"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Завершена"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="completed_photo",
            field=models.ImageField(blank=True, upload_to="workday/work_completed/%Y/%m/%d/", verbose_name="Фото завершения"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="completed_latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="GPS широта (завершение)"),
        ),
        migrations.AddField(
            model_name="completedwork",
            name="completed_longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="GPS долгота (завершение)"),
        ),
        migrations.CreateModel(
            name="BrigadeGpsCheck",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="GPS широта")),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="GPS долгота")),
                ("captured_at", models.DateTimeField(verbose_name="Время фиксации")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Загружено")),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="gps_checks",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Член бригады",
                )),
                ("workday", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="gps_checks",
                    to="workday.workday",
                    verbose_name="Рабочий день",
                )),
            ],
            options={
                "verbose_name": "GPS-чек члена бригады",
                "verbose_name_plural": "GPS-чеки бригады",
                "db_table": "workday_brigadegpscheck",
                "ordering": ("-created_at",),
                "unique_together": {("workday", "user")},
            },
        ),
    ]
