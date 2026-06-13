#!/usr/bin/env python3
"""Fetch Kaggle competition discussion threads and save as Markdown files.

Usage:
    uv run python fetch_discussions.py <competition-slug> [--output-dir <dir>]

Example:
    uv run python fetch_discussions.py informs-ras-2026-problem-solving-competition
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kaggle_client import KaggleClient
from kagglesdk.competitions.types.competition_api_service import (
    ApiListCompetitionTopicsRequest,
    ApiListTopicMessagesRequest,
)
from kagglesdk.discussions.types.discussions_enums import (
    TopicListSortBy,
    CommentListSortBy,
)


OFFICIAL_SIGNATURES = [
    "INFORMS RAS",
    "Organizing Team",
]

OFFICIAL_PHRASES = [
    "thank you for the question",
    "thank you for pointing this out",
    "thank you for your patience",
    "thank you for your careful testing",
    "thank you for raising this issue",
    "thank you for catching this issue",
    "thank you for the feedback",
    "we have updated",
    "we have fixed",
    "we have made",
    "we are preparing",
    "we will contact",
    "we will post",
    "we noticed this issue",
    "the updated scorer",
    "the updated version",
    "the new solution",
    "the leaderboard has been reset",
    "please download and use",
    "please use the official",
    "please follow the validator",
    "for this competition",
    "the current validator",
    "the scoring formula",
    "the kaggle backend",
    "this update does not change",
    "this logic is consistent",
    "you may now submit",
    "for scoring, please follow",
    "participants are kindly reminded",
    "the current scoring",
    "the problem statement",
    "the official validation",
    "the backend metric",
]


def extract_mentions(text: str) -> list[str]:
    """Extract @username patterns and Kaggle profile links from text."""
    usernames: set[str] = set()
    stopwords = {"gmail", "com", "http", "https", "yahoo", "outlook", "example"}
    for m in re.findall(r'(?<!\w)@(\w{3,30})(?!\w)', text):
        if m.lower() not in stopwords:
            usernames.add(m)
    ignore_paths = {
        "competitions", "datasets", "kernels", "models", "discussion",
        "account", "static", "images", "www", "api", "code", "learn",
        "benchmarks", "game-arena", "c", "d", "k", "m",
    }
    for m in re.findall(r'kaggle\.com/([a-zA-Z][\w.-]{2,30})(?:/|"|\s|>|\?)', text):
        if m.lower() not in ignore_paths:
            usernames.add(m)
    return list(usernames)


def detect_official(text: str) -> bool:
    """Check if a message appears to be from competition organizers."""
    text_lower = text.lower()
    for sig in OFFICIAL_SIGNATURES:
        if sig.lower() in text_lower:
            return True
    matches = sum(1 for p in OFFICIAL_PHRASES if p.lower() in text_lower)
    return matches >= 2


def get_topic_author(messages: list, raw_topic_author: str = "") -> str:
    """Infer the topic author from content analysis."""
    if raw_topic_author and raw_topic_author.strip():
        return raw_topic_author

    all_text = ""
    first_msg_text = ""
    for msg in messages:
        md = (msg.raw_markdown or "") + " " + (msg.content or "")
        if not first_msg_text:
            first_msg_text = md
        all_text += md + " "
        for reply in msg.replies or []:
            all_text += (reply.raw_markdown or "") + " " + (reply.content or "") + " "

    if detect_official(first_msg_text):
        return "Organizer"

    if len(messages) > 1:
        msg2 = messages[1]
        md2 = (msg2.raw_markdown or "") + (msg2.content or "")
        addressed = extract_mentions(md2)
        non_official = [a for a in addressed if a not in ("peiranhan",)]
        if non_official and not detect_official(first_msg_text):
            return non_official[0]

    for msg in messages:
        for reply in msg.replies or []:
            rd = (reply.raw_markdown or "") + (reply.content or "")
            addressed = extract_mentions(rd)
            for a in addressed:
                if a not in ("peiranhan",):
                    return a

    all_mentions = extract_mentions(all_text)
    for a in all_mentions:
        if a not in ("peiranhan",):
            return a

    return "Unknown"


def get_msg_author(msg, topic_author: str, msg_index: int, is_first: bool) -> str:
    """Infer the author of a specific message."""
    if msg.author_name and msg.author_name.strip():
        return msg.author_name

    md = (msg.raw_markdown or "") + (msg.content or "")
    if detect_official(md):
        return "Organizer"
    if is_first:
        return topic_author

    mentions_in_msg = extract_mentions(md)
    if mentions_in_msg and msg_index <= 1:
        for mention in mentions_in_msg:
            if mention == topic_author:
                return "Organizer"
    return topic_author


def render_message(msg, depth: int = 0, author: str = "Unknown") -> list[str]:
    """Render a message tree into markdown lines."""
    lines: list[str] = []
    content = msg.raw_markdown or msg.content or ""
    if not content.strip():
        content = "*[deleted or empty]*"

    date_str = msg.post_date.strftime("%Y-%m-%d %H:%M") if msg.post_date else ""

    if depth == 0:
        lines.append(f"**Author:** {author}")
        lines.append(f"**Date:** {date_str}")
        lines.append(f"**Votes:** {msg.votes}")
        if hasattr(msg, "is_pinned") and msg.is_pinned:
            lines.append("**Pinned**")
        lines.append("")
        lines.append(content)
        lines.append("")
    else:
        lines.append(f"> **{author}** ({date_str}) — {msg.votes} votes")
        lines.append(">")
        for line in content.split("\n"):
            lines.append(f"> {line}")
        lines.append("")

    for reply in msg.replies or []:
        md_r = (reply.raw_markdown or "") + (reply.content or "")
        reply_author = "Unknown"
        if detect_official(md_r):
            reply_author = "Organizer"
        lines.extend(render_message(reply, depth + 1, reply_author))
    return lines


def sanitize_filename(title: str, max_len: int = 80) -> str:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
    safe = "_".join(safe.split())[:max_len]
    return safe or "topic"


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Kaggle competition discussion threads as Markdown"
    )
    parser.add_argument("competition", help="Competition slug (e.g. informs-ras-2026-problem-solving-competition)")
    parser.add_argument("--output-dir", default="discussions", help="Output directory (default: discussions/)")
    args = parser.parse_args()

    api = KaggleApi()
    api.authenticate()
    client: KaggleClient = api.build_kaggle_client()
    topics_client = client.competitions.competition_api_client

    print(f"Fetching topics for '{args.competition}'...")
    page = 1
    all_topics = []

    while True:
        req = ApiListCompetitionTopicsRequest()
        req.competition_name = args.competition
        req.sort_by = TopicListSortBy.TOPIC_LIST_SORT_BY_RECENT
        req.page = page
        resp = topics_client.list_competition_topics(req)

        new_topics = list(resp.topics or [])
        if not new_topics:
            break
        all_topics.extend(new_topics)
        if len(all_topics) >= (resp.total_count or len(all_topics)):
            break
        page += 1

    print(f"Total topics: {len(all_topics)}")
    if not all_topics:
        print("No topics found. Check the competition slug and API credentials.")
        return

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    topic_data: dict = {}
    for topic in all_topics:
        tid = topic.id
        try:
            req = ApiListTopicMessagesRequest()
            req.competition_name = args.competition
            req.topic_id = tid
            req.sort_by = CommentListSortBy.COMMENT_LIST_SORT_BY_OLD
            req.page_size = -1
            resp = topics_client.list_topic_messages(req)
            messages = list(resp.messages or [])
            author = get_topic_author(messages, topic.author_name)
            topic_data[tid] = {"topic": topic, "messages": messages, "author": author}
        except Exception as e:
            print(f"  ERROR topic {tid}: {e}")
            topic_data[tid] = {"topic": topic, "messages": [], "author": "Unknown"}

    index_lines = [
        f"# {args.competition} — Discussion Threads",
        "",
        f"*Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        f"Total topics: {len(all_topics)}",
        "",
        "| # | Title | Author | Comments | Votes | Date |",
        "|---|-------|--------|----------|-------|------|",
    ]

    for i, topic in enumerate(all_topics):
        title = topic.title or f"Topic {topic.id}"
        author = topic_data[topic.id]["author"]
        comments = topic.comment_count
        votes = topic.votes
        date_str = topic.last_comment_post_date.strftime("%Y-%m-%d") if topic.last_comment_post_date else "?"
        fn = f"{sanitize_filename(title)}_{topic.id}.md"
        index_lines.append(f"| {i + 1} | [{title}]({fn}) | {author} | {comments} | {votes} | {date_str} |")

    with open(output_path / "README.md", "w") as f:
        f.write("\n".join(index_lines) + "\n")

    for i, topic in enumerate(all_topics):
        tid = topic.id
        td = topic_data[tid]
        title = topic.title or f"Topic {tid}"
        messages = td["messages"]
        topic_author = td["author"]
        topic_url = f"https://www.kaggle.com/competitions/{args.competition}/discussion/{tid}"

        print(f"[{i + 1}/{len(all_topics)}] {title[:80]}")

        md_lines = [
            f"# {title}",
            "",
            f"**Topic URL:** {topic_url}",
            f"**Author:** {topic_author}",
            f"**Posted:** {topic.post_date.strftime('%Y-%m-%d %H:%M') if topic.post_date else 'Unknown'}",
            f"**Comments:** {topic.comment_count}",
            f"**Votes:** {topic.votes}",
            f"**Sticky:** {topic.is_sticky}",
            "",
            "---",
            "",
        ]

        for mi, msg in enumerate(messages):
            author = get_msg_author(msg, topic_author, mi, mi == 0)
            md_lines.extend(render_message(msg, depth=0, author=author))
            md_lines.append("---")
            md_lines.append("")

        fn = f"{sanitize_filename(title)}_{tid}.md"
        with open(output_path / fn, "w") as f:
            f.write("\n".join(md_lines))
        print(f"  -> {len(messages)} messages to {fn}")

    print(f"\nSaved {len(all_topics)} topics to {output_path}/")


if __name__ == "__main__":
    main()
