import os

from openai import OpenAI


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set in this terminal."
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://bedrock-mantle.us-west-2.api.aws/v1",
    )

    print("Sending test request to Amazon Bedrock...\n")

    try:
        response = client.responses.create(
            model="openai.gpt-oss-20b",
            input=(
                "Explain in one short sentence what "
                "a long-running AI agent is."
            ),
        )

        print("BEDROCK RESPONSE:")
        print(response.output_text)

    except Exception as exc:
        print("BEDROCK ERROR:")
        print(type(exc).__name__)
        print(str(exc))


if __name__ == "__main__":
    main()