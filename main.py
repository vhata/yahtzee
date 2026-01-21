#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame
"""
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
    reset_game as engine_reset_game
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

# Dice constants
DICE_SIZE = 80
DICE_MARGIN = 20
DOT_RADIUS = 6

# Game constants
MAX_ROLLS_PER_TURN = 3


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

    def __init__(self):
        """Initialize the game window and basic components"""
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Yahtzee")
        self.clock = pygame.time.Clock()
        self.running = True

        # Game state (from engine)
        self.state = GameState.create_initial()

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
        play_again_y = 450
        self.play_again_button = Button(play_again_x, play_again_y, play_again_width, play_again_height, "PLAY AGAIN", 40)

        # Animation state (GUI concern only)
        self.is_rolling = False
        self.roll_timer = 0
        self.roll_duration = 60  # frames (1 second at 60 FPS)
        self.animation_dice_values = [die.value for die in self.state.dice]  # For animation display
        self.final_values = []
        self._pending_state = None  # State to commit after animation

        # UI state
        self.category_rects = {}  # Maps Category to pygame.Rect for click detection
        self.hovered_category = None

    def reset_game(self):
        """Reset the game to start a new game"""
        self.state = engine_reset_game()
        self.animation_dice_values = [die.value for die in self.state.dice]

    def roll_dice(self):
        """Start the dice rolling animation"""
        if not self.is_rolling and can_roll(self.state):
            self.is_rolling = True
            self.roll_timer = 0

            # Update game state through engine
            new_state = engine_roll_dice(self.state)

            # Store final values for animation
            self.final_values = [die.value for die in new_state.dice]

            # Don't update state yet - wait for animation to finish
            self._pending_state = new_state

    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.MOUSEMOTION:
                # Check hover over scorecard categories (only if game not over)
                self.hovered_category = None
                if not self.state.game_over:
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and not self.state.scorecard.is_filled(cat):
                            self.hovered_category = cat
                            break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if scorecard category was clicked
                    clicked_category = False
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and can_select_category(self.state, cat):
                            # Lock in score and advance turn
                            self.state = engine_select_category(self.state, cat)
                            clicked_category = True
                            break

                    # Check if any die was clicked (only when not rolling, didn't click category, and game not over)
                    if not clicked_category and not self.is_rolling and not self.state.game_over:
                        for i, sprite in enumerate(self.dice_sprites):
                            if sprite.contains_point(event.pos):
                                self.state = engine_toggle_die(self.state, i)
                                break

            # Handle button clicks (only if not currently rolling)
            if self.roll_button.handle_event(event) and not self.is_rolling:
                self.roll_dice()

            # Handle play again button (only when game is over)
            if self.state.game_over and self.play_again_button.handle_event(event):
                self.reset_game()

    def update(self):
        """Update game state"""
        # Handle rolling animation
        if self.is_rolling:
            self.roll_timer += 1

            # During animation, rapidly change display values (only for unheld dice)
            if self.roll_timer < self.roll_duration:
                for i, die in enumerate(self.state.dice):
                    if not die.held:
                        self.animation_dice_values[i] = random.randint(1, 6)
            else:
                # Animation complete - commit state change
                self.state = self._pending_state
                self.animation_dice_values = self.final_values.copy()
                self.is_rolling = False

    def draw_scorecard(self):
        """Draw the scorecard UI on the right side of screen"""
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

        # Upper section header
        header = font_bold.render("UPPER SECTION", True, SECTION_HEADER_COLOR)
        self.screen.blit(header, (scorecard_x, y))
        y += row_height + 5

        # Upper section categories
        upper_cats = [Category.ONES, Category.TWOS, Category.THREES,
                     Category.FOURS, Category.FIVES, Category.SIXES]

        for cat in upper_cats:
            # Create clickable rect for this category
            cat_rect = pygame.Rect(scorecard_x - 5, y - 2, col_width + 50, row_height)
            self.category_rects[cat] = cat_rect

            # Draw hover highlight for unfilled categories
            if not self.state.scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            # Category name
            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            # Score (filled or potential)
            if self.state.scorecard.is_filled(cat):
                score = self.state.scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, self.state.dice)
                # Show valid scores in green, zero scores in gray
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Upper section totals
        y += 5
        upper_total = self.state.scorecard.get_upper_section_total()
        total_text = font.render(f"Total: {upper_total}", True, BLACK)
        self.screen.blit(total_text, (scorecard_x, y))
        y += row_height

        bonus = self.state.scorecard.get_upper_section_bonus()
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
            # Create clickable rect for this category
            cat_rect = pygame.Rect(scorecard_x - 5, y - 2, col_width + 50, row_height)
            self.category_rects[cat] = cat_rect

            # Draw hover highlight for unfilled categories
            if not self.state.scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            # Category name
            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            # Score (filled or potential)
            if self.state.scorecard.is_filled(cat):
                score = self.state.scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, self.state.dice)
                # Show valid scores in green, zero scores in gray
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Grand total
        y += 10
        grand_total = self.state.scorecard.get_grand_total()
        total_text = font_bold.render(f"GRAND TOTAL: {grand_total}", True, BLACK)
        self.screen.blit(total_text, (scorecard_x, y))

    def draw_game_over(self):
        """Draw the game over screen overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((240, 240, 240))
        self.screen.blit(overlay, (0, 0))

        # Game Over title
        title_font = pygame.font.Font(None, 96)
        title_text = title_font.render("GAME OVER!", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(title_text, title_rect)

        # Final score
        score_font = pygame.font.Font(None, 72)
        final_score = self.state.scorecard.get_grand_total()
        score_text = score_font.render(f"Final Score: {final_score}", True, (50, 100, 150))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 320))
        self.screen.blit(score_text, score_rect)

        # Breakdown
        breakdown_font = pygame.font.Font(None, 36)
        upper_total = self.state.scorecard.get_upper_section_total()
        upper_bonus = self.state.scorecard.get_upper_section_bonus()
        lower_total = self.state.scorecard.get_lower_section_total()

        y = 380
        breakdown_texts = [
            f"Upper Section: {upper_total}",
            f"Bonus: {upper_bonus}",
            f"Lower Section: {lower_total}"
        ]
        for text in breakdown_texts:
            rendered = breakdown_font.render(text, True, BLACK)
            rect = rendered.get_rect(center=(WINDOW_WIDTH // 2, y))
            self.screen.blit(rendered, rect)
            y += 35

        # Play again button
        self.play_again_button.draw(self.screen)

    def draw(self):
        """Draw everything to the screen"""
        # Clear screen with subtle background color
        self.screen.fill(BACKGROUND)

        # Draw title with shadow effect
        font = pygame.font.Font(None, 72)
        # Shadow
        title_shadow = font.render("YAHTZEE", True, (180, 180, 180))
        shadow_rect = title_shadow.get_rect(center=(WINDOW_WIDTH // 2 + 3, 103))
        self.screen.blit(title_shadow, shadow_rect)
        # Main title
        title = font.render("YAHTZEE", True, SECTION_HEADER_COLOR)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        # Draw round indicator
        round_font = pygame.font.Font(None, 36)
        round_text = round_font.render(f"Round {self.state.current_round}/13", True, BLACK)
        self.screen.blit(round_text, (50, 50))

        # Draw all dice sprites with shake effect during rolling
        for i, sprite in enumerate(self.dice_sprites):
            die_state = self.state.dice[i]

            # Use animation values during rolling, actual values otherwise
            if self.is_rolling:
                # Create temporary DieState for animation display
                display_value = self.animation_dice_values[i]
                display_state = DieState(value=display_value, held=die_state.held)
            else:
                display_state = die_state

            # Add shake effect during rolling for unheld dice
            if self.is_rolling and not die_state.held:
                shake_x = int(math.sin(self.roll_timer * 0.5) * 3)
                shake_y = int(math.cos(self.roll_timer * 0.7) * 3)
                sprite.draw(self.screen, display_state, shake_x, shake_y)
            else:
                sprite.draw(self.screen, display_state)

        # Draw roll button (disable during rolling animation, out of rolls, or game over)
        self.roll_button.enabled = can_roll(self.state) and not self.is_rolling
        self.roll_button.draw(self.screen)

        # Draw roll count
        roll_font = pygame.font.Font(None, 32)
        rolls_remaining = MAX_ROLLS_PER_TURN - self.state.rolls_used
        roll_text = roll_font.render(f"Rolls left: {rolls_remaining}", True, BLACK)
        self.screen.blit(roll_text, (200, 560))

        # Draw scorecard
        self.draw_scorecard()

        # Draw game over screen if game is over
        if self.state.game_over:
            self.draw_game_over()

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


def main():
    """Entry point for the game"""
    game = YahtzeeGame()
    game.run()


if __name__ == "__main__":
    main()
