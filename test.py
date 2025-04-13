import pygame
import sys
import random
import os
import json
from typing import List

# Инициализация
pygame.init()
pygame.mixer.init()

# Настройки
WIDTH, HEIGHT = 1240, 768
FPS = 60

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (100, 100, 100)
PURPLE = (128, 0, 128)
DARK_BLUE = (0, 0, 100)
YELLOW = (255, 255, 0)

# Шрифты
font_small = pygame.font.Font(None, 36)
font_medium = pygame.font.Font(None, 48)
font_large = pygame.font.Font(None, 72)

# Звуки (глобальная загрузка)
HACK_SOUND = None
JUMP_SOUND = None
DAMAGE_SOUND = None
try:
    HACK_SOUND = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'hack.wav'))
    JUMP_SOUND = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'jump.wav'))
    DAMAGE_SOUND = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'damage.wav'))
except:
    print("Не удалось загрузить некоторые звуки")

def load_image(name, colorkey=None, scale=1):
    """Загрузка изображения с обработкой прозрачности и масштабированием"""
    fullname = os.path.join('assets', 'images', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as e:
        print(f"Не могу загрузить изображение: {fullname}")
        print(f"Ошибка: {e}")
        image = pygame.Surface((50, 50))
        image.fill(RED)
    
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    
    if scale != 1:
        size = image.get_size()
        image = pygame.transform.scale(image, (int(size[0] * scale), int(size[1] * scale)))
    
    return image

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=10)
        
        text_surf = font_medium.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

class Player:
    def __init__(self):
        self.idle_img = load_image('player.png', colorkey=-1, scale=0.8)
        self.rect = self.idle_img.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.speed = 7
        self.jump_power = 18
        self.velocity_y = 0
        self.on_ground = False
        self.facing_right = True
        self.hacking = False
        self.target_drone = None
        self.fish_count = 0
        self.skins = ["default"]
        self.current_skin = "default"
        self.upgrades = {
            "speed": 0,
            "jump": 0,
            "double_jump": 0
        }
        self.health = 100
        self.max_health = 100
        self.invincible = False
        self.invincible_timer = 0
        self.jumps_left = 1
        self.platform_rects = []
    
    def update(self, platforms: List[pygame.Rect]):
        # Обновляем таймер неуязвимости
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False
        
        # Гравитация
        self.velocity_y += 0.8
        self.rect.y += self.velocity_y
        
        # Обновляем список rect'ов платформ для оптимизации
        self.platform_rects = [p.rect for p in platforms] if hasattr(platforms[0], 'rect') else platforms
        
        # Проверка коллизий с оптимизацией
        hits = []
        for platform in platforms:
            if self.rect.colliderect(platform.rect if hasattr(platform, 'rect') else platform):
                hits.append(platform)
        
        self.on_ground = False
        for platform in hits:
            platform_rect = platform.rect if hasattr(platform, 'rect') else platform
            if self.velocity_y > 0 and abs(self.rect.bottom - platform_rect.top) <= 10:
                self.rect.bottom = platform_rect.top
                self.on_ground = True
                self.velocity_y = 0
                self.jumps_left = 1 + self.upgrades["double_jump"]
                break
        
        # Невидимые стены
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
    
    def take_damage(self, amount):
        if not self.invincible:
            self.health -= amount
            self.invincible = True
            self.invincible_timer = 60  # 1 секунда неуязвимости
            if DAMAGE_SOUND:
                DAMAGE_SOUND.play()
            return True
        return False
    
    def draw(self, surface):
        img = self.idle_img
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
        
        # Мигание при неуязвимости
        if not self.invincible or pygame.time.get_ticks() % 200 < 100:
            surface.blit(img, self.rect)
        
        # Полоска здоровья
        health_width = 50
        health_height = 5
        health_x = self.rect.x + (self.rect.width - health_width) // 2
        health_y = self.rect.y - 10
        
        # Фон полоски
        pygame.draw.rect(surface, RED, (health_x, health_y, health_width, health_height))
        # Текущее здоровье
        current_width = (self.health / self.max_health) * health_width
        pygame.draw.rect(surface, GREEN, (health_x, health_y, current_width, health_height))

class Drone:
    def __init__(self, x, y):
        self.image = load_image('drone.png', colorkey=-1, scale=0.4)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = random.uniform(1.5, 3.5)
        self.has_fish = random.random() < 0.3
        self.damage = 10
    
    def update(self):
        self.rect.x -= self.speed
        if self.rect.right < 0:
            return True
        return False
    
    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.has_fish:
            fish_ind = pygame.Surface((10, 10))
            fish_ind.fill(GREEN)
            surface.blit(fish_ind, (self.rect.centerx - 5, self.rect.top - 15))

class FishReward:
    def __init__(self, x, y):
        self.image = load_image('fish.png', colorkey=-1, scale=0.5)
        self.rect = self.image.get_rect(center=(x, y))
        self.lifetime = 180
        self.blink_timer = 0
    
    def update(self):
        self.lifetime -= 1
        self.blink_timer = (self.blink_timer + 1) % 10
        return self.lifetime <= 0
    
    def draw(self, surface):
        # Мерцание в последние 60 кадров
        if self.lifetime > 60 or self.blink_timer < 5:
            surface.blit(self.image, self.rect)

class HackingGame:
    def __init__(self, drone):
        self.drone = drone
        self.code = str(random.randint(1000, 9999))
        self.input = ""
        self.font = font_medium
        self.active = True
        self.background = pygame.Surface((500, 250))
        self.background.fill((30, 30, 50))
    
    def draw(self, surface):
        surface.blit(self.background, (WIDTH//2-250, HEIGHT//2-125))
        
        texts = [
            f"Взлом: {len(self.input)*25}%",
            f"Код: {self.code}",
            f"Ввод: {self.input}",
            "[ESC] - Отмена"
        ]
        
        for i, text in enumerate(texts):
            text_surf = self.font.render(text, True, WHITE)
            surface.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 
                                  HEIGHT//2 - 100 + i*50))
    
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
            elif event.key == pygame.K_RETURN:
                if self.input == self.code:
                    if HACK_SOUND:
                        HACK_SOUND.play()
                    return "success"
                self.input = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input = self.input[:-1]
            elif event.unicode.isdigit() and len(self.input) < 4:
                self.input += event.unicode

class Shop:
    def __init__(self, player):
        self.player = player
        self.active = False
        self.items = [
            {"name": "Ускорение", "cost": 5, "type": "speed", "level": 0, "max_level": 3, "effect": "+2 к скорости"},
            {"name": "Прыжок", "cost": 5, "type": "jump", "level": 0, "max_level": 3, "effect": "+3 к прыжку"},
            {"name": "Двойной прыжок", "cost": 10, "type": "double_jump", "level": 0, "max_level": 1, "effect": "Позволяет прыгать в воздухе"}
        ]
        self.buttons = []
        for i, item in enumerate(self.items):
            self.buttons.append(Button(WIDTH//2 - 150, 200 + i*80, 300, 50, 
                                     f"{item['name']} - {item['cost']} рыб", 
                                     PURPLE, BLUE))
    
    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        
        title = font_large.render("МАГАЗИН", True, WHITE)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        fish_text = font_medium.render(f"Рыб: {self.player.fish_count}", True, WHITE)
        surface.blit(fish_text, (WIDTH//2 - fish_text.get_width()//2, 120))
        
        back_button = Button(WIDTH//2 - 100, HEIGHT - 100, 200, 50, "Назад", RED, PURPLE)
        back_button.check_hover(pygame.mouse.get_pos())
        back_button.draw(surface)
        
        for i, (button, item) in enumerate(zip(self.buttons, self.items)):
            button.draw(surface)
            level_text = font_small.render(f"Ур. {item['level']}/{item['max_level']}", True, WHITE)
            effect_text = font_small.render(item["effect"], True, YELLOW)
            surface.blit(level_text, (WIDTH//2 + 160, 215 + i*80))
            surface.blit(effect_text, (WIDTH//2 - 140, 245 + i*80))
        
        return back_button
    
    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()
        back_button = self.draw(pygame.display.get_surface())
        
        if back_button.is_clicked(mouse_pos, event):
            self.active = False
        
        for button, item in zip(self.buttons, self.items):
            button.check_hover(mouse_pos)
            
            if button.is_clicked(mouse_pos, event):
                if (self.player.fish_count >= item["cost"] and 
                    item["level"] < item["max_level"]):
                    
                    self.player.fish_count -= item["cost"]
                    item["level"] += 1
                    item["cost"] = int(item["cost"] * 1.5)  # Увеличиваем стоимость
                    
                    if item["type"] == "speed":
                        self.player.speed += 2
                    elif item["type"] == "jump":
                        self.player.jump_power += 3
                    elif item["type"] == "double_jump":
                        self.player.upgrades["double_jump"] = 1
                        self.player.jumps_left = 2

class GameMenu:
    def __init__(self, player):
        self.active = False
        self.player = player
        self.buttons = [
            Button(WIDTH//2 - 150, HEIGHT//2 - 60, 300, 50, "Продолжить", GREEN, BLUE),
            Button(WIDTH//2 - 150, HEIGHT//2 + 20, 300, 50, "Магазин", PURPLE, DARK_BLUE),
            Button(WIDTH//2 - 150, HEIGHT//2 + 100, 300, 50, "Выйти в меню", RED, PURPLE)
        ]
    
    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        
        title = font_large.render("ПАУЗА", True, WHITE)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
        
        fish_text = font_medium.render(f"Рыб: {self.player.fish_count}", True, WHITE)
        surface.blit(fish_text, (WIDTH//2 - fish_text.get_width()//2, HEIGHT//4 + 100))
        
        for button in self.buttons:
            button.draw(surface)
    
    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)
        
        if self.buttons[0].is_clicked(mouse_pos, event):
            self.active = False
            return "continue"
        elif self.buttons[1].is_clicked(mouse_pos, event):
            return "shop"
        elif self.buttons[2].is_clicked(mouse_pos, event):
            return "main_menu"
        
        return None

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(GRAY)
        self.rect = self.image.get_rect(topleft=(x, y))

def generate_platforms():
    platforms = []
    # Пол
    platforms.append(Platform(0, HEIGHT-40, WIDTH, 40))
    
    for i in range(5):
        while True:
            width = random.randint(150, 300)
            height = 20
            x = random.randint(50, WIDTH - width - 50)
            y = random.randint(HEIGHT//2, HEIGHT - 100)
            
            new_platform = Platform(x, y, width, height)
            
            intersects = False
            for platform in platforms:
                if new_platform.rect.colliderect(platform.rect):
                    intersects = True
                    break
            
            if not intersects:
                platforms.append(new_platform)
                break
    
    return platforms

def show_main_menu():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("КиберБарсик 2045 - Меню")
    
    title = font_large.render("КИБЕРБАРСИК 2045", True, WHITE)
    start_button = Button(WIDTH//2 - 100, HEIGHT//2, 200, 50, "Начать игру", GREEN, BLUE)
    exit_button = Button(WIDTH//2 - 100, HEIGHT//2 + 70, 200, 50, "Выход", RED, PURPLE)
    
    # Загрузка сохранения
    try:
        with open('save.json', 'r') as f:
            save_data = json.load(f)
        save_text = font_medium.render(f"Рекорд: {save_data.get('fish', 0)} рыб", True, YELLOW)
    except:
        save_text = font_medium.render("Рекорд: нет данных", True, YELLOW)
    
    running = True
    while running:
        screen.fill(BLACK)
        
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if start_button.is_clicked(mouse_pos, event):
                return "start"
            if exit_button.is_clicked(mouse_pos, event):
                pygame.quit()
                sys.exit()
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
        screen.blit(save_text, (WIDTH//2 - save_text.get_width()//2, HEIGHT//4 + 100))
        start_button.draw(screen)
        exit_button.draw(screen)
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def draw_fish_counter(surface, count):
    counter_bg = pygame.Rect(20, 20, 200, 60)
    pygame.draw.rect(surface, (30, 30, 50, 150), counter_bg, border_radius=10)
    pygame.draw.rect(surface, WHITE, counter_bg, 2, border_radius=10)
    
    fish_icon = load_image('fish.png', colorkey=-1, scale=0.4)
    surface.blit(fish_icon, (30, 30))
    
    count_text = font_medium.render(f"x {count}", True, WHITE)
    surface.blit(count_text, (80, 35))

def draw_controls(surface):
    controls_text = font_small.render("WASD - движение | H - взлом | ESC - меню", True, WHITE)
    surface.blit(controls_text, (10, HEIGHT - 30))

def save_game(player):
    data = {
        "fish": player.fish_count,
        "upgrades": player.upgrades,
        "health": player.health
    }
    with open('save.json', 'w') as f:
        json.dump(data, f)

def load_game(player):
    try:
        with open('save.json', 'r') as f:
            data = json.load(f)
            player.fish_count = data.get("fish", 0)
            player.upgrades = data.get("upgrades", {"speed": 0, "jump": 0, "double_jump": 0})
            player.health = data.get("health", 100)
            
            # Применяем улучшения
            player.speed = 7 + 2 * player.upgrades["speed"]
            player.jump_power = 18 + 3 * player.upgrades["jump"]
            player.jumps_left = 1 + player.upgrades["double_jump"]
    except:
        print("Не удалось загрузить сохранение")

def main_game():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("КиберБарсик 2045")
    clock = pygame.time.Clock()
    
    background = load_image('background.jpg')
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))
    platform_img = load_image('platform.png')
    
    player = Player()
    load_game(player)  # Загружаем сохранение
    
    platforms = generate_platforms()
    drones = []
    fishes = []
    hacking_game = None
    shop = Shop(player)
    game_menu = GameMenu(player)
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game(player)
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and not hacking_game:
                    game_menu.active = not game_menu.active
                    shop.active = False
                
                if not game_menu.active and not shop.active:
                    if event.key == pygame.K_w and (player.on_ground or player.jumps_left > 0):
                        player.velocity_y = -player.jump_power
                        if not player.on_ground:
                            player.jumps_left -= 1
                        if JUMP_SOUND:
                            JUMP_SOUND.play()
                    if event.key == pygame.K_h and player.target_drone and not player.hacking:
                        hacking_game = HackingGame(player.target_drone)
                        player.hacking = True
            
            if shop.active:
                shop.handle_event(event)
            elif game_menu.active:
                result = game_menu.handle_event(event)
                if result == "continue":
                    game_menu.active = False
                elif result == "shop":
                    game_menu.active = False
                    shop.active = True
                elif result == "main_menu":
                    save_game(player)
                    return "menu"
            elif hacking_game:
                result = hacking_game.handle_event(event)
                if result == "success":
                    if hacking_game.drone.has_fish:
                        fishes.append(FishReward(hacking_game.drone.rect.centerx, 
                                               hacking_game.drone.rect.centery))
                    drones.remove(hacking_game.drone)
                    hacking_game = None
                    player.hacking = False
        
        if not shop.active and not game_menu.active and not player.hacking:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]: 
                player.rect.x -= player.speed
                player.facing_right = False
            if keys[pygame.K_d]: 
                player.rect.x += player.speed
                player.facing_right = True
        
        player.update(platforms)
        
        # Спавн дронов
        if random.random() < 0.01 and len(drones) < 2 + player.upgrades["speed"]:
            drones.append(Drone(WIDTH + 100, random.randint(100, HEIGHT-200)))
        
        # Обновление дронов и проверка урона
        player.target_drone = None
        for drone in drones[:]:
            if drone.update():
                drones.remove(drone)
            elif player.rect.colliderect(drone.rect) and not player.hacking:
                if not player.invincible:
                    player.take_damage(drone.damage)
                player.target_drone = drone
        
        # Обновление рыб
        for fish in fishes[:]:
            if fish.update():
                fishes.remove(fish)
            elif player.rect.colliderect(fish.rect):
                player.fish_count += 1
                fishes.remove(fish)
        
        # Проверка смерти
        if player.health <= 0:
            save_game(player)
            return "menu"
        
        # Отрисовка
        screen.blit(background, (0, 0))
        
        for platform in platforms:
            screen.blit(platform.image, platform.rect)
        
        for drone in drones:
            drone.draw(screen)
        
        for fish in fishes:
            fish.draw(screen)
        
        player.draw(screen)
        
        if hacking_game:
            hacking_game.draw(screen)
        
        draw_fish_counter(screen, player.fish_count)
        draw_controls(screen)
        
        if shop.active:
            shop.draw(screen)
        
        if game_menu.active:
            game_menu.draw(screen)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    return "exit"

if __name__ == "__main__":
    pygame.mixer.music.load(os.path.join('assets', 'sounds', 'background.mp3'))
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
    
    game_state = "menu"
    
    while True:
        if game_state == "menu":
            game_state = show_main_menu()
        elif game_state == "start":
            game_state = main_game()
        elif game_state == "exit":
            pygame.quit()
            sys.exit()