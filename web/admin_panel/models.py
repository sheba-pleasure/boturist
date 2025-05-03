from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class TelegramUser(models.Model):
    """Telegram user model"""
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    is_bot = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Telegram User')
        verbose_name_plural = _('Telegram Users')
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})"

class Request(models.Model):
    """Модель запроса на парсинг"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
    ]

    PLATFORM_CHOICES = [
        ('vk', 'ВКонтакте'),
        ('instagram', 'Instagram'),
        ('yandex_maps', 'Яндекс.Карты'),
    ]

    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='requests')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    query = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = 'Запрос'
        verbose_name_plural = 'Запросы'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} - {self.query[:50]}"

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

class RequestFile(models.Model):
    """Модель файла, прикрепленного к запросу"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='request_files/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = 'Файл запроса'
        verbose_name_plural = 'Файлы запросов'
        ordering = ['-created_at']

    def __str__(self):
        return self.file_name

class RequestMessage(models.Model):
    """Модель сообщения, связанного с запросом"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField()
    is_from_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = 'Сообщение запроса'
        verbose_name_plural = 'Сообщения запросов'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.text[:50]}..."

class Material(models.Model):
    """Model for managing educational and promotional materials"""
    CATEGORIES = [
        ('checklist', _('Checklist')),
        ('instruction', _('Instruction')),
        ('document', _('Document')),
        ('promo', _('Promotional')),
    ]

    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    category = models.CharField(_('Category'), max_length=20, choices=CATEGORIES)
    file = models.FileField(_('File'), upload_to='materials/')
    tags = models.JSONField(_('Tags'), default=list)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Material')
        verbose_name_plural = _('Materials')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Publication(models.Model):
    """Publication model"""
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    platform = models.CharField(
        max_length=20,
        choices=[
            ('telegram', 'Telegram'),
            ('vk', 'VKontakte'),
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram')
        ]
    )
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('published', 'Published'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Publication')
        verbose_name_plural = _('Publications')
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"{self.material.title} - {self.platform}"

class Campaign(models.Model):
    """Model for managing advertising campaigns"""
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('paused', _('Paused')),
        ('completed', _('Completed')),
    ]

    name = models.CharField(_('Name'), max_length=200)
    description = models.TextField(_('Description'))
    start_date = models.DateField(_('Start date'))
    end_date = models.DateField(_('End date'))
    budget = models.DecimalField(_('Budget'), max_digits=10, decimal_places=2)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    target_audience = models.JSONField(_('Target audience'))
    materials = models.ManyToManyField(Material, related_name='campaigns')
    metrics = models.JSONField(_('Performance metrics'), default=dict)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Campaign')
        verbose_name_plural = _('Campaigns')
        ordering = ['-start_date']

    def __str__(self):
        return self.name

class RequestFromPost(models.Model):
    """Model for handling requests from social media posts"""
    STATUS_CHOICES = [
        ('new', _('New')),
        ('processing', _('Processing')),
        ('resolved', _('Resolved')),
        ('rejected', _('Rejected')),
    ]

    platform = models.CharField(_('Platform'), max_length=50)
    post_id = models.CharField(_('Post ID'), max_length=100)
    content = models.TextField(_('Content'))
    author = models.JSONField(_('Author info'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    response = models.TextField(_('Response'), blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Request from post')
        verbose_name_plural = _('Requests from posts')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} - {self.post_id}"

class LawyerProfile(models.Model):
    """Model for lawyer profiles"""
    SPECIALIZATION_CHOICES = [
        ('civil', _('Civil Law')),
        ('criminal', _('Criminal Law')),
        ('corporate', _('Corporate Law')),
        ('family', _('Family Law')),
        ('labor', _('Labor Law')),
        ('tax', _('Tax Law')),
        ('intellectual', _('Intellectual Property')),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='lawyer_profile'
    )
    specializations = models.JSONField(
        _('Specializations'),
        help_text=_('List of lawyer specializations'),
        default=list
    )
    categories = models.JSONField(
        _('Request Categories'),
        help_text=_('Categories of requests this lawyer can handle'),
        default=list
    )
    experience_years = models.PositiveIntegerField(
        _('Years of Experience'),
        default=0
    )
    education = models.TextField(
        _('Education'),
        blank=True
    )
    certifications = models.JSONField(
        _('Certifications'),
        default=list
    )
    languages = models.JSONField(
        _('Languages'),
        default=list
    )
    rating = models.DecimalField(
        _('Rating'),
        max_digits=3,
        decimal_places=2,
        default=5.00
    )
    reviews_count = models.PositiveIntegerField(
        _('Number of Reviews'),
        default=0
    )
    is_available = models.BooleanField(
        _('Is Available'),
        default=True
    )
    active_cases = models.PositiveIntegerField(
        _('Active Cases'),
        default=0
    )
    max_cases = models.PositiveIntegerField(
        _('Maximum Cases'),
        default=10
    )
    hourly_rate = models.DecimalField(
        _('Hourly Rate'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    schedule = models.JSONField(
        _('Working Schedule'),
        default=dict
    )
    telegram_id = models.BigIntegerField(
        _('Telegram ID'),
        null=True,
        blank=True
    )
    notification_preferences = models.JSONField(
        _('Notification Preferences'),
        default=dict
    )
    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Lawyer Profile')
        verbose_name_plural = _('Lawyer Profiles')
        ordering = ['-rating', '-experience_years']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.username})"

    def can_take_case(self) -> bool:
        """Check if lawyer can take new case"""
        return (
            self.is_available and
            self.active_cases < self.max_cases
        )

    def increment_active_cases(self) -> None:
        """Increment active cases count"""
        self.active_cases += 1
        if self.active_cases >= self.max_cases:
            self.is_available = False
        self.save()

    def decrement_active_cases(self) -> None:
        """Decrement active cases count"""
        if self.active_cases > 0:
            self.active_cases -= 1
            if self.active_cases < self.max_cases:
                self.is_available = True
            self.save()

    def update_rating(self, new_rating: int) -> None:
        """Update lawyer's rating"""
        total = self.rating * self.reviews_count
        self.reviews_count += 1
        self.rating = (total + new_rating) / self.reviews_count
        self.save()

class LawyerReview(models.Model):
    """Model for lawyer reviews"""
    lawyer = models.ForeignKey(
        LawyerProfile,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    request = models.ForeignKey(
        'RequestFromPost',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lawyer_reviews'
    )
    client = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lawyer_reviews'
    )
    rating = models.PositiveIntegerField(
        _('Rating'),
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    comment = models.TextField(
        _('Comment'),
        blank=True
    )
    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _('Lawyer Review')
        verbose_name_plural = _('Lawyer Reviews')
        ordering = ['-created_at']
        unique_together = ['lawyer', 'request', 'client']

    def __str__(self):
        return f"Review for {self.lawyer} by {self.client}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.lawyer.update_rating(self.rating)

class BotSettings(models.Model):
    """Global bot settings"""
    ai_assistant_enabled = models.BooleanField(
        default=True,
        verbose_name=_("AI Assistant Enabled"),
        help_text=_("Enable or disable AI assistant functionality")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'admin_panel'
        verbose_name = _("Bot Settings")
        verbose_name_plural = _("Bot Settings")

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and BotSettings.objects.exists():
            return BotSettings.objects.first()
        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create bot settings"""
        settings, _ = cls.objects.get_or_create()
        return settings 