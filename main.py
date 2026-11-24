"""Точка входа в игру «Астероиды»."""

from game import Game


def main() -> None:
    """Создаёт игру и запускает её."""
    Game().run()


if __name__ == "__main__":
    main()
