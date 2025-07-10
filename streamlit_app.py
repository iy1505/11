import streamlit as st
import time
import random
import pygame

# Pygameの初期化
pygame.init()

# ゲームの設定
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Streamlit Invaders')

# 色
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

# プレイヤーのクラス
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 30))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH // 2, HEIGHT - 30)

    def update(self, move_left, move_right):
        if move_left and self.rect.left > 0:
            self.rect.x -= 5
        if move_right and self.rect.right < WIDTH:
            self.rect.x += 5

# 弾のクラス
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 10))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        self.rect.y -= 10
        if self.rect.bottom < 0:
            self.kill()

# 敵のクラス
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 30))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self):
        self.rect.x += random.choice([-1, 1]) * 2
        if self.rect.right > WIDTH or self.rect.left < 0:
            self.rect.y += 20
            self.rect.x = random.randint(0, WIDTH - 40)

# ゲームのメイン処理
def game_loop():
    player = Player()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    for i in range(5):
        for j in range(3):
            enemy = Enemy(100 * i + 50, 50 * j + 50)
            enemies.add(enemy)

    all_sprites = pygame.sprite.Group(player, *enemies)

    move_left = False
    move_right = False
    shoot = False

    score = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                st.stop()

        # Streamlitのインタラクションでプレイヤーの動きを決定
        move_left = st.button('Move Left')
        move_right = st.button('Move Right')
        shoot = st.button('Shoot')

        player.update(move_left, move_right)

        # 弾の発射
        if shoot:
            bullet = Bullet(player.rect.centerx, player.rect.top)
            bullets.add(bullet)
            all_sprites.add(bullet)

        bullets.update()
        enemies.update()

        # 衝突判定
        for bullet in bullets:
            enemy_hit = pygame.sprite.spritecollide(bullet, enemies, True)
            if enemy_hit:
                score += 10
                bullet.kill()

        # 描画
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # スコア表示
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        pygame.display.flip()
        clock.tick(30)

# StreamlitのUI
st.title('Streamlit Invaders')
st.write('Move left or right, and shoot to destroy the enemies!')

# ゲームの実行
if st.button('Start Game'):
    game_loop()
