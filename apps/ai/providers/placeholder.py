from .base import AIProvider


class PlaceholderAIProvider(AIProvider):
    provider_name = "none"

    def analyze_complaint(self, complaint):
        return {
            "configured": False,
            "message": "AI integration is not configured.",
        }
