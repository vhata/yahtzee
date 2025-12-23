# Yahtzee Game Development Plan

This document outlines the step-by-step plan for building a Yahtzee game using pygame with graphics.

## Project Overview
- **Technology**: Python with pygame
- **Environment**: uv-managed virtualenv
- **Development Approach**: Small, incremental commits for each feature

---

## Development Steps

### Step 1: Project Setup
- Create `pyproject.toml` for uv dependency management
- Add `.gitignore` (virtualenv, __pycache__, etc.)
- Initialize uv virtualenv and add pygame dependency
- Basic README with setup instructions

**Deliverable**: Project can be cloned and set up with `uv sync`

---

### Step 2: Basic Pygame Window
- Create `main.py` with pygame initialization
- Set up game loop with event handling and display
- Window sizing and basic structure

**Deliverable**: Running game shows empty window with proper game loop

---

### Step 3: Dice Class & Graphics
- Implement `Dice` class to represent a single die
- Draw dice faces graphically (dots for 1-6)
- Render 5 dice on screen in a row

**Deliverable**: 5 dice displayed on screen with visible faces

---

### Step 4: Dice Rolling Mechanics
- Add rolling animation (visual feedback)
- Random number generation for dice values
- "Roll" button to trigger rolling

**Deliverable**: Clicking "Roll" button randomizes all dice values

---

### Step 5: Dice Selection UI
- Implement click-to-hold/release dice functionality
- Visual indicator for held dice (highlight or different color)
- Held dice don't re-roll on subsequent rolls

**Deliverable**: Can click dice to hold/release, held dice stay constant when rolling

---

### Step 6: Scorecard Data Structure
- Create score category classes (Ones, Twos, etc.)
- Validation logic to check which categories are valid for current dice
- Data model to track filled vs available categories

**Deliverable**: Backend data structure for managing scorecard state

---

### Step 7: Score Calculation Logic
- Implement scoring algorithms for all 13 categories:
  - **Upper section**: Ones, Twos, Threes, Fours, Fives, Sixes
  - **Lower section**: 3 of a Kind, 4 of a Kind, Full House, Small Straight, Large Straight, Yahtzee, Chance

**Deliverable**: Given dice values, can calculate score for any category

---

### Step 8: Scorecard UI Rendering
- Display all 13 categories on screen
- Show current score and potential scores for available categories
- Visual layout for upper/lower sections and totals

**Deliverable**: Scorecard visible on screen with all categories

---

### Step 9: Turn Management
- Enforce 3-roll maximum per turn
- Track roll count and disable roll button after 3rd roll
- Reset turn state after scoring

**Deliverable**: Game enforces 3-roll limit per turn

---

### Step 10: Score Selection
- Click on scorecard category to lock in score
- Validate that category is available
- Update scorecard and move to next turn

**Deliverable**: Can select and lock in scores, scorecard updates correctly

---

### Step 11: Game Flow
- Implement 13-round game loop
- Calculate upper section bonus (35 points if upper section >= 63)
- Track game state (current round, game over)

**Deliverable**: Full 13-round game plays from start to finish

---

### Step 12: Game Over Screen
- Display final total score
- Show game summary
- "Play Again" button to restart

**Deliverable**: Game ends properly with final score display

---

### Step 13: Visual Polish
- Improve colors and fonts
- Add hover effects on buttons and scorecard
- Better spacing and layout
- Animation improvements

**Deliverable**: Polished, visually appealing game

---

## Progress Tracking

- [ ] Step 1: Project Setup
- [ ] Step 2: Basic Pygame Window
- [ ] Step 3: Dice Class & Graphics
- [ ] Step 4: Dice Rolling Mechanics
- [ ] Step 5: Dice Selection UI
- [ ] Step 6: Scorecard Data Structure
- [ ] Step 7: Score Calculation Logic
- [ ] Step 8: Scorecard UI Rendering
- [ ] Step 9: Turn Management
- [ ] Step 10: Score Selection
- [ ] Step 11: Game Flow
- [ ] Step 12: Game Over Screen
- [ ] Step 13: Visual Polish

---

## Notes

Each step is designed to be:
- Independently testable
- Committable to git
- Buildable on previous steps
- Small enough to complete in one session
