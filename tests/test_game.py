"""Проверки физики, столкновений и переходов состояния игры."""

import os
import unittest

import pygame

import settings
from entities import (
    Asteroid,
    Bullet,
    Ship,
    circles_collide,
    wrap_position,
)
from game import Game


def setUpModule() -> None:
    """Выбирает виртуальный видеодрайвер для тестов без монитора."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class EntityTests(unittest.TestCase):
    """Проверяет движение и столкновения игровых объектов."""

    def test_position_wraps_at_both_field_edges(self) -> None:
        """Объект появляется с противоположного края поля."""
        position = pygame.Vector2(-2, settings.SCREEN_HEIGHT + 3)

        wrap_position(position)

        self.assertEqual(position, (settings.SCREEN_WIDTH - 2, 3))

    def test_collision_crosses_horizontal_edge(self) -> None:
        """Столкновение определяется и по разные стороны края."""
        self.assertTrue(
            circles_collide(
                pygame.Vector2(2, 100),
                5,
                pygame.Vector2(settings.SCREEN_WIDTH - 2, 100),
                5,
            )
        )

    def test_ship_accelerates_and_slows_without_thrust(self) -> None:
        """Ускорение увеличивает скорость, сопротивление её уменьшает."""
        ship = Ship()
        ship.accelerate(0.2)
        accelerated_speed = ship.velocity.length()

        ship.update(0.2)

        self.assertGreater(accelerated_speed, 0)
        self.assertLess(ship.velocity.length(), accelerated_speed)

    def test_bullet_expires_before_crossing_the_small_field_dimension(self) -> None:
        """Время жизни ракеты ограничивает её дальность полёта."""
        bullet = Bullet(pygame.Vector2(100, 100), 0)

        bullet.update(settings.BULLET_LIFETIME)

        self.assertLessEqual(bullet.lifetime, 0)
        self.assertLess(
            settings.BULLET_SPEED * settings.BULLET_LIFETIME,
            min(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
        )


class GameTests(unittest.TestCase):
    """Проверяет правила игры и обработку пользовательского ввода."""

    @classmethod
    def setUpClass(cls) -> None:
        """Инициализирует Pygame для тестов без настоящего окна."""
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        """Освобождает ресурсы Pygame после тестов."""
        pygame.quit()

    def setUp(self) -> None:
        """Создаёт игру в начальном состоянии."""
        pygame.event.clear()
        self.game = Game()

    def test_only_a_click_on_the_banner_starts_the_game(self) -> None:
        """Щелчок вне заставки игнорируется."""
        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": (0, 0)},
            )
        )
        self.game._handle_events()
        self.assertFalse(self.game.started)

        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": self.game.banner.center},
            )
        )
        self.game._handle_events()

        self.assertTrue(self.game.started)
        self.assertIsNotNone(self.game.ship)

    def test_title_screen_draws(self) -> None:
        """Начальный экран отрисовывается с тремя жизнями и нулём очков."""
        self.game._draw()

        self.assertEqual(self.game.lives, settings.INITIAL_LIVES)
        self.assertEqual(self.game.score, 0)

    def test_bullet_hit_scores_and_removes_both_objects(self) -> None:
        """Попадание удаляет ракету и астероид и начисляет очко."""
        asteroid = Asteroid(
            (2, 100),
            radius=18,
            velocity=pygame.Vector2(),
            spin=0,
        )
        bullet = Bullet(pygame.Vector2(), 0)
        bullet.position = pygame.Vector2(settings.SCREEN_WIDTH - 2, 100)
        self.game.ship = None
        self.game.asteroids = [asteroid]
        self.game.bullets = [bullet]

        self.game._resolve_collisions()

        self.assertEqual(self.game.score, 1)
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(self.game.bullets, [])
        self.assertEqual(len(self.game.explosions), 1)

    def test_ship_collision_removes_life_and_respawns_in_center(self) -> None:
        """После столкновения корабль неподвижно появляется в центре."""
        ship = Ship()
        self.game.ship = ship
        self.game.asteroids = [
            Asteroid(
                ship.position,
                radius=18,
                velocity=pygame.Vector2(),
                spin=0,
            )
        ]

        self.game._resolve_collisions()

        self.assertEqual(self.game.lives, settings.INITIAL_LIVES - 1)
        self.assertEqual(self.game.ship.position, ship.position)
        self.assertEqual(self.game.ship.velocity, (0, 0))
        self.assertEqual(self.game.ship.invulnerability, settings.SHIP_INVULNERABILITY)

    def test_last_life_shows_game_over_and_click_resets_the_game(self) -> None:
        """После последней жизни повторный запуск начинает новую игру."""
        self.game.lives = 1
        ship = Ship()
        self.game.ship = ship
        self.game.asteroids = [
            Asteroid(
                ship.position,
                radius=18,
                velocity=pygame.Vector2(),
                spin=0,
            )
        ]
        bullet = Bullet(ship.position, 0)
        bullet.position = pygame.Vector2(100, 100)
        self.game.bullets = [bullet]
        self.game.score = 4

        self.game._resolve_collisions()

        self.assertTrue(self.game.game_over)
        self.assertFalse(self.game.started)
        self.assertIsNone(self.game.ship)
        self.assertEqual(self.game.score, 4)
        self.assertEqual(self.game.lives, 0)
        self.assertEqual(self.game.bullets, [])
        self.assertEqual(self.game.asteroids, [])

        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": (0, 0)},
            )
        )
        self.game._handle_events()
        self.assertTrue(self.game.game_over)
        self.assertEqual(self.game.score, 4)

        pygame.event.post(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": self.game.banner.center},
            )
        )
        self.game._handle_events()

        self.assertFalse(self.game.game_over)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, settings.INITIAL_LIVES)
        self.assertTrue(self.game.started)


if __name__ == "__main__":
    unittest.main()
