from __future__ import annotations

import os
import math
import random
import sys
import pygame

TITLE = "Doodle Jump"
WIDTH, HEIGHT = 400, 600
FPS = 60

GRAVITY = 0.4
JUMP_FORCE = -13.0
SPRING_FORCE = -20.0
PLAYER_SPEED = 5

PLATFORM_W = 68
PLATFORM_H = 14
PLATFORM_MIN_GAP = 60
PLATFORM_MAX_GAP = 110

C_BG = (240, 248, 255)
C_SKY_TOP = (135, 206, 235)
C_SKY_BOT = (240, 248, 255)
C_WHITE = (255, 255, 255)
C_BLACK = (10, 10, 10)
C_SCORE = (50, 50, 80)
C_SHADOW = (180, 180, 200)

C_PLAT_GREEN = (72, 199, 100)
C_PLAT_EDGE_G = (40, 150, 65)
C_PLAT_MOVE = (90, 160, 230)
C_PLAT_EDGE_M = (50, 110, 190)
C_PLAT_BREAK = (210, 100, 60)
C_PLAT_EDGE_B = (170, 60, 30)
C_PLAT_SPRING = (230, 210, 50)
C_PLAT_EDGE_S = (180, 160, 20)
C_SPRING_COIL = (200, 180, 40)
C_SPRING_TOP = (255, 80, 80)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

class SoundManager:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = True
        self._load_all()

    def _load_all(self) -> None:
        files = {
            "jump": "jump.wav",
            "break": "break.wav",
            "spring": "spring.wav",
            "fall": "fall.wav",
        }
        for key, fname in files.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                try:
                    self._sounds[key] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass

    def play(self, name: str, volume: float = 1.0) -> None:
        if not self._enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.set_volume(volume)
            snd.play()

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled

class AssetManager:
    def __init__(self) -> None:
        self._fonts: dict[int, pygame.font.Font] = {}

    def font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._fonts[size]

class Camera:
    def __init__(self) -> None:
        self.offset_y: float = 0.0
        self.highest_y: float = HEIGHT // 2

    def update(self, player_y: float) -> None:
        if player_y < self.highest_y:
            diff = self.highest_y - player_y
            self.offset_y += diff
            self.highest_y = player_y

    def apply(self, y: float) -> float:
        return y + self.offset_y

    def reset(self) -> None:
        self.offset_y = 0.0
        self.highest_y = HEIGHT // 2

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "size", "life", "max_life")

    def __init__(self, x: float, y: float, color: tuple) -> None:
        self.x, self.y = x, y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2
        self.color = color
        self.size = random.randint(3, 7)
        self.max_life = random.randint(20, 40)
        self.life = self.max_life

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        alpha = self.life / self.max_life
        r, g, b = self.color
        color = (int(r * alpha), int(g * alpha), int(b * alpha))
        sz = max(1, int(self.size * alpha))
        screen_y = cam.apply(self.y)
        pygame.draw.circle(surface, color, (int(self.x), int(screen_y)), sz)

class ParticleSystem:
    def __init__(self) -> None:
        self._pool: list[Particle] = []

    def emit(self, x: float, y: float, color: tuple, count: int = 12) -> None:
        for _ in range(count):
            self._pool.append(Particle(x, y, color))

    def update(self) -> None:
        self._pool = [p for p in self._pool if p.alive]
        for p in self._pool:
            p.update()

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        for p in self._pool:
            p.draw(surface, cam)

class Platform:
    COLOR_FILL = C_PLAT_GREEN
    COLOR_EDGE = C_PLAT_EDGE_G
    KIND = "normal"

    def __init__(self, x: float, y: float, w: int = PLATFORM_W, h: int = PLATFORM_H) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.alive = True

    def update(self) -> None:
        pass

    def on_land(self, player: "Player", sounds: SoundManager, particles: ParticleSystem) -> None:
        sounds.play("jump", 0.9)

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        screen_y = int(cam.apply(self.rect.y))
        r = pygame.Rect(self.rect.x, screen_y, self.rect.w, self.rect.h)
        shadow = pygame.Rect(r.x + 3, r.y + 5, r.w, r.h)
        pygame.draw.rect(surface, C_SHADOW, shadow, border_radius=7)
        pygame.draw.rect(surface, self.COLOR_FILL, r, border_radius=7)
        edge = pygame.Rect(r.x, r.y, r.w, 5)
        pygame.draw.rect(surface, self.COLOR_EDGE, edge, border_radius=7)
        shine = pygame.Rect(r.x + 6, r.y + 2, r.w // 3, 3)
        pygame.draw.rect(surface, C_WHITE, shine, border_radius=2)

class MovingPlatform(Platform):
    COLOR_FILL = C_PLAT_MOVE
    COLOR_EDGE = C_PLAT_EDGE_M
    KIND = "moving"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self._speed = random.choice([-2, -1.5, 1.5, 2])
        self._left = max(0, x - random.randint(50, 100))
        self._right = min(WIDTH - PLATFORM_W, x + random.randint(50, 100))

    def update(self) -> None:
        self.rect.x += self._speed
        if self.rect.x <= self._left or self.rect.x + self.rect.w >= self._right + self.rect.w:
            self._speed *= -1

class BreakablePlatform(Platform):
    COLOR_FILL = C_PLAT_BREAK
    COLOR_EDGE = C_PLAT_EDGE_B
    KIND = "breakable"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self._broken = False
        self._break_timer = 0

    def on_land(self, player: "Player", sounds: SoundManager, particles: ParticleSystem) -> None:
        if not self._broken:
            self._broken = True
            sounds.play("break", 1.0)
            cx, cy = self.rect.centerx, self.rect.centery
            particles.emit(cx, cy, C_PLAT_BREAK, 18)
            particles.emit(cx, cy, C_PLAT_EDGE_B, 10)

    def update(self) -> None:
        if self._broken:
            self._break_timer += 1
            self.rect.y += self._break_timer // 3
            if self._break_timer > 40:
                self.alive = False

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        if self._broken:
            screen_y = int(cam.apply(self.rect.y))
            r = pygame.Rect(self.rect.x, screen_y, self.rect.w, self.rect.h)
            half_w = r.w // 2
            left = pygame.Rect(r.x - self._break_timer, r.y + self._break_timer, half_w - 2, r.h)
            right = pygame.Rect(r.x + half_w + self._break_timer, r.y + self._break_timer, half_w - 2, r.h)
            pygame.draw.rect(surface, self.COLOR_FILL, left, border_radius=5)
            pygame.draw.rect(surface, self.COLOR_FILL, right, border_radius=5)
        else:
            super().draw(surface, cam)
            screen_y = int(cam.apply(self.rect.y))
            cx, cy = self.rect.x + self.rect.w // 2, screen_y + self.rect.h // 2
            pygame.draw.line(surface, C_WHITE, (cx-8, cy-4), (cx+8, cy+4), 2)
            pygame.draw.line(surface, C_WHITE, (cx+8, cy-4), (cx-8, cy+4), 2)

class SpringPlatform(Platform):
    COLOR_FILL = C_PLAT_SPRING
    COLOR_EDGE = C_PLAT_EDGE_S
    KIND = "spring"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self._compressed = False
        self._comp_timer = 0

    def on_land(self, player: "Player", sounds: SoundManager, particles: ParticleSystem) -> None:
        self._compressed = True
        self._comp_timer = 0
        player.velocity_y = SPRING_FORCE
        sounds.play("spring", 1.0)
        particles.emit(self.rect.centerx, self.rect.centery, C_PLAT_SPRING, 10)

    def update(self) -> None:
        if self._compressed:
            self._comp_timer += 1
            if self._comp_timer > 20:
                self._compressed = False

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        super().draw(surface, cam)
        screen_y = int(cam.apply(self.rect.y))
        cx = self.rect.x + self.rect.w // 2
        coil_h = 10 if not self._compressed else 5
        for i in range(3):
            yy = screen_y - (i + 1) * (coil_h // 3 + 2)
            pygame.draw.ellipse(surface, C_SPRING_COIL, (cx - 7, yy, 14, 5))
        top_y = screen_y - coil_h - 5
        pygame.draw.circle(surface, C_SPRING_TOP, (cx, top_y), 5)

class Player:
    W, H = 38, 44

    def __init__(self) -> None:
        self.x: float = WIDTH // 2 - self.W // 2
        self.y: float = HEIGHT - 150.0
        self.velocity_y: float = JUMP_FORCE
        self.velocity_x: float = 0.0
        self.facing_right: bool = True
        self._alive: bool = True
        self._jump_anim: int = 0
        self._blink: int = 0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def alive(self) -> bool:
        return self._alive

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        self.velocity_x = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity_x = PLAYER_SPEED
            self.facing_right = True

    def update(self) -> None:
        self.velocity_y += GRAVITY
        self.y += self.velocity_y
        self.x += self.velocity_x
        if self.x + self.W < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = -self.W
        if self._jump_anim > 0:
            self._jump_anim -= 1

    def jump(self, force: float = JUMP_FORCE) -> None:
        self.velocity_y = force
        self._jump_anim = 10

    def kill(self) -> None:
        self._alive = False

    def check_fall(self, cam: Camera) -> None:
        if cam.apply(self.y) > HEIGHT + 50:
            self._alive = False

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        screen_y = int(cam.apply(self.y))
        cx = int(self.x + self.W // 2)
        body_y = screen_y
        squish = 1.0
        if self._jump_anim > 0:
            squish = 1.0 + 0.15 * (self._jump_anim / 10)
        body_h, body_w = int(self.H * squish), int(self.W / squish)
        body_x = cx - body_w // 2
        body_rect = pygame.Rect(body_x, body_y - (body_h - self.H), body_w, body_h)
        pygame.draw.rect(surface, (100, 200, 80), body_rect, border_radius=10)
        pygame.draw.rect(surface, (60, 140, 50), body_rect, 2, border_radius=10)
        eye_y = body_y - (body_h - self.H) + body_h // 3
        eye_x = body_x + body_w * 2 // 3 if self.facing_right else body_x + body_w // 3
        pygame.draw.circle(surface, C_WHITE, (eye_x, eye_y), 7)
        pygame.draw.circle(surface, C_BLACK, (eye_x + (2 if self.facing_right else -2), eye_y), 4)
        pygame.draw.circle(surface, C_WHITE, (eye_x + (3 if self.facing_right else -3), eye_y - 1), 1)
        mouth_y = eye_y + 9
        if self.velocity_y < 0:
            pygame.draw.arc(surface, C_BLACK, (cx - 7, mouth_y - 3, 14, 8), math.pi, 0, 2)
        else:
            pygame.draw.ellipse(surface, C_BLACK, (cx - 4, mouth_y, 8, 6))
        pygame.draw.line(surface, (60, 140, 50), (cx, body_y - (body_h - self.H)), (cx + (8 if self.facing_right else -8), body_y - (body_h - self.H) - 12), 3)
        pygame.draw.circle(surface, (255, 80, 80), (cx + (8 if self.facing_right else -8), body_y - (body_h - self.H) - 12), 4)

class PlatformFactory:
    WEIGHTS = {"normal": 60, "moving": 20, "breakable": 12, "spring": 8}

    @classmethod
    def create(cls, x: float, y: float, score: int) -> Platform:
        pool = []
        for kind, w in cls.WEIGHTS.items():
            if kind == "normal":
                actual_w = max(20, w - score // 200)
            elif kind == "breakable":
                actual_w = min(30, w + score // 300)
            else:
                actual_w = w
            pool.extend([kind] * actual_w)
        choice = random.choice(pool)
        if choice == "moving": return MovingPlatform(x, y)
        if choice == "breakable": return BreakablePlatform(x, y)
        if choice == "spring": return SpringPlatform(x, y)
        return Platform(x, y)

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        self._screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self._clock = pygame.time.Clock()
        self._assets, self._sounds = AssetManager(), SoundManager()
        self._running, self._state = True, "menu"
        self._player, self._camera, self._platforms, self._particles = None, None, [], None
        self._score, self._best = 0, 0
        self._bg_surf = self._build_bg()

    def _new_game(self) -> None:
        self._player, self._camera, self._particles = Player(), Camera(), ParticleSystem()
        self._score, self._platforms = 0, []
        self._generate_initial_platforms()
        self._state = "playing"

    def _generate_initial_platforms(self) -> None:
        self._platforms.append(Platform(WIDTH // 2 - PLATFORM_W // 2, HEIGHT - 100))
        y = HEIGHT - 100
        for _ in range(14):
            gap = random.randint(PLATFORM_MIN_GAP, PLATFORM_MAX_GAP)
            y -= gap
            x = random.randint(10, WIDTH - PLATFORM_W - 10)
            self._platforms.append(PlatformFactory.create(x, y, 0))

    def _build_bg(self) -> pygame.Surface:
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(C_SKY_TOP[0] * (1 - t) + C_SKY_BOT[0] * t)
            g = int(C_SKY_TOP[1] * (1 - t) + C_SKY_BOT[1] * t)
            b = int(C_SKY_TOP[2] * (1 - t) + C_SKY_BOT[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))
        return surf

    def run(self) -> None:
        while self._running:
            self._handle_events()
            if self._state == "playing":
                self._update()
                self._draw_game()
            elif self._state == "menu": self._draw_menu()
            elif self._state == "dead": self._draw_dead()
            elif self._state == "paused": self._draw_paused()
            pygame.display.flip()
            self._clock.tick(FPS)
        pygame.quit()
        sys.exit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._state == "playing": self._state = "paused"
                    elif self._state == "paused": self._state = "playing"
                    else: self._running = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self._state in ("menu", "dead"): self._new_game()
                    elif self._state == "paused": self._state = "playing"
                elif event.key == pygame.K_m:
                    self._sounds.toggle()

    def _update(self) -> None:
        self._player.handle_input()
        self._player.update()
        self._camera.update(self._player.y)
        self._player.check_fall(self._camera)
        if self._player.velocity_y > 0:
            pr = self._player.rect
            for plat in self._platforms:
                if not plat.alive: continue
                sr = pygame.Rect(plat.rect.x, plat.rect.y, plat.rect.w, plat.rect.h)
                if (pr.bottom >= sr.top and pr.bottom <= sr.top + 18 and
                    pr.right > sr.left and pr.left < sr.right):
                    if plat.KIND != "breakable" and not getattr(plat, "_broken", False):
                        self._player.y = sr.top - self._player.H
                        self._player.velocity_y = JUMP_FORCE
                    plat.on_land(self._player, self._sounds, self._particles)
        for plat in self._platforms: plat.update()
        self._platforms = [p for p in self._platforms if p.alive]
        self._spawn_platforms()
        self._platforms = [p for p in self._platforms if self._camera.apply(p.rect.y) < HEIGHT + 50]
        self._particles.update()
        new_score = int(self._camera.offset_y // 5)
        if new_score > self._score: self._score = new_score
        if self._score > self._best: self._best = self._score
        if not self._player.alive:
            self._sounds.play("fall", 0.8)
            self._state = "dead"

    def _spawn_platforms(self) -> None:
        if not self._platforms: return
        top_y = min(p.rect.y for p in self._platforms)
        while top_y > -self._camera.offset_y - HEIGHT // 2:
            gap = random.randint(PLATFORM_MIN_GAP, PLATFORM_MAX_GAP)
            top_y -= gap
            x = random.randint(10, WIDTH - PLATFORM_W - 10)
            self._platforms.append(PlatformFactory.create(x, top_y, self._score))

    def _draw_game(self) -> None:
        self._screen.blit(self._bg_surf, (0, 0))
        for plat in self._platforms: plat.draw(self._screen, self._camera)
        self._particles.draw(self._screen, self._camera)
        self._player.draw(self._screen, self._camera)
        self._draw_hud()

    def _draw_hud(self) -> None:
        f_big, f_small = self._assets.font(26), self._assets.font(16)
        self._screen.blit(f_big.render(f"Score: {self._score}", True, C_SCORE), (10, 10))
        self._screen.blit(f_small.render(f"Best: {self._best}", True, C_SCORE), (10, 40))
        hint = f_small.render("M – звук  |  ESC – пауза", True, (150, 150, 170))
        self._screen.blit(hint, (WIDTH - hint.get_width() - 8, 10))
        legend = [("■ Звичайна", C_PLAT_GREEN), ("■ Рухома", C_PLAT_MOVE), ("■ Ламається", C_PLAT_BREAK), ("■ Пружина", C_PLAT_SPRING)]
        f_leg = self._assets.font(13)
        for i, (text, color) in enumerate(legend):
            self._screen.blit(f_leg.render(text, True, color), (10, HEIGHT - 70 + i * 17))

    def _draw_menu(self) -> None:
        self._screen.blit(self._bg_surf, (0, 0))
        f1, f2, f3 = self._assets.font(52), self._assets.font(22), self._assets.font(17)
        t_surf = f1.render("DOODLE JUMP", True, (60, 120, 200))
        s_surf = f2.render("ENTER або SPACE — старт", True, C_SCORE)
        p_surf = f3.render("← → або A/D  |  M – звук", True, (120, 120, 160))
        self._screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, 180))
        self._screen.blit(s_surf, (WIDTH // 2 - s_surf.get_width() // 2, 280))
        self._screen.blit(p_surf, (WIDTH // 2 - p_surf.get_width() // 2, 320))
        t = pygame.time.get_ticks() / 500
        ball_y = int(HEIGHT // 2 - 50 + math.sin(t) * 20)
        pygame.draw.circle(self._screen, (100, 200, 80), (WIDTH // 2, ball_y), 22)
        pygame.draw.circle(self._screen, C_WHITE, (WIDTH // 2 + 7, ball_y - 5), 7)
        pygame.draw.circle(self._screen, C_BLACK, (WIDTH // 2 + 9, ball_y - 5), 4)
        if self._best:
            b_surf = self._assets.font(18).render(f"Рекорд: {self._best}", True, (200, 150, 50))
            self._screen.blit(b_surf, (WIDTH // 2 - b_surf.get_width() // 2, 360))

    def _draw_dead(self) -> None:
        self._screen.blit(self._bg_surf, (0, 0))
        f1, f2, f3 = self._assets.font(46), self._assets.font(24), self._assets.font(20)
        g_surf = f1.render("GAME OVER", True, (200, 60, 60))
        sc_surf = f2.render(f"Рахунок: {self._score}", True, C_SCORE)
        b_surf = f3.render(f"Рекорд:  {self._best}", True, (200, 150, 50))
        r_surf = f2.render("ENTER — знову", True, (60, 120, 60))
        self._screen.blit(g_surf, (WIDTH // 2 - g_surf.get_width() // 2, 200))
        self._screen.blit(sc_surf, (WIDTH // 2 - sc_surf.get_width() // 2, 280))
        self._screen.blit(b_surf, (WIDTH // 2 - b_surf.get_width() // 2, 315))
        self._screen.blit(r_surf, (WIDTH // 2 - r_surf.get_width() // 2, 380))

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self._screen.blit(overlay, (0, 0))
        f1, f2 = self._assets.font(48), self._assets.font(22)
        p_surf, c_surf = f1.render("ПАУЗА", True, C_WHITE), f2.render("ENTER / ESC — продовжити", True, (200, 200, 220))
        self._screen.blit(p_surf, (WIDTH // 2 - p_surf.get_width() // 2, 240))
        self._screen.blit(c_surf, (WIDTH // 2 - c_surf.get_width() // 2, 310))

if __name__ == "__main__":
    game = Game()
    game.run()