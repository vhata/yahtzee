#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame
"""
import argparse
import pygame
import sys
import random
import math
from game_engine import (
    Category, Scorecard, calculate_score,
    GameState, DieState,
    roll_dice as engine_roll_dice,
    toggle_die_hold as engine_toggle_die,
    select_category as engine_select_category,
    can_roll, can_select_category,
    reset_game as engine_reset_game,
    MultiplayerGameState,
    mp_roll_dice, mp_toggle_die_hold, mp_select_category,
    mp_can_roll, mp_can_select_category, mp_get_current_scorecard,
)
from ai import (
    RollAction, ScoreAction,
    RandomStrategy, GreedyStrategy, ExpectedValueStrategy,
)

# Initialize pygame
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
PLAYER_COLORS = [
    (70, 130, 180),   # Steel blue (Player 1)
    (180, 80, 80),    # Red (Player 2)
    (80, 160, 80),    # Green (Player 3)
    (160, 120, 50),   # Gold (Player 4)
]

# Dice constants
DICE_SIZE = 80
DICE_MARGIN = 20
DOT_RADIUS = 6

# Game constants
MAX_ROLLS_PER_TURN = 3

# Speed presets for AI playback: (ai_delay, roll_duration, hold_show_duration) in frames
SPEED_PRESETS = {
    "slow":   (60, 90, 30),
    "normal": (30, 60, 20),
    "fast":   (10, 20, 8),
}
SPEED_NAMES = ["slow", "normal", "fast"]


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

    def draw(self, surface, die_state, offset_x=0, offset_y=0):
        """
        Draw the die based on its state.

        Args:
            surface: pygame surface to draw on
            die_state: DieState object with value and held status
            offset_x: X offset for animation effects
            offset_y: Y offset for animation effects
        """
        # Apply offsets for animation effects
        x = self.x + offset_x
        y = self.y + offset_y

        # Draw subtle shadow for depth
        shadow_rect = pygame.Rect(x + 3, y + 3, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, (200, 200, 200, 50), shadow_rect, border_radius=10)

        # Draw dice background
        dice_rect = pygame.Rect(x, y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, DICE_COLOR, dice_rect, border_radius=10)

        # Draw border - thicker and colored if held
        if die_state.held:
            # Green highlight for held dice
            pygame.draw.rect(surface, (50, 200, 50), dice_rect, width=5, border_radius=10)
        else:
            pygame.draw.rect(surface, (100, 100, 100), dice_rect, width=2, border_radius=10)

        # Draw dots based on value
        self._draw_dots(surface, die_state.value, offset_x, offset_y)

    def draw_in_cup(self, surface):
        """Draw the die in its 'in the cup' state — face-down, gray, with '?' text.

        Used when rolls_used == 0 to show dice haven't been rolled yet this turn.
        """
        # Draw subtle shadow
        shadow_rect = pygame.Rect(self.x + 3, self.y + 3, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, (200, 200, 200, 50), shadow_rect, border_radius=10)

        # Gray background
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, IN_CUP_COLOR, dice_rect, border_radius=10)

        # Light border
        pygame.draw.rect(surface, (150, 155, 165), dice_rect, width=2, border_radius=10)

        # "?" text centered on the die
        font = pygame.font.Font(None, 48)
        text = font.render("?", True, (120, 125, 135))
        text_rect = text.get_rect(center=(self.x + DICE_SIZE // 2, self.y + DICE_SIZE // 2))
        surface.blit(text, text_rect)

    def _draw_dots(self, surface, value, offset_x=0, offset_y=0):
        """
        Draw the dots/pips on the die face.

        Args:
            surface: pygame surface to draw on
            value: Die value (1-6)
            offset_x: X offset for animation effects
            offset_y: Y offset for animation effects
        """
        # Calculate dot positions relative to die center
        center_x = self.x + DICE_SIZE // 2 + offset_x
        center_y = self.y + DICE_SIZE // 2 + offset_y
        offset = DICE_SIZE // 4

        # Define dot positions for each value
        # 1: center
        if value == 1:
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)

        # 2: diagonal top-left to bottom-right
        elif value == 2:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 3: diagonal plus center
        elif value == 3:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 4: four corners
        elif value == 4:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 5: four corners plus center
        elif value == 5:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 6: two columns of three
        elif value == 6:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)


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

    def draw(self, surface):
        """Draw the button"""
        # Choose color based on state
        if not self.enabled:
            color = GRAY
        elif self.is_hovered:
            color = BUTTON_HOVER_COLOR
        else:
            color = BUTTON_COLOR

        # Draw button background
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, BLACK, self.rect, width=2, border_radius=8)

        # Draw button text
        text_surface = self.font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class YahtzeeGame:
    """Main game class for Yahtzee"""

    def __init__(self, ai_strategy=None, speed="normal", players=None):
        """Initialize the game window and basic components

        Args:
            ai_strategy: Optional AI strategy instance. If provided, AI plays the game.
                         Used only in single-player mode.
            speed: Speed preset name for AI playback ("slow", "normal", "fast").
            players: Optional list of (name, strategy_or_None) tuples for multiplayer.
                     None means single-player mode (backward compatible).
        """
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Yahtzee")
        self.clock = pygame.time.Clock()
        self.running = True

        # Multiplayer mode
        self.multiplayer = players is not None
        if self.multiplayer:
            self.player_configs = players  # list of (name, strategy_or_None)
            self.mp_state = MultiplayerGameState.create_initial(len(players))
            # Synthetic single-player state not used; use mp_state instead
            self.state = None
            # Turn transition overlay
            self.turn_transition = True  # Show initial "Player 1's turn!" overlay
            self.turn_transition_timer = 0
            self.turn_transition_duration = 45  # frames (~0.75 sec)
        else:
            self.player_configs = None
            self.mp_state = None
            # Game state (from engine) — single-player path
            self.state = GameState.create_initial()
            self.turn_transition = False

        # AI state (shared by both modes)
        self.ai_strategy = ai_strategy  # single-player only
        self.ai_timer = 0
        self.speed_name = speed
        self.ai_delay, self.roll_duration, self.ai_hold_show_duration = SPEED_PRESETS[self.speed_name]
        self.ai_needs_first_roll = True  # AI needs to roll at start of each turn
        self.ai_reason = ""  # Latest AI reasoning explanation
        self.ai_showing_holds = False  # Pause to show AI's held dice before rolling
        self.ai_hold_timer = 0

        # Dice sprites (visual representation only)
        self.dice_sprites = []
        dice_y = 300
        # Position dice on left side to avoid scorecard overlap
        start_x = 80

        for i in range(5):
            x = start_x + i * (DICE_SIZE + DICE_MARGIN)
            sprite = DiceSprite(x, dice_y)
            self.dice_sprites.append(sprite)

        # Create roll button (positioned on left side with dice)
        button_width = 150
        button_height = 50
        button_x = start_x + 165  # Center under dice area
        button_y = 500
        self.roll_button = Button(button_x, button_y, button_width, button_height, "ROLL")

        # Play again button (for game over screen)
        play_again_width = 200
        play_again_height = 60
        play_again_x = (WINDOW_WIDTH - play_again_width) // 2
        play_again_y = 550
        self.play_again_button = Button(play_again_x, play_again_y, play_again_width, play_again_height, "PLAY AGAIN", 40)

        # Animation state (GUI concern only)
        self.is_rolling = False
        self.roll_timer = 0
        initial_dice = self.mp_state.dice if self.multiplayer else self.state.dice
        self.animation_dice_values = [die.value for die in initial_dice]
        self.final_values = []
        self._pending_state = None  # State to commit after animation
        self._pending_mp_state = None  # Multiplayer state to commit after animation

        # UI state
        self.category_rects = {}  # Maps Category to pygame.Rect for click detection
        self.hovered_category = None

    def reset_game(self):
        """Reset the game to start a new game"""
        if self.multiplayer:
            self.mp_state = MultiplayerGameState.create_initial(len(self.player_configs))
            self.animation_dice_values = [die.value for die in self.mp_state.dice]
            self.turn_transition = True
            self.turn_transition_timer = 0
        else:
            self.state = engine_reset_game()
            self.animation_dice_values = [die.value for die in self.state.dice]
        self.ai_needs_first_roll = True
        self.ai_timer = 0
        self.ai_reason = ""
        self.ai_showing_holds = False
        self.ai_hold_timer = 0

    def roll_dice(self):
        """Start the dice rolling animation"""
        if self.multiplayer:
            if not self.is_rolling and mp_can_roll(self.mp_state):
                self.is_rolling = True
                self.roll_timer = 0
                new_mp_state = mp_roll_dice(self.mp_state)
                self.final_values = [die.value for die in new_mp_state.dice]
                self._pending_mp_state = new_mp_state
        else:
            if not self.is_rolling and can_roll(self.state):
                self.is_rolling = True
                self.roll_timer = 0
                new_state = engine_roll_dice(self.state)
                self.final_values = [die.value for die in new_state.dice]
                self._pending_state = new_state

    def _get_dice(self):
        """Get current dice tuple from the active game state."""
        return self.mp_state.dice if self.multiplayer else self.state.dice

    def _get_rolls_used(self):
        """Get current rolls_used from the active game state."""
        return self.mp_state.rolls_used if self.multiplayer else self.state.rolls_used

    def _is_game_over(self):
        """Check if the game is over."""
        return self.mp_state.game_over if self.multiplayer else self.state.game_over

    def _get_current_round(self):
        """Get the current round number."""
        return self.mp_state.current_round if self.multiplayer else self.state.current_round

    def _get_scorecard(self):
        """Get the current player's scorecard."""
        if self.multiplayer:
            return mp_get_current_scorecard(self.mp_state)
        return self.state.scorecard

    def _is_current_player_human(self):
        """In multiplayer, check if the current player is human."""
        if not self.multiplayer:
            return self.ai_strategy is None
        _, strategy = self.player_configs[self.mp_state.current_player_index]
        return strategy is None

    def _get_current_ai_strategy(self):
        """In multiplayer, get the current player's AI strategy (or None if human)."""
        if not self.multiplayer:
            return self.ai_strategy
        _, strategy = self.player_configs[self.mp_state.current_player_index]
        return strategy

    def _has_any_ai(self):
        """Check if any player is AI (for speed control display)."""
        if self.multiplayer:
            return any(s is not None for _, s in self.player_configs)
        return self.ai_strategy is not None

    def handle_events(self):
        """Handle pygame events"""
        is_human_turn = self._is_current_player_human()
        game_over = self._is_game_over()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                # Speed control (+/- keys) — when any AI is present
                if self._has_any_ai() and not game_over:
                    if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        idx = SPEED_NAMES.index(self.speed_name)
                        if idx < len(SPEED_NAMES) - 1:
                            self.speed_name = SPEED_NAMES[idx + 1]
                            self.ai_delay, self.roll_duration, self.ai_hold_show_duration = SPEED_PRESETS[self.speed_name]
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        idx = SPEED_NAMES.index(self.speed_name)
                        if idx > 0:
                            self.speed_name = SPEED_NAMES[idx - 1]
                            self.ai_delay, self.roll_duration, self.ai_hold_show_duration = SPEED_PRESETS[self.speed_name]
                # Keyboard shortcuts for human players
                if is_human_turn and not game_over and not self.is_rolling:
                    if event.key == pygame.K_SPACE:
                        self.roll_dice()
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        die_index = event.key - pygame.K_1
                        if self.multiplayer:
                            self.mp_state = mp_toggle_die_hold(self.mp_state, die_index)
                        else:
                            self.state = engine_toggle_die(self.state, die_index)
            elif event.type == pygame.MOUSEMOTION:
                self.hovered_category = None
                if not game_over and is_human_turn:
                    scorecard = self._get_scorecard()
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and not scorecard.is_filled(cat):
                            self.hovered_category = cat
                            break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and is_human_turn:
                    clicked_category = False
                    if self.multiplayer:
                        for cat, rect in self.category_rects.items():
                            if rect.collidepoint(event.pos) and mp_can_select_category(self.mp_state, cat):
                                self.mp_state = mp_select_category(self.mp_state, cat)
                                self._on_turn_scored()
                                clicked_category = True
                                break
                    else:
                        for cat, rect in self.category_rects.items():
                            if rect.collidepoint(event.pos) and can_select_category(self.state, cat):
                                self.state = engine_select_category(self.state, cat)
                                clicked_category = True
                                break

                    if not clicked_category and not self.is_rolling and not game_over:
                        for i, sprite in enumerate(self.dice_sprites):
                            if sprite.contains_point(event.pos):
                                if self.multiplayer:
                                    self.mp_state = mp_toggle_die_hold(self.mp_state, i)
                                else:
                                    self.state = engine_toggle_die(self.state, i)
                                break

            # Handle button clicks (only if not currently rolling and human turn)
            if is_human_turn and self.roll_button.handle_event(event) and not self.is_rolling:
                self.roll_dice()

            # Handle play again button (only when game is over)
            if game_over and self.play_again_button.handle_event(event):
                self.reset_game()

    def _on_turn_scored(self):
        """Called after any player (human or AI) scores in multiplayer.
        Triggers turn transition and resets AI state for the next player."""
        if not self.multiplayer:
            return
        self.ai_needs_first_roll = True
        self.ai_timer = 0
        self.ai_reason = ""
        self.ai_showing_holds = False
        self.ai_hold_timer = 0
        if not self.mp_state.game_over:
            self.turn_transition = True
            self.turn_transition_timer = 0

    def update(self):
        """Update game state"""
        # Handle turn transition overlay (multiplayer only)
        if self.turn_transition:
            self.turn_transition_timer += 1
            if self.turn_transition_timer >= self.turn_transition_duration:
                self.turn_transition = False
            return

        # Handle rolling animation
        if self.is_rolling:
            self.roll_timer += 1
            current_dice = self._get_dice()

            # During animation, rapidly change display values (only for unheld dice)
            if self.roll_timer < self.roll_duration:
                for i, die in enumerate(current_dice):
                    if not die.held:
                        self.animation_dice_values[i] = random.randint(1, 6)
            else:
                # Animation complete - commit state change
                if self.multiplayer:
                    self.mp_state = self._pending_mp_state
                else:
                    self.state = self._pending_state
                self.animation_dice_values = self.final_values.copy()
                self.is_rolling = False
            return

        # AI hold-showing pause — briefly display held dice before rolling
        if self.ai_showing_holds:
            self.ai_hold_timer += 1
            if self.ai_hold_timer >= self.ai_hold_show_duration:
                self.ai_showing_holds = False
                self.roll_dice()
            return

        # Determine if current player is AI
        current_strategy = self._get_current_ai_strategy()
        game_over = self._is_game_over()

        # AI controller — paces decisions with a timer so you can watch
        if current_strategy and not game_over:
            self.ai_timer += 1
            if self.ai_timer < self.ai_delay:
                return
            self.ai_timer = 0

            # First roll of the turn (mandatory)
            if self.ai_needs_first_roll:
                self.roll_dice()
                self.ai_needs_first_roll = False
                return

            # Build a temporary single-player GameState for the AI strategy
            if self.multiplayer:
                temp_state = GameState(
                    dice=self.mp_state.dice,
                    scorecard=mp_get_current_scorecard(self.mp_state),
                    rolls_used=self.mp_state.rolls_used,
                    current_round=self.mp_state.current_round,
                    game_over=self.mp_state.game_over,
                )
                action = current_strategy.choose_action(temp_state)
            else:
                action = current_strategy.choose_action(self.state)
            self.ai_reason = action.reason

            if isinstance(action, ScoreAction):
                if self.multiplayer:
                    self.mp_state = mp_select_category(self.mp_state, action.category)
                    self._on_turn_scored()
                else:
                    self.state = engine_select_category(self.state, action.category)
                    self.ai_needs_first_roll = True
            elif isinstance(action, RollAction):
                # Apply holds: set each die to match the strategy's request
                if self.multiplayer:
                    for i in range(5):
                        should_hold = i in action.hold
                        is_held = self.mp_state.dice[i].held
                        if should_hold != is_held:
                            self.mp_state = mp_toggle_die_hold(self.mp_state, i)
                else:
                    for i in range(5):
                        should_hold = i in action.hold
                        is_held = self.state.dice[i].held
                        if should_hold != is_held:
                            self.state = engine_toggle_die(self.state, i)
                # Pause to show the held dice before rolling
                self.ai_showing_holds = True
                self.ai_hold_timer = 0

    def draw_scorecard(self):
        """Draw the scorecard UI on the right side of screen"""
        scorecard = self._get_scorecard()
        dice = self._get_dice()

        # Scorecard position and dimensions
        scorecard_x = 620
        scorecard_y = 150
        row_height = 28
        col_width = 180

        # Draw scorecard background panel
        panel_rect = pygame.Rect(scorecard_x - 15, scorecard_y - 15, 360, 520)
        pygame.draw.rect(self.screen, SCORECARD_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, (180, 180, 200), panel_rect, width=2, border_radius=12)

        # Fonts
        font = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 20)
        font_bold = pygame.font.Font(None, 28)

        y = scorecard_y

        # Player name header in multiplayer
        if self.multiplayer:
            idx = self.mp_state.current_player_index
            name, _ = self.player_configs[idx]
            color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
            name_header = font_bold.render(f"{name}'s Scorecard", True, color)
            self.screen.blit(name_header, (scorecard_x, y))
            y += row_height + 2

        # Upper section header
        header = font_bold.render("UPPER SECTION", True, SECTION_HEADER_COLOR)
        self.screen.blit(header, (scorecard_x, y))
        y += row_height + 5

        # Upper section categories
        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                     Category.FOURS, Category.FIVES, Category.SIXES]

        for cat in upper_cats:
            cat_rect = pygame.Rect(scorecard_x - 5, y - 2, col_width + 50, row_height)
            self.category_rects[cat] = cat_rect

            if not scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            if scorecard.is_filled(cat):
                score = scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, dice)
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Upper section totals
        y += 5
        upper_total = scorecard.get_upper_section_total()
        total_text = font.render(f"Total: {upper_total}", True, BLACK)
        self.screen.blit(total_text, (scorecard_x, y))
        y += row_height

        bonus = scorecard.get_upper_section_bonus()
        bonus_text = font_small.render(f"Bonus (63+): {bonus}", True, BLACK)
        self.screen.blit(bonus_text, (scorecard_x, y))
        y += row_height + 10

        # Lower section header
        header = font_bold.render("LOWER SECTION", True, SECTION_HEADER_COLOR)
        self.screen.blit(header, (scorecard_x, y))
        y += row_height + 5

        # Lower section categories
        lower_cats = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                     Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                     Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]

        for cat in lower_cats:
            cat_rect = pygame.Rect(scorecard_x - 5, y - 2, col_width + 50, row_height)
            self.category_rects[cat] = cat_rect

            if not scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            if scorecard.is_filled(cat):
                score = scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, dice)
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Grand total
        y += 10
        grand_total = scorecard.get_grand_total()
        total_text = font_bold.render(f"GRAND TOTAL: {grand_total}", True, BLACK)
        self.screen.blit(total_text, (scorecard_x, y))

    def draw_player_bar(self):
        """Draw horizontal bar showing all players' names and scores (multiplayer only)."""
        bar_y = 130
        bar_height = 32
        font = pygame.font.Font(None, 26)
        num = self.mp_state.num_players
        # Calculate per-player chip width to fit across the available width
        bar_width = min(180, (WINDOW_WIDTH - 100) // num)
        total_width = bar_width * num
        start_x = (WINDOW_WIDTH - total_width) // 2

        for i in range(num):
            name, strategy = self.player_configs[i]
            score = self.mp_state.scorecards[i].get_grand_total()
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            chip_rect = pygame.Rect(start_x + i * bar_width, bar_y, bar_width - 4, bar_height)

            if i == self.mp_state.current_player_index and not self.mp_state.game_over:
                # Active player: filled background
                pygame.draw.rect(self.screen, color, chip_rect, border_radius=6)
                text_color = WHITE
            else:
                # Inactive: outlined
                pygame.draw.rect(self.screen, SCORECARD_BG, chip_rect, border_radius=6)
                pygame.draw.rect(self.screen, color, chip_rect, width=2, border_radius=6)
                text_color = color

            label = f"{name}: {score}"
            text = font.render(label, True, text_color)
            text_rect = text.get_rect(center=chip_rect.center)
            self.screen.blit(text, text_rect)

    def draw_turn_transition(self):
        """Draw brief overlay showing whose turn it is next."""
        if not self.turn_transition:
            return
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        idx = self.mp_state.current_player_index
        name, strategy = self.player_configs[idx]
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

        font = pygame.font.Font(None, 56)
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
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((240, 240, 240))
        self.screen.blit(overlay, (0, 0))

        if self.multiplayer:
            self._draw_game_over_multiplayer()
        else:
            self._draw_game_over_single()

        # Play again button
        self.play_again_button.draw(self.screen)

    def _draw_game_over_single(self):
        """Draw single-player game over with per-category score breakdown."""
        scorecard = self.state.scorecard

        # Game Over title
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("GAME OVER!", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 60))
        self.screen.blit(title_text, title_rect)

        # Final score
        score_font = pygame.font.Font(None, 56)
        final_score = scorecard.get_grand_total()
        score_text = score_font.render(f"Final Score: {final_score}", True, (50, 100, 150))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 115))
        self.screen.blit(score_text, score_rect)

        # Fonts for breakdown
        header_font = pygame.font.Font(None, 30)
        cat_font = pygame.font.Font(None, 24)
        total_font = pygame.font.Font(None, 28)

        # --- Left column: Upper section ---
        left_x = 180
        y = 160

        header = header_font.render("UPPER SECTION", True, SECTION_HEADER_COLOR)
        self.screen.blit(header, (left_x, y))
        y += 28

        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                      Category.FOURS, Category.FIVES, Category.SIXES]
        for cat in upper_cats:
            score = scorecard.scores.get(cat, 0)
            name_text = cat_font.render(cat.value, True, BLACK)
            score_text = cat_font.render(str(score), True, BLACK)
            self.screen.blit(name_text, (left_x + 10, y))
            self.screen.blit(score_text, (left_x + 160, y))
            y += 24

        y += 6
        upper_total = scorecard.get_upper_section_total()
        sub_text = total_font.render(f"Subtotal: {upper_total}", True, BLACK)
        self.screen.blit(sub_text, (left_x + 10, y))
        y += 26

        bonus = scorecard.get_upper_section_bonus()
        bonus_color = VALID_SCORE_COLOR if bonus > 0 else GRAY
        bonus_text = total_font.render(f"Bonus: {bonus}", True, bonus_color)
        self.screen.blit(bonus_text, (left_x + 10, y))

        # --- Right column: Lower section ---
        right_x = 550
        y = 160

        header = header_font.render("LOWER SECTION", True, SECTION_HEADER_COLOR)
        self.screen.blit(header, (right_x, y))
        y += 28

        lower_cats = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                      Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                      Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]
        for cat in lower_cats:
            score = scorecard.scores.get(cat, 0)
            name_text = cat_font.render(cat.value, True, BLACK)
            score_text = cat_font.render(str(score), True, BLACK)
            self.screen.blit(name_text, (right_x + 10, y))
            self.screen.blit(score_text, (right_x + 160, y))
            y += 24

        y += 6
        lower_total = scorecard.get_lower_section_total()
        sub_text = total_font.render(f"Subtotal: {lower_total}", True, BLACK)
        self.screen.blit(sub_text, (right_x + 10, y))

        # Grand total centered below both columns
        grand_font = pygame.font.Font(None, 40)
        grand_text = grand_font.render(f"GRAND TOTAL: {final_score}", True, BLACK)
        grand_rect = grand_text.get_rect(center=(WINDOW_WIDTH // 2, 500))
        self.screen.blit(grand_text, grand_rect)

    def _draw_game_over_multiplayer(self):
        """Draw multiplayer game over with ranked standings."""
        # Game Over title
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("GAME OVER!", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 80))
        self.screen.blit(title_text, title_rect)

        # Build standings: list of (player_index, name, strategy, score) sorted by score desc
        standings = []
        for i, (name, strategy) in enumerate(self.player_configs):
            score = self.mp_state.scorecards[i].get_grand_total()
            standings.append((i, name, strategy, score))
        standings.sort(key=lambda x: x[3], reverse=True)

        # Rank labels
        rank_labels = ["1st", "2nd", "3rd", "4th"]

        # Draw standings
        rank_font = pygame.font.Font(None, 44)
        name_font = pygame.font.Font(None, 40)
        score_font = pygame.font.Font(None, 44)
        detail_font = pygame.font.Font(None, 26)

        y = 160
        for rank, (idx, name, strategy, score) in enumerate(standings):
            color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

            # Draw rank
            rank_text = rank_font.render(rank_labels[rank], True, BLACK)
            self.screen.blit(rank_text, (150, y))

            # Draw player name
            if strategy is not None:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                label = f"{name} ({ai_name})"
            else:
                label = f"{name} (Human)"
            name_text = name_font.render(label, True, color)
            self.screen.blit(name_text, (220, y))

            # Draw score
            score_text = score_font.render(str(score), True, BLACK)
            score_rect = score_text.get_rect(right=820, top=y)
            self.screen.blit(score_text, score_rect)

            # Draw score breakdown details
            sc = self.mp_state.scorecards[idx]
            upper = sc.get_upper_section_total()
            bonus = sc.get_upper_section_bonus()
            lower = sc.get_lower_section_total()
            detail = f"Upper: {upper}  Bonus: {bonus}  Lower: {lower}"
            detail_text = detail_font.render(detail, True, GRAY)
            self.screen.blit(detail_text, (220, y + 34))

            y += 80

            # Winner highlight — gold bar behind first place
            if rank == 0:
                crown_font = pygame.font.Font(None, 36)
                crown_text = crown_font.render("WINNER!", True, (200, 160, 30))
                self.screen.blit(crown_text, (70, y - 80))

    def draw(self):
        """Draw everything to the screen"""
        # Clear screen with subtle background color
        self.screen.fill(BACKGROUND)

        dice = self._get_dice()
        rolls_used = self._get_rolls_used()
        game_over = self._is_game_over()
        current_round = self._get_current_round()

        # Draw title with shadow effect
        font = pygame.font.Font(None, 72)
        title_shadow = font.render("YAHTZEE", True, (180, 180, 180))
        shadow_rect = title_shadow.get_rect(center=(WINDOW_WIDTH // 2 + 3, 53))
        self.screen.blit(title_shadow, shadow_rect)
        title = font.render("YAHTZEE", True, SECTION_HEADER_COLOR)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)

        # Draw round and turn indicator
        round_font = pygame.font.Font(None, 36)
        if self.multiplayer:
            idx = self.mp_state.current_player_index
            name, strategy = self.player_configs[idx]
            color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
            if strategy is None:
                turn_label = f"Round {current_round}/13 — Your turn ({name})"
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                turn_label = f"Round {current_round}/13 — {name}'s turn ({ai_name} AI)"
            round_text = round_font.render(turn_label, True, color)
            self.screen.blit(round_text, (50, 90))
        else:
            round_text = round_font.render(f"Round {current_round}/13", True, BLACK)
            self.screen.blit(round_text, (50, 90))

        # Draw AI/speed indicator
        if not self.multiplayer and self.ai_strategy:
            ai_font = pygame.font.Font(None, 28)
            ai_name = self.ai_strategy.__class__.__name__.replace("Strategy", "")
            speed_label = self.speed_name.capitalize()
            ai_text = ai_font.render(f"AI: {ai_name} | Speed: {speed_label} (+/-)", True, (180, 80, 80))
            self.screen.blit(ai_text, (50, 120))
        elif self.multiplayer and self._has_any_ai():
            ai_font = pygame.font.Font(None, 24)
            speed_label = self.speed_name.capitalize()
            ai_text = ai_font.render(f"Speed: {speed_label} (+/-)", True, (140, 140, 160))
            self.screen.blit(ai_text, (50, 120))

        # Draw player bar (multiplayer only)
        if self.multiplayer:
            self.draw_player_bar()

        # Draw all dice sprites
        for i, sprite in enumerate(self.dice_sprites):
            die_state = dice[i]

            if rolls_used == 0 and not self.is_rolling:
                sprite.draw_in_cup(self.screen)
                continue

            if self.is_rolling:
                display_value = self.animation_dice_values[i]
                display_state = DieState(value=display_value, held=die_state.held)
            else:
                display_state = die_state

            if self.is_rolling and not die_state.held:
                shake_x = int(math.sin(self.roll_timer * 0.5) * 3)
                shake_y = int(math.cos(self.roll_timer * 0.7) * 3)
                sprite.draw(self.screen, display_state, shake_x, shake_y)
            else:
                sprite.draw(self.screen, display_state)

        # Draw roll button
        if self.multiplayer:
            can_roll_now = mp_can_roll(self.mp_state) and not self.is_rolling
        else:
            can_roll_now = can_roll(self.state) and not self.is_rolling
        self.roll_button.enabled = can_roll_now
        self.roll_button.draw(self.screen)

        # Draw roll status
        roll_font = pygame.font.Font(None, 32)
        if rolls_used == 0:
            roll_text = roll_font.render("Roll the dice!", True, SECTION_HEADER_COLOR)
        else:
            rolls_remaining = MAX_ROLLS_PER_TURN - rolls_used
            roll_text = roll_font.render(f"Rolls left: {rolls_remaining}", True, BLACK)
        self.screen.blit(roll_text, (200, 560))

        # Draw AI reasoning text below roll status
        current_strategy = self._get_current_ai_strategy()
        if current_strategy and self.ai_reason:
            reason_font = pygame.font.Font(None, 24)
            max_width = 480
            words = self.ai_reason.split()
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

            reason_color = (120, 120, 140)
            reason_y = 590
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
        if self.multiplayer:
            self.draw_turn_transition()

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


def _make_strategy(token):
    """Create a strategy instance from a CLI token, or None for 'human'."""
    if token == "human":
        return None
    elif token == "random":
        return RandomStrategy()
    elif token == "greedy":
        return GreedyStrategy()
    elif token == "ev":
        return ExpectedValueStrategy()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Yahtzee Game")
    # Single-player AI mode (backward compatible)
    parser.add_argument("--ai", action="store_true", help="Enable AI player")
    parser.add_argument("--random", action="store_true", help="Use Random strategy (with --ai)")
    parser.add_argument("--greedy", action="store_true", help="Use Greedy strategy (with --ai)")
    parser.add_argument("--ev", action="store_true", help="Use ExpectedValue strategy (with --ai)")
    # Multiplayer mode
    parser.add_argument("--players", nargs="+", choices=["human", "random", "greedy", "ev"],
                        metavar="TYPE",
                        help="Multiplayer: list player types (human, random, greedy, ev)")
    parser.add_argument("--speed", choices=["slow", "normal", "fast"], default="normal",
                        help="AI playback speed (default: normal)")
    return parser.parse_args()


def main():
    """Entry point for the game"""
    args = parse_args()

    if args.players:
        # Multiplayer mode
        if len(args.players) < 2:
            print("Error: --players requires at least 2 players")
            sys.exit(1)
        if len(args.players) > 4:
            print("Error: --players supports at most 4 players")
            sys.exit(1)

        players = []
        for i, token in enumerate(args.players):
            strategy = _make_strategy(token)
            if strategy is None:
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
                ai_strategy = RandomStrategy()
            elif args.ev:
                ai_strategy = ExpectedValueStrategy()
            else:
                ai_strategy = GreedyStrategy()

        game = YahtzeeGame(ai_strategy=ai_strategy, speed=args.speed)

    game.run()


if __name__ == "__main__":
    main()
