#!/usr/bin/env python3
"""
Yahtzee AI Benchmark — Run N games per strategy and print score distributions.

Usage: uv run python ai_benchmark.py [--games N] [--strategy NAME]
       uv run python ai_benchmark.py --verbose --games 50
       uv run python ai_benchmark.py --csv --games 200
"""
import argparse
import random
import statistics
import time

from ai import (
    ExpectedValueStrategy,
    GreedyStrategy,
    OptimalStrategy,
    RandomStrategy,
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


def print_results(name, scores, elapsed, verbose=False):
    """Print formatted benchmark results.

    Default output matches the original format (backward compatible).
    With verbose=True, adds stdev, median, and percentiles.
    """
    avg = sum(scores) / len(scores)
    lo = min(scores)
    hi = max(scores)
    per_game = elapsed / len(scores) * 1000  # ms per game
    print(f"  {name:25s}  avg={avg:6.1f}  min={lo:4d}  max={hi:4d}  "
          f"({len(scores)} games in {elapsed:.2f}s, {per_game:.1f}ms/game)")

    if verbose:
        stdev = statistics.stdev(scores) if len(scores) >= 2 else 0.0
        median = statistics.median(scores)
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        p25 = sorted_scores[n // 4]
        p75 = sorted_scores[(3 * n) // 4]
        print(f"  {'':25s}  stdev={stdev:5.1f}  median={median:5.0f}  "
              f"p25={p25:4d}  p75={p75:4d}")


def print_csv_header():
    """Print CSV header row."""
    print("strategy,games,avg,stdev,median,min,max,p25,p75,elapsed_s")


def print_csv_row(name, scores, elapsed):
    """Print one CSV data row."""
    avg = sum(scores) / len(scores)
    stdev = statistics.stdev(scores) if len(scores) >= 2 else 0.0
    median = statistics.median(scores)
    lo = min(scores)
    hi = max(scores)
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    p25 = sorted_scores[n // 4]
    p75 = sorted_scores[(3 * n) // 4]
    print(f"{name},{len(scores)},{avg:.1f},{stdev:.1f},{median:.0f},"
          f"{lo},{hi},{p25},{p75},{elapsed:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Yahtzee AI Benchmark")
    parser.add_argument("--games", type=int, default=200,
                        help="Number of games per strategy (default: 200)")
    parser.add_argument("--ev-sims", type=int, default=200,
                        help="Simulations per decision for EV strategy (default: 200)")
    parser.add_argument("--strategy", choices=["random", "greedy", "ev", "optimal"],
                        help="Run only a single strategy (default: all)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show extra statistics (stdev, median, percentiles)")
    parser.add_argument("--csv", action="store_true",
                        help="Output results as CSV")
    args = parser.parse_args()

    # Build strategy list — EV is created here so --ev-sims is honoured
    ev_entry = (f"ExpectedValue(n={args.ev_sims})",
                ExpectedValueStrategy(num_simulations=args.ev_sims))
    all_strategies = {
        "random": ("Random", RandomStrategy()),
        "greedy": ("Greedy", GreedyStrategy()),
        "ev": ev_entry,
        "optimal": ("Optimal", OptimalStrategy()),
    }

    if args.strategy:
        strategies = [all_strategies[args.strategy]]
    else:
        strategies = list(all_strategies.values())

    if args.csv:
        print_csv_header()
        for name, strategy in strategies:
            scores, elapsed = benchmark_strategy(strategy, args.games)
            print_csv_row(name, scores, elapsed)
    else:
        print(f"Yahtzee AI Benchmark — {args.games} games per strategy")
        print("=" * 80)

        for name, strategy in strategies:
            scores, elapsed = benchmark_strategy(strategy, args.games)
            print_results(name, scores, elapsed, verbose=args.verbose)

        print("=" * 80)


if __name__ == "__main__":
    main()
