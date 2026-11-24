"""Игровые объекты и их отрисовка."""

import math
import random
from typing import Optional

import pygame

import settings


def wrap_position(position: pygame.Vector2) -> None:
    """Переносит позицию объекта на противоположную сторону поля."""
    position.x %= settings.SCREEN_WIDTH
    position.y %= settings.SCREEN_HEIGHT


class Ship:
    """Корабль игрока с инерцией и управляемым ускорением."""

    def __init__(self) -> None:
        """Создаёт корабль в центре поля."""
        self.position = pygame.Vector2(
            settings.SCREEN_WIDTH / 2,
            settings.SCREEN_HEIGHT / 2,
        )
        self.velocity = pygame.Vector2()
        self.angle = -90.0
        self.invulnerability = 0.0

    @property
    def radius(self) -> int:
        """Возвращает радиус столкновения корабля."""
        return settings.SHIP_RADIUS

    def rotate(self, direction: int, delta_time: float) -> None:
        """Поворачивает корабль влево или вправо."""
        self.angle = (
            self.angle + direction * settings.TURN_SPEED * delta_time
        ) % 360

    def accelerate(self, delta_time: float) -> None:
        """Увеличивает скорость корабля в направлении его носа."""
        direction = pygame.Vector2(1, 0).rotate(self.angle)
        self.velocity += direction * settings.SHIP_ACCELERATION * delta_time
        if self.velocity.length() > settings.SHIP_MAX_SPEED:
            self.velocity.scale_to_length(settings.SHIP_MAX_SPEED)

    def update(self, delta_time: float) -> None:
        """Двигает корабль, применяет сопротивление и переносит через край."""
        self.position += self.velocity * delta_time
        self.velocity *= math.exp(-settings.SHIP_FRICTION * delta_time)
        wrap_position(self.position)
        self.invulnerability = max(0, self.invulnerability - delta_time)

    def draw(self, surface: pygame.Surface, thrusting: bool = False) -> None:
        """Рисует корпус корабля и, при ускорении, языки пламени."""
        if self.invulnerability > 0 and int(self.invulnerability * 12) % 2:
            return

        nose = pygame.Vector2(settings.SHIP_RADIUS, 0)
        rear_left = pygame.Vector2(-settings.SHIP_RADIUS * 0.7, -11)
        rear_right = pygame.Vector2(-settings.SHIP_RADIUS * 0.7, 11)
        points = [
            self.position + point.rotate(self.angle)
            for point in (nose, rear_left, rear_right)
        ]

        if thrusting:
            flame_points = [
                self.position + pygame.Vector2(-10, -5).rotate(self.angle),
                self.position + pygame.Vector2(-22, 0).rotate(self.angle),
                self.position + pygame.Vector2(-10, 5).rotate(self.angle),
            ]
            pygame.draw.polygon(surface, (255, 135, 45), flame_points)

        pygame.draw.polygon(surface, (210, 230, 255), points)
        pygame.draw.polygon(surface, (60, 125, 210), points, 2)


class Asteroid:
    """Астероид с заданным радиусом, скоростью и вращением."""

    def __init__(
        self,
        position: tuple[float, float],
        radius: Optional[int] = None,
        velocity: Optional[pygame.Vector2] = None,
        spin: Optional[float] = None,
    ) -> None:
        """Создаёт астероид и неровный контур его поверхности."""
        self.position = pygame.Vector2(position)
        self.radius = radius or random.randint(
            settings.ASTEROID_MIN_RADIUS,
            settings.ASTEROID_MAX_RADIUS,
        )
        self.velocity = (
            velocity
            if velocity is not None
            else pygame.Vector2(
                random.uniform(
                    -settings.ASTEROID_MAX_SPEED,
                    settings.ASTEROID_MAX_SPEED,
                ),
                random.uniform(
                    -settings.ASTEROID_MAX_SPEED,
                    settings.ASTEROID_MAX_SPEED,
                ),
            )
        )
        self.spin = spin if spin is not None else random.uniform(-70, 70)
        self.angle = random.uniform(0, 360)
        self.vertices = [
            self.radius * random.uniform(0.78, 1.18)
            for _ in range(random.randint(9, 13))
        ]

    def update(self, delta_time: float) -> None:
        """Двигает астероид и вращает его вокруг центра."""
        self.position += self.velocity * delta_time
        wrap_position(self.position)
        self.angle = (self.angle + self.spin * delta_time) % 360

    def draw(self, surface: pygame.Surface) -> None:
        """Рисует каменистый контур астероида."""
        points = []
        for index, distance in enumerate(self.vertices):
            angle = self.angle + index * 360 / len(self.vertices)
            point = pygame.Vector2(distance, 0).rotate(angle)
            points.append(self.position + point)

        pygame.draw.polygon(surface, (105, 113, 132), points)
        pygame.draw.polygon(surface, (185, 195, 215), points, 2)


class Bullet:
    """Ракета, летящая с постоянной скоростью ограниченное время."""

    def __init__(self, position: pygame.Vector2, angle: float) -> None:
        """Создаёт ракету у носа корабля."""
        direction = pygame.Vector2(1, 0).rotate(angle)
        self.position = position + direction * (settings.SHIP_RADIUS + 4)
        self.velocity = direction * settings.BULLET_SPEED
        self.lifetime = settings.BULLET_LIFETIME

    @property
    def radius(self) -> int:
        """Возвращает радиус столкновения ракеты."""
        return settings.BULLET_RADIUS

    def update(self, delta_time: float) -> None:
        """Двигает ракету, переносит через край и уменьшает время жизни."""
        self.position += self.velocity * delta_time
        wrap_position(self.position)
        self.lifetime -= delta_time

    def draw(self, surface: pygame.Surface) -> None:
        """Рисует яркую точку ракеты."""
        pygame.draw.circle(
            surface,
            (255, 238, 135),
            (round(self.position.x), round(self.position.y)),
            self.radius,
        )


class Explosion:
    """Короткая анимация разлетающихся искр."""

    def __init__(self, position: pygame.Vector2, radius: int) -> None:
        """Создаёт набор искр вокруг места столкновения."""
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.age = 0.0
        self.duration = settings.EXPLOSION_DURATION
        self.sparks = [
            (
                pygame.Vector2(1, 0).rotate(random.uniform(0, 360)),
                random.uniform(radius * 1.2, radius * 2.8),
            )
            for _ in range(12)
        ]

    @property
    def finished(self) -> bool:
        """Показывает, завершилась ли анимация взрыва."""
        return self.age >= self.duration

    def update(self, delta_time: float) -> None:
        """Продвигает анимацию взрыва."""
        self.age += delta_time

    def draw(self, surface: pygame.Surface) -> None:
        """Рисует расширяющиеся искры взрыва."""
        progress = min(self.age / self.duration, 1)
        for direction, distance in self.sparks:
            position = self.position + direction * distance * progress
            color = (255, int(220 * (1 - progress)), 45)
            pygame.draw.circle(
                surface,
                color,
                (round(position.x), round(position.y)),
                max(1, round(4 * (1 - progress))),
            )
