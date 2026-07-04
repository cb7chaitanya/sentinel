from sentinel_common.config import BaseServiceSettings


def test_defaults() -> None:
    settings = BaseServiceSettings()
    assert settings.service_name == "sentinel-service"
    assert settings.port == 8000
