"""
Pure-Python layout constants and computation for the pygame frontend.

Extracted from main.py so that tests can import layout data without
triggering pygame initialization (which opens a window and plays audio).
"""
from dataclasses import dataclass

# Window
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700

# Dice constants
DICE_SIZE = 80
DICE_MARGIN = 20


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
