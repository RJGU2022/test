#!/usr/bin/env python3
"""
五子棋人机对弈程序
功能：
1. 黑先白后
2. 自动积分
3. 五局三胜制
4. 落子有声
5. 最优落子提示
"""

import pygame
import sys
import random
from pygame import mixer
from PIL import Image, ImageDraw, ImageFont
import io

# ==================== 常量定义 ====================
SCREEN_SIZE = 900
BOARD_SIZE = 15
CELL_SIZE = 45
MARGIN = 30

# 颜色
COLOR_BOARD = (221, 185, 109)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_HINT = (255, 0, 0)
COLOR_LAST = (0, 255, 0)
COLOR_BG = (240, 220, 180)
COLOR_TEXT = (50, 50, 50)
COLOR_WIN = (0, 200, 0)
COLOR_LOSE = (200, 0, 0)
COLOR_OVERLAY = (0, 0, 0, 180)

# 游戏状态
EMPTY = 0
BLACK = 1
WHITE = 2

# 方向
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# 中文字体路径 - 尝试多个可能的字体
FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]

FONT_TITLE = None
FONT_TEXT = None
FONT_SMALL = None

for fp in FONT_PATHS:
    try:
        FONT_TITLE = ImageFont.truetype(fp, 40)
        FONT_TEXT = ImageFont.truetype(fp, 24)
        FONT_SMALL = ImageFont.truetype(fp, 18)
        print(f"Using font: {fp}")
        break
    except:
        continue

if FONT_TITLE is None:
    FONT_TITLE = ImageFont.load_default()
    FONT_TEXT = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    print("Warning: No Chinese font found, using default")

# ==================== 工具函数 ====================
def render_chinese(text, font, color=(50, 50, 50)):
    """使用PIL渲染中文文本为pygame surface"""
    # 获取文本边界
    temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 20
    height = bbox[3] - bbox[1] + 10
    
    # 创建正确大小的图像
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制文本
    draw.text((10, 5), text, font=font, fill=color + (255,))
    
    # 转换为pygame surface
    mode = img.mode
    size = img.size
    data = img.tobytes()
    surface = pygame.image.frombuffer(data, size, mode)
    return surface.convert_alpha()

# ==================== 棋盘类 ====================
class GobangBoard:
    def __init__(self):
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = BLACK
        self.last_move = None
        self.game_over = False
        self.winner = None
        self.black_score = 0
        self.white_score = 0
        self.round_wins = {'black': 0, 'white': 0}
        self.current_round = 1
        self.max_rounds = 5
        
    def reset_board(self):
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.last_move = None
        self.game_over = False
        self.winner = None
        
    def reset_game(self):
        self.reset_board()
        self.black_score = 0
        self.white_score = 0
        self.round_wins = {'black': 0, 'white': 0}
        self.current_round = 1
        
    def place_piece(self, x, y):
        if self.board[y][x] != EMPTY or self.game_over:
            return False
        
        self.board[y][x] = self.current_player
        self.last_move = (x, y)
        
        if self.check_win(x, y):
            self.game_over = True
            self.winner = self.current_player
            if self.current_player == BLACK:
                self.round_wins['black'] += 1
                self.black_score += 1
            else:
                self.round_wins['white'] += 1
                self.white_score += 1
            return True
        
        self.current_player = WHITE if self.current_player == BLACK else BLACK
        return True
    
    def check_win(self, x, y):
        color = self.board[y][x]
        for dx, dy in DIRECTIONS:
            count = 1
            nx, ny = x + dx, y + dy
            while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and self.board[ny][nx] == color:
                count += 1
                nx += dx
                ny += dy
            nx, ny = x - dx, y - dy
            while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and self.board[ny][nx] == color:
                count += 1
                nx -= dx
                ny -= dy
            if count >= 5:
                return True
        return False
    
    def get_empty_positions(self):
        positions = []
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.board[y][x] == EMPTY:
                    positions.append((x, y))
        return positions

# ==================== AI算法 ====================
class GobangAI:
    def __init__(self, board):
        self.board = board
        
    def evaluate_position(self, x, y, color):
        if self.board.board[y][x] != EMPTY:
            return -1
        total_score = 0
        for dx, dy in DIRECTIONS:
            line = self.evaluate_line(x, y, dx, dy, color)
            total_score += line
        return total_score
    
    def evaluate_line(self, x, y, dx, dy, color):
        count = 1
        open_end = 0
        nx, ny = x + dx, y + dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
            if self.board.board[ny][nx] == color:
                count += 1
            elif self.board.board[ny][nx] == EMPTY:
                open_end += 1
                break
            else:
                break
            nx += dx
            ny += dy
        
        nx, ny = x - dx, y - dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
            if self.board.board[ny][nx] == color:
                count += 1
            elif self.board.board[ny][nx] == EMPTY:
                open_end += 1
                break
            else:
                break
            nx -= dx
            ny -= dy
        
        if count >= 5:
            return 100000
        elif count == 4:
            if open_end == 2:
                return 10000
            elif open_end == 1:
                return 1000
        elif count == 3:
            if open_end == 2:
                return 1000
            elif open_end == 1:
                return 100
        elif count == 2:
            if open_end == 2:
                return 100
            elif open_end == 1:
                return 10
        return count * open_end
    
    def get_best_move(self):
        ai_color = WHITE
        human_color = BLACK
        best_score = -1
        best_moves = []
        empty_positions = self.board.get_empty_positions()
        center = BOARD_SIZE // 2
        
        for x, y in empty_positions:
            attack_score = self.evaluate_position(x, y, ai_color)
            defend_score = self.evaluate_position(x, y, human_color)
            score = attack_score + defend_score * 1.1
            dist_to_center = abs(x - center) + abs(y - center)
            score -= dist_to_center * 0.1
            
            if score > best_score:
                best_score = score
                best_moves = [(x, y)]
            elif score == best_score:
                best_moves.append((x, y))
        
        if best_moves:
            return random.choice(best_moves)
        return None
    
    def get_hint(self, human_color=BLACK):
        best_score = -1
        best_move = None
        empty_positions = self.board.get_empty_positions()
        center = BOARD_SIZE // 2
        
        for x, y in empty_positions:
            score = self.evaluate_position(x, y, human_color)
            dist_to_center = abs(x - center) + abs(y - center)
            score -= dist_to_center * 0.5
            
            if score > best_score:
                best_score = score
                best_move = (x, y)
        
        return best_move

# ==================== 绘制函数 ====================
def draw_board(screen):
    screen.fill(COLOR_BG)
    for i in range(BOARD_SIZE):
        start = (MARGIN, MARGIN + i * CELL_SIZE)
        end = (MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, MARGIN + i * CELL_SIZE)
        pygame.draw.line(screen, COLOR_BLACK, start, end, 1)
        
        start = (MARGIN + i * CELL_SIZE, MARGIN)
        end = (MARGIN + i * CELL_SIZE, MARGIN + (BOARD_SIZE - 1) * CELL_SIZE)
        pygame.draw.line(screen, COLOR_BLACK, start, end, 1)
    
    star_points = [(3, 3), (11, 3), (3, 11), (11, 11), (7, 7)]
    for x, y in star_points:
        pygame.draw.circle(screen, COLOR_BLACK, 
                          (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE), 4)

def draw_pieces(screen, board):
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board.board[y][x] != EMPTY:
                pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
                if board.board[y][x] == BLACK:
                    pygame.draw.circle(screen, COLOR_BLACK, pos, 20)
                else:
                    pygame.draw.circle(screen, COLOR_WHITE, pos, 20)
                    pygame.draw.circle(screen, (200, 200, 200), pos, 20, 1)

def draw_last_piece(screen, board):
    if board.last_move:
        x, y = board.last_move
        pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
        pygame.draw.circle(screen, COLOR_LAST, pos, 22, 2)

def draw_hint(screen, hint_pos):
    if hint_pos:
        x, y = hint_pos
        pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
        pygame.draw.circle(screen, COLOR_HINT, pos, 15, 2)

def draw_info(screen, board, ai):
    info_x = MARGIN + (BOARD_SIZE - 1) * CELL_SIZE + 20
    line_height = 30
    
    # 当前玩家
    if not board.game_over:
        if board.current_player == BLACK:
            player_text = u"当前: 黑方 (你)"
        else:
            player_text = u"当前: 白方 (AI)"
    else:
        if board.winner == BLACK:
            player_text = u"本局: 黑方获胜!"
        else:
            player_text = u"本局: 白方获胜!"
    
    surface = render_chinese(player_text, FONT_TEXT)
    screen.blit(surface, (info_x, MARGIN))
    
    # 比分
    score_text = u"积分: 黑%d 白%d" % (board.black_score, board.white_score)
    surface = render_chinese(score_text, FONT_SMALL)
    screen.blit(surface, (info_x, MARGIN + line_height + 5))
    
    # 局数
    round_text = u"第%d/%d局" % (board.current_round, board.max_rounds)
    surface = render_chinese(round_text, FONT_SMALL)
    screen.blit(surface, (info_x, MARGIN + (line_height + 5) * 2))
    
    # 本局胜场
    wins_text = u"三局两胜: 黑%d 白%d" % (board.round_wins['black'], board.round_wins['white'])
    surface = render_chinese(wins_text, FONT_SMALL)
    screen.blit(surface, (info_x, MARGIN + (line_height + 5) * 3))
    
    # 操作提示
    hint_text = u"H:提示  R:重置  N:下一局"
    surface = render_chinese(hint_text, FONT_SMALL, (100, 100, 100))
    screen.blit(surface, (info_x, MARGIN + (line_height + 5) * 5))
    
    # 提示位置
    if board.current_player == BLACK and not board.game_over:
        hint_pos = ai.get_hint(BLACK)
        if hint_pos:
            draw_hint(screen, hint_pos)

def draw_game_over(screen, board):
    """绘制游戏结束弹窗"""
    if not board.game_over:
        return
    
    # 创建半透明遮罩
    overlay = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE), pygame.SRCALPHA)
    overlay.fill(COLOR_OVERLAY)
    screen.blit(overlay, (0, 0))
    
    # 弹窗背景
    popup_w, popup_h = 400, 200
    popup_x = (SCREEN_SIZE - popup_w) // 2
    popup_y = (SCREEN_SIZE - popup_h) // 2
    
    pygame.draw.rect(screen, (255, 255, 255), (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(screen, COLOR_BLACK, (popup_x, popup_y, popup_w, popup_h), 3)
    
    # 标题
    if board.winner == BLACK:
        title = u"黑方获胜!"
        color = COLOR_WIN
    else:
        title = u"白方获胜!"
        color = COLOR_LOSE
    
    surface = render_chinese(title, FONT_TITLE, color)
    rect = surface.get_rect(center=(SCREEN_SIZE // 2, popup_y + 60))
    screen.blit(surface, rect)
    
    # 比分
    score_text = u"本局得分 - 黑方: %d  白方: %d" % (board.black_score, board.white_score)
    surface = render_chinese(score_text, FONT_TEXT)
    rect = surface.get_rect(center=(SCREEN_SIZE // 2, popup_y + 110))
    screen.blit(surface, rect)
    
    # 总体比分
    if board.round_wins['black'] >= 3 or board.round_wins['white'] >= 3:
        if board.round_wins['black'] >= 3:
            final = u"黑方获得最终胜利!"
            final_color = COLOR_WIN
        else:
            final = u"白方获得最终胜利!"
            final_color = COLOR_LOSE
        surface = render_chinese(final, FONT_TEXT, final_color)
        rect = surface.get_rect(center=(SCREEN_SIZE // 2, popup_y + 150))
        screen.blit(surface, rect)
    elif board.current_round < board.max_rounds:
        hint = u"按 N 继续下一局"
        surface = render_chinese(hint, FONT_SMALL, (100, 100, 100))
        rect = surface.get_rect(center=(SCREEN_SIZE // 2, popup_y + 150))
        screen.blit(surface, rect)
    else:
        if board.round_wins['black'] > board.round_wins['white']:
            final = u"黑方获得最终胜利!"
            final_color = COLOR_WIN
        elif board.round_wins['white'] > board.round_wins['black']:
            final = u"白方获得最终胜利!"
            final_color = COLOR_LOSE
        else:
            final = u"平局!"
            final_color = COLOR_TEXT
        surface = render_chinese(final, FONT_TEXT, final_color)
        rect = surface.get_rect(center=(SCREEN_SIZE // 2, popup_y + 150))
        screen.blit(surface, rect)

def get_board_position(mouse_pos):
    x, y = mouse_pos
    board_x = round((x - MARGIN) / CELL_SIZE)
    board_y = round((y - MARGIN) / CELL_SIZE)
    
    if 0 <= board_x < BOARD_SIZE and 0 <= board_y < BOARD_SIZE:
        actual_x = MARGIN + board_x * CELL_SIZE
        actual_y = MARGIN + board_y * CELL_SIZE
        if abs(x - actual_x) <= CELL_SIZE // 2 and abs(y - actual_y) <= CELL_SIZE // 2:
            return board_x, board_y
    return None

# ==================== 主程序 ====================
def init_sound():
    try:
        import numpy as np
        import scipy.io.wavfile as wav
        
        sample_rate = 44100
        duration = 0.05
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        freq1 = 800
        freq2 = 1200
        wave = np.sin(2 * np.pi * freq1 * t) * 0.5 + np.sin(2 * np.pi * freq2 * t) * 0.3
        envelope = np.exp(-t * 30)
        wave = wave * envelope
        wave = (wave * 32767).astype(np.int16)
        
        sound_file = '/tmp/place_piece.wav'
        wav.write(sound_file, sample_rate, wave)
        return sound_file
    except:
        return None

def main():
    pygame.init()
    mixer.init()
    
    screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
    pygame.display.set_caption(u"五子棋 - 人机对弈")
    
    sound_file = init_sound()
    place_sound = None
    if sound_file:
        try:
            place_sound = mixer.Sound(sound_file)
        except:
            pass
    
    board = GobangBoard()
    ai = GobangAI(board)
    
    running = True
    clock = pygame.time.Clock()
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not board.game_over:
                    if board.current_player == BLACK:
                        pos = get_board_position(event.pos)
                        if pos:
                            x, y = pos
                            if board.place_piece(x, y):
                                if place_sound:
                                    place_sound.play()
                                
                                if not board.game_over:
                                    pygame.time.wait(300)
                                    ai_move = ai.get_best_move()
                                    if ai_move:
                                        ax, ay = ai_move
                                        board.place_piece(ax, ay)
                                        if place_sound:
                                            place_sound.play()
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    board.reset_game()
                elif event.key == pygame.K_n:
                    if board.game_over:
                        if board.current_round < board.max_rounds:
                            board.current_round += 1
                            board.reset_board()
                        elif board.round_wins['black'] >= 3 or board.round_wins['white'] >= 3:
                            board.reset_game()
        
        draw_board(screen)
        draw_pieces(screen, board)
        draw_last_piece(screen, board)
        draw_info(screen, board, ai)
        draw_game_over(screen, board)
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
