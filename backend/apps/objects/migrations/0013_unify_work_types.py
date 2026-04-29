from django.db import migrations, models


def migrate_available_to_plans(apps, schema_editor):
    """Для каждой записи в M2M, если плана нет — создаём с planned_volume=0."""
    ProjectObject = apps.get_model("objects", "ProjectObject")
    ObjectWorkPlan = apps.get_model("objects", "ObjectWorkPlan")
    for obj in ProjectObject.objects.all():
        existing_types = set(
            ObjectWorkPlan.objects.filter(project_object=obj).values_list("work_type_id", flat=True)
        )
        for wt_id in obj.available_work_types.values_list("id", flat=True):
            if wt_id not in existing_types:
                ObjectWorkPlan.objects.create(
                    project_object=obj,
                    work_type_id=wt_id,
                    planned_volume=0,
                )


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0012_objectworkplan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="objectworkplan",
            name="planned_volume",
            field=models.DecimalField(
                decimal_places=3, default=0, max_digits=14,
                help_text="Можно оставить 0, если просто нужно разрешить вид работ без планирования объёма.",
                verbose_name="Плановый объём",
            ),
        ),
        migrations.RunPython(migrate_available_to_plans, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="projectobject",
            name="available_work_types",
        ),
    ]
