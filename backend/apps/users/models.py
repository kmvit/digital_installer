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


class User(AbstractUser):
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Телефон",
    )
    status = models.CharField(
        max_length=16,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
        verbose_name="Статус",
        help_text="Текущий статус сотрудника в системе.",
    )
    role = models.CharField(
        max_length=32,
        choices=RoleCode.choices,
        default=RoleCode.WORKER,
        db_index=True,
        verbose_name="Роль",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.username

    def has_role(self, role_code: str) -> bool:
        return self.role == role_code


class Brigade(models.Model):
    name = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Название бригады",
    )
    foreman = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="foreman_brigades",
        verbose_name="Бригадир",
    )
    members = models.ManyToManyField(
        User,
        blank=True,
        related_name="brigades",
        verbose_name="Состав бригады",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Бригада"
        verbose_name_plural = "Бригады"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
