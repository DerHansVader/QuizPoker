#!/usr/bin/env python3
"""
QuizPoker Hint Generator - Creates perfect hints for estimation questions.
Uses GPT-5.1 with high reasoning effort to brainstorm and select the best hints.

Usage:
    python scripts/polish_questions_web.py --input data/questions.csv --output data/questions.csv --start 1 --end 10
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load .env if present
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI")
if not API_KEY:
    sys.exit("Error: Set OPENAI_API_KEY or OPENAI in environment or .env")

MODEL = "gpt-5.1"
CONCURRENCY = 25

# ============================================================================
# THE PROMPT - This is where the magic happens
# ============================================================================

SYSTEM_PROMPT = """
Du bist ein erfahrener Spieleautor und erstellst perfekte Hinweise für das Schätzspiel "QuizPoker".

═══════════════════════════════════════════════════════════════════════════════
WAS IST QUIZPOKER?
═══════════════════════════════════════════════════════════════════════════════

Spieler bekommen eine Schätzfrage und schreiben GEHEIM ihre Schätzung auf.
Dann wird gesetzt (wie Poker). Dann kommt TIPP 1. Wieder setzen. Dann TIPP 2. 
Wieder setzen. Auflösung: Wer am nächsten dran ist gewinnt.

DAS ZIEL DER TIPPS:
Nach jedem Tipp sollen Spieler denken: "Ah interessant! Damit kann ich meine 
Schätzung überdenken." Die Tipps müssen NEUES WISSEN liefern das beim Schätzen 
hilft - nicht Dinge die jeder weiß oder die nichts zur Schätzung beitragen.

═══════════════════════════════════════════════════════════════════════════════
WAS MACHT EINEN TIPP WERTVOLL?
═══════════════════════════════════════════════════════════════════════════════

Ein guter Tipp ist ein ANKER - ein Fakt der die Schätzung in eine Richtung lenkt:
• Ein Vergleichswert (andere Zahl aus dem Kontext)
• Eine Relation (größer/kleiner als X)  
• Ein Rechenbaustein (Teilinfo mit der man rechnen könnte)
• Eine zeitliche Einordnung (war X im Jahr Y)

═══════════════════════════════════════════════════════════════════════════════
KONKRETE BEISPIELE: SCHLECHT vs GUT
═══════════════════════════════════════════════════════════════════════════════

FRAGE: Wie hoch ist der Mount Everest?
❌ SCHLECHT: "Er ist der höchste Berg der Erde" 
   → Weiß jeder. Hilft NULL beim Schätzen.
❌ SCHLECHT: "Er liegt im Himalaya an der Grenze Nepal/Tibet"
   → Geografie-Fakt. Hilft NULL beim Schätzen der HÖHE.
❌ SCHLECHT: "Unit: Meter"
   → Offensichtlich. Hilft NULL.
✅ GUT: "Der K2 ist mit 8611m der zweithöchste Berg"
   → ANKER! Jetzt weiß man: Everest ist ETWAS höher als 8611m.
✅ GUT: "Flugzeuge fliegen auf Reiseflughöhe bei etwa 10-12 km"
   → ANKER! Jetzt kann man einordnen wo der Everest im Vergleich liegt.

FRAGE: Wie viele Stufen hat der Empire State Building Treppenlauf?
❌ SCHLECHT: "Der Lauf endet an der Aussichtsplattform"
   → Hilft NULL beim Schätzen der Stufenzahl.
❌ SCHLECHT: "1945 stürzte ein Bomber ins Gebäude"
   → Fun Fact aber hilft NULL beim Schätzen.
❌ SCHLECHT: "Das Gebäude hat 102 Stockwerke und ein Stockwerk hat 15-20 Stufen"
   → ZU DIREKT! Man kann sofort 102*17=1734 rechnen.
✅ GUT: "Das Gebäude hat 102 Stockwerke"
   → Gibt eine Dimension ohne direkte Lösung.
✅ GUT: "Der Rekord liegt bei unter 10 Minuten"
   → Interessant! Man denkt: Wie viele Stufen schafft man pro Minute?

FRAGE: Wie viele erfolgreiche Everest-Besteigungen bis 2023?
❌ SCHLECHT: "Gezählt werden Gipfelereignisse nicht Personen"
   → Methodischer Fakt. Hilft NULL beim Schätzen.
❌ SCHLECHT: "Seit den 1990ern gibt es viele Besteigungen"
   → Vage. Hilft NULL.
✅ GUT: "Bis 2010 waren es etwa 5100 Besteigungen"
   → PERFEKTER ANKER! Man kann hochrechnen.
✅ GUT: "2023 allein gab es über 600 erfolgreiche Besteigungen"
   → ANKER! Man kann überlegen wie viele Jahre es schon geht.

FRAGE: Wie hoch ist der Burj Khalifa?
❌ SCHLECHT: "Eröffnung 2010; Bau begann 2004"
   → Hilft NULL beim Schätzen der Höhe.
❌ SCHLECHT: "Steht in Dubai; ist der höchste Turm der Welt"
   → Weiß jeder. Hilft NULL.
✅ GUT: "Der Eiffelturm ist 330m hoch und deutlich kleiner"
   → ANKER mit Vergleich!
✅ GUT: "Das zweithöchste Gebäude (Merdeka 118) ist 679m hoch"
   → PERFEKTER ANKER! Burj muss höher sein.

FRAGE: Wie viele Achttausender gibt es?
❌ SCHLECHT: "Alle liegen im Himalaya oder Karakorum"
   → Geografie. Hilft NULL beim Schätzen der ANZAHL.
❌ SCHLECHT: "Es geht um die anerkannten Achttausender"
   → Definiert nur den Begriff. Hilft NULL.
✅ GUT: "Der erste wurde 1950 bestiegen (Annapurna)"
   → Gibt zeitlichen Kontext.
✅ GUT: "Reinhold Messner hat alle bestiegen - das dauerte 16 Jahre"
   → Interessant! Impliziert: Es sind nicht SO viele dass es Jahrzehnte dauert.

═══════════════════════════════════════════════════════════════════════════════
STRENGE REGELN - NIEMALS MACHEN
═══════════════════════════════════════════════════════════════════════════════

VERBOTEN - Diese Phrasen/Konzepte sind WERTLOS:
• "Unit: ..." oder "Einheit: ..." (offensichtlich)
• "liegt zwischen X und Y" (zu direkt)
• "ist dreistellig/vierstellig" (zu technisch)  
• "höchster/größter/längster der Welt" (weiß jeder bei bekannten Dingen)
• "liegt in [Land/Region]" OHNE Bezug zur gesuchten Zahl
• "wurde gegründet/eröffnet in Jahr X" OHNE Bezug zur gesuchten Zahl
• "Quelle ist..." oder "laut Messung..." (administrativ)
• Reine Fun Facts ohne Schätz-Relevanz

KRITISCH - NIEMALS ZAHLEN NENNEN DIE ZU NAH AN DER ANTWORT SIND:
• NIEMALS "knapp unter X" oder "knapp über X" wenn X nah an der Antwort ist
• NIEMALS "etwa X Stufen/Meter" wenn X die Antwort praktisch verrät
• Beispiel: Antwort ist 1576 → NIEMALS "1860 Stufen" oder "1500 Stufen" sagen!
• Beispiel: Antwort ist 2962 → NIEMALS "knapp unter 3000" sagen!
• Der Tipp soll HELFEN zu schätzen aber NICHT die Antwort verraten!

═══════════════════════════════════════════════════════════════════════════════
DEINE AUFGABE
═══════════════════════════════════════════════════════════════════════════════

1. VERSTEHE die Frage und was geschätzt werden soll
2. RECHERCHIERE (nutze web_search!) nach interessanten Ankerfakten
3. BRAINSTORME mindestens 6 mögliche Hinweise
4. BEWERTE jeden: Hilft er WIRKLICH beim Schätzen? Ist er zu direkt? Zu vage?
5. WÄHLE die 2 besten:
   - Tipp 1: Etwas breiter; öffnet den Denkraum
   - Tipp 2: Konkreter Anker; grenzt stärker ein (aber nicht lösbar!)

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Antworte NUR mit diesem JSON (keine Erklärung davor/danach):
{
  "brainstorm": ["Idee 1", "Idee 2", "Idee 3", "Idee 4", "Idee 5", "Idee 6"],
  "tipp1": "Gewählter Tipp 1 (kurz; max 15 Wörter)",
  "tipp2": "Gewählter Tipp 2 (kurz; max 15 Wörter)"
}

WICHTIG: Keine Kommas in den Tipps verwenden! Nutze Semikolons oder Bindestriche.
"""

# ============================================================================
# QUALITY GATES - Reject bad hints automatically
# ============================================================================

BAD_PATTERNS = [
    r"(?i)\bunit[:\s]",
    r"(?i)\beinheit[:\s]",
    r"(?i)liegt zwischen",
    r"(?i)between \d+ and \d+",
    r"(?i)(drei|vier|fünf|sechs|sieben|acht)stellig",
    r"(?i)\b(höchste|größte|längste|tiefste)[rns]?\b.{0,20}\b(der|die|das) welt",
    r"(?i)quelle ist",
    r"(?i)laut messung",
    r"(?i)wird in (metern?|kilometern?|prozent) (angegeben|gemessen)",
    r"(?i)knapp (unter|über|ueber)",
    r"(?i)nur knapp",
    r"(?i)fast genau",
    r"(?i)ungefähr \d+",
]

def extract_numbers(text: str) -> list:
    """Extract all numbers from text."""
    # Match integers and decimals, handle German decimal comma
    matches = re.findall(r'\b\d+(?:[.,]\d+)?\b', text)
    numbers = []
    for m in matches:
        try:
            numbers.append(float(m.replace(',', '.')))
        except ValueError:
            pass
    return numbers

def hint_is_too_close(hint: str, answer: str) -> bool:
    """Check if hint contains a number within ±25% of the answer."""
    try:
        # Parse answer (handle German decimals and remove non-numeric suffixes)
        ans_clean = re.sub(r'[^\d.,]', '', answer.split()[0] if answer else "0")
        ans_val = float(ans_clean.replace(',', '.')) if ans_clean else 0
        if ans_val == 0:
            return False
        
        hint_numbers = extract_numbers(hint)
        for num in hint_numbers:
            if num == 0:
                continue
            # Check if within ±25% of answer
            ratio = num / ans_val if ans_val != 0 else 0
            if 0.75 <= ratio <= 1.25:
                return True
    except (ValueError, ZeroDivisionError):
        pass
    return False

def hint_is_bad(hint: str, answer: str = "") -> bool:
    for pattern in BAD_PATTERNS:
        if re.search(pattern, hint):
            return True
    if answer and hint_is_too_close(hint, answer):
        return True
    return False


# ============================================================================
# API CALL WITH REASONING
# ============================================================================

async def generate_hints(client, question: str, answer: str, semaphore) -> dict:
    async with semaphore:
        user_prompt = f"""FRAGE: {question}
KORREKTE ANTWORT: {answer}

Recherchiere interessante Fakten und erstelle perfekte QuizPoker-Hinweise.
WICHTIG: Nenne KEINE Zahl die nah an {answer} liegt (±25%)! Das würde die Antwort verraten.
Gib Vergleichswerte die WEITER WEG sind aber trotzdem beim Einordnen helfen."""

        for attempt in range(3):
            try:
                response = await client.responses.create(
                    model=MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=user_prompt,
                    tools=[{"type": "web_search"}],
                    reasoning={"effort": "medium"},
                )
                
                # Extract text from response
                text = ""
                for item in response.output:
                    if hasattr(item, "content"):
                        for block in item.content:
                            if hasattr(block, "text"):
                                text += block.text
                
                # Find JSON in response
                json_match = re.search(r'\{[^{}]*"tipp1"[^{}]*"tipp2"[^{}]*\}', text, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                
                if json_match:
                    data = json.loads(json_match.group())
                    tipp1 = data.get("tipp1", "").replace(",", ";").strip()
                    tipp2 = data.get("tipp2", "").replace(",", ";").strip()
                    
                    # Remove markdown links/sources like ([url](link))
                    tipp1 = re.sub(r'\s*\([^\)]*\[[^\]]*\]\([^\)]*\)[^\)]*\)', '', tipp1).strip()
                    tipp2 = re.sub(r'\s*\([^\)]*\[[^\]]*\]\([^\)]*\)[^\)]*\)', '', tipp2).strip()
                    # Also remove standalone [text](url) patterns
                    tipp1 = re.sub(r'\s*\[[^\]]*\]\([^\)]*\)', '', tipp1).strip()
                    tipp2 = re.sub(r'\s*\[[^\]]*\]\([^\)]*\)', '', tipp2).strip()
                    
                    # Quality check
                    if hint_is_bad(tipp1, answer) or hint_is_bad(tipp2, answer):
                        print(f"  [Retry {attempt+1}] Bad pattern or too-close number detected")
                        continue
                    
                    if len(tipp1) < 10 or len(tipp2) < 10:
                        print(f"  [Retry {attempt+1}] Hints too short")
                        continue
                    
                    return {"tipp1": tipp1, "tipp2": tipp2}
                
            except Exception as e:
                print(f"  [Error] {e}")
        
        return {"tipp1": "", "tipp2": ""}


# ============================================================================
# MAIN PROCESSING - BATCHED WITH PROGRESS
# ============================================================================

BATCH_SIZE = 50

async def process_batch(rows: list, concurrency: int, client) -> list:
    semaphore = asyncio.Semaphore(concurrency)
    
    async def process_one(row: dict) -> dict:
        q = row.get("frage", "")
        a = row.get("loesung", "")
        if not q:
            return row
        
        result = await generate_hints(client, q, a, semaphore)
        
        if result["tipp1"]:
            row["tipp1"] = result["tipp1"]
        if result["tipp2"]:
            row["tipp2"] = result["tipp2"]
        
        return row
    
    tasks = [process_one(r) for r in rows]
    return await asyncio.gather(*tasks)


def save_csv(all_rows: list, fieldnames: list, output_path: str):
    """Save all rows to CSV."""
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """Simple progress bar."""
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.1f}%)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    # Read CSV
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = Path(args.input).parent / f"questions.backup-{timestamp}.csv"
    save_csv(all_rows, fieldnames, str(backup_path))
    print(f"Backup: {backup_path}")

    # Filter rows to process
    end_id = args.end or 999999
    target_ids = set(
        int(r.get("id", 0)) for r in all_rows 
        if args.start <= int(r.get("id", 0)) <= end_id
    )
    
    print(f"Processing {len(target_ids)} rows (IDs {args.start}..{args.end or 'end'})")
    print(f"Batch size: {args.batch_size} | Concurrency: {args.concurrency}")
    print()

    # Create async client
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=API_KEY)

    # Process in batches
    target_rows = [r for r in all_rows if int(r.get("id", 0)) in target_ids]
    total_batches = (len(target_rows) + args.batch_size - 1) // args.batch_size
    processed_count = 0

    for batch_idx in range(total_batches):
        batch_start = batch_idx * args.batch_size
        batch_end = min(batch_start + args.batch_size, len(target_rows))
        batch = target_rows[batch_start:batch_end]
        
        batch_ids = [r.get("id") for r in batch]
        print(f"\n{'='*60}")
        print(f"Batch {batch_idx + 1}/{total_batches} | IDs {batch_ids[0]}..{batch_ids[-1]}")
        print(f"{'='*60}")
        
        # Process batch
        updated_batch = asyncio.run(process_batch(batch, args.concurrency, client))
        
        # Update all_rows with processed batch
        id_to_updated = {r.get("id"): r for r in updated_batch}
        for i, row in enumerate(all_rows):
            if row.get("id") in id_to_updated:
                all_rows[i] = id_to_updated[row.get("id")]
        
        # Save after each batch
        save_csv(all_rows, fieldnames, args.output)
        
        processed_count += len(batch)
        print(f"\n{progress_bar(processed_count, len(target_rows))}")
        print(f"Saved to {args.output}")

    print(f"\n{'='*60}")
    print(f"DONE! Processed {processed_count} questions.")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
