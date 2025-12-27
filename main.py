#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame
"""
import pygame
import sys
import random

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
DICE_COLOR = (240, 240, 240)
DOT_COLOR = (50, 50, 50)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 149, 237)
BUTTON_TEXT_COLOR = (255, 255, 255)

# Dice constants
DICE_SIZE = 80
DICE_MARGIN = 20
DOT_RADIUS = 6


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
        # Draw dice background
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, DICE_COLOR, dice_rect, border_radius=10)

        # Draw border - thicker and colored if held
        if self.held:
            # Green highlight for held dice
            pygame.draw.rect(surface, (50, 200, 50), dice_rect, width=5, border_radius=10)
        else:
            pygame.draw.rect(surface, BLACK, dice_rect, width=2, border_radius=10)

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

        # Animation state
        self.is_rolling = False
        self.roll_timer = 0
        self.roll_duration = 30  # frames (0.5 seconds at 60 FPS)
        self.final_values = []

    def roll_dice(self):
        """Start the dice rolling animation"""
        if not self.is_rolling:
            self.is_rolling = True
            self.roll_timer = 0
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
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if any die was clicked (only when not rolling)
                    if not self.is_rolling:
                        for die in self.dice:
                            if die.contains_point(event.pos):
                                die.toggle_held()
                                break

            # Handle button clicks (only if not currently rolling)
            if self.roll_button.handle_event(event) and not self.is_rolling:
                self.roll_dice()

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

    def draw(self):
        """Draw everything to the screen"""
        # Clear screen with white background
        self.screen.fill(WHITE)

        # Draw a simple title for now
        font = pygame.font.Font(None, 72)
        title = font.render("YAHTZEE", True, BLACK)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        # Draw all dice
        for die in self.dice:
            die.draw(self.screen)

        # Draw roll button (disable during rolling animation)
        self.roll_button.enabled = not self.is_rolling
        self.roll_button.draw(self.screen)

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
