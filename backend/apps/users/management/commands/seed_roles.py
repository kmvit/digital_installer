from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Команда оставлена для обратной совместимости"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Команда seed_roles больше не требуется: роли теперь задаются choices в users.User.role."
            )
        )
