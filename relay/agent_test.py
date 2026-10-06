from strands import Agent
from strands.models import BedrockModel


def main() -> None:
    model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-west-2",
    )

    agent = Agent(model=model)

    response = agent(
        "Explain in one short sentence what a long-running AI agent is."
    )

    print(response)


if __name__ == "__main__":
    main()