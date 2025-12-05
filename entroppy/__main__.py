"""Main entry point for autocorrgen package."""

from loguru import logger

from entroppy.cli import create_parser
from entroppy.core import load_config
from entroppy.processing import run_pipeline
from entroppy.utils.constants import Constants
from entroppy.utils.debug import DebugTypoMatcher
from entroppy.utils.logging import setup_logger


def _print_startup_banner(verbose: bool) -> None:
    """Print startup banner if verbose."""
    if verbose:
        logger.info("=" * 60)
        logger.info("EntropPy - Autocorrect Dictionary Generator")
        logger.info("=" * 60)
        logger.info("")


def _validate_config(config, parser) -> None:
    """Validate configuration settings."""
    if not config.top_n and not config.include:
        parser.error("Must specify either --top-n or --include (or both)")

    if (
        config.platform == "espanso"
        and config.max_entries_per_file > Constants.ESPANSO_MAX_ENTRIES_WARNING
    ):
        logger.warning("")
        logger.warning("⚠️  WARNING: max_entries_per_file exceeds recommended limit")
        logger.warning(f"   Current value: {config.max_entries_per_file}")
        logger.warning("   Recommended: ≤ 1000")
        logger.warning("   Large files may cause Espanso performance issues")
        logger.warning("")

    if (config.debug_words or config.debug_typos) and not (config.debug and config.verbose):
        parser.error("--debug-words and --debug-typos require BOTH --debug and --verbose flags")


def _setup_debug_matcher(config) -> None:
    """Create debug typo matcher if needed."""
    if config.debug_typos:
        config.debug_typo_matcher = DebugTypoMatcher.from_patterns(config.debug_typos)


def _print_config_summary(config) -> None:
    """Print configuration summary if verbose."""
    if config.verbose:
        logger.info("Configuration:")
        logger.info(f"  Platform: {config.platform}")
        if config.top_n:
            logger.info(f"  Top N words: {config.top_n}")
        if config.include:
            logger.info(f"  Include file: {config.include}")
        if config.exclude:
            logger.info(f"  Exclude file: {config.exclude}")
        if config.max_corrections:
            logger.info(f"  Max corrections: {config.max_corrections}")
        logger.info(f"  Workers: {config.jobs}")
        logger.info("")


def _run_pipeline_with_error_handling(config) -> None:
    """Run pipeline with proper error handling."""
    try:
        run_pipeline(config)
        if config.verbose:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ Processing completed successfully")
            logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  Processing interrupted by user")
        raise
    except Exception:
        if config.verbose:
            logger.error("")
            logger.error("=" * 60)
            logger.error("✗ Processing failed")
            logger.error("=" * 60)
        raise


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config, args, parser)

    # Setup logging
    setup_logger(verbose=config.verbose, debug=config.debug)

    # Print startup banner
    _print_startup_banner(config.verbose)

    # Validate configuration
    _validate_config(config, parser)

    # Setup debug matcher
    _setup_debug_matcher(config)

    # Print configuration summary
    _print_config_summary(config)

    # Run pipeline
    _run_pipeline_with_error_handling(config)


if __name__ == "__main__":
    main()
