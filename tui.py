#!/usr/bin/env python3
"""
Yahtzee TUI — Terminal-based frontend using Textual.

Keyboard-driven interface with ASCII dice, scorecard table,
overlays, multiplayer, and AI spectator support.
"""
import random
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Center
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Label, Static
from textual.reactive import reactive
from textual import on

from game_engine import Category, calculate_score_in_context
from game_coordinator import GameCoordinator, parse_args, _make_strategy
from frontend_adapter import (
    FrontendAdapter, NullSound,
    CATEGORY_ORDER, CATEGORY_TOOLTIPS, OPTIMAL_EXPECTED_TOTAL,
)


# ── Unicode die faces ─────────────────────────────────────────────────────────

DIE_FACES = {1: "\u2680", 2: "\u2681", 3: "\u2682", 4: "\u2683", 5: "\u2684", 6: "\u2685"}

# Box-art die faces (7 lines each)
BOX_ART = {
    1: [
        "┌───────┐",
        "│       │",
        "│   ●   │",
        "│       │",
        "└───────┘",
    ],
    2: [
        "┌───────┐",
        "│ ●     │",
        "│       │",
        "│     ● │",
        "└───────┘",
    ],
    3: [
        "┌───────┐",
        "│ ●     │",
        "│   ●   │",
        "│     ● │",
        "└───────┘",
    ],
    4: [
        "┌───────┐",
        "│ ●   ● │",
        "│       │",
        "│ ●   ● │",
        "└───────┘",
    ],
    5: [
        "┌───────┐",
        "│ ●   ● │",
        "│   ●   │",
        "│ ●   ● │",
        "└───────┘",
    ],
    6: [
        "┌───────┐",
        "│ ●   ● │",
        "│ ●   ● │",
        "│ ●   ● │",
        "└───────┘",
    ],
}

BOX_ART_HELD = {
    v: [
        line.replace("┌", "╔").replace("┐", "╗")
        .replace("└", "╚").replace("┘", "╝")
        .replace("─", "═").replace("│", "║")
        for line in lines
    ]
    for v, lines in BOX_ART.items()
}

BOX_ART_CUP = [
    "┌───────┐",
    "│       │",
    "│   ?   │",
    "│       │",
    "└───────┘",
]


def render_dice_box(dice, rolls_used, is_rolling, colorblind=False):
    """Render 5 dice as box art, side by side."""
    if rolls_used == 0 and not is_rolling:
        # All in cup
        lines = []
        for row in range(5):
            lines.append("  ".join(BOX_ART_CUP[row] for _ in range(5)))
        label_parts = []
        for i in range(5):
            label_parts.append(f"   [{i+1}]   ")
        lines.append("  ".join(label_parts))
        return "\n".join(lines)

    lines = []
    for row in range(5):
        parts = []
        for i, die in enumerate(dice):
            if is_rolling and not die.held:
                val = random.randint(1, 6)
            else:
                val = die.value
            if die.held:
                parts.append(BOX_ART_HELD[val][row])
            else:
                parts.append(BOX_ART[val][row])
        lines.append("  ".join(parts))

    # Labels below dice
    label_parts = []
    for i, die in enumerate(dice):
        held_label = " HELD" if die.held else ""
        if colorblind and die.held:
            held_label = " [H]"
        label_parts.append(f"  [{i+1}]{held_label}".ljust(11))
    lines.append("".join(label_parts))
    return "\n".join(lines)


# ── Widgets ──────────────────────────────────────────────────────────────────

class DiceDisplay(Static):
    """Renders the 5 dice using box art."""

    def render(self):
        app = self.app
        coord = app.coordinator
        return render_dice_box(
            coord.dice, coord.rolls_used, coord.is_rolling,
            colorblind=app.adapter.colorblind_mode,
        )


class StatusDisplay(Static):
    """Shows roll status and AI reasoning."""

    def render(self):
        app = self.app
        coord = app.coordinator
        lines = []

        if coord.game_over:
            lines.append("[bold]GAME OVER![/bold]")
        elif coord.rolls_used == 0:
            lines.append("[bold]Roll the dice![/bold]")
        else:
            remaining = 3 - coord.rolls_used
            lines.append(f"Rolls left: {remaining}")

        if coord.current_ai_strategy and coord.ai_reason:
            lines.append(f"[dim]{coord.ai_reason}[/dim]")

        if coord.turn_transition and coord.multiplayer:
            idx = coord.current_player_index
            name, strategy = coord.player_configs[idx]
            if strategy is None:
                lines.append(f"\n[bold]{name}'s Turn![/bold]")
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                lines.append(f"\n[bold]{name}'s Turn! ({ai_name} AI)[/bold]")

        return "\n".join(lines)


class RoundDisplay(Static):
    """Shows round info and player bar."""

    def render(self):
        app = self.app
        coord = app.coordinator
        lines = []

        if coord.multiplayer:
            idx = coord.current_player_index
            name, strategy = coord.player_configs[idx]
            if strategy is None:
                lines.append(f"[bold]Round {coord.current_round}/13 — {name}'s turn[/bold]")
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                lines.append(f"[bold]Round {coord.current_round}/13 — {name} ({ai_name} AI)[/bold]")
            # Player bar
            parts = []
            for i in range(coord.num_players):
                pname, _ = coord.player_configs[i]
                score = coord.all_scorecards[i].get_grand_total()
                marker = ">" if i == idx and not coord.game_over else " "
                parts.append(f"{marker}{pname}: {score}")
            lines.append("  ".join(parts))
        else:
            lines.append(f"[bold]Round {coord.current_round}/13[/bold]")

        if coord.has_any_ai:
            lines.append(f"Speed: {coord.speed_name.capitalize()} (+/-)")

        return "\n".join(lines)


class ScorecardDisplay(Static):
    """Renders the scorecard as a text table."""

    def render(self):
        app = self.app
        coord = app.coordinator
        adapter = app.adapter
        scorecard = coord.scorecard
        dice = coord.dice

        lines = []

        # Header
        if coord.multiplayer:
            idx = coord.current_player_index
            name, _ = coord.player_configs[idx]
            lines.append(f"[bold]{name}'s Scorecard[/bold]")

        lines.append("[bold]── UPPER SECTION ──[/bold]")

        upper_cats = CATEGORY_ORDER[:6]
        lower_cats = CATEGORY_ORDER[6:]

        for cat in upper_cats:
            lines.append(self._format_row(cat, scorecard, dice, coord, adapter))

        upper_total = scorecard.get_upper_section_total()
        bonus = scorecard.get_upper_section_bonus()
        lines.append(f"  Total: {upper_total}  Bonus: {bonus}")

        lines.append("[bold]── LOWER SECTION ──[/bold]")

        for cat in lower_cats:
            lines.append(self._format_row(cat, scorecard, dice, coord, adapter))

        grand_total = scorecard.get_grand_total()
        lines.append(f"[bold]  GRAND TOTAL: {grand_total}[/bold]")

        # Tooltip
        tooltip_cat = None
        if adapter.hovered_category is not None:
            tooltip_cat = adapter.hovered_category
        elif adapter.kb_selected_index is not None:
            tooltip_cat = CATEGORY_ORDER[adapter.kb_selected_index]
        if tooltip_cat and not scorecard.is_filled(tooltip_cat) and coord.rolls_used > 0:
            tip = CATEGORY_TOOLTIPS.get(tooltip_cat, "")
            lines.append(f"\n[dim]{tip}[/dim]")

        return "\n".join(lines)

    def _format_row(self, cat, scorecard, dice, coord, adapter):
        """Format a single scorecard row."""
        idx = CATEGORY_ORDER.index(cat)
        is_selected = (adapter.kb_selected_index == idx)
        is_ai_choice = (coord.ai_showing_score_choice and
                        coord.ai_score_choice_category == cat)
        is_flash = (adapter.score_flash_category == cat)

        marker = ">>" if is_selected else "  "

        if scorecard.is_filled(cat):
            score = scorecard.scores[cat]
            if is_flash:
                return f"{marker}[bold yellow]{cat.value:<18} {score:>3}[/bold yellow]"
            return f"{marker}{cat.value:<18} {score:>3}"
        else:
            if coord.rolls_used > 0:
                potential = calculate_score_in_context(cat, dice, scorecard)
                if is_ai_choice:
                    return f"{marker}[bold cyan]{cat.value:<18} ({potential:>3})[/bold cyan]"
                elif is_selected:
                    return f"{marker}[bold]{cat.value:<18} ({potential:>3})[/bold]"
                elif potential > 0:
                    return f"{marker}[green]{cat.value:<18} ({potential:>3})[/green]"
                else:
                    return f"{marker}[dim]{cat.value:<18} ({potential:>3})[/dim]"
            else:
                return f"{marker}[dim]{cat.value:<18}  — [/dim]"


class GameOverDisplay(Static):
    """Shows game over summary."""

    def render(self):
        app = self.app
        coord = app.coordinator

        if not coord.game_over:
            return ""

        lines = ["", "[bold]═══ GAME OVER ═══[/bold]", ""]

        if coord.multiplayer:
            totals = [coord.all_scorecards[i].get_grand_total() for i in range(coord.num_players)]
            winner_idx = max(range(coord.num_players), key=lambda i: totals[i])
            winner_name = coord.player_configs[winner_idx][0]
            lines.append(f"[bold]{winner_name} wins![/bold]")
            lines.append("")
            for i in range(coord.num_players):
                name, strategy = coord.player_configs[i]
                score = totals[i]
                marker = " *" if i == winner_idx else ""
                lines.append(f"  {name}: {score}{marker}")
                if strategy is None:
                    pct = score / OPTIMAL_EXPECTED_TOTAL * 100
                    lines.append(f"    ({pct:.0f}% of optimal)")
        else:
            score = coord.scorecard.get_grand_total()
            lines.append(f"Final Score: [bold]{score}[/bold]")
            if coord.ai_strategy is None:
                pct = score / OPTIMAL_EXPECTED_TOTAL * 100
                lines.append(f"{pct:.0f}% of optimal play ({int(OPTIMAL_EXPECTED_TOTAL)} avg)")

        lines.append("")
        lines.append("[dim]Press N for new game, R for replay[/dim]")
        return "\n".join(lines)


# ── Modal Screens ────────────────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    """Help overlay showing key bindings."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
        Binding("f1", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        controls = [
            ("Space", "Roll dice"),
            ("1-5", "Toggle die hold"),
            ("Tab / ↓", "Next category"),
            ("Shift+Tab / ↑", "Previous category"),
            ("Enter", "Score selected category"),
            ("H", "Score history"),
            ("+/-", "AI speed"),
            ("Ctrl+Z", "Undo"),
            ("C", "Colorblind mode"),
            ("D", "Dark mode"),
            ("R", "Game replay (after game)"),
            ("Esc", "Close overlay / Quit"),
            ("? / F1", "This help screen"),
        ]
        text = "[bold]CONTROLS[/bold]\n\n"
        for key, desc in controls:
            text += f"  {key:<20} {desc}\n"
        text += "\n[dim]Press Esc or ? to close[/dim]"
        yield Center(Static(text, id="help-panel"))


class HistoryScreen(ModalScreen):
    """Score history overlay."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("h", "dismiss", "Close"),
        Binding("p", "cycle_player", "Player filter"),
        Binding("m", "cycle_mode", "Mode filter"),
    ]

    def compose(self) -> ComposeResult:
        yield Center(Static(self._build_text(), id="history-panel"))

    def _build_text(self):
        adapter = self.app.adapter
        entries = adapter.get_filtered_history(limit=20)
        p_label = adapter.history_filter_player.capitalize()
        m_label = adapter.history_filter_mode.capitalize()

        text = f"[bold]SCORE HISTORY[/bold]\n"
        text += f"Player: {p_label} (P)  |  Mode: {m_label} (M)\n"
        text += "─" * 60 + "\n"
        text += f"{'#':<4} {'Score':<8} {'Player':<12} {'Mode':<14} {'Date':<12}\n"
        text += "─" * 60 + "\n"

        if not entries:
            text += "\n  No scores recorded yet.\n"
        else:
            for i, entry in enumerate(entries):
                score = entry.get("score", "?")
                player = entry.get("player_type", "?").capitalize()
                mode = entry.get("mode", "?").capitalize()
                date = entry.get("date", "")[:10]
                text += f"{i+1:<4} {score:<8} {player:<12} {mode:<14} {date:<12}\n"

        text += "\n[dim]P/M: filter | H or Esc to close[/dim]"
        return text

    def action_cycle_player(self):
        self.app.adapter.cycle_player_filter()
        self.query_one("#history-panel", Static).update(self._build_text())

    def action_cycle_mode(self):
        self.app.adapter.cycle_mode_filter()
        self.query_one("#history-panel", Static).update(self._build_text())


class ReplayScreen(ModalScreen):
    """Post-game replay overlay."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("r", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Center(Static(self._build_text(), id="replay-panel"))

    def _build_text(self):
        coord = self.app.coordinator
        game_log = coord.game_log

        text = "[bold]GAME REPLAY[/bold]\n\n"

        score_entries = game_log.get_score_entries(player_index=0)
        if not score_entries:
            all_entries = [e for e in game_log.entries if e.event_type == "score"]
            if all_entries:
                score_entries = all_entries

        if not score_entries:
            text += "  No replay data available.\n"
        else:
            for entry in score_entries:
                turn_entries = game_log.get_turn_entries(entry.turn, entry.player_index)
                rolls = [e for e in turn_entries if e.event_type == "roll"]
                dice_str = ""
                if rolls:
                    parts = [f"[{','.join(str(v) for v in r.dice_values)}]" for r in rolls]
                    dice_str = " → ".join(parts)

                cat_name = entry.category.value if entry.category else "?"
                score_val = entry.score if entry.score is not None else "?"

                if coord.multiplayer:
                    pname = coord.player_configs[entry.player_index][0] if entry.player_index < len(coord.player_configs) else f"P{entry.player_index}"
                    line = f"T{entry.turn} {pname}: {dice_str} → {cat_name}: {score_val}"
                else:
                    line = f"Turn {entry.turn}: {dice_str} → {cat_name}: {score_val}"

                # Truncate long lines
                if len(line) > 70:
                    line = line[:67] + "..."
                text += f"  {line}\n"

        text += "\n[dim]R or Esc to close[/dim]"
        return text


class ConfirmZeroScreen(ModalScreen[bool]):
    """Confirm scoring 0 dialog."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("enter", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "No"),
    ]

    def __init__(self, category_name: str):
        super().__init__()
        self.category_name = category_name

    def compose(self) -> ComposeResult:
        text = f"[bold]Score 0 in {self.category_name}?[/bold]\n\n"
        text += "Y / Enter to confirm,  N / Esc to cancel"
        yield Center(Static(text, id="confirm-panel"))

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


class AutosaveResumeScreen(ModalScreen[bool]):
    """Prompt to resume a saved game."""

    BINDINGS = [
        Binding("y", "resume", "Resume"),
        Binding("n", "fresh", "New game"),
        Binding("escape", "fresh", "New game"),
    ]

    def compose(self) -> ComposeResult:
        text = "[bold]Resume previous game?[/bold]\n\n"
        text += "Y to resume,  N to start fresh"
        yield Center(Static(text, id="resume-panel"))

    def action_resume(self):
        self.dismiss(True)

    def action_fresh(self):
        self.dismiss(False)


# ── Main App ─────────────────────────────────────────────────────────────────

class YahtzeeApp(App):
    """Yahtzee terminal UI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #game-area {
        layout: horizontal;
        height: 1fr;
    }

    #dice-panel {
        width: 60;
        padding: 1 2;
    }

    #scorecard-panel {
        width: 1fr;
        padding: 1 2;
    }

    #round-display {
        height: auto;
        padding: 0 2;
    }

    #dice-display {
        height: auto;
    }

    #status-display {
        height: auto;
        margin-top: 1;
    }

    #roll-btn {
        margin-top: 1;
        width: 20;
    }

    #game-over-display {
        height: auto;
    }

    #help-panel, #history-panel, #replay-panel, #confirm-panel, #resume-panel {
        padding: 2 4;
        border: thick $accent;
        background: $surface;
        width: 70;
        height: auto;
        max-height: 80vh;
    }
    """

    BINDINGS = [
        Binding("space", "roll", "Roll", show=True),
        Binding("1", "hold_1", "Hold 1"),
        Binding("2", "hold_2", "Hold 2"),
        Binding("3", "hold_3", "Hold 3"),
        Binding("4", "hold_4", "Hold 4"),
        Binding("5", "hold_5", "Hold 5"),
        Binding("tab", "next_cat", "Next category", show=True),
        Binding("shift+tab", "prev_cat", "Prev category"),
        Binding("down", "next_cat", "Next"),
        Binding("up", "prev_cat", "Prev"),
        Binding("enter", "score", "Score", show=True),
        Binding("question_mark", "help", "Help"),
        Binding("f1", "help", "Help"),
        Binding("h", "history", "History"),
        Binding("r", "replay", "Replay"),
        Binding("c", "colorblind", "Colorblind"),
        Binding("d", "dark", "Dark mode"),
        Binding("plus", "speed_up", "+Speed"),
        Binding("equals", "speed_up", "+Speed"),
        Binding("minus", "speed_down", "-Speed"),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("n", "new_game", "New game"),
        Binding("escape", "quit_or_close", "Quit"),
    ]

    def __init__(self, coordinator=None, ai_strategy=None, speed="normal", players=None):
        super().__init__()
        if coordinator is not None:
            self.coordinator = coordinator
        else:
            self.coordinator = GameCoordinator(
                ai_strategy=ai_strategy, speed=speed, players=players
            )
        self.adapter = FrontendAdapter(self.coordinator, sound=NullSound())
        self._tick_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="round-display")
        with Horizontal(id="game-area"):
            with Vertical(id="dice-panel"):
                yield DiceDisplay(id="dice-display")
                yield Button("ROLL", id="roll-btn", variant="primary")
                yield StatusDisplay(id="status-display")
                yield GameOverDisplay(id="game-over-display")
            with Vertical(id="scorecard-panel"):
                yield ScorecardDisplay(id="scorecard-display")
        yield Footer()

    def on_mount(self):
        self.title = "Yahtzee"
        self.adapter.load_settings()
        self.dark = self.adapter.dark_mode
        self._tick_timer = self.set_interval(1 / 20, self._game_tick)

    def _game_tick(self):
        """Per-frame game update at ~20 FPS."""
        coord = self.coordinator

        # Pause when idle (human turn, not rolling, no transition)
        if (coord.is_current_player_human and not coord.is_rolling
                and not coord.turn_transition and not coord.game_over):
            self._refresh_display()
            return

        self.adapter.update()
        self._refresh_display()

    def _refresh_display(self):
        """Refresh all display widgets."""
        try:
            self.query_one("#dice-display", DiceDisplay).refresh()
            self.query_one("#status-display", StatusDisplay).refresh()
            self.query_one("#scorecard-display", ScorecardDisplay).refresh()
            self.query_one("#round-display", Static).update(self._round_text())
            self.query_one("#game-over-display", GameOverDisplay).refresh()
            self.query_one("#roll-btn", Button).disabled = not coord_can_roll(self.coordinator)
        except Exception:
            import logging
            logging.getLogger(__name__).debug("Refresh error", exc_info=True)

    def _round_text(self):
        """Build round/player bar text."""
        coord = self.coordinator
        if coord.multiplayer:
            idx = coord.current_player_index
            name, strategy = coord.player_configs[idx]
            parts = []
            for i in range(coord.num_players):
                pname, _ = coord.player_configs[i]
                score = coord.all_scorecards[i].get_grand_total()
                marker = "▸" if i == idx and not coord.game_over else " "
                parts.append(f"{marker}{pname}:{score}")
            bar = "  ".join(parts)
            return f"Round {coord.current_round}/13 | {bar}"
        else:
            speed_info = ""
            if coord.has_any_ai:
                speed_info = f" | Speed: {coord.speed_name.capitalize()}"
            return f"Round {coord.current_round}/13{speed_info}"

    # ── Actions ──────────────────────────────────────────────────────────

    def _can_play(self):
        """Whether human input is allowed right now."""
        coord = self.coordinator
        return (coord.is_current_player_human and not coord.game_over
                and not coord.is_rolling and not coord.turn_transition)

    def action_roll(self):
        if not self._can_play():
            return
        self.adapter.do_roll()
        self._refresh_display()

    @on(Button.Pressed, "#roll-btn")
    def on_roll_button(self):
        self.action_roll()

    def action_hold_1(self):
        self._do_hold(0)

    def action_hold_2(self):
        self._do_hold(1)

    def action_hold_3(self):
        self._do_hold(2)

    def action_hold_4(self):
        self._do_hold(3)

    def action_hold_5(self):
        self._do_hold(4)

    def _do_hold(self, index):
        if not self._can_play():
            return
        self.adapter.do_hold(index)
        self._refresh_display()

    def action_next_cat(self):
        if not self._can_play():
            return
        self.adapter.navigate_category(+1)
        self._refresh_display()

    def action_prev_cat(self):
        if not self._can_play():
            return
        self.adapter.navigate_category(-1)
        self._refresh_display()

    def action_score(self):
        if not self._can_play():
            return
        adapter = self.adapter
        if adapter.kb_selected_index is None:
            return
        cat = CATEGORY_ORDER[adapter.kb_selected_index]
        score = calculate_score_in_context(cat, self.coordinator.dice, self.coordinator.scorecard)
        if self.coordinator.scorecard.is_filled(cat) or self.coordinator.rolls_used == 0:
            return

        if score == 0:
            # Show confirmation dialog
            def on_confirm(result: bool):
                if result:
                    adapter.confirm_zero_category = cat
                    adapter.confirm_zero_yes()
                else:
                    adapter.confirm_zero_no()
                self._refresh_display()
            self.push_screen(ConfirmZeroScreen(cat.value), on_confirm)
        else:
            adapter.try_score_category(cat)
            self._refresh_display()

    def action_help(self):
        self.push_screen(HelpScreen())

    def action_history(self):
        self.push_screen(HistoryScreen())

    def action_replay(self):
        if self.coordinator.game_over:
            self.push_screen(ReplayScreen())

    def action_colorblind(self):
        self.adapter.toggle_colorblind()
        self._refresh_display()

    def action_dark(self):
        self.adapter.toggle_dark_mode()
        self.dark = self.adapter.dark_mode
        self._refresh_display()

    def action_speed_up(self):
        self.adapter.change_speed(+1)
        self._refresh_display()

    def action_speed_down(self):
        self.adapter.change_speed(-1)
        self._refresh_display()

    def action_undo(self):
        if self.adapter.do_undo():
            self._refresh_display()

    def action_new_game(self):
        if self.coordinator.game_over:
            self.adapter.do_reset()
            self._refresh_display()

    def action_quit_or_close(self):
        # If any screen is stacked, pop it
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.exit()


def coord_can_roll(coord):
    """Whether roll button should be enabled."""
    return (coord.is_current_player_human and coord.can_roll_now
            and not coord.turn_transition)


def main(argv=None):
    """Entry point for the TUI."""
    args = parse_args(argv)

    # Check for autosave
    saved_coord = GameCoordinator.load_state()
    coordinator = None

    if saved_coord is not None:
        # In TUI, we can't easily prompt before app start, so just resume
        # (the user can press N to start fresh once in the app)
        coordinator = saved_coord

    if coordinator is None:
        if args.players:
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

            coordinator = GameCoordinator(speed=args.speed, players=players)
        else:
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

            coordinator = GameCoordinator(ai_strategy=ai_strategy, speed=args.speed)

    app = YahtzeeApp(coordinator=coordinator)
    app.run()


if __name__ == "__main__":
    main()
