"""Command-line interface."""

import argparse
from multiprocessing import cpu_count


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate Espanso autocorrect dictionary from common typos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using JSON config
  %(prog)s --config config.json
  
  # Using CLI args
  %(prog)s --top-n 1000 -o ~/.config/espanso/match/ -v
  
  # Mix both (CLI overrides JSON)
  %(prog)s --config config.json --top-n 500 -v
  
  # With the top 1000 most common English words and my custom words
  %(prog)s --top-n 1000 --include mywords.txt -o ~/.config/espanso/match/

  # With custom words only, do not use english-words dictionary
  %(prog)s --include mywords.txt -o ~/.config/espanso/match/

Output files are organized alphabetically in the output directory:
- If corrections exceed max_entries_per_file: typos_<first_word>_to_<last_word>.yml
- Otherwise: typos_<letter>.yml or typos_symbols.yml

Example config.json:
{
  "top_n": 1000,
  "max_word_length": 10,
  "min_word_length": 3,
  "min_typo_length": 5,
  "freq_ratio": 10.0,
  "max_entries_per_file": 750,
  "typo_freq_threshold": 1e-8,
  "output": "~/.config/espanso/match/",
  "reports": "./reports",
  "verbose": true,
  "jobs": 4
}
        """,
    )

    # Configuration
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="JSON configuration file (CLI args override JSON values)",
    )

    # Output
    parser.add_argument(
        "-o", "--output", type=str, help="Output directory for YAML files"
    )
    parser.add_argument(
        "--reports",
        type=str,
        help="Directory to generate detailed reports (creates timestamped subdirectories)",
    )

    # Word lists
    parser.add_argument(
        "--top-n", type=int, help="Pull top N most common English words"
    )
    parser.add_argument(
        "--include", type=str, help="File with additional words to include"
    )
    parser.add_argument("--exclude", type=str, help="File with exclusion patterns")
    parser.add_argument(
        "--adjacent-letters", type=str, help="File mapping keys to adjacent letters"
    )

    # Parameters
    parser.add_argument(
        "--freq-ratio",
        type=float,
        help="Minimum frequency ratio for collision resolution",
        default=10.0,
    )
    parser.add_argument(
        "--max-word-length", type=int, help="Maximum word length to process", default=10
    )
    parser.add_argument(
        "--min-word-length", type=int, help="Minimum source word length", default=3
    )
    parser.add_argument(
        "--min-typo-length",
        type=int,
        help="Minimum typo length to include in output",
        default=4,
    )
    parser.add_argument(
        "--max-entries-per-file",
        type=int,
        help="Maximum corrections per YAML file",
        default=500,
    )
    parser.add_argument(
        "--typo-freq-threshold",
        type=float,
        help="Skip typos with wordfreq frequency above this",
        default=0.0,
    )

    # Flags
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        help=f"Number of parallel workers (default: {cpu_count()})",
    )

    return parser
