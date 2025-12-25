import requests
from django.conf import settings

class AIServiceError(Exception):
    pass

def call_ai(service_name: str, payload: dict, timeout: int | None = None) -> dict:
    services = getattr(settings, "AI_SERVICES", {})
    url = services.get(service_name)

    if not url:
        raise AIServiceError(f"AI service '{service_name}' is not configured")

    timeout = timeout or getattr(settings, "AI_TIMEOUT_SECONDS", 60)

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        raise AIServiceError("AI service timeout")
    except requests.RequestException as e:
        raise AIServiceError(f"AI request failed: {str(e)}")
    except ValueError:
        raise AIServiceError("AI response is not valid JSON")