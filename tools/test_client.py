from config import HOST, USER, PASSWORD
from windhager.client import WindhagerClient


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    print("Verbunden.")
    print()

    modules = client.lookup("1")

    for module in modules:
        print(
            f"{module['nodeId']:>2}  {module['name']}"
        )


if __name__ == "__main__":
    main()