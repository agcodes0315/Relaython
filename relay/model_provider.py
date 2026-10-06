import os

from openai import OpenAI


DEFAULT_MODEL = "openai.gpt-oss-20b"
DEFAULT_BASE_URL = "https://bedrock-mantle.us-west-2.api.aws/v1"


def get_model_name() -> str:
    return os.environ.get(
        "RELAY_MODEL",
        DEFAULT_MODEL,
    )


def get_bedrock_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Set your Amazon Bedrock API key in the current terminal."
        )

    base_url = os.environ.get(
        "OPENAI_BASE_URL",
        DEFAULT_BASE_URL,
    )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
