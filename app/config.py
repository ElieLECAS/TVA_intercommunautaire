import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    return default if val is None else val.strip().lower() in {"1", "true", "yes"}


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://tva:tva@localhost:5432/tva_referentiel"
)

VIES_BASE_URL = os.getenv(
    "VIES_BASE_URL", "https://ec.europa.eu/taxation_customs/vies/rest-api"
)
VIES_TIMEOUT_SECONDS = float(os.getenv("VIES_TIMEOUT_SECONDS", "10"))
VIES_DELAY_BETWEEN_CALLS_SECONDS = float(
    os.getenv("VIES_DELAY_BETWEEN_CALLS_SECONDS", "1.0")
)

SAMPLE_SIZE_DEFAULT = int(os.getenv("SAMPLE_SIZE_DEFAULT", "200"))
VIES_VERDICT_TTL_DAYS = int(os.getenv("VIES_VERDICT_TTL_DAYS", "90"))
