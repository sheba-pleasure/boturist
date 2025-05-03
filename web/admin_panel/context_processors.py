from .models import BotSettings

def bot_settings(request):
    """Add bot settings to template context"""
    return {
        'bot_settings': BotSettings.get_settings()
    } 