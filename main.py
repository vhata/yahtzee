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

class YahtzeeGame:
    """Main game class for Yahtzee"""

    def __init__(self):
        """Initialize the game window and basic components"""
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Yahtzee")
        self.clock = pygame.time.Clock()
        self.running = True

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
