import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from datetime import datetime, timezone

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    is_active = True

class MessageFactory(DjangoModelFactory):
    class Meta:
        model = 'dashboard.Message'  # Замените на вашу модель сообщений

    user = factory.SubFactory(UserFactory)
    text = factory.Faker('text', max_nb_chars=200)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    is_processed = False

class ChatFactory(DjangoModelFactory):
    class Meta:
        model = 'dashboard.Chat'  # Замените на вашу модель чатов

    telegram_id = factory.Sequence(lambda n: n)
    title = factory.Faker('company')
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    is_active = True 