#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame

Thin rendering shell that delegates all game coordination to GameCoordinator
and UI state management to FrontendAdapter.
"""
import math
import random
import sys
from dataclasses import dataclass

import pygame

from frontend_adapter import (
    CATEGORY_ORDER,
    CATEGORY_TOOLTIPS,
    OPTIMAL_EXPECTED_TOTAL,
    FrontendAdapter,
    SoundInterface,
)
from game_coordinator import GameCoordinator, _make_strategy, parse_args
from game_engine import (
    Category,
    DieState,
    calculate_score_in_context,
)
from sounds import SoundManager

# Initialize pygame (mixer pre-init for low-latency audio)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (240, 240, 245)
BACKGROUND = (245, 250, 255)
DICE_COLOR = (255, 255, 255)
DOT_COLOR = (40, 40, 40)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 149, 237)
BUTTON_TEXT_COLOR = (255, 255, 255)
SCORECARD_BG = (250, 252, 255)
SECTION_HEADER_COLOR = (60, 120, 160)
VALID_SCORE_COLOR = (40, 180, 80)
HOVER_COLOR = (220, 240, 255)
IN_CUP_COLOR = (180, 185, 195)  # muted gray for unrolled dice
FLASH_HIGHLIGHT = (255, 240, 180)  # warm gold for score flash
AI_CHOICE_HIGHLIGHT = (180, 220, 255)  # light blue for AI score choice preview
PLAYER_COLORS = [
    (70, 130, 180),   # Steel blue (Player 1)
    (180, 80, 80),    # Red (Player 2)
    (80, 160, 80),    # Green (Player 3)
    (160, 120, 50),   # Gold (Player 4)
]

# Colorblind-friendly palette alternatives
CB_HELD_COLOR = (0, 120, 220)        # Blue instead of green
CB_VALID_SCORE_COLOR = (0, 100, 200)  # Blue instead of green
CB_PLAYER_COLORS = [
    (0, 90, 180),    # Blue
    (230, 130, 0),   # Orange
    (0, 160, 160),   # Teal
    (160, 80, 200),  # Purple
]

# Dark mode palette
DARK_BACKGROUND = (30, 32, 38)
DARK_SCORECARD_BG = (40, 42, 50)
DARK_TEXT = (220, 220, 230)
DARK_GRAY = (90, 90, 100)
DARK_HOVER_COLOR = (50, 60, 80)
DARK_SECTION_HEADER = (100, 170, 220)
DARK_BUTTON_COLOR = (50, 100, 150)
DARK_BUTTON_HOVER = (70, 120, 180)
DARK_FLASH_HIGHLIGHT = (120, 100, 40)
DARK_DICE_COLOR = (60, 62, 70)
DARK_DOT_COLOR = (220, 220, 230)
DARK_IN_CUP_COLOR = (50, 52, 60)
DARK_AI_CHOICE_HIGHLIGHT = (40, 60, 90)
DARK_PANEL_BG = (45, 48, 56)
DARK_PANEL_BORDER = (70, 72, 85)
DARK_SHADOW_COLOR = (20, 20, 25, 50)
DARK_BORDER_COLOR = (80, 80, 90)

# Dice constants
DICE_SIZE = 80
DICE_MARGIN = 20
DOT_RADIUS = 6

# Game constants
MAX_ROLLS_PER_TURN = 3


# ── Layout ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Layout:
    """Centralized layout constants for the game window.

    All position/size values live here so that dependent values (e.g. scorecard
    top derived from player bar bottom) update automatically when a base value
    changes.  Frozen because layout is immutable once computed.
    """

    # Window
    window_width: int
    window_height: int

    # Title area
    title_y: int
    round_text_y: int
    ai_indicator_y: int

    # Player bar (multiplayer)
    player_bar_y: int
    player_bar_height: int
    player_bar_bottom: int  # computed: player_bar_y + player_bar_height

    # Scorecard
    scorecard_x: int
    scorecard_y: int
    scorecard_row_height: int
    scorecard_col_width: int
    scorecard_panel_width: int
    scorecard_panel_height: int
    scorecard_panel_top: int     # computed: scorecard_y - 15
    scorecard_panel_bottom: int  # computed: scorecard_panel_top + panel_height

    # Dice area
    dice_start_x: int
    dice_y: int

    # Roll button
    roll_button_x: int
    roll_button_y: int
    roll_button_width: int
    roll_button_height: int

    # Status text
    roll_status_y: int
    ai_reason_y: int

    # Play again button
    play_again_x: int  # computed: (window_width - play_again_width) // 2
    play_again_y: int
    play_again_width: int
    play_again_height: int


def compute_layout(multiplayer: bool = False) -> Layout:
    """Build a Layout with all dependent values computed from base constants.

    The multiplayer flag shifts the scorecard down to clear the player bar and
    uses tighter rows to fit the extra player-name header without overflowing.
    """
    window_width = WINDOW_WIDTH
    window_height = WINDOW_HEIGHT

    # Title area
    title_y = 50
    round_text_y = 90
    ai_indicator_y = 120

    # Player bar
    player_bar_y = 130
    player_bar_height = 32
    player_bar_bottom = player_bar_y + player_bar_height  # 162

    # Scorecard — multiplayer shifts down to clear the player bar
    scorecard_x = 620
    scorecard_panel_width = 360
    scorecard_col_width = 180

    if multiplayer:
        scorecard_panel_top = player_bar_bottom + 3  # 165
        scorecard_y = scorecard_panel_top + 15        # 180
        scorecard_row_height = 24
        scorecard_panel_height = 525
    else:
        scorecard_y = 150
        scorecard_panel_top = scorecard_y - 15        # 135
        scorecard_row_height = 28
        scorecard_panel_height = 520

    scorecard_panel_bottom = scorecard_panel_top + scorecard_panel_height

    # Dice area
    dice_start_x = 80
    dice_y = 300

    # Roll button (centered under the dice area)
    roll_button_width = 150
    roll_button_height = 50
    roll_button_x = dice_start_x + 165  # 245
    roll_button_y = 500

    # Status text
    roll_status_y = 560
    ai_reason_y = 590

    # Play again button
    play_again_width = 200
    play_again_height = 60
    play_again_x = (window_width - play_again_width) // 2  # 400
    play_again_y = 620

    return Layout(
        window_width=window_width,
        window_height=window_height,
        title_y=title_y,
        round_text_y=round_text_y,
        ai_indicator_y=ai_indicator_y,
        player_bar_y=player_bar_y,
        player_bar_height=player_bar_height,
        player_bar_bottom=player_bar_bottom,
        scorecard_x=scorecard_x,
        scorecard_y=scorecard_y,
        scorecard_row_height=scorecard_row_height,
        scorecard_col_width=scorecard_col_width,
        scorecard_panel_width=scorecard_panel_width,
        scorecard_panel_height=scorecard_panel_height,
        scorecard_panel_top=scorecard_panel_top,
        scorecard_panel_bottom=scorecard_panel_bottom,
        dice_start_x=dice_start_x,
        dice_y=dice_y,
        roll_button_x=roll_button_x,
        roll_button_y=roll_button_y,
        roll_button_width=roll_button_width,
        roll_button_height=roll_button_height,
        roll_status_y=roll_status_y,
        ai_reason_y=ai_reason_y,
        play_again_x=play_again_x,
        play_again_y=play_again_y,
        play_again_width=play_again_width,
        play_again_height=play_again_height,
    )


# ── Pygame Sound Adapter ─────────────────────────────────────────────────────

class PygameSoundAdapter(SoundInterface):
    """Wraps SoundManager to implement the frontend adapter's SoundInterface."""

    def __init__(self):
        self._manager = SoundManager()

    def play_roll(self):
        self._manager.play_roll()

    def play_click(self):
        self._manager.play_click()

    def play_score(self):
        self._manager.play_score()

    def play_fanfare(self):
        self._manager.play_fanfare()

    def toggle(self):
        return self._manager.toggle()

    @property
    def enabled(self):
        return self._manager.enabled


class DiceSprite:
    """Visual representation of a die - handles only positioning and rendering"""

    def __init__(self, x, y):
        """
        Initialize a dice sprite at a position.

        Args:
            x: X position on screen
            y: Y position on screen
        """
        self.x = x
        self.y = y

    def contains_point(self, pos):
        """
        Check if a point is inside the die.

        Args:
            pos: Tuple of (x, y) coordinates

        Returns:
            True if point is inside die, False otherwise
        """
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        return dice_rect.collidepoint(pos)

    def draw(self, surface, die_state, offset_x=0, offset_y=0, colorblind=False,
             dice_color=None, dot_color=None, shadow_color=None, border_color=None):
        """
        Draw the die based on its state.

        Args:
            surface: pygame surface to draw on
            die_state: DieState object with value and held status
            offset_x: X offset for animation effects
            offset_y: Y offset for animation effects
            colorblind: If True, use colorblind-friendly held color and markers
            dice_color: Override dice face color (for dark mode)
            dot_color: Override dot color (for dark mode)
            shadow_color: Override shadow color (for dark mode)
            border_color: Override unheld border color (for dark mode)
        """
        # Apply offsets for animation effects
        x = self.x + offset_x
        y = self.y + offset_y

        _dice_color = dice_color or DICE_COLOR
        _dot_color = dot_color or DOT_COLOR
        _shadow_color = shadow_color or (200, 200, 200, 50)
        _border_color = border_color or (100, 100, 100)

        # Draw subtle shadow for depth
        shadow_rect = pygame.Rect(x + 3, y + 3, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, _shadow_color, shadow_rect, border_radius=10)

        # Draw dice background
        dice_rect = pygame.Rect(x, y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, _dice_color, dice_rect, border_radius=10)

        # Draw border - thicker and colored if held
        if die_state.held:
            held_color = CB_HELD_COLOR if colorblind else (50, 200, 50)
            border_width = 6 if colorblind else 5
            pygame.draw.rect(surface, held_color, dice_rect, width=border_width, border_radius=10)
            # Colorblind: add diagonal stripe pattern for extra visual cue
            if colorblind:
                clip_rect = pygame.Rect(x + 4, y + 4, DICE_SIZE - 8, DICE_SIZE - 8)
                surface.set_clip(clip_rect)
                for i in range(-DICE_SIZE, DICE_SIZE * 2, 16):
                    pygame.draw.line(surface, (*held_color, 60),
                                     (x + i, y), (x + i + DICE_SIZE, y + DICE_SIZE), 2)
                surface.set_clip(None)
        else:
            pygame.draw.rect(surface, _border_color, dice_rect, width=2, border_radius=10)

        # Draw dots based on value
        self._draw_dots(surface, die_state.value, offset_x, offset_y, _dot_color)

    def draw_in_cup(self, surface, cup_color=None, shadow_color=None, border_color=None, text_color=None):
        """Draw the die in its 'in the cup' state — face-down, gray, with '?' text.

        Used when rolls_used == 0 to show dice haven't been rolled yet this turn.
        """
        _cup_color = cup_color or IN_CUP_COLOR
        _shadow_color = shadow_color or (200, 200, 200, 50)
        _border_color = border_color or (150, 155, 165)
        _text_color = text_color or (120, 125, 135)

        # Draw subtle shadow
        shadow_rect = pygame.Rect(self.x + 3, self.y + 3, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, _shadow_color, shadow_rect, border_radius=10)

        # Gray background
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, _cup_color, dice_rect, border_radius=10)

        # Light border
        pygame.draw.rect(surface, _border_color, dice_rect, width=2, border_radius=10)

        # "?" text centered on the die
        font = pygame.font.Font(None, 48)
        text = font.render("?", True, _text_color)
        text_rect = text.get_rect(center=(self.x + DICE_SIZE // 2, self.y + DICE_SIZE // 2))
        surface.blit(text, text_rect)

    def _draw_dots(self, surface, value, offset_x=0, offset_y=0, color=None):
        """
        Draw the dots/pips on the die face.

        Args:
            surface: pygame surface to draw on
            value: Die value (1-6)
            offset_x: X offset for animation effects
            offset_y: Y offset for animation effects
            color: Dot color override (for dark mode)
        """
        dot_c = color or DOT_COLOR
        # Calculate dot positions relative to die center
        center_x = self.x + DICE_SIZE // 2 + offset_x
        center_y = self.y + DICE_SIZE // 2 + offset_y
        offset = DICE_SIZE // 4

        # Define dot positions for each value
        # 1: center
        if value == 1:
            pygame.draw.circle(surface, dot_c, (center_x, center_y), DOT_RADIUS)

        # 2: diagonal top-left to bottom-right
        elif value == 2:
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 3: diagonal plus center
        elif value == 3:
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 4: four corners
        elif value == 4:
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 5: four corners plus center
        elif value == 5:
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 6: two columns of three
        elif value == 6:
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, dot_c, (center_x + offset, center_y + offset), DOT_RADIUS)


class Button:
    """A simple button class for UI interactions"""

    def __init__(self, x, y, width, height, text, font_size=36):
        """
        Initialize a button

        Args:
            x: X position of button
            y: Y position of button
            width: Button width
            height: Button height
            text: Button text
            font_size: Size of button text font
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.is_hovered = False
        self.enabled = True

    def handle_event(self, event):
        """
        Handle mouse events for the button

        Args:
            event: pygame event

        Returns:
            True if button was clicked, False otherwise
        """
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos) and self.enabled
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.is_hovered and self.enabled:
                return True
        return False

    def draw(self, surface, button_color=None, hover_color=None, disabled_color=None, border_color=None):
        """Draw the button with optional color overrides for theming."""
        _btn = button_color or BUTTON_COLOR
        _hover = hover_color or BUTTON_HOVER_COLOR
        _disabled = disabled_color or GRAY
        _border = border_color or BLACK

        # Choose color based on state
        if not self.enabled:
            color = _disabled
        elif self.is_hovered:
            color = _hover
        else:
            color = _btn

        # Draw button background
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, _border, self.rect, width=2, border_radius=8)

        # Draw button text
        text_surface = self.font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class YahtzeeGame:
    """Main game class for Yahtzee — thin rendering shell over GameCoordinator"""

    def __init__(self, ai_strategy=None, speed="normal", players=None, coordinator=None):
        """Initialize the game window and basic components

        Args:
            ai_strategy: Optional AI strategy instance. If provided, AI plays the game.
                         Used only in single-player mode.
            speed: Speed preset name for AI playback ("slow", "normal", "fast").
            players: Optional list of (name, strategy_or_None) tuples for multiplayer.
                     None means single-player mode (backward compatible).
            coordinator: Optional pre-configured GameCoordinator (for resume).
        """
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Yahtzee")
        self.clock = pygame.time.Clock()
        self.running = True

        # All game coordination logic lives in the coordinator
        if coordinator is not None:
            self.coordinator = coordinator
        else:
            self.coordinator = GameCoordinator(
                ai_strategy=ai_strategy, speed=speed, players=players
            )

        # Frontend adapter manages shared UI state (overlays, settings, etc.)
        self.adapter = FrontendAdapter(
            self.coordinator, sound=PygameSoundAdapter()
        )

        # Centralized layout — all positions/sizes derived from one source
        self.layout = compute_layout(multiplayer=self.coordinator.multiplayer)

        # Dice sprites (visual representation only)
        self.dice_sprites = []
        for i in range(5):
            x = self.layout.dice_start_x + i * (DICE_SIZE + DICE_MARGIN)
            sprite = DiceSprite(x, self.layout.dice_y)
            self.dice_sprites.append(sprite)

        # Create roll button (positioned on left side with dice)
        self.roll_button = Button(
            self.layout.roll_button_x, self.layout.roll_button_y,
            self.layout.roll_button_width, self.layout.roll_button_height, "ROLL",
        )

        # Play again button (for game over screen)
        self.play_again_button = Button(
            self.layout.play_again_x, self.layout.play_again_y,
            self.layout.play_again_width, self.layout.play_again_height, "PLAY AGAIN", 40,
        )

        # Animation state (GUI concern only — randomized display values during roll)
        self.animation_dice_values = [die.value for die in self.coordinator.dice]

        # Bounce animation state — dice hop when landing after a roll
        self.bounce_active = [False] * 5
        self.bounce_timers = [0] * 5
        self.bounce_duration = 15  # frames

        # Pygame-only UI state
        self.category_rects = {}  # Maps Category to pygame.Rect for click detection

        # Font cache — avoids recreating Font objects every frame
        self._font_cache = {}

    # ── Properties delegating to adapter (for backward compatibility) ─────

    @property
    def colorblind_mode(self):
        return self.adapter.colorblind_mode

    @colorblind_mode.setter
    def colorblind_mode(self, value):
        self.adapter.colorblind_mode = value

    @property
    def dark_mode(self):
        return self.adapter.dark_mode

    @dark_mode.setter
    def dark_mode(self, value):
        self.adapter.dark_mode = value

    @property
    def hovered_category(self):
        return self.adapter.hovered_category

    @hovered_category.setter
    def hovered_category(self, value):
        self.adapter.hovered_category = value

    @property
    def kb_selected_index(self):
        return self.adapter.kb_selected_index

    @kb_selected_index.setter
    def kb_selected_index(self, value):
        self.adapter.kb_selected_index = value

    @property
    def showing_help(self):
        return self.adapter.showing_help

    @property
    def showing_history(self):
        return self.adapter.showing_history

    @property
    def showing_replay(self):
        return self.adapter.showing_replay

    @property
    def showing_scores(self):
        return self.adapter.showing_scores

    @property
    def confirm_zero_category(self):
        return self.adapter.confirm_zero_category

    @property
    def score_flash_category(self):
        return self.adapter.score_flash_category

    @property
    def score_flash_timer(self):
        return self.adapter.score_flash_timer

    @property
    def score_flash_duration(self):
        return self.adapter.score_flash_duration

    @property
    def history_filter_player(self):
        return self.adapter.history_filter_player

    @property
    def history_filter_mode(self):
        return self.adapter.history_filter_mode

    @property
    def sounds(self):
        """Access the underlying SoundManager for backward compatibility."""
        return self.adapter.sound._manager

    def _valid_color(self):
        """Return the valid score color based on colorblind mode."""
        return CB_VALID_SCORE_COLOR if self.colorblind_mode else VALID_SCORE_COLOR

    def _player_colors(self):
        """Return the player color palette based on colorblind mode."""
        return CB_PLAYER_COLORS if self.colorblind_mode else PLAYER_COLORS

    def _font(self, size):
        """Return a cached pygame Font of the given size."""
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.Font(None, size)
        return self._font_cache[size]

    # ── Theme helpers (dark mode vs light mode) ──────────────────────────

    def _bg_color(self):
        return DARK_BACKGROUND if self.dark_mode else BACKGROUND

    def _text_color(self):
        return DARK_TEXT if self.dark_mode else BLACK

    def _scorecard_bg(self):
        return DARK_SCORECARD_BG if self.dark_mode else SCORECARD_BG

    def _section_header_color(self):
        return DARK_SECTION_HEADER if self.dark_mode else SECTION_HEADER_COLOR

    def _hover_color(self):
        return DARK_HOVER_COLOR if self.dark_mode else HOVER_COLOR

    def _gray_color(self):
        return DARK_GRAY if self.dark_mode else GRAY

    def _flash_highlight(self):
        return DARK_FLASH_HIGHLIGHT if self.dark_mode else FLASH_HIGHLIGHT

    def _dice_colors(self):
        """Return (dice_color, dot_color, shadow_color, border_color) for current theme."""
        if self.dark_mode:
            return DARK_DICE_COLOR, DARK_DOT_COLOR, DARK_SHADOW_COLOR, DARK_BORDER_COLOR
        return DICE_COLOR, DOT_COLOR, (200, 200, 200, 50), (100, 100, 100)

    def _cup_colors(self):
        """Return (cup_color, shadow_color, border_color, text_color) for in-cup dice."""
        if self.dark_mode:
            return DARK_IN_CUP_COLOR, DARK_SHADOW_COLOR, (60, 62, 70), (80, 85, 95)
        return IN_CUP_COLOR, (200, 200, 200, 50), (150, 155, 165), (120, 125, 135)

    def _button_colors(self):
        """Return (button, hover, disabled, border) for current theme."""
        if self.dark_mode:
            return DARK_BUTTON_COLOR, DARK_BUTTON_HOVER, DARK_GRAY, DARK_BORDER_COLOR
        return BUTTON_COLOR, BUTTON_HOVER_COLOR, GRAY, BLACK

    def _ai_choice_highlight(self):
        return DARK_AI_CHOICE_HIGHLIGHT if self.dark_mode else AI_CHOICE_HIGHLIGHT

    def _panel_colors(self):
        """Return (bg, border) for overlay panels."""
        if self.dark_mode:
            return DARK_PANEL_BG, DARK_PANEL_BORDER
        return (250, 252, 255), (100, 100, 120)

    def _scorecard_border(self):
        return DARK_PANEL_BORDER if self.dark_mode else (180, 180, 200)

    def _game_over_overlay(self):
        """Return overlay fill color for game over screen."""
        if self.dark_mode:
            return (25, 27, 33)
        return (240, 240, 240)

    def _winner_highlight(self):
        if self.dark_mode:
            return (80, 70, 30)
        return (255, 245, 200)

    def handle_events(self):
        """Handle pygame events — translates input to adapter/coordinator actions"""
        coord = self.coordinator
        adapter = self.adapter
        is_human_turn = coord.is_current_player_human
        game_over = coord.game_over

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Zero-score confirmation dialog takes priority
                if adapter.confirm_zero_category is not None:
                    if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                        adapter.confirm_zero_yes()
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        adapter.confirm_zero_no()
                    continue  # Block all other input while dialog showing

                if event.key == pygame.K_ESCAPE:
                    if not adapter.close_top_overlay():
                        self.running = False
                # Help overlay (? or F1)
                if event.key == pygame.K_F1 or (event.key == pygame.K_SLASH and event.mod & pygame.KMOD_SHIFT):
                    adapter.toggle_help()
                # History overlay (H key)
                if event.key == pygame.K_h:
                    adapter.toggle_history()
                # Scores overlay (S key, multiplayer only)
                if event.key == pygame.K_s:
                    adapter.toggle_scores()
                # History filter cycling (P/M keys while overlay showing)
                if adapter.showing_history:
                    if event.key == pygame.K_p:
                        adapter.cycle_player_filter()
                    elif event.key == pygame.K_m:
                        adapter.cycle_mode_filter()
                # Speed control (+/- keys) — when any AI is present
                if coord.has_any_ai and not game_over:
                    if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        adapter.change_speed(+1)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        adapter.change_speed(-1)
                # Sound toggle (M key) — not while history overlay is showing
                if event.key == pygame.K_m and not adapter.showing_history:
                    adapter.toggle_sound()
                # Colorblind mode toggle (C key)
                if event.key == pygame.K_c:
                    adapter.toggle_colorblind()
                # Dark mode toggle (D key)
                if event.key == pygame.K_d:
                    adapter.toggle_dark_mode()
                # Replay overlay (R key, game over only)
                if event.key == pygame.K_r and game_over:
                    adapter.toggle_replay()
                # Undo (Ctrl+Z) for human players
                if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL or event.mod & pygame.KMOD_META):
                    if adapter.do_undo():
                        self.animation_dice_values = [die.value for die in coord.dice]
                # Keyboard shortcuts for human players
                if (is_human_turn and not game_over and not coord.is_rolling
                        and not adapter.has_active_overlay):
                    if event.key == pygame.K_SPACE:
                        adapter.do_roll()
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        die_index = event.key - pygame.K_1
                        adapter.do_hold(die_index)
                    elif event.key in (pygame.K_TAB, pygame.K_DOWN) and not (event.mod & pygame.KMOD_SHIFT):
                        adapter.navigate_category(+1)
                    elif event.key == pygame.K_UP or (event.key == pygame.K_TAB and event.mod & pygame.KMOD_SHIFT):
                        adapter.navigate_category(-1)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        if adapter.kb_selected_index is not None:
                            cat = CATEGORY_ORDER[adapter.kb_selected_index]
                            adapter.try_score_category(cat)
            elif event.type == pygame.MOUSEMOTION:
                adapter.clear_hover()
                adapter.kb_selected_index = None  # Mouse clears keyboard selection
                if not game_over and is_human_turn and not adapter.has_active_overlay:
                    scorecard = coord.scorecard
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and not scorecard.is_filled(cat):
                            adapter.set_hovered_category(cat)
                            break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if adapter.confirm_zero_category is not None:
                    continue  # Block mouse clicks while dialog showing
                if event.button == 1 and is_human_turn and not adapter.has_active_overlay:
                    clicked_category = False
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos):
                            adapter.try_score_category(cat)
                            clicked_category = True
                            break

                    if not clicked_category and not coord.is_rolling and not game_over:
                        for i, sprite in enumerate(self.dice_sprites):
                            if sprite.contains_point(event.pos):
                                adapter.do_hold(i)
                                break

            # Handle button clicks (only if not currently rolling and human turn)
            if (is_human_turn and not adapter.has_active_overlay
                    and adapter.confirm_zero_category is None
                    and self.roll_button.handle_event(event) and not coord.is_rolling):
                adapter.do_roll()

            # Handle play again button (only when game is over)
            if game_over and self.play_again_button.handle_event(event):
                adapter.do_reset()

    def update(self):
        """Update animation display values, then tick via the adapter."""
        coord = self.coordinator

        # Snapshot rolling state before tick (for bounce detection)
        was_rolling = coord.is_rolling

        # During rolling, randomize display values for unheld dice (GUI-only animation)
        if coord.is_rolling:
            for i, die in enumerate(coord.dice):
                if not die.held:
                    self.animation_dice_values[i] = random.randint(1, 6)

        # Tick the coordinator and update adapter state (sounds, flash, game over)
        self.adapter.update()

        # After tick, if rolling just finished, sync animation values to final
        if not coord.is_rolling:
            self.animation_dice_values = [die.value for die in coord.dice]

        # Trigger bounce when rolling just ended
        if was_rolling and not coord.is_rolling:
            for i, die in enumerate(coord.dice):
                if not die.held:
                    self.bounce_active[i] = True
                    self.bounce_timers[i] = 0

        # Advance bounce timers
        for i in range(5):
            if self.bounce_active[i]:
                self.bounce_timers[i] += 1
                if self.bounce_timers[i] >= self.bounce_duration:
                    self.bounce_active[i] = False

    def _draw_category_row(self, cat, scorecard, dice, coord, font, scorecard_x, col_width, y):
        """Draw a single category row in the scorecard with proper theming."""
        cat_rect = pygame.Rect(scorecard_x - 5, y - 2, col_width + 50, 28)
        self.category_rects[cat] = cat_rect

        sc_bg = self._scorecard_bg()
        flash_hl = self._flash_highlight()

        if cat == self.score_flash_category:
            t = self.score_flash_timer / self.score_flash_duration
            alpha = (1 + math.sin(t * 4 * math.pi - math.pi / 2)) / 2
            flash_color = tuple(
                int(sc_bg[c] + (flash_hl[c] - sc_bg[c]) * alpha)
                for c in range(3)
            )
            pygame.draw.rect(self.screen, flash_color, cat_rect, border_radius=5)
        elif coord.ai_showing_score_choice and cat == coord.ai_score_choice_category:
            pygame.draw.rect(self.screen, self._ai_choice_highlight(), cat_rect, border_radius=5)
        elif not scorecard.is_filled(cat) and (
                self.hovered_category == cat
                or (self.kb_selected_index is not None and CATEGORY_ORDER[self.kb_selected_index] == cat)):
            pygame.draw.rect(self.screen, self._hover_color(), cat_rect, border_radius=5)

        name_text = font.render(cat.value, True, self._text_color())
        self.screen.blit(name_text, (scorecard_x, y))

        if scorecard.is_filled(cat):
            score = scorecard.scores[cat]
            score_color = self._text_color()
        else:
            score = calculate_score_in_context(cat, dice, scorecard)
            score_color = self._valid_color() if score > 0 else self._gray_color()

        score_text = font.render(str(score), True, score_color)
        self.screen.blit(score_text, (scorecard_x + col_width, y))

    def draw_scorecard(self):
        """Draw the scorecard UI on the right side of screen"""
        coord = self.coordinator
        scorecard = coord.scorecard
        dice = coord.dice
        lo = self.layout

        scorecard_x = lo.scorecard_x
        scorecard_y = lo.scorecard_y
        row_height = lo.scorecard_row_height
        col_width = lo.scorecard_col_width

        # Draw scorecard background panel
        panel_rect = pygame.Rect(
            scorecard_x - 15, lo.scorecard_panel_top,
            lo.scorecard_panel_width, lo.scorecard_panel_height,
        )
        pygame.draw.rect(self.screen, self._scorecard_bg(), panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, self._scorecard_border(), panel_rect, width=2, border_radius=12)

        # Fonts
        font = self._font(24)
        font_small = self._font(20)
        font_bold = self._font(28)

        text_color = self._text_color()
        header_color = self._section_header_color()

        y = scorecard_y

        # Player name header in multiplayer
        if coord.multiplayer:
            idx = coord.current_player_index
            name, _ = coord.player_configs[idx]
            color = self._player_colors()[idx % len(self._player_colors())]
            name_header = font_bold.render(f"{name}'s Scorecard", True, color)
            self.screen.blit(name_header, (scorecard_x, y))
            y += row_height + 2

        # Upper section header
        header = font_bold.render("UPPER SECTION", True, header_color)
        self.screen.blit(header, (scorecard_x, y))
        y += row_height + 5

        # Upper section categories
        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                     Category.FOURS, Category.FIVES, Category.SIXES]

        for cat in upper_cats:
            self._draw_category_row(cat, scorecard, dice, coord, font, scorecard_x, col_width, y)
            y += row_height

        # Upper section totals
        y += 5
        upper_total = scorecard.get_upper_section_total()
        total_text = font.render(f"Total: {upper_total}", True, text_color)
        self.screen.blit(total_text, (scorecard_x, y))
        y += row_height

        bonus = scorecard.get_upper_section_bonus()
        bonus_text = font_small.render(f"Bonus (63+): {bonus}", True, text_color)
        self.screen.blit(bonus_text, (scorecard_x, y))
        y += row_height + 10

        # Lower section header
        header = font_bold.render("LOWER SECTION", True, header_color)
        self.screen.blit(header, (scorecard_x, y))
        y += row_height + 5

        # Lower section categories
        lower_cats = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                     Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                     Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]

        for cat in lower_cats:
            self._draw_category_row(cat, scorecard, dice, coord, font, scorecard_x, col_width, y)
            y += row_height

        # Grand total
        y += 10
        grand_total = scorecard.get_grand_total()
        total_text = font_bold.render(f"GRAND TOTAL: {grand_total}", True, text_color)
        self.screen.blit(total_text, (scorecard_x, y))

        # Tooltip for hovered/selected unfilled category
        if not self.adapter.has_active_overlay and not coord.game_over and coord.rolls_used > 0:
            tooltip_cat = None
            if self.hovered_category is not None:
                tooltip_cat = self.hovered_category
            elif self.kb_selected_index is not None:
                tooltip_cat = CATEGORY_ORDER[self.kb_selected_index]
            if tooltip_cat is not None and not scorecard.is_filled(tooltip_cat):
                self._draw_tooltip(tooltip_cat, scorecard_x)

    def _draw_tooltip(self, category, scorecard_x):
        """Draw tooltip popup to the left of the scorecard for the hovered category."""
        tip_text = CATEGORY_TOOLTIPS.get(category)
        if not tip_text:
            return

        panel_bg, panel_border = self._panel_colors()
        tip_font = self._font(20)

        # Get the category row rect for vertical alignment
        cat_rect = self.category_rects.get(category)
        if cat_rect is None:
            return

        # Render text and measure
        text_surface = tip_font.render(tip_text, True, self._text_color())
        text_w, text_h = text_surface.get_size()

        # Position to the left of the scorecard panel
        padding = 8
        box_w = text_w + padding * 2
        box_h = text_h + padding * 2
        box_x = scorecard_x - 20 - box_w
        box_y = cat_rect.centery - box_h // 2

        # Draw tooltip box
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, panel_bg, box_rect, border_radius=6)
        pygame.draw.rect(self.screen, panel_border, box_rect, width=1, border_radius=6)

        # Draw text
        self.screen.blit(text_surface, (box_x + padding, box_y + padding))

    def draw_player_bar(self):
        """Draw horizontal bar showing all players' names and scores (multiplayer only)."""
        coord = self.coordinator
        bar_y = self.layout.player_bar_y
        bar_height = self.layout.player_bar_height
        font = self._font(26)
        num = coord.num_players
        # Calculate per-player chip width to fit across the available width
        bar_width = min(180, (WINDOW_WIDTH - 100) // num)
        total_width = bar_width * num
        start_x = (WINDOW_WIDTH - total_width) // 2

        for i in range(num):
            name, strategy = coord.player_configs[i]
            score = coord.all_scorecards[i].get_grand_total()
            color = self._player_colors()[i % len(self._player_colors())]
            chip_rect = pygame.Rect(start_x + i * bar_width, bar_y, bar_width - 4, bar_height)

            if i == coord.current_player_index and not coord.game_over:
                # Active player: filled background
                pygame.draw.rect(self.screen, color, chip_rect, border_radius=6)
                text_color = WHITE
            else:
                # Inactive: outlined
                pygame.draw.rect(self.screen, self._scorecard_bg(), chip_rect, border_radius=6)
                pygame.draw.rect(self.screen, color, chip_rect, width=2, border_radius=6)
                text_color = color

            label = f"{name}: {score}"
            text = font.render(label, True, text_color)
            text_rect = text.get_rect(center=chip_rect.center)
            self.screen.blit(text, text_rect)

    def draw_turn_transition(self):
        """Draw brief overlay showing whose turn it is next."""
        coord = self.coordinator
        if not coord.turn_transition:
            return
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        idx = coord.current_player_index
        name, strategy = coord.player_configs[idx]
        color = self._player_colors()[idx % len(self._player_colors())]

        font = self._font(56)
        if strategy is None:
            label = f"{name}'s Turn!"
        else:
            ai_name = strategy.__class__.__name__.replace("Strategy", "")
            label = f"{name}'s Turn! ({ai_name} AI)"

        text = font.render(label, True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))

        # Draw a colored rounded rect behind the text
        bg_rect = text_rect.inflate(40, 20)
        pygame.draw.rect(self.screen, color, bg_rect, border_radius=12)
        self.screen.blit(text, text_rect)

    def draw_game_over(self):
        """Draw the game over screen overlay."""
        coord = self.coordinator
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(self._game_over_overlay())
        self.screen.blit(overlay, (0, 0))

        if coord.multiplayer:
            self._draw_game_over_multiplayer()
        else:
            self._draw_game_over_single()

        # Play again button
        btn, hover, disabled, border = self._button_colors()
        self.play_again_button.draw(self.screen, button_color=btn, hover_color=hover,
                                    disabled_color=disabled, border_color=border)

    def _draw_game_over_single(self):
        """Draw single-player game over with per-category score breakdown."""
        coord = self.coordinator
        scorecard = coord.scorecard
        text_color = self._text_color()
        header_color = self._section_header_color()

        # Game Over title
        title_font = self._font(72)
        title_text = title_font.render("GAME OVER!", True, text_color)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 60))
        self.screen.blit(title_text, title_rect)

        # Final score
        score_font = self._font(56)
        final_score = scorecard.get_grand_total()
        score_text = score_font.render(f"Final Score: {final_score}", True, header_color)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 115))
        self.screen.blit(score_text, score_rect)

        # Fonts for breakdown
        header_font = self._font(30)
        cat_font = self._font(24)
        total_font = self._font(28)

        # --- Left column: Upper section ---
        left_x = 180
        y = 160

        header = header_font.render("UPPER SECTION", True, header_color)
        self.screen.blit(header, (left_x, y))
        y += 28

        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                      Category.FOURS, Category.FIVES, Category.SIXES]
        for cat in upper_cats:
            score = scorecard.scores.get(cat, 0)
            name_text = cat_font.render(cat.value, True, text_color)
            score_text = cat_font.render(str(score), True, text_color)
            self.screen.blit(name_text, (left_x + 10, y))
            self.screen.blit(score_text, (left_x + 160, y))
            y += 24

        y += 6
        upper_total = scorecard.get_upper_section_total()
        sub_text = total_font.render(f"Subtotal: {upper_total}", True, text_color)
        self.screen.blit(sub_text, (left_x + 10, y))
        y += 26

        bonus = scorecard.get_upper_section_bonus()
        bonus_color = self._valid_color() if bonus > 0 else self._gray_color()
        bonus_text = total_font.render(f"Bonus: {bonus}", True, bonus_color)
        self.screen.blit(bonus_text, (left_x + 10, y))

        # --- Right column: Lower section ---
        right_x = 550
        y = 160

        header = header_font.render("LOWER SECTION", True, header_color)
        self.screen.blit(header, (right_x, y))
        y += 28

        lower_cats = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                      Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                      Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]
        for cat in lower_cats:
            score = scorecard.scores.get(cat, 0)
            name_text = cat_font.render(cat.value, True, text_color)
            score_text = cat_font.render(str(score), True, text_color)
            self.screen.blit(name_text, (right_x + 10, y))
            self.screen.blit(score_text, (right_x + 160, y))
            y += 24

        y += 6
        lower_total = scorecard.get_lower_section_total()
        sub_text = total_font.render(f"Subtotal: {lower_total}", True, text_color)
        self.screen.blit(sub_text, (right_x + 10, y))

        # Grand total centered below both columns
        grand_font = self._font(40)
        grand_text = grand_font.render(f"GRAND TOTAL: {final_score}", True, text_color)
        grand_rect = grand_text.get_rect(center=(WINDOW_WIDTH // 2, 430))
        self.screen.blit(grand_text, grand_rect)

        # Yahtzee bonus row (only if any bonuses were earned)
        stats_y = 452
        if scorecard.yahtzee_bonus_count > 0:
            bonus_amount = scorecard.yahtzee_bonus_count * 100
            yb_font = self._font(30)
            yb_text = yb_font.render(f"Yahtzee Bonus: +{bonus_amount}", True, self._valid_color())
            yb_rect = yb_text.get_rect(center=(WINDOW_WIDTH // 2, stats_y))
            self.screen.blit(yb_text, yb_rect)
            stats_y += 24

        # Performance vs optimal (human players only, not AI spectator)
        is_human_game = coord.ai_strategy is None
        if is_human_game:
            pct = final_score / OPTIMAL_EXPECTED_TOTAL * 100
            pct_font = self._font(28)
            if pct >= 100:
                pct_color = self._valid_color()
            elif pct >= 70:
                pct_color = header_color
            else:
                pct_color = self._gray_color()
            pct_label = f"{pct:.0f}% of optimal play ({int(OPTIMAL_EXPECTED_TOTAL)} avg)"
            pct_text = pct_font.render(pct_label, True, pct_color)
            pct_rect = pct_text.get_rect(center=(WINDOW_WIDTH // 2, stats_y))
            self.screen.blit(pct_text, pct_rect)
            stats_y += 24

        # High scores section
        high_scores = self.adapter.get_high_scores(limit=5)
        if high_scores:
            hs_font = self._font(28)
            hs_label = hs_font.render("Top Human Scores", True, header_color)
            hs_rect = hs_label.get_rect(center=(WINDOW_WIDTH // 2, stats_y))
            self.screen.blit(hs_label, hs_rect)
            stats_y += 22

            hs_entry_font = self._font(24)
            dim_color = (160, 160, 170) if self.dark_mode else (80, 80, 80)
            for rank, entry in enumerate(high_scores):
                score_val = entry.get("score", 0)
                date_str = entry.get("date", "")[:10]  # Just the date part
                is_current = (score_val == final_score and rank == 0)
                color = (180, 80, 80) if is_current else dim_color
                label = f"{rank + 1}. {score_val}   ({date_str})"
                hs_text = hs_entry_font.render(label, True, color)
                hs_text_rect = hs_text.get_rect(center=(WINDOW_WIDTH // 2, stats_y))
                self.screen.blit(hs_text, hs_text_rect)
                stats_y += 22

    def _draw_scorecard_grid(self, grid_x, grid_y, row_height, show_optimal=False):
        """Draw a full per-category scorecard grid for all players.

        Shared helper used by both the game-over screen and the mid-game
        scores overlay to avoid duplicating grid rendering logic.

        Args:
            grid_x: Left edge X of the grid.
            grid_y: Top Y of the grid (player name headers start here).
            row_height: Vertical spacing between rows.
            show_optimal: If True, show "% Optimal" row for human players.
        """
        coord = self.coordinator
        num = coord.num_players
        text_color = self._text_color()
        header_color = self._section_header_color()

        totals = [coord.all_scorecards[i].get_grand_total() for i in range(num)]
        winner_idx = max(range(num), key=lambda i: totals[i])

        label_col_width = 140
        player_col_width = min(130, (WINDOW_WIDTH - label_col_width - 80) // num)

        cat_font = self._font(21)
        header_font = self._font(22)
        section_font = self._font(22)
        total_font = self._font(24)

        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                      Category.FOURS, Category.FIVES, Category.SIXES]
        lower_cats = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                      Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                      Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]

        y = grid_y

        # Player name headers
        for i in range(num):
            name = coord.player_configs[i][0]
            color = self._player_colors()[i % len(self._player_colors())]
            col_x = grid_x + label_col_width + i * player_col_width
            name_text = header_font.render(name, True, color)
            name_rect = name_text.get_rect(centerx=col_x + player_col_width // 2, top=y)
            self.screen.blit(name_text, name_rect)
        y += row_height + 4

        # --- Upper section ---
        section_text = section_font.render("UPPER SECTION", True, header_color)
        self.screen.blit(section_text, (grid_x, y))
        y += row_height

        for cat in upper_cats:
            label = cat_font.render(cat.value, True, text_color)
            self.screen.blit(label, (grid_x + 8, y))
            for i in range(num):
                sc = coord.all_scorecards[i]
                score = sc.scores.get(cat, 0)
                col_x = grid_x + label_col_width + i * player_col_width
                score_text = cat_font.render(str(score), True, text_color)
                score_rect = score_text.get_rect(centerx=col_x + player_col_width // 2, top=y)
                self.screen.blit(score_text, score_rect)
            y += row_height

        # Upper subtotal + bonus
        y += 2
        label = cat_font.render("Subtotal", True, text_color)
        self.screen.blit(label, (grid_x + 8, y))
        for i in range(num):
            sc = coord.all_scorecards[i]
            val = sc.get_upper_section_total()
            col_x = grid_x + label_col_width + i * player_col_width
            text = cat_font.render(str(val), True, text_color)
            rect = text.get_rect(centerx=col_x + player_col_width // 2, top=y)
            self.screen.blit(text, rect)
        y += row_height

        label = cat_font.render("Bonus", True, text_color)
        self.screen.blit(label, (grid_x + 8, y))
        for i in range(num):
            sc = coord.all_scorecards[i]
            val = sc.get_upper_section_bonus()
            col_x = grid_x + label_col_width + i * player_col_width
            color = self._valid_color() if val > 0 else self._gray_color()
            text = cat_font.render(str(val), True, color)
            rect = text.get_rect(centerx=col_x + player_col_width // 2, top=y)
            self.screen.blit(text, rect)
        y += row_height + 4

        # --- Lower section ---
        section_text = section_font.render("LOWER SECTION", True, header_color)
        self.screen.blit(section_text, (grid_x, y))
        y += row_height

        for cat in lower_cats:
            label = cat_font.render(cat.value, True, text_color)
            self.screen.blit(label, (grid_x + 8, y))
            for i in range(num):
                sc = coord.all_scorecards[i]
                score = sc.scores.get(cat, 0)
                col_x = grid_x + label_col_width + i * player_col_width
                score_text = cat_font.render(str(score), True, text_color)
                score_rect = score_text.get_rect(centerx=col_x + player_col_width // 2, top=y)
                self.screen.blit(score_text, score_rect)
            y += row_height

        # Grand total
        y += 6
        label = total_font.render("GRAND TOTAL", True, text_color)
        self.screen.blit(label, (grid_x, y))
        for i in range(num):
            val = totals[i]
            col_x = grid_x + label_col_width + i * player_col_width
            color = self._player_colors()[i % len(self._player_colors())]
            is_winner = (i == winner_idx) and coord.game_over
            text = total_font.render(str(val), True, color)
            rect = text.get_rect(centerx=col_x + player_col_width // 2, top=y)
            if is_winner:
                highlight_rect = rect.inflate(16, 4)
                pygame.draw.rect(self.screen, self._winner_highlight(), highlight_rect, border_radius=4)
            self.screen.blit(text, rect)

        # % of optimal for human players (game-over only)
        if show_optimal:
            any_human = any(s is None for _, s in coord.player_configs)
            if any_human:
                y += row_height
                label = cat_font.render("% Optimal", True, text_color)
                self.screen.blit(label, (grid_x + 8, y))
                for i in range(num):
                    _, strategy = coord.player_configs[i]
                    if strategy is None:
                        pct = totals[i] / OPTIMAL_EXPECTED_TOTAL * 100
                        pct_str = f"{pct:.0f}%"
                        if pct >= 100:
                            color = self._valid_color()
                        elif pct >= 70:
                            color = header_color
                        else:
                            color = self._gray_color()
                    else:
                        pct_str = ""
                        color = self._gray_color()
                    col_x = grid_x + label_col_width + i * player_col_width
                    text = cat_font.render(pct_str, True, color)
                    rect = text.get_rect(centerx=col_x + player_col_width // 2, top=y)
                    self.screen.blit(text, rect)

        # Yahtzee bonus row (only if any player earned bonuses)
        any_bonuses = any(coord.all_scorecards[i].yahtzee_bonus_count > 0 for i in range(num))
        if any_bonuses:
            y += row_height + 2
            label = cat_font.render("Yahtzee Bonus", True, text_color)
            self.screen.blit(label, (grid_x + 8, y))
            for i in range(num):
                sc = coord.all_scorecards[i]
                if sc.yahtzee_bonus_count > 0:
                    bonus_str = f"+{sc.yahtzee_bonus_count * 100}"
                    color = self._valid_color()
                else:
                    bonus_str = "0"
                    color = self._gray_color()
                col_x = grid_x + label_col_width + i * player_col_width
                text = cat_font.render(bonus_str, True, color)
                rect = text.get_rect(centerx=col_x + player_col_width // 2, top=y)
                self.screen.blit(text, rect)

    def _draw_game_over_multiplayer(self):
        """Draw multiplayer game over with full per-category scorecard grid."""
        coord = self.coordinator
        text_color = self._text_color()

        # Game Over title
        title_font = self._font(64)
        title_text = title_font.render("GAME OVER!", True, text_color)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 45))
        self.screen.blit(title_text, title_rect)

        # Find winner
        num = coord.num_players
        totals = [coord.all_scorecards[i].get_grand_total() for i in range(num)]
        winner_idx = max(range(num), key=lambda i: totals[i])
        winner_name = coord.player_configs[winner_idx][0]
        winner_color = self._player_colors()[winner_idx % len(self._player_colors())]

        winner_font = self._font(36)
        winner_text = winner_font.render(f"{winner_name} wins!", True, winner_color)
        winner_rect = winner_text.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.screen.blit(winner_text, winner_rect)

        # Compute grid position (same layout as before extraction)
        label_col_width = 140
        player_col_width = min(130, (WINDOW_WIDTH - label_col_width - 80) // num)
        grid_width = label_col_width + player_col_width * num
        grid_x = (WINDOW_WIDTH - grid_width) // 2

        self._draw_scorecard_grid(grid_x, 105, row_height=22, show_optimal=True)

    def draw_scores_overlay(self):
        """Draw semi-transparent overlay showing all players' full scorecards.

        Only available in multiplayer — lets players see opponents' per-category
        scores during the game instead of just the grand totals in the player bar.
        """
        coord = self.coordinator
        num = coord.num_players
        header_color = self._section_header_color()

        # Semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Panel
        panel_bg, panel_border = self._panel_colors()
        panel_w, panel_h = 700, 550
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, panel_border, panel_rect, width=2, border_radius=12)

        # Title
        title_font = self._font(48)
        title = title_font.render("ALL SCORES", True, header_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 35))
        self.screen.blit(title, title_rect)

        # Compute grid position inside the panel
        label_col_width = 140
        player_col_width = min(130, (panel_w - label_col_width - 40) // num)
        grid_width = label_col_width + player_col_width * num
        grid_x = (WINDOW_WIDTH - grid_width) // 2

        self._draw_scorecard_grid(grid_x, panel_y + 65, row_height=22)

        # Footer
        footer_font = self._font(24)
        footer = footer_font.render("S or Escape to close", True, self._gray_color())
        footer_rect = footer.get_rect(center=(WINDOW_WIDTH // 2, panel_y + panel_h - 25))
        self.screen.blit(footer, footer_rect)

    def draw_history_overlay(self):
        """Draw semi-transparent overlay showing recent score history."""
        panel_bg, panel_border = self._panel_colors()
        header_color = self._section_header_color()

        # Semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = 700, 550
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, panel_border, panel_rect, width=2, border_radius=12)

        # Title
        title_font = self._font(48)
        title = title_font.render("SCORE HISTORY", True, header_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 35))
        self.screen.blit(title, title_rect)

        # Filter bar
        filter_font = self._font(22)
        filter_y = panel_y + 60
        player_label = self.history_filter_player.capitalize()
        mode_label = self.history_filter_mode.capitalize()
        dim_color = self._gray_color()
        p_color = header_color if self.history_filter_player != "all" else dim_color
        m_color = header_color if self.history_filter_mode != "all" else dim_color
        filter_text = filter_font.render(f"Player: {player_label}  (P)", True, p_color)
        self.screen.blit(filter_text, (panel_x + 40, filter_y))
        filter_text2 = filter_font.render(f"Mode: {mode_label}  (M)", True, m_color)
        self.screen.blit(filter_text2, (panel_x + 350, filter_y))

        # Column headers
        header_font = self._font(26)
        header_y = panel_y + 85
        headers = [("Rank", panel_x + 40), ("Score", panel_x + 110),
                   ("Player", panel_x + 210), ("Mode", panel_x + 350),
                   ("Date", panel_x + 470)]
        for text, x in headers:
            surface = header_font.render(text, True, header_color)
            self.screen.blit(surface, (x, header_y))

        # Divider line
        divider_color = self._scorecard_border()
        pygame.draw.line(self.screen, divider_color,
                         (panel_x + 20, header_y + 25),
                         (panel_x + panel_w - 20, header_y + 25))

        # Score entries (use adapter's filtered history)
        entries = self.adapter.get_filtered_history(limit=20)
        entry_font = self._font(24)
        row_y = header_y + 35

        if not entries:
            no_data = entry_font.render("No scores recorded yet.", True, self._gray_color())
            no_rect = no_data.get_rect(center=(WINDOW_WIDTH // 2, row_y + 40))
            self.screen.blit(no_data, no_rect)
        else:
            for i, entry in enumerate(entries):
                if self.dark_mode:
                    color = (190, 190, 200) if i % 2 == 0 else (160, 160, 170)
                else:
                    color = (60, 60, 60) if i % 2 == 0 else (80, 80, 80)

                rank_text = entry_font.render(str(i + 1), True, color)
                self.screen.blit(rank_text, (panel_x + 50, row_y))

                score_text = entry_font.render(str(entry.get("score", "?")), True, color)
                self.screen.blit(score_text, (panel_x + 110, row_y))

                player = entry.get("player_type", "?")
                player_text = entry_font.render(player.capitalize(), True, color)
                self.screen.blit(player_text, (panel_x + 210, row_y))

                mode = entry.get("mode", "?")
                mode_text = entry_font.render(mode.capitalize(), True, color)
                self.screen.blit(mode_text, (panel_x + 350, row_y))

                date = entry.get("date", "")[:10]
                date_text = entry_font.render(date, True, color)
                self.screen.blit(date_text, (panel_x + 470, row_y))

                row_y += 22

        # Footer
        footer_font = self._font(24)
        footer = footer_font.render("P/M: filter  |  H or Escape to close", True, self._gray_color())
        footer_rect = footer.get_rect(center=(WINDOW_WIDTH // 2, panel_y + panel_h - 25))
        self.screen.blit(footer, footer_rect)

    def draw_confirm_dialog(self):
        """Draw a small centered dialog asking to confirm scoring 0."""
        cat = self.confirm_zero_category
        if cat is None:
            return

        panel_bg, panel_border = self._panel_colors()

        # Semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # Dialog box
        dialog_w, dialog_h = 360, 120
        dialog_x = (WINDOW_WIDTH - dialog_w) // 2
        dialog_y = (WINDOW_HEIGHT - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(self.screen, panel_bg, dialog_rect, border_radius=10)
        pygame.draw.rect(self.screen, (180, 80, 80), dialog_rect, width=2, border_radius=10)

        # Question text
        q_font = self._font(28)
        q_text = q_font.render(f"Score 0 in {cat.value}?", True, self._text_color())
        q_rect = q_text.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 40))
        self.screen.blit(q_text, q_rect)

        # Instructions
        i_font = self._font(22)
        i_text = i_font.render("Y / Enter to confirm,  N / Esc to cancel", True, self._gray_color())
        i_rect = i_text.get_rect(center=(WINDOW_WIDTH // 2, dialog_y + 80))
        self.screen.blit(i_text, i_rect)

    def draw_help_overlay(self):
        """Draw semi-transparent overlay showing keyboard controls."""
        panel_bg, panel_border = self._panel_colors()
        header_color = self._section_header_color()
        text_color = self._text_color()

        # Semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = 500, 500
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, panel_border, panel_rect, width=2, border_radius=12)

        # Title
        title_font = self._font(48)
        title = title_font.render("CONTROLS", True, header_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 35))
        self.screen.blit(title, title_rect)

        # Key-action pairs
        controls = [
            ("Space", "Roll dice"),
            ("1-5", "Toggle die hold"),
            ("Tab / \u2193", "Next category"),
            ("Shift+Tab / \u2191", "Previous category"),
            ("Enter", "Score selected category"),
            ("H", "Score history"),
            ("S", "All player scores (multiplayer)"),
            ("M", "Toggle sound"),
            ("+/-", "AI speed"),
            ("Ctrl+Z", "Undo"),
            ("C", "Colorblind mode"),
            ("D", "Dark mode"),
            ("R", "Game replay (after game)"),
            ("Esc", "Close overlay / Quit"),
            ("? / F1", "This help screen"),
        ]

        key_font = self._font(26)
        desc_font = self._font(24)
        row_y = panel_y + 70
        key_x = panel_x + 40
        desc_x = panel_x + 220

        for key, desc in controls:
            key_surface = key_font.render(key, True, header_color)
            desc_surface = desc_font.render(desc, True, text_color)
            self.screen.blit(key_surface, (key_x, row_y))
            self.screen.blit(desc_surface, (desc_x, row_y))
            row_y += 26

        # Footer
        footer_font = self._font(24)
        footer = footer_font.render("Press ? or Escape to close", True, self._gray_color())
        footer_rect = footer.get_rect(center=(WINDOW_WIDTH // 2, panel_y + panel_h - 25))
        self.screen.blit(footer, footer_rect)

    def draw_replay_overlay(self):
        """Draw post-game replay overlay showing turn-by-turn summary."""
        panel_bg, panel_border = self._panel_colors()
        header_color = self._section_header_color()
        text_color = self._text_color()
        coord = self.coordinator
        game_log = coord.game_log

        # Semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = 700, 550
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, panel_border, panel_rect, width=2, border_radius=12)

        # Title
        title_font = self._font(48)
        title = title_font.render("GAME REPLAY", True, header_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 35))
        self.screen.blit(title, title_rect)

        # Build turn summaries for player 0 (single-player) or all players
        entry_font = self._font(22)
        row_y = panel_y + 70

        # For single-player, show one column; for multiplayer, just show scoring summary
        score_entries = game_log.get_score_entries(player_index=0)
        if not score_entries:
            # Try to show all players' entries
            all_score_entries = [e for e in game_log.entries if e.event_type == "score"]
            if all_score_entries:
                score_entries = all_score_entries
            else:
                no_data = entry_font.render("No replay data available.", True, self._gray_color())
                no_rect = no_data.get_rect(center=(WINDOW_WIDTH // 2, row_y + 60))
                self.screen.blit(no_data, no_rect)

        for entry in score_entries:
            if row_y > panel_y + panel_h - 60:
                break

            # Build the turn summary line
            turn_entries = game_log.get_turn_entries(entry.turn, entry.player_index)
            rolls = [e for e in turn_entries if e.event_type == "roll"]

            # Format: "Turn 3: [2,3,3,5,6] → 3 of a Kind: 20"
            dice_str = ""
            if rolls:
                parts = []
                for r in rolls:
                    parts.append(f"[{','.join(str(v) for v in r.dice_values)}]")
                dice_str = " → ".join(parts)

            cat_name = entry.category.value if entry.category else "?"
            score_val = entry.score if entry.score is not None else "?"

            # Player prefix for multiplayer
            if coord.multiplayer:
                pname = (coord.player_configs[entry.player_index][0]
                        if entry.player_index < len(coord.player_configs)
                        else f"P{entry.player_index}")
                line = f"T{entry.turn} {pname}: {dice_str} → {cat_name}: {score_val}"
            else:
                line = f"Turn {entry.turn}: {dice_str} → {cat_name}: {score_val}"

            # Truncate if too long
            max_w = panel_w - 40
            while entry_font.size(line)[0] > max_w and len(line) > 20:
                line = line[:-4] + "..."

            text_surface = entry_font.render(line, True, text_color)
            self.screen.blit(text_surface, (panel_x + 20, row_y))
            row_y += 26

        # Footer
        footer_font = self._font(24)
        footer = footer_font.render("R or Escape to close", True, self._gray_color())
        footer_rect = footer.get_rect(center=(WINDOW_WIDTH // 2, panel_y + panel_h - 25))
        self.screen.blit(footer, footer_rect)

    def draw(self):
        """Draw everything to the screen"""
        coord = self.coordinator
        text_color = self._text_color()
        header_color = self._section_header_color()

        # Clear screen with themed background color
        self.screen.fill(self._bg_color())

        dice = coord.dice
        rolls_used = coord.rolls_used
        game_over = coord.game_over
        current_round = coord.current_round

        lo = self.layout

        # Draw title with shadow effect
        font = self._font(72)
        shadow_color = (60, 60, 70) if self.dark_mode else (180, 180, 180)
        title_shadow = font.render("YAHTZEE", True, shadow_color)
        shadow_rect = title_shadow.get_rect(center=(WINDOW_WIDTH // 2 + 3, lo.title_y + 3))
        self.screen.blit(title_shadow, shadow_rect)
        title = font.render("YAHTZEE", True, header_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, lo.title_y))
        self.screen.blit(title, title_rect)

        # Draw round and turn indicator
        round_font = self._font(36)
        if coord.multiplayer:
            idx = coord.current_player_index
            name, strategy = coord.player_configs[idx]
            color = self._player_colors()[idx % len(self._player_colors())]
            if strategy is None:
                turn_label = f"Round {current_round}/13 — Your turn ({name})"
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                turn_label = f"Round {current_round}/13 — {name}'s turn ({ai_name} AI)"
            round_text = round_font.render(turn_label, True, color)
            self.screen.blit(round_text, (50, lo.round_text_y))
        else:
            round_text = round_font.render(f"Round {current_round}/13", True, text_color)
            self.screen.blit(round_text, (50, lo.round_text_y))

        # Draw AI/speed indicator
        if not coord.multiplayer and coord.ai_strategy:
            ai_font = self._font(28)
            ai_name = coord.ai_strategy.__class__.__name__.replace("Strategy", "")
            speed_label = coord.speed_name.capitalize()
            ai_text = ai_font.render(f"AI: {ai_name} | Speed: {speed_label} (+/-)", True, (180, 80, 80))
            self.screen.blit(ai_text, (50, lo.ai_indicator_y))
        elif coord.multiplayer and coord.has_any_ai:
            ai_font = self._font(24)
            speed_label = coord.speed_name.capitalize()
            ai_text = ai_font.render(f"Speed: {speed_label} (+/-)", True, self._gray_color())
            self.screen.blit(ai_text, (50, lo.ai_indicator_y))

        # Draw player bar (multiplayer only)
        if coord.multiplayer:
            self.draw_player_bar()

        # Get dice theme colors
        dice_c, dot_c, shadow_c, border_c = self._dice_colors()
        cup_c, cup_shadow, cup_border, cup_text = self._cup_colors()

        # Draw all dice sprites
        for i, sprite in enumerate(self.dice_sprites):
            die_state = dice[i]

            if rolls_used == 0 and not coord.is_rolling:
                sprite.draw_in_cup(self.screen, cup_color=cup_c, shadow_color=cup_shadow,
                                   border_color=cup_border, text_color=cup_text)
                continue

            if coord.is_rolling:
                display_value = self.animation_dice_values[i]
                display_state = DieState(value=display_value, held=die_state.held)
            else:
                display_state = die_state

            if coord.is_rolling and not die_state.held:
                shake_x = int(math.sin(coord.roll_timer * 0.5) * 3)
                shake_y = int(math.cos(coord.roll_timer * 0.7) * 3)
                sprite.draw(self.screen, display_state, shake_x, shake_y,
                            colorblind=self.colorblind_mode,
                            dice_color=dice_c, dot_color=dot_c,
                            shadow_color=shadow_c, border_color=border_c)
            else:
                # Apply bounce offset (damped upward hop after landing)
                bounce_y = 0
                if self.bounce_active[i]:
                    t = self.bounce_timers[i] / self.bounce_duration
                    bounce_y = int(-8 * math.sin(t * math.pi) * (1 - t))
                sprite.draw(self.screen, display_state, offset_y=bounce_y,
                            colorblind=self.colorblind_mode,
                            dice_color=dice_c, dot_color=dot_c,
                            shadow_color=shadow_c, border_color=border_c)

        # Draw roll button
        self.roll_button.enabled = coord.can_roll_now
        btn, hover, disabled, btn_border = self._button_colors()
        self.roll_button.draw(self.screen, button_color=btn, hover_color=hover,
                              disabled_color=disabled, border_color=btn_border)

        # Draw roll status
        roll_font = self._font(32)
        if rolls_used == 0:
            roll_text = roll_font.render("Roll the dice!", True, header_color)
        else:
            rolls_remaining = MAX_ROLLS_PER_TURN - rolls_used
            roll_text = roll_font.render(f"Rolls left: {rolls_remaining}", True, text_color)
        self.screen.blit(roll_text, (200, lo.roll_status_y))

        # Draw AI reasoning text below roll status
        if coord.current_ai_strategy and coord.ai_reason:
            reason_font = self._font(24)
            max_width = 480
            words = coord.ai_reason.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if reason_font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            reason_color = self._gray_color()
            reason_y = lo.ai_reason_y
            for line in lines:
                reason_surface = reason_font.render(line, True, reason_color)
                self.screen.blit(reason_surface, (80, reason_y))
                reason_y += 20

        # Draw scorecard
        self.draw_scorecard()

        # Draw game over screen if game is over
        if game_over:
            self.draw_game_over()

        # Draw turn transition overlay (on top of everything)
        if coord.multiplayer:
            self.draw_turn_transition()

        # Draw zero-score confirmation dialog
        if self.confirm_zero_category is not None:
            self.draw_confirm_dialog()

        # Draw scores overlay (multiplayer all-player scores)
        if self.showing_scores:
            self.draw_scores_overlay()

        # Draw history overlay
        if self.showing_history:
            self.draw_history_overlay()

        # Draw replay overlay
        if self.showing_replay:
            self.draw_replay_overlay()

        # Draw help overlay
        if self.showing_help:
            self.draw_help_overlay()

        # Update display
        pygame.display.flip()

    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def _prompt_resume(screen, clock):
    """Show a simple pygame prompt asking to resume a previous game.

    Returns True if user wants to resume, False otherwise.
    """
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 32)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return True
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    return False

        screen.fill(BACKGROUND)
        title = font.render("Resume previous game?", True, SECTION_HEADER_COLOR)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
        screen.blit(title, title_rect)

        hint = small_font.render("Y to resume,  N to start fresh", True, (100, 100, 100))
        hint_rect = hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
        screen.blit(hint, hint_rect)

        pygame.display.flip()
        clock.tick(FPS)


def _apply_settings(game):
    """Apply persisted settings to a game instance at startup."""
    game.adapter.load_settings()


def main():
    """Entry point for the game"""
    args = parse_args()
    print("Yahtzee! Use --help for options, --players for multiplayer")

    # Check for autosave before processing args
    saved_coord = GameCoordinator.load_state()
    if saved_coord is not None:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Yahtzee")
        clock = pygame.time.Clock()
        if _prompt_resume(screen, clock):
            game = YahtzeeGame(coordinator=saved_coord)
            _apply_settings(game)
            game.run()
            return
        # User declined — clear the save and continue with fresh game
        GameCoordinator.clear_autosave()

    if args.players:
        # Multiplayer mode
        if len(args.players) < 2:
            print("Error: --players requires at least 2 players")
            sys.exit(1)
        if len(args.players) > 4:
            print("Error: --players supports at most 4 players")
            sys.exit(1)
        if args.names and len(args.names) != len(args.players):
            print(f"Error: --names count ({len(args.names)}) must match --players count ({len(args.players)})")
            sys.exit(1)

        players = []
        for i, token in enumerate(args.players):
            strategy = _make_strategy(token)
            if args.names:
                name = args.names[i]
            elif strategy is None:
                name = f"Player {i + 1}"
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                name = f"P{i + 1} {ai_name}"
            players.append((name, strategy))

        game = YahtzeeGame(speed=args.speed, players=players)
    else:
        # Single-player mode (backward compatible)
        ai_strategy = None
        if args.ai:
            if args.random:
                ai_strategy = _make_strategy("random")
            elif args.ev:
                ai_strategy = _make_strategy("ev")
            elif args.optimal:
                ai_strategy = _make_strategy("optimal")
            else:
                ai_strategy = _make_strategy("greedy")

        game = YahtzeeGame(ai_strategy=ai_strategy, speed=args.speed)

    _apply_settings(game)
    game.run()


if __name__ == "__main__":
    main()
