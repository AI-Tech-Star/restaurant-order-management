from src import settings


def test_app_name_default() -> None:
    assert settings.APP_NAME == "restaurant-api"


def test_app_env_default() -> None:
    assert settings.APP_ENV == "development"