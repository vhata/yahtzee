# Features

## Core Game
- Full Yahtzee rules: 13 categories, upper/lower sections, upper bonus (35 pts for 63+)
- Graphical dice with dot rendering and roll animation
- Click-to-hold dice selection with visual indicators
- Scorecard UI showing filled scores, potential scores, and totals
- 3-roll-per-turn enforcement
- Game over screen with final score

## Multiplayer
- 2–4 players taking turns (any mix of human and AI)
- Turn transition overlay between players
- Per-player scorecards with winner announcement
- CLI: `--players human optimal greedy` etc.

## AI Players
- **RandomStrategy**: random holds and category selection (baseline)
- **GreedyStrategy**: picks highest-scoring category each turn
- **ExpectedValueStrategy**: Monte Carlo simulation over future rolls
- **OptimalStrategy**: exact probability computation via precomputed dice tables (fastest and strongest)
- Single-player spectator mode: `--ai --optimal`
- AI hold visualization (brief pause showing held dice before rolling)

## Sound Effects
- Synthesized PCM waveforms (no external assets or numpy)
- Dice roll, click, score, and fanfare sounds
- M key to toggle mute

## Undo
- Ctrl+Z / Cmd+Z undoes human actions (rolls, holds, category selections)
- Blocked during AI turns, roll animations, and turn transitions
- Stack clears on game reset and multiplayer turn boundaries

## Score Animation
- Scored category flashes with gold sine-wave highlight

## Speed Control
- Three presets: slow, normal, fast
- +/- keys to adjust AI playback speed
- `--speed` CLI flag

## Testing
- 370 automated tests across 4 test files
- Engine tests (single-player + multiplayer), AI legality/quality tests, dice table tests
- Coordinator tests (state machine, undo, score animation, integration, smoke rendering)
- Integration tests verify coordinator tick loop matches headless `play_game()` exactly
