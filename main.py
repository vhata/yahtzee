#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame
"""
import pygame
import sys
import random
from enum import Enum
from collections import Counter

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


class Category(Enum):
    """Yahtzee score categories"""
    ONES = "Ones"
    TWOS = "Twos"
    THREES = "Threes"
    FOURS = "Fours"
    FIVES = "Fives"
    SIXES = "Sixes"
    THREE_OF_KIND = "3 of a Kind"
    FOUR_OF_KIND = "4 of a Kind"
    FULL_HOUSE = "Full House"
    SMALL_STRAIGHT = "Small Straight"
    LARGE_STRAIGHT = "Large Straight"
    YAHTZEE = "Yahtzee"
    CHANCE = "Chance"


class Scorecard:
    """Manages the Yahtzee scorecard"""

    def __init__(self):
        """Initialize an empty scorecard"""
        # Dictionary to store scores for each category (None = not filled)
        self.scores = {category: None for category in Category}

    def is_filled(self, category):
        """Check if a category has been filled"""
        return self.scores[category] is not None

    def set_score(self, category, score):
        """Set the score for a category"""
        if not self.is_filled(category):
            self.scores[category] = score

    def get_upper_section_total(self):
        """Calculate total for upper section (Ones through Sixes)"""
        upper_categories = [Category.ONES, Category.TWOS, Category.THREES,
                           Category.FOURS, Category.FIVES, Category.SIXES]
        total = 0
        for cat in upper_categories:
            if self.scores[cat] is not None:
                total += self.scores[cat]
        return total

    def get_upper_section_bonus(self):
        """Calculate bonus (35 points if upper section >= 63)"""
        return 35 if self.get_upper_section_total() >= 63 else 0

    def get_lower_section_total(self):
        """Calculate total for lower section"""
        lower_categories = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                           Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                           Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]
        total = 0
        for cat in lower_categories:
            if self.scores[cat] is not None:
                total += self.scores[cat]
        return total

    def get_grand_total(self):
        """Calculate grand total including bonus"""
        return (self.get_upper_section_total() +
                self.get_upper_section_bonus() +
                self.get_lower_section_total())

    def is_complete(self):
        """Check if all categories are filled"""
        return all(score is not None for score in self.scores.values())


def count_values(dice):
    """
    Count occurrences of each die value

    Args:
        dice: List of Dice objects

    Returns:
        Counter object with die values as keys
    """
    values = [die.value for die in dice]
    return Counter(values)


def has_n_of_kind(dice, n):
    """
    Check if dice contain at least n of the same value

    Args:
        dice: List of Dice objects
        n: Number of matching dice required

    Returns:
        True if at least n dice have the same value
    """
    counts = count_values(dice)
    return max(counts.values()) >= n


def has_full_house(dice):
    """
    Check if dice form a full house (3 of one value, 2 of another)

    Args:
        dice: List of Dice objects

    Returns:
        True if dice form a full house
    """
    counts = count_values(dice)
    sorted_counts = sorted(counts.values(), reverse=True)
    return sorted_counts == [3, 2]


def has_small_straight(dice):
    """
    Check if dice contain a small straight (4 consecutive values)

    Args:
        dice: List of Dice objects

    Returns:
        True if dice contain a small straight
    """
    values = set(die.value for die in dice)
    # Possible small straights: 1-2-3-4, 2-3-4-5, 3-4-5-6
    small_straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
    return any(straight.issubset(values) for straight in small_straights)


def has_large_straight(dice):
    """
    Check if dice contain a large straight (5 consecutive values)

    Args:
        dice: List of Dice objects

    Returns:
        True if dice contain a large straight
    """
    values = set(die.value for die in dice)
    # Possible large straights: 1-2-3-4-5, 2-3-4-5-6
    large_straights = [{1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}]
    return any(straight == values for straight in large_straights)


def has_yahtzee(dice):
    """
    Check if all dice have the same value

    Args:
        dice: List of Dice objects

    Returns:
        True if all dice match
    """
    return has_n_of_kind(dice, 5)


def calculate_score(category, dice):
    """
    Calculate the score for a given category and dice

    Args:
        category: Category enum value
        dice: List of Dice objects

    Returns:
        Integer score for the category (0 if doesn't qualify)
    """
    values = [die.value for die in dice]
    total = sum(values)
    counts = count_values(dice)

    # Upper section - sum of matching dice
    if category == Category.ONES:
        return counts[1] * 1
    elif category == Category.TWOS:
        return counts[2] * 2
    elif category == Category.THREES:
        return counts[3] * 3
    elif category == Category.FOURS:
        return counts[4] * 4
    elif category == Category.FIVES:
        return counts[5] * 5
    elif category == Category.SIXES:
        return counts[6] * 6

    # Three of a kind - sum of all dice if at least 3 match
    elif category == Category.THREE_OF_KIND:
        return total if has_n_of_kind(dice, 3) else 0

    # Four of a kind - sum of all dice if at least 4 match
    elif category == Category.FOUR_OF_KIND:
        return total if has_n_of_kind(dice, 4) else 0

    # Full house - 25 points
    elif category == Category.FULL_HOUSE:
        return 25 if has_full_house(dice) else 0

    # Small straight - 30 points
    elif category == Category.SMALL_STRAIGHT:
        return 30 if has_small_straight(dice) else 0

    # Large straight - 40 points
    elif category == Category.LARGE_STRAIGHT:
        return 40 if has_large_straight(dice) else 0

    # Yahtzee - 50 points
    elif category == Category.YAHTZEE:
        return 50 if has_yahtzee(dice) else 0

    # Chance - sum of all dice
    elif category == Category.CHANCE:
        return total

    return 0


class Dice:
    """Represents a single die with graphical rendering"""

    def __init__(self, x, y, value=1):
        """
        Initialize a die

        Args:
            x: X position on screen
            y: Y position on screen
            value: Die value (1-6)
        """
        self.x = x
        self.y = y
        self.value = value
        self.held = False

    def roll(self):
        """Roll the die to a random value between 1 and 6"""
        self.value = random.randint(1, 6)

    def contains_point(self, pos):
        """
        Check if a point is inside the die

        Args:
            pos: Tuple of (x, y) coordinates

        Returns:
            True if point is inside die, False otherwise
        """
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        return dice_rect.collidepoint(pos)

    def toggle_held(self):
        """Toggle the held state of the die"""
        self.held = not self.held

    def draw(self, surface):
        """Draw the die with its current value"""
        # Draw subtle shadow for depth
        shadow_rect = pygame.Rect(self.x + 3, self.y + 3, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, (200, 200, 200, 50), shadow_rect, border_radius=10)

        # Draw dice background
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, DICE_COLOR, dice_rect, border_radius=10)

        # Draw border - thicker and colored if held
        if self.held:
            # Green highlight for held dice
            pygame.draw.rect(surface, (50, 200, 50), dice_rect, width=5, border_radius=10)
        else:
            pygame.draw.rect(surface, (100, 100, 100), dice_rect, width=2, border_radius=10)

        # Draw dots based on value
        self._draw_dots(surface)

    def _draw_dots(self, surface):
        """Draw the dots/pips on the die face"""
        # Calculate dot positions relative to die center
        center_x = self.x + DICE_SIZE // 2
        center_y = self.y + DICE_SIZE // 2
        offset = DICE_SIZE // 4

        # Define dot positions for each value
        # 1: center
        if self.value == 1:
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)

        # 2: diagonal top-left to bottom-right
        elif self.value == 2:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 3: diagonal plus center
        elif self.value == 3:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 4: four corners
        elif self.value == 4:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 5: four corners plus center
        elif self.value == 5:
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y - offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x, center_y), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x - offset, center_y + offset), DOT_RADIUS)
            pygame.draw.circle(surface, DOT_COLOR, (center_x + offset, center_y + offset), DOT_RADIUS)

        # 6: two columns of three
        elif self.value == 6:
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

        # Create 5 dice with different values to showcase all faces
        self.dice = []
        dice_y = 300
        total_width = 5 * DICE_SIZE + 4 * DICE_MARGIN
        start_x = (WINDOW_WIDTH - total_width) // 2

        for i in range(5):
            x = start_x + i * (DICE_SIZE + DICE_MARGIN)
            # Initialize with random values
            dice = Dice(x, dice_y, value=random.randint(1, 6))
            self.dice.append(dice)

        # Create roll button
        button_width = 150
        button_height = 50
        button_x = (WINDOW_WIDTH - button_width) // 2
        button_y = 500
        self.roll_button = Button(button_x, button_y, button_width, button_height, "ROLL")

        # Play again button (for game over screen)
        play_again_width = 200
        play_again_height = 60
        play_again_x = (WINDOW_WIDTH - play_again_width) // 2
        play_again_y = 450
        self.play_again_button = Button(play_again_x, play_again_y, play_again_width, play_again_height, "PLAY AGAIN", 40)

        # Animation state
        self.is_rolling = False
        self.roll_timer = 0
        self.roll_duration = 30  # frames (0.5 seconds at 60 FPS)
        self.final_values = []

        # Scorecard
        self.scorecard = Scorecard()

        # Turn management
        self.rolls_used = 0

        # Score selection tracking
        self.category_rects = {}  # Maps Category to pygame.Rect for click detection
        self.hovered_category = None

        # Game flow
        self.current_round = 1
        self.game_over = False

    def start_new_turn(self):
        """Start a new turn - reset rolls and held dice"""
        self.rolls_used = 0
        for die in self.dice:
            die.held = False

    def reset_game(self):
        """Reset the game to start a new game"""
        self.scorecard = Scorecard()
        self.current_round = 1
        self.game_over = False
        self.rolls_used = 0
        for die in self.dice:
            die.held = False
            die.value = random.randint(1, 6)

    def roll_dice(self):
        """Start the dice rolling animation"""
        if not self.is_rolling and self.rolls_used < MAX_ROLLS_PER_TURN and not self.game_over:
            self.is_rolling = True
            self.roll_timer = 0
            self.rolls_used += 1
            # Determine final values for each die (only for unheld dice)
            self.final_values = []
            for die in self.dice:
                if die.held:
                    self.final_values.append(die.value)  # Keep current value
                else:
                    self.final_values.append(random.randint(1, 6))  # New random value

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
                if not self.game_over:
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and not self.scorecard.is_filled(cat):
                            self.hovered_category = cat
                            break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if scorecard category was clicked
                    clicked_category = False
                    for cat, rect in self.category_rects.items():
                        if rect.collidepoint(event.pos) and not self.scorecard.is_filled(cat):
                            # Lock in the score
                            score = calculate_score(cat, self.dice)
                            self.scorecard.set_score(cat, score)

                            # Check if game is complete
                            if self.scorecard.is_complete():
                                self.game_over = True
                            else:
                                self.current_round += 1
                                self.start_new_turn()

                            clicked_category = True
                            break

                    # Check if any die was clicked (only when not rolling, didn't click category, and game not over)
                    if not clicked_category and not self.is_rolling and not self.game_over:
                        for die in self.dice:
                            if die.contains_point(event.pos):
                                die.toggle_held()
                                break

            # Handle button clicks (only if not currently rolling)
            if self.roll_button.handle_event(event) and not self.is_rolling:
                self.roll_dice()

            # Handle play again button (only when game is over)
            if self.game_over and self.play_again_button.handle_event(event):
                self.reset_game()

    def update(self):
        """Update game state"""
        # Handle rolling animation
        if self.is_rolling:
            self.roll_timer += 1

            # During animation, rapidly change dice values (only for unheld dice)
            if self.roll_timer < self.roll_duration:
                for die in self.dice:
                    if not die.held:
                        die.value = random.randint(1, 6)
            else:
                # Animation complete - set final values
                for i, die in enumerate(self.dice):
                    die.value = self.final_values[i]
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
            if not self.scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            # Category name
            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            # Score (filled or potential)
            if self.scorecard.is_filled(cat):
                score = self.scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, self.dice)
                # Show valid scores in green, zero scores in gray
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Upper section totals
        y += 5
        upper_total = self.scorecard.get_upper_section_total()
        total_text = font.render(f"Total: {upper_total}", True, BLACK)
        self.screen.blit(total_text, (scorecard_x, y))
        y += row_height

        bonus = self.scorecard.get_upper_section_bonus()
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
            if not self.scorecard.is_filled(cat) and self.hovered_category == cat:
                pygame.draw.rect(self.screen, HOVER_COLOR, cat_rect, border_radius=5)

            # Category name
            name_text = font.render(cat.value, True, BLACK)
            self.screen.blit(name_text, (scorecard_x, y))

            # Score (filled or potential)
            if self.scorecard.is_filled(cat):
                score = self.scorecard.scores[cat]
                score_color = BLACK
            else:
                score = calculate_score(cat, self.dice)
                # Show valid scores in green, zero scores in gray
                score_color = VALID_SCORE_COLOR if score > 0 else GRAY

            score_text = font.render(str(score), True, score_color)
            self.screen.blit(score_text, (scorecard_x + col_width, y))
            y += row_height

        # Grand total
        y += 10
        grand_total = self.scorecard.get_grand_total()
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
        final_score = self.scorecard.get_grand_total()
        score_text = score_font.render(f"Final Score: {final_score}", True, (50, 100, 150))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 320))
        self.screen.blit(score_text, score_rect)

        # Breakdown
        breakdown_font = pygame.font.Font(None, 36)
        upper_total = self.scorecard.get_upper_section_total()
        upper_bonus = self.scorecard.get_upper_section_bonus()
        lower_total = self.scorecard.get_lower_section_total()

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
        round_text = round_font.render(f"Round {self.current_round}/13", True, BLACK)
        self.screen.blit(round_text, (50, 50))

        # Draw all dice
        for die in self.dice:
            die.draw(self.screen)

        # Draw roll button (disable during rolling animation, out of rolls, or game over)
        self.roll_button.enabled = not self.is_rolling and self.rolls_used < MAX_ROLLS_PER_TURN and not self.game_over
        self.roll_button.draw(self.screen)

        # Draw roll count
        roll_font = pygame.font.Font(None, 32)
        rolls_remaining = MAX_ROLLS_PER_TURN - self.rolls_used
        roll_text = roll_font.render(f"Rolls left: {rolls_remaining}", True, BLACK)
        self.screen.blit(roll_text, (350, 560))

        # Draw scorecard
        self.draw_scorecard()

        # Draw game over screen if game is over
        if self.game_over:
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
