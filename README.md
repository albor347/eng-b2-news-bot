# Breaking News English B2 Bot

This script fetches the latest Level 4 articles from [BreakingNewsEnglish.com](https://breakingnewsenglish.com/), summarizes them in Turkish using GPT-4o and produces vocabulary questions.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run in dry mode (no network or GPT calls):

```bash
python bne_b2_bot.py --dry-run
```

Run with GPT and optional Anki deck generation:

```bash
OPENAI_API_KEY=your-key python bne_b2_bot.py --run --anki
```

The script creates a markdown file named `YYYY-MM-DD_bne_b2.md` and, if `--anki` is supplied, an Anki `.apkg` file.

## macOS Cron Example

To run every Monday at 8am:

```
0 8 * * 1 /usr/local/bin/python3 /path/to/bne_b2_bot.py --run >> ~/bne_bot.log 2>&1
```

## Tests

Run tests with:

```bash
python -m pytest
```

Tests use `--dry-run` mode and verify markdown output creation.
