import os

from openai import OpenAI


def main() -> None:
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://bedrock-mantle.us-west-2.api.aws/v1",
    )

    models = client.models.list()

    print("Models available to this AWS account:\n")

    for model in models.data:
        print(model.id)


if __name__ == "__main__":
    main()