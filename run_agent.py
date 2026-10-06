from relay.agent import RelayAgent


def main() -> None:
    print()
    print("=" * 60)
    print("Relay Agent")
    print("Delegate outcomes. Relay handles the rest.")
    print("=" * 60)

    agent = RelayAgent()

    while True:
        print()

        user_message = input("You: ").strip()

        if not user_message:
            continue

        if user_message.lower() in {
            "exit",
            "quit",
            "q",
        }:
            print()
            print("Relay: Goodbye.")
            break

        try:
            response = agent.run(
                user_message
            )

            print()
            print(
                f"Relay: {response}"
            )

        except KeyboardInterrupt:
            print()
            print("Relay: Stopped.")
            break

        except Exception as exc:
            print()
            print("Relay encountered an error:")
            print(
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
