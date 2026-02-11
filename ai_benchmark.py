#!/usr/bin/env python3
"""
Yahtzee AI Benchmark — Run N games per strategy and print score distributions.

Usage: uv run python ai_benchmark.py [--games N]
"""
import argparse
import random
import time

from ai import (
    RandomStrategy, GreedyStrategy, ExpectedValueStrategy,
    play_game,
)


def benchmark_strategy(strategy, num_games, start_seed=0):
    """Run num_games with a strategy and return scores and elapsed time."""
    scores = []
    t0 = time.perf_counter()
    for seed in range(start_seed, start_seed + num_games):
        random.seed(seed)
        state = play_game(strategy)
        scores.append(state.scorecard.get_grand_total())
    elapsed = time.perf_counter() - t0
    return scores, elapsed


def print_results(name, scores, elapsed):
    """Print formatted benchmark results."""
    avg = sum(scores) / len(scores)
    lo = min(scores)
    hi = max(scores)
    per_game = elapsed / len(scores) * 1000  # ms per game
    print(f"  {name:25s}  avg={avg:6.1f}  min={lo:4d}  max={hi:4d}  "
          f"({len(scores)} games in {elapsed:.2f}s, {per_game:.1f}ms/game)")


def main():
    parser = argparse.ArgumentParser(description="Yahtzee AI Benchmark")
    parser.add_argument("--games", type=int, default=200,
                        help="Number of games per strategy (default: 200)")
    parser.add_argument("--ev-sims", type=int, default=200,
                        help="Simulations per decision for EV strategy (default: 200)")
    args = parser.parse_args()

    strategies = [
        ("Random", RandomStrategy()),
        ("Greedy", GreedyStrategy()),
        (f"ExpectedValue(n={args.ev_sims})", ExpectedValueStrategy(num_simulations=args.ev_sims)),
    ]

    print(f"Yahtzee AI Benchmark — {args.games} games per strategy")
    print("=" * 80)

    for name, strategy in strategies:
        scores, elapsed = benchmark_strategy(strategy, args.games)
        print_results(name, scores, elapsed)

    print("=" * 80)


if __name__ == "__main__":
    main()
