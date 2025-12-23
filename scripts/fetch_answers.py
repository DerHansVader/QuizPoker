#!/usr/bin/env python3
"""
Fetch answers for quiz questions using OpenAI API.
Runs 25 requests concurrently for speed.

Usage:
    python scripts/fetch_answers.py --input data/questions.csv --output data/questions.csv
"""

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

MODEL = "gpt-4o"
CONCURRENCY = 25


async def fetch_answer(client, question: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        try:
            prompt = f"""Du bist ein Quizmaster. Beantworte die folgende Schaetzfrage mit einer EINZIGEN ZAHL oder einem KURZEN FAKTUM.
Gib NUR die Antwort - keine Erklaerung - keine Einheit wiederholen wenn schon in der Frage.

Frage: {question}

Antwort:"""

            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return ""


async def process_questions(rows: list, client) -> list:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    
    async def process_row(row: dict) -> dict:
        if row.get("loesung", "").strip():
            print(f"[{row['id']}] Skip")
            return row
        
        question = row.get("frage", "")
        if not question:
            return row
        
        print(f"[{row['id']}] {question[:50]}...")
        answer = await fetch_answer(client, question, semaphore)
        row["loesung"] = answer
        print(f"[{row['id']}] -> {answer}")
        return row
    
    tasks = [process_row(row) for row in rows]
    return await asyncio.gather(*tasks)


def main():
    print("Starting...")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from openai import OpenAI
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY env var")
    client = OpenAI()

    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} questions")

    updated_rows = asyncio.run(process_questions(rows, client))

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    answered = sum(1 for r in updated_rows if r.get("loesung", "").strip())
    print(f"Done! {answered}/{len(updated_rows)} answered")


if __name__ == "__main__":
    main()

