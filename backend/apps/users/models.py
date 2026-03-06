from django.contrib.auth.models import AbstractUser
from django.db import models


class RoleCode(models.TextChoices):
    ADMINISTRATOR = "administrator", "Администратор"
    DIRECTOR = "director", "Директор"
    PROJECT_MANAGER = "project_manager", "Руководитель проекта"
    FOREMAN = "foreman", "Мастер (бригадир)"
    WORKER = "worker", "Монтажник"
    SUPPORT_MANAGER = "support_manager", "Менеджер по сопровождению"
    DESIGNER = "designer", "Проектировщик"
    CUSTOMER = "customer", "Заказчик"
    ACCOUNTANT = "accountant", "Бухгалтер"


class UserStatus(models.TextChoices):
    ACTIVE = "active", "Активен"
    BLOCKED = "blocked", "Заблокирован"
    DISMISSED = "dismissed", "Уволен"


class Role(models.Model):
    code = models.CharField(max_length=64, unique=True, choices=RoleCode.choices)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=16,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
    )
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name="users",
        verbose_name="Роли",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.username

    def has_role(self, role_code: str) -> bool:
        return self.roles.filter(code=role_code).exists()
