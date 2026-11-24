"""Окно игры, заставка и главный цикл."""

import random
from typing import Optional

import pygame

import settings
from entities import (
    Asteroid,
    Bullet,
    Explosion,
    Ship,
    circles_collide,
)


class Game:
    """Создаёт окно и управляет игровым циклом."""

    def __init__(self) -> None:
        """Настраивает окно, фон и начальные показатели игры."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        pygame.display.set_caption("Астероиды")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("arial", 54, bold=True)
        self.button_font = pygame.font.SysFont("arial", 23, bold=True)
        self.hud_font = pygame.font.SysFont("arial", 25, bold=True)
        self.background = self._create_background()
        self.backdrop_asteroids = self._create_backdrop_asteroids()
        self.banner = pygame.Rect(
            settings.SCREEN_WIDTH // 2 - 220,
            settings.SCREEN_HEIGHT // 2 - 118,
            440,
            236,
        )
        self.running = True
        self.started = False
        self.ship: Optional[Ship] = None
        self.thrusting = False
        self.asteroids: list[Asteroid] = []
        self.bullets: list[Bullet] = []
        self.explosions: list[Explosion] = []
        self.asteroid_timer = 0.0
        self.game_over = False
        self.score = 0
        self.lives = settings.INITIAL_LIVES

    def run(self) -> None:
        """Запускает обработку событий, обновление и отрисовку."""
        try:
            while self.running:
                delta_time = min(self.clock.tick(settings.FPS) / 1000, 0.05)
                self._handle_events()
                self._update(delta_time)
                self._draw()
                pygame.display.flip()
        finally:
            pygame.quit()

    def _create_background(self) -> pygame.Surface:
        """Создаёт неподвижный фон со звёздами."""
        background = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        background.fill(settings.BACKGROUND_COLOR)
        for _ in range(150):
            position = (
                random.randrange(settings.SCREEN_WIDTH),
                random.randrange(settings.SCREEN_HEIGHT),
            )
            color = random.choice(
                (settings.STAR_COLOR, (110, 142, 205), (255, 215, 160))
            )
            pygame.draw.circle(
                background,
                color,
                position,
                random.choice((1, 1, 1, 2)),
            )
        return background

    def _create_backdrop_asteroids(
        self,
    ) -> list[tuple[float, float, pygame.Surface]]:
        """Создаёт полупрозрачные астероиды для движущегося фона."""
        asteroids = []
        for index in range(7):
            radius = random.randint(22, 52)
            size = radius * 2 + 8
            image = pygame.Surface(
                (size, size),
                pygame.SRCALPHA,
            )
            points = []
            for point_index in range(11):
                angle = point_index * 360 / 11
                distance = radius * random.uniform(0.75, 1.15)
                point = pygame.Vector2(distance, 0).rotate(angle)
                points.append(point + pygame.Vector2(size / 2, size / 2))
            pygame.draw.polygon(image, (105, 127, 165, 65), points)
            pygame.draw.polygon(image, (175, 195, 230, 70), points, 2)
            x = random.randrange(settings.SCREEN_WIDTH)
            y = random.randrange(settings.SCREEN_HEIGHT)
            asteroids.append((x, y, image))
        return asteroids

    def _handle_events(self) -> None:
        """Обрабатывает закрытие окна и щелчок по заставке."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and not self.started
                and self.banner.collidepoint(event.pos)
            ):
                self._start_game()
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_SPACE
                and self.started
                and self.ship is not None
            ):
                self.bullets.append(Bullet(self.ship.position, self.ship.angle))

    def _start_game(self) -> None:
        """Начинает игру или обнуляет результаты после поражения."""
        if self.game_over:
            self.score = 0
            self.lives = settings.INITIAL_LIVES
            self.game_over = False

        self.started = True
        self.ship = Ship()
        self.asteroids = []
        self.bullets = []
        self.explosions = []
        self.asteroid_timer = settings.ASTEROID_SPAWN_INTERVAL

    def _update(self, delta_time: float) -> None:
        """Перемещает динамический фон и обновляет корабль."""
        moved_asteroids = []
        for x, y, image in self.backdrop_asteroids:
            x -= 24 * delta_time
            if x < -image.get_width():
                x = settings.SCREEN_WIDTH
            moved_asteroids.append((x, y, image))
        self.backdrop_asteroids = moved_asteroids

        if self.started and self.ship is not None:
            keys = pygame.key.get_pressed()
            turn_direction = (
                int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
            )
            self.ship.rotate(turn_direction, delta_time)
            self.thrusting = bool(keys[pygame.K_UP])
            if self.thrusting:
                self.ship.accelerate(delta_time)
            self.ship.update(delta_time)

            self.asteroid_timer += delta_time
            if self.asteroid_timer >= settings.ASTEROID_SPAWN_INTERVAL:
                self.asteroid_timer -= settings.ASTEROID_SPAWN_INTERVAL
                position = (
                    random.randrange(settings.SCREEN_WIDTH),
                    random.randrange(settings.SCREEN_HEIGHT),
                )
                self.asteroids.append(Asteroid(position))

            for asteroid in self.asteroids:
                asteroid.update(delta_time)
            for bullet in self.bullets:
                bullet.update(delta_time)
            self.bullets = [
                bullet for bullet in self.bullets if bullet.lifetime > 0
            ]
            for explosion in self.explosions:
                explosion.update(delta_time)
            self.explosions = [
                explosion
                for explosion in self.explosions
                if not explosion.finished
            ]
            self._resolve_collisions()

    def _resolve_collisions(self) -> None:
        """Обрабатывает попадания ракет и столкновения с кораблём."""
        surviving_asteroids = list(self.asteroids)
        surviving_bullets = []
        for bullet in self.bullets:
            hit_asteroid = next(
                (
                    asteroid
                    for asteroid in surviving_asteroids
                    if circles_collide(
                        bullet.position,
                        bullet.radius,
                        asteroid.position,
                        asteroid.radius,
                    )
                ),
                None,
            )
            if hit_asteroid is None:
                surviving_bullets.append(bullet)
                continue

            surviving_asteroids.remove(hit_asteroid)
            self.explosions.append(
                Explosion(hit_asteroid.position, hit_asteroid.radius)
            )
            self.score += 1

        self.asteroids = surviving_asteroids
        self.bullets = surviving_bullets

        if self.ship is None or self.ship.invulnerability > 0:
            return

        hit_asteroid = next(
            (
                asteroid
                for asteroid in self.asteroids
                if circles_collide(
                    self.ship.position,
                    self.ship.radius,
                    asteroid.position,
                    asteroid.radius,
                )
            ),
            None,
        )
        if hit_asteroid is None:
            return

        self.asteroids.remove(hit_asteroid)
        self.explosions.append(
            Explosion(hit_asteroid.position, hit_asteroid.radius)
        )
        self.lives -= 1
        if self.lives == 0:
            self.game_over = True
            self.started = False
            self.ship = None
            self.asteroids.clear()
            self.bullets.clear()
            self.explosions.clear()
            return

        self.ship = Ship()
        self.ship.invulnerability = settings.SHIP_INVULNERABILITY

    def _draw(self) -> None:
        """Рисует фон, показатели, корабль и заставку."""
        self.screen.blit(self.background, (0, 0))
        for x, y, image in self.backdrop_asteroids:
            self.screen.blit(image, (round(x), round(y)))

        lives = self.hud_font.render(
            f"Жизни: {self.lives}",
            True,
            settings.HUD_COLOR,
        )
        score = self.hud_font.render(
            f"Очки: {self.score}",
            True,
            settings.HUD_COLOR,
        )
        self.screen.blit(lives, (24, 16))
        self.screen.blit(score, (settings.SCREEN_WIDTH - score.get_width() - 24, 16))

        for asteroid in self.asteroids:
            asteroid.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)
        for explosion in self.explosions:
            explosion.draw(self.screen)

        if self.started and self.ship is not None:
            self.ship.draw(self.screen, self.thrusting)
        else:
            self._draw_banner()

    def _draw_banner(self) -> None:
        """Рисует центральную кнопку начала игры."""
        panel = pygame.Surface(self.banner.size, pygame.SRCALPHA)
        panel.fill((20, 32, 75, 205))
        self.screen.blit(panel, self.banner.topleft)
        pygame.draw.rect(self.screen, settings.ACCENT_COLOR, self.banner, 3)

        if self.game_over:
            title = self.button_font.render(
                "ИГРА ОКОНЧЕНА",
                True,
                settings.TEXT_COLOR,
            )
            prompt_text = "ЩЁЛКНИ, ЧТОБЫ НАЧАТЬ ЗАНОВО"
        else:
            title = self.title_font.render(
                "АСТЕРОИДЫ",
                True,
                settings.TEXT_COLOR,
            )
            prompt_text = "ЩЁЛКНИ, ЧТОБЫ НАЧАТЬ"
        prompt = self.button_font.render(
            prompt_text,
            True,
            settings.TEXT_COLOR,
        )
        self.screen.blit(
            title,
            title.get_rect(center=(self.banner.centerx, self.banner.centery - 28)),
        )
        self.screen.blit(
            prompt,
            prompt.get_rect(center=(self.banner.centerx, self.banner.centery + 45)),
        )
