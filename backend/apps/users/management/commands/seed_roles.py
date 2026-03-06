from django.core.management.base import BaseCommand

from apps.users.models import Role, RoleCode


class Command(BaseCommand):
    help = "Создает системные роли RBAC, если они отсутствуют"

    def handle(self, *args, **options):
        for role in RoleCode:
            _, created = Role.objects.get_or_create(
                code=role.value,
                defaults={"name": role.label, "is_system": True},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Создана роль: {role.value}"))
