#!/usr/bin/env python3
"""
Yahtzee Game - A graphical implementation using pygame
"""
import pygame
import sys

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

    def draw(self, surface):
        """Draw the die with its current value"""
        # Draw dice background
        dice_rect = pygame.Rect(self.x, self.y, DICE_SIZE, DICE_SIZE)
        pygame.draw.rect(surface, DICE_COLOR, dice_rect, border_radius=10)
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
            # Show values 1-5 for demonstration
            dice = Dice(x, dice_y, value=i + 1)
            self.dice.append(dice)

    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        """Update game state"""
        pass

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
