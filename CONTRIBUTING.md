# Contributing to Polymarket Arbitrage Bot

Thank you for your interest in contributing! This project is an educational tool for exploring prediction market arbitrage.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature suggestion:

1. Check existing issues to avoid duplicates
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Relevant logs or error messages

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Make your changes following our coding standards
4. Write tests for new functionality
5. Run tests: `pytest tests/ -v`
6. Commit with conventional commits (see below)
7. Push and create a pull request

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for function signatures
- Add docstrings for all public functions/classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable names

Example:
```python
def calculate_divergence(exchange_price: float, market_odds: float) -> float:
    """
    Calculate price divergence between exchange and market.
    
    Args:
        exchange_price: Current price on exchange
        market_odds: Probability from prediction market
        
    Returns:
        Divergence value (0-1)
    """
    # Implementation here
    pass
```

### Commit Messages

Use conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for Coinbase exchange monitoring
fix: correct P&L calculation for short positions
docs: update configuration examples
test: add integration tests for position manager
refactor: extract market filtering into separate module
```

**No emojis in commit messages or code.**

### Code Comments

Write comments that explain **why**, not **what**:

```python
# Good: Explain the reasoning
# Use 30-second cooldown to avoid duplicate signals
# when rapid price movements trigger multiple alerts
cooldown_seconds = 30

# Bad: Describe what the code does (obvious from reading it)
# Set cooldown to 30 seconds
cooldown_seconds = 30
```

## Testing

All new features should include tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_arbitrage_detector.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

Test structure:
```python
def test_feature_description():
    """Test that feature works correctly."""
    # Arrange
    detector = ArbitrageDetector()
    
    # Act
    result = detector.detect_opportunity(...)
    
    # Assert
    assert result is not None
    assert result.divergence > 0.05
```

## Documentation

- Update README.md if adding new features
- Add docstrings to all public functions
- Update QUICKSTART.md for user-facing changes
- Comment complex algorithms or business logic

## Project Structure

```
polymarket-arbitrage-bot/
├── src/                    # Core modules
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   ├── exchange_monitor.py    # Exchange price monitoring
│   ├── polymarket_client.py   # Polymarket API
│   ├── arbitrage_detector.py  # Opportunity detection
│   ├── position_manager.py    # Trade execution
│   └── risk_manager.py        # Risk controls
├── tests/                 # Unit tests
├── bot.py                 # Main entry point
├── config.example.json    # Configuration template
├── requirements.txt       # Dependencies
└── README.md             # Project documentation
```

## Feature Ideas

Potential areas for contribution:

### High Priority
- Real Polymarket market data integration
- Backtesting framework with historical data
- Web dashboard for monitoring
- More sophisticated divergence detection algorithms
- Support for additional exchanges (Kraken, FTX, etc.)

### Medium Priority
- Telegram/Discord notifications
- Database for trade history
- Performance analytics and reporting
- Configuration validation improvements
- Dry-run mode for paper trading

### Advanced
- Machine learning for opportunity prediction
- Multi-leg arbitrage strategies
- Cross-market correlation analysis
- Automated parameter optimization

## Code Review Process

Pull requests will be reviewed for:

1. **Correctness**: Does it work as intended?
2. **Tests**: Are there adequate tests?
3. **Style**: Does it follow our standards?
4. **Documentation**: Is it well-documented?
5. **Performance**: Any performance implications?

## Getting Help

- Check existing issues and discussions
- Read the code - it's well-commented
- Ask questions in your PR or issue

## Legal

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make this project better!
