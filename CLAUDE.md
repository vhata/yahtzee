# Claude Agent Workflow Guide

This document explains how to work on this Yahtzee project using the established workflow and conventions.

## Project Overview

This is a Yahtzee game built with Python and pygame, developed using an incremental, step-by-step approach with clear documentation and git history.

## Core Principles

1. **Plan First, Code Second**: Always start with a clear plan documented in PLAN.md
2. **Small, Atomic Commits**: Each feature/fix gets exactly one commit
3. **Documentation is Mandatory**: Update PLAN.md as work progresses
4. **Clear Communication**: Explain the "why" behind changes, not just the "what"

## Development Workflow

### Phase 1: Planning

1. Break down the project into discrete, testable steps
2. Document each step in PLAN.md with:
   - Clear description of what to build
   - Deliverable (what success looks like)
   - Dependencies on previous steps
3. Each step should be completable in one session
4. Create a progress tracking checklist

**Example from this project**: We broke Yahtzee into 13 steps from "Project Setup" to "Visual Polish"

### Phase 2: Implementation

For each step:

1. **Mark as in-progress** in your todo list (use TodoWrite tool)
2. **Implement the feature**:
   - Read relevant files first
   - Make focused changes
   - Keep changes minimal and on-topic
3. **Test the changes**:
   - Run the code to verify it works
   - Check for visual/functional issues
4. **Commit with detailed message**:
   - Use the heredoc format for multi-line commits
   - Explain what changed and why
   - Include "Step X:" prefix for step commits
   - Use "Bug Fix X:" prefix for bug fixes
5. **Mark as completed** in your todo list

**Commit Message Format**:
```bash
git commit -m "$(cat <<'EOF'
Step X: Brief title

- Bullet point of what changed
- Another change
- Why this approach was chosen

Result/impact of the changes.
EOF
)"
```

### Phase 3: Quality Assurance

After completing all planned development steps:

1. **Test the complete application**
2. **Identify issues**:
   - Visual bugs
   - UX problems
   - Logic errors
   - Performance issues
3. **Document findings** before fixing

### Phase 4: Bug Fixes

For each bug discovered:

1. **Document in PLAN.md** under "Quality Assurance & Bug Fixes":
   ```markdown
   ## Bug Fix N: Brief Title (commit hash)

   **Issue Discovered**: What was wrong

   **Root Cause**: Why it happened

   **Fix Applied**:
   - What was changed
   - Technical details

   **Deliverable**: Expected result after fix
   ```

2. **Implement the fix**
3. **Commit with "Bug Fix X:" prefix**
4. **Update progress tracking** in PLAN.md

## File Structure Conventions

```
yahtzee/
├── PLAN.md          # Development plan and progress tracking
├── CLAUDE.md        # This file - workflow documentation
├── README.md        # User-facing documentation
├── main.py          # Main game code
├── pyproject.toml   # Dependencies
└── .gitignore       # Git ignore rules
```

## When User Reports Issues

1. **Listen carefully** to the user's description
2. **Test/verify the issue** if possible
3. **Explain what you're going to do** before doing it
4. **Ask for confirmation** on approach if there are multiple solutions
5. **Update documentation** (PLAN.md) to reflect the bug fix

**Example**: User said "2.5 of the dice are hidden behind the score panel"
- We tested and confirmed the issue
- Explained the fix approach (reposition dice to left)
- Implemented the fix
- Documented it in PLAN.md

## PLAN.md Structure

The PLAN.md file has two major sections:

### 1. Development Steps
- Steps 1-N with detailed descriptions
- Progress tracking checklist
- Each step marked [x] when complete

### 2. Quality Assurance & Bug Fixes
- Separate section after development
- Individual bug fix entries numbered sequentially
- Same level of detail as development steps
- Progress tracking for bug fixes

## Todo List Management

Use the TodoWrite tool throughout:
- Create todos at project start
- Mark exactly ONE todo as "in_progress" at a time
- Mark as "completed" immediately after finishing
- Keep the list current and accurate

## Communication Style

When working with the user:
- **Be proactive**: Suggest improvements you notice
- **Explain your reasoning**: Help the user understand decisions
- **Ask when uncertain**: Multiple valid approaches? Ask which they prefer
- **Confirm understanding**: Repeat back complex requests
- **Celebrate progress**: Acknowledge milestones

## Git Conventions

- **One feature = One commit**: Never bundle unrelated changes
- **Atomic commits**: Each commit should be independently valid
- **Clear commit messages**: Future developers should understand the "why"
- **Test before committing**: Code should work at every commit
- **Update documentation in same commit**: Keep docs in sync with code

## Tools and Environment

- **Package Manager**: uv (not pip)
- **Python**: 3.10+
- **Game Framework**: pygame
- **Testing**: Manual testing via `uv run python main.py`

## Common Patterns in This Project

### Adding New Features
1. Read existing code to understand patterns
2. Follow established naming conventions
3. Use existing constants for colors, sizes, etc.
4. Maintain consistent visual style

### Modifying UI
1. Check current layout/positioning
2. Consider impact on other UI elements
3. Test at runtime to verify appearance
4. Update related elements (buttons, text, etc.)

### Animation Changes
1. Use existing animation framework (`is_rolling`, `roll_timer`)
2. Maintain consistent timing with FPS constant
3. Test that animations feel smooth
4. Consider interaction disabling during animations

## Troubleshooting

If the user reports an issue:
1. **Reproduce it**: Understand the exact problem
2. **Check recent changes**: What might have caused it?
3. **Read relevant code**: Understand the current implementation
4. **Propose solution**: Explain what you'll change and why
5. **Implement carefully**: Make minimal, focused changes
6. **Test thoroughly**: Verify the fix works

## Project Completion Checklist

- [ ] All planned steps completed and committed
- [ ] All features tested and working
- [ ] QA phase completed
- [ ] All discovered bugs fixed and documented
- [ ] PLAN.md fully updated with all changes
- [ ] Progress tracking shows [x] for all items
- [ ] Total commit count accurate

## Key Learnings from This Project

1. **Planning prevents rework**: The step-by-step plan kept us focused
2. **Small commits are valuable**: Easy to review, revert, or cherry-pick
3. **Documentation matters**: PLAN.md became our project history
4. **QA reveals issues**: Even "complete" code needs testing
5. **User feedback is gold**: The user spotted issues we missed

## Continuing This Project

If you (future Claude agent) need to continue this project:

1. **Read PLAN.md first**: Understand what's been done
2. **Check git log**: Review recent commits
3. **Run the game**: See current state
4. **Ask user for priorities**: What needs work next?
5. **Follow this workflow**: Maintain consistency

## Example Session Flow

```
User: "Let's add feature X"
Claude:
  1. Reviews PLAN.md to see if it fits into existing structure
  2. Proposes approach: "I'll add this as Bug Fix N" or "This is a new feature"
  3. Reads relevant code to understand current implementation
  4. Implements the change
  5. Tests it works
  6. Commits with detailed message
  7. Updates PLAN.md
  8. Confirms completion with user
```

---

**Remember**: This workflow exists to maintain quality, clarity, and consistency. When in doubt, refer back to these principles and ask the user for guidance.
