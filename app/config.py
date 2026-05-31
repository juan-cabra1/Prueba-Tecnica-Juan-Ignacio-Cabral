from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    docs_path: str = "docs"
    chroma_path: str = "/data/chroma"
    collection_name: str = "soporte_registros"
    model_name: str = "intfloat/multilingual-e5-small"
    top_k: int = 3
    threshold: float = 0.80

    model_config = {"env_prefix": "RAG_", "env_file": ".env"}


settings = Settings()
