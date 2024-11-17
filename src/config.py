# src/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Settings Object.

    Args:
        :param BaseSettings: (BaseSettings) Base Settings Object.
    """

    # Global Config (Optional)
    OUTPUT_DIR: str = "output"

    class Config:
        """
        Config Object.
        """

        env_file = ".env"


settings = Settings()
