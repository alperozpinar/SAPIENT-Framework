"""API key yönetimi. .env dosyasından veya environment'tan yükler."""
import os
from pathlib import Path


def load_env():
    """Proje kökündeki .env dosyasını yükle."""
    for candidate in [
        Path(__file__).parent.parent / ".env",   # sapient/.env
        Path(__file__).parent.parent.parent / ".env",  # üst dizin
    ]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        k, v = key.strip(), value.strip()
                        if v and (not os.environ.get(k)):
                            os.environ[k] = v
            return


def get_api_key(provider: str) -> str:
    """Provider'a göre API key döndür."""
    load_env()
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_var = key_map.get(provider)
    if not env_var:
        raise ValueError(f"Bilinmeyen provider: {provider}")
    key = os.environ.get(env_var)
    if not key or key.startswith("your-"):
        raise EnvironmentError(
            f"{env_var} ayarlanmamış. .env dosyası oluşturun veya export edin.\n"
            f"Bkz: .env.example"
        )
    return key
