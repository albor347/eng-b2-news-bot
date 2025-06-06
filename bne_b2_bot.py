import argparse
import datetime
import os
import re
from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup

# Optional imports for runtime
try:
    import openai
except Exception:
    openai = None

try:
    import genanki
except Exception:
    genanki = None


@dataclass
class Article:
    title: str
    url: str
    text: str
    mp3_url: str
    discussion: List[str]


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a URL and return BeautifulSoup object."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_level4_links(base_url: str, count: int = 3) -> List[str]:
    """Return latest `count` Level 4 article links."""
    soup = fetch_page(base_url)
    # Find link to the Level 4 page under 'Harder'
    level4_link = None
    for a in soup.find_all("a"):
        if a.text.strip().lower() == "level 4":
            level4_link = a.get("href")
            break
    if not level4_link:
        raise ValueError("Could not find Level 4 link")
    if not level4_link.startswith("http"):
        level4_link = requests.compat.urljoin(base_url, level4_link)

    level4_soup = fetch_page(level4_link)
    article_links = []
    for a in level4_soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"_4\.htm[l]?$", href):
            if not href.startswith("http"):
                href = requests.compat.urljoin(level4_link, href)
            if href not in article_links:
                article_links.append(href)
        if len(article_links) >= count:
            break
    return article_links


def parse_article(url: str) -> Article:
    """Parse article details."""
    soup = fetch_page(url)
    title = soup.find("title").text.strip()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.select("p")]
    text = "\n".join(paragraphs)

    mp3_tag = soup.find("a", href=re.compile(r"\.mp3$"))
    mp3_url = mp3_tag["href"] if mp3_tag else ""
    if mp3_url and not mp3_url.startswith("http"):
        mp3_url = requests.compat.urljoin(url, mp3_url)

    discussion_header = soup.find(lambda tag: tag.name in ["h2", "h3"] and "discussion" in tag.text.lower())
    discussion = []
    if discussion_header:
        for elem in discussion_header.find_all_next():
            if elem.name in ["h2", "h3"]:
                break
            if elem.name in ["p", "li"]:
                discussion.append(elem.get_text(" ", strip=True))
    return Article(title=title, url=url, text=text, mp3_url=mp3_url, discussion=discussion)


def generate_content(article: Article, dry_run: bool = False) -> str:
    """Generate summary and questions using GPT-4o."""
    if dry_run or openai is None:
        summary = f"[DRY RUN] {article.title} özet."
        questions = [
            {
                "question": f"[DRY RUN] Question {i+1}",
                "options": ["A", "B", "C", "D"],
                "answer": "A",
            }
            for i in range(5)
        ]
    else:
        prompt = (
            "You are a helpful assistant. Read the following article and "
            "write a 200-250 word summary in Turkish. Then create 5 B2 level "
            "multiple choice vocabulary questions with answer key in JSON format."
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": article.text},
        ]
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
        )
        content = resp["choices"][0]["message"]["content"]
        summary, q_json = content.split("---", 1)
        questions = []
        try:
            questions = eval(q_json.strip())
        except Exception:
            pass
    md = [f"## {article.title}", "", summary.strip(), ""]
    md.append("### Vocabulary Questions")
    for i, q in enumerate(questions, 1):
        md.append(f"{i}. {q['question']}")
        for opt in q["options"]:
            md.append(f"   - {opt}")
        md.append("")
    md.append("Answer Key: " + ", ".join(q["answer"] for q in questions))
    md.append("")
    md.append("MP3: " + article.mp3_url)
    if article.discussion:
        md.append("### Discussion Questions")
        for d in article.discussion:
            md.append(f"- {d}")
    md.append("")
    return "\n".join(md)


def build_anki(articles: List[Article], deck_name: str) -> None:
    if genanki is None:
        raise RuntimeError("genanki not installed")
    deck = genanki.Deck(2059400110, deck_name)
    model = genanki.Model(
        1607392319,
        "BNE Model",
        fields=[{"name": "Question"}, {"name": "Answer"}, {"name": "Audio"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Question}}<br>{{Audio}}",
                "afmt": "{{FrontSide}}<hr id='answer'>{{Answer}}",
            }
        ],
    )
    for article in articles:
        note = genanki.Note(
            model=model,
            fields=[article.title, article.mp3_url, f"[sound:{article.mp3_url.split('/')[-1]}]"],
        )
        deck.add_note(note)
    genanki.Package(deck).write_to_file(f"{deck_name}.apkg")


def main() -> None:
    parser = argparse.ArgumentParser(description="BreakingNewsEnglish B2 bot")
    parser.add_argument("--dry-run", action="store_true", help="use dummy GPT")
    parser.add_argument("--run", action="store_true", help="call GPT API")
    parser.add_argument("--anki", action="store_true", help="generate Anki deck")
    args = parser.parse_args()

    dry_run = args.dry_run or not args.run
    base_url = "https://breakingnewsenglish.com/"
    if dry_run:
        articles = [
            Article(
                title=f"Example Article {i+1}",
                url="http://example.com",
                text="Example text",
                mp3_url="",
                discussion=[],
            )
            for i in range(3)
        ]
    else:
        links = get_level4_links(base_url)
        articles = [parse_article(url) for url in links]

    today = datetime.date.today().isoformat()
    md_filename = f"{today}_bne_b2.md"
    sections = [f"# Breaking News English B2 - {today}", ""]
    for article in articles:
        sections.append(generate_content(article, dry_run=dry_run))
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"Markdown saved to {md_filename}")

    if args.anki:
        build_anki(articles, f"bne_b2_{today}")
        print("Anki deck created")


if __name__ == "__main__":
    main()
