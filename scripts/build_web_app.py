import csv
import json
import os
from pathlib import Path

# Config
INPUT_CSV = Path("data/questions.csv")
OUTPUT_HTML = Path("output/web/index.html")

# Palette
PALETTE = {
    "A": {"bg": "#9DBC79", "text": "#ffffff", "accent": "#5d7542", "name": "Welt & Natur"}, 
    "B": {"bg": "#E5D9C4", "text": "#ffffff", "accent": "#8a7b62", "name": "Kultur & Menschen"}, 
    "C": {"bg": "#88C0E8", "text": "#ffffff", "accent": "#456f8f", "name": "Technik & Fortschritt"}, 
    "default": {"bg": "#94a3b8", "text": "#ffffff", "accent": "#0f172a", "name": "Allgemein"},
}

def load_data():
    questions = {}
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat_key = row["kategorie"][0].upper() if row["kategorie"] else "A"
            questions[row["id"]] = {
                "id": row["id"],
                "cat_key": cat_key,
                "category": row["kategorie"],
                "subcategory": row["subkategorie"],
                "question": row["frage"],
                "hint1": row["tipp1"],
                "hint2": row["tipp2"],
                "answer": row["loesung"]
            }
    return questions

def generate_html(data):
    json_data = json.dumps(data, ensure_ascii=False)
    
    # CSS Template
    css_template = """
        :root {
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --color-bg: #f1f5f9;
            --color-text: #1e293b;
            --color-text-dim: #94a3b8;
            
            /* Dynamic Colors */
            --col-a-bg: __COL_A_BG__;
            --col-a-accent: __COL_A_ACCENT__;
            --col-b-bg: __COL_B_BG__;
            --col-b-accent: __COL_B_ACCENT__;
            --col-c-bg: __COL_C_BG__;
            --col-c-accent: __COL_C_ACCENT__;
            --col-def-bg: __COL_DEF_BG__;
            
            --ease-out: cubic-bezier(0.215, 0.61, 0.355, 1);
            --ease-in: cubic-bezier(0.55, 0.055, 0.675, 0.19);
            --ease-elastic: cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; -webkit-user-select: none; }
        
        body {
            font-family: var(--font-main);
            background-color: var(--color-bg);
            color: var(--color-text);
            margin: 0;
            padding: 0;
            height: 100vh;
            overflow: hidden; /* Prevent scroll bouncing */
            display: flex;
            justify-content: center;
        }

        /* --- SEARCH VIEW --- */
        #view-search {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: white;
            z-index: 100;
            position: absolute;
            transition: opacity 0.3s;
        }
        
        .logo { font-size: 3rem; font-weight: 900; letter-spacing: -0.05em; margin-bottom: 40px; color: #0f172a; }
        .logo span { color: #cbd5e1; }
        
        .search-box {
            width: 100%; max-width: 320px;
            display: flex; flex-direction: column; gap: 16px;
        }
        
        .id-input {
            font-size: 2.5rem; text-align: center; font-weight: 700;
            border: 3px solid #e2e8f0; border-radius: 20px; padding: 20px;
            width: 100%; outline: none; color: #0f172a;
            transition: border-color 0.2s;
        }
        .id-input:focus { border-color: #0f172a; }
        
        .go-btn {
            background: #0f172a; color: white; border: none; padding: 20px;
            border-radius: 20px; font-size: 1.2rem; font-weight: 700;
            cursor: pointer; transition: transform 0.1s;
        }
        .go-btn:active { transform: scale(0.95); }

        /* --- GAME VIEW --- */
        #view-game {
            width: 100%;
            max-width: 500px;
            height: 100%;
            display: none;
            flex-direction: column;
            position: relative;
            background: var(--color-bg);
        }

        /* THEMING */
        .theme-a { --theme-color: var(--col-a-bg); --theme-dark: var(--col-a-accent); }
        .theme-b { --theme-color: var(--col-b-bg); --theme-dark: var(--col-b-accent); }
        .theme-c { --theme-color: var(--col-c-bg); --theme-dark: var(--col-c-accent); }
        .theme-def { --theme-color: var(--col-def-bg); --theme-dark: #334155; }

        /* HEADER */
        .game-header {
            padding: 30px 24px 20px;
            text-align: center;
            background: var(--color-bg);
            z-index: 10;
            flex-shrink: 0;
        }
        
        .cat-pill {
            display: inline-block;
            background: white;
            color: var(--theme-dark);
            padding: 6px 14px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 16px;
        }
        
        .question-text {
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.4;
            color: #334155;
        }

        /* STAGE (Flex Layout) */
        .stage {
            flex: 1;
            padding: 16px 24px 32px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow: hidden; /* No scrolling, fit to screen */
        }

        /* CARD COMPONENT */
        .game-card {
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            position: relative;
            overflow: hidden;
            transition: flex-grow 0.6s var(--ease-elastic), opacity 0.4s;
            
            /* Flex Layout Props */
            flex-grow: 1; /* Default: Share space equally */
            flex-basis: 0; /* Important for equal splitting */
            min-height: 60px; /* Minimum tappable area */
            
            display: flex;
            flex-direction: column;
        }

        /* STATES */
        /* Locked: Grayed out */
        .game-card.locked {
            opacity: 0.6;
            filter: grayscale(1);
            pointer-events: none;
            flex-grow: 1;
        }
        
        /* Active: Ready to interact */
        .game-card.active {
            opacity: 1;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
            border: 2px solid white;
            flex-grow: 1;
            cursor: pointer;
        }
        
        /* Revealed: Takes up dominant space */
        .game-card.revealed {
            flex-grow: 4; /* Takes 4x space of others */
            cursor: default;
            box-shadow: 0 10px 30px -5px rgba(0,0,0,0.12);
        }
        
        /* Collapsed (Done): Shrinks to minimal bar */
        .game-card.done {
            flex-grow: 0.0001; /* Effectively 0 but keeps transition smooth? */
            /* Better strategy: Keep it visible but small? 
               User asked for "1/3rd for clicking to hint 2".
               Actually, "100% solution" implies others disappear.
               Let's try:
               Start: 1:1:1
               Hint1 Open: 4:1:1 (Hint 1 big, others small)
               Hint2 Open: 0:4:1 (Hint 1 gone, Hint 2 big, Sol small)
               Sol Open:   0:0:1 (Sol full screen)
            */
            flex-grow: 0;
            min-height: 0;
            margin: 0;
            opacity: 0;
            padding: 0;
            border: none;
        }

        /* ACTION LAYER (Button Overlay) */
        .card-action {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%; /* Cover full card */
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 5;
            background: white;
            transition: opacity 0.4s;
        }
        
        /* Hide action layer when revealed to show content behind */
        .game-card.revealed .card-action {
            opacity: 0;
            pointer-events: none;
        }

        /* Fill Animation Background */
        .fill-bg {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 0%;
            background: var(--theme-color);
            opacity: 0.2;
            transition: height 0.1s linear; 
        }
        
        .game-card.pressing .fill-bg {
            height: 100%;
            transition: height 0.8s linear; 
            opacity: 0.3;
        }

        /* Labels inside Button */
        .action-content {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }

        .action-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #334155;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .action-sub {
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--color-text-dim);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            opacity: 0.6;
            transition: opacity 0.3s;
        }
        
        .game-card.pressing .action-sub { opacity: 1; color: var(--theme-dark); }
        .game-card.pressing .action-title { color: var(--theme-dark); }

        /* CONTENT LAYER */
        .card-content {
            flex: 1; /* Fill the card space */
            padding: 24px;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.5s 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            height: 100%;
            overflow-y: auto; /* Allow scroll if text huge */
        }
        
        .game-card.revealed .card-content {
            opacity: 1;
            transform: translateY(0);
        }

        .hint-text {
            font-size: 1.25rem;
            line-height: 1.6;
            color: #1e293b;
            font-weight: 500;
        }

        .sol-text {
            font-size: 4.5rem;
            font-weight: 900;
            color: var(--theme-dark);
            line-height: 1;
            letter-spacing: -0.03em;
            animation: popIn 0.5s var(--ease-elastic);
        }
        
        @keyframes popIn {
            0% { transform: scale(0.5); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }

        /* TOAST */
        #toast {
            position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%) translateY(20px);
            background: #1e293b; color: white; padding: 12px 24px; border-radius: 50px;
            font-size: 0.9rem; font-weight: 600; opacity: 0; transition: all 0.3s ease;
            pointer-events: none; z-index: 100;
        }
        #toast.visible { opacity: 1; transform: translateX(-50%) translateY(0); }

        /* NAV */
        .nav-btn {
            margin-top: auto;
            padding: 20px;
            background: none; border: none; color: #94a3b8;
            font-weight: 700; cursor: pointer;
        }

    """
    
    css = css_template.replace("__COL_A_BG__", PALETTE["A"]["bg"]) \
                      .replace("__COL_A_ACCENT__", PALETTE["A"]["accent"]) \
                      .replace("__COL_B_BG__", PALETTE["B"]["bg"]) \
                      .replace("__COL_B_ACCENT__", PALETTE["B"]["accent"]) \
                      .replace("__COL_C_BG__", PALETTE["C"]["bg"]) \
                      .replace("__COL_C_ACCENT__", PALETTE["C"]["accent"]) \
                      .replace("__COL_DEF_BG__", PALETTE["default"]["bg"])

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>QuizPoker</title>
    <style>{css}</style>
</head>
<body>

    <div id="toast">Hold to reveal</div>

    <!-- SEARCH -->
    <div id="view-search">
        <div class="logo">QUIZ<span>POKER</span></div>
        <div class="search-box">
            <input type="number" id="id-input" class="id-input" placeholder="#" inputmode="numeric">
            <button class="go-btn" onclick="search()">Start Round</button>
        </div>
    </div>

    <!-- GAME -->
    <div id="view-game">
        <div class="game-header">
            <span class="cat-pill" id="lbl-sub">Subcategory</span>
            <div class="question-text" id="lbl-q">Question?</div>
        </div>

        <div class="stage">
            
            <!-- HINT 1 -->
            <div class="game-card active" id="card-hint1">
                <div class="card-action" data-target="hint1">
                    <div class="fill-bg"></div>
                    <div class="action-content">
                        <span class="action-title">First Hint</span>
                        <span class="action-sub">Hold to Reveal</span>
                    </div>
                </div>
                <div class="card-content">
                    <div class="hint-text" id="txt-hint1">...</div>
                </div>
            </div>

            <!-- HINT 2 -->
            <div class="game-card locked" id="card-hint2">
                <div class="card-action" data-target="hint2">
                    <div class="fill-bg"></div>
                    <div class="action-content">
                        <span class="action-title">Second Hint</span>
                        <span class="action-sub">Hold to Reveal</span>
                    </div>
                </div>
                <div class="card-content">
                    <div class="hint-text" id="txt-hint2">...</div>
                </div>
            </div>

            <!-- SOLUTION -->
            <div class="game-card locked" id="card-sol">
                <div class="card-action" data-target="sol">
                    <div class="fill-bg"></div>
                    <div class="action-content">
                        <span class="action-title">Solution</span>
                        <span class="action-sub">Hold to Reveal</span>
                    </div>
                </div>
                <div class="card-content">
                    <div class="sol-text" id="txt-sol">000</div>
                </div>
            </div>

            <button class="nav-btn" onclick="showSearch()">New Card</button>
        </div>
    </div>

    <script>
        const DB = __JSON_DATA__;
        const HOLD_TIME = 800; // ms
        const toast = document.getElementById('toast');
        
        let timer = null;
        let startTs = 0;

        // --- INIT ---
        window.addEventListener('DOMContentLoaded', () => {{
            const id = new URLSearchParams(window.location.search).get('id');
            setupInteractions();
            if(id) loadCard(id);
        }});

        document.getElementById('id-input').addEventListener("keypress", (e) => {{
            if(e.key === "Enter") search();
        }});

        // --- CORE LOGIC ---
        function search() {{
            const val = document.getElementById('id-input').value.trim();
            if(val && DB[val]) {{
                history.pushState({{}}, '', '?id='+val);
                loadCard(val);
            }} else {{
                showToast("Card ID not found");
            }}
        }}

        function showSearch() {{
            document.getElementById('view-game').style.display = 'none';
            document.getElementById('view-search').style.display = 'flex';
            document.getElementById('id-input').value = '';
            document.getElementById('id-input').focus();
            history.pushState({{}}, '', window.location.pathname);
        }}

        function loadCard(id) {{
            const data = DB[id];
            if(!data) return showSearch();

            // Populate
            document.getElementById('lbl-sub').textContent = data.subcategory;
            document.getElementById('lbl-q').textContent = data.question;
            document.getElementById('txt-hint1').textContent = data.hint1;
            document.getElementById('txt-hint2').textContent = data.hint2;
            document.getElementById('txt-sol').textContent = data.answer;

            // Theme
            const view = document.getElementById('view-game');
            view.className = 'theme-' + data.cat_key.toLowerCase();
            view.style.display = 'flex';
            document.getElementById('view-search').style.display = 'none';

            // Reset Cards
            resetCard('hint1', true);
            resetCard('hint2', false);
            resetCard('sol', false);
        }}

        function resetCard(key, active) {{
            const el = document.getElementById('card-' + key);
            el.className = 'game-card'; // clear all states
            if(active) el.classList.add('active');
            else el.classList.add('locked');
        }}

        function reveal(target) {{
            const card = document.getElementById('card-' + target);
            card.classList.remove('active', 'pressing');
            card.classList.add('revealed');

            // Sequence Logic
            if(target === 'hint1') {{
                unlock('hint2');
            }} else if(target === 'hint2') {{
                dismiss('hint1');
                unlock('sol');
            }} else if(target === 'sol') {{
                dismiss('hint2');
            }}
        }}

        function unlock(target) {{
            const el = document.getElementById('card-' + target);
            el.classList.remove('locked');
            el.classList.add('active');
        }}

        function dismiss(target) {{
            const el = document.getElementById('card-' + target);
            el.classList.add('done');
        }}

        function showToast(msg) {{
            toast.textContent = msg || "Hold to reveal";
            toast.classList.add('visible');
            setTimeout(() => toast.classList.remove('visible'), 2000);
        }}

        // --- INPUT HANDLING ---
        function setupInteractions() {{
            document.querySelectorAll('.card-action').forEach(btn => {{
                const target = btn.dataset.target;
                const card = document.getElementById('card-' + target);

                const start = (e) => {{
                    if(e.type === 'mousedown' && e.button !== 0) return;
                    if(!card.classList.contains('active')) return;

                    startTs = Date.now();
                    card.classList.add('pressing');
                    
                    timer = setTimeout(() => {{
                        timer = null;
                        if(navigator.vibrate) navigator.vibrate(50);
                        reveal(target);
                    }}, HOLD_TIME);
                }};

                const end = (e) => {{
                    if(timer) {{
                        clearTimeout(timer);
                        timer = null;
                    }}
                    
                    if(card.classList.contains('pressing')) {{
                        card.classList.remove('pressing');
                        // Check short press
                        const dur = Date.now() - startTs;
                        if(dur > 50 && dur < HOLD_TIME) {{
                            showToast("Hold to Reveal");
                        }}
                    }}
                }};

                btn.addEventListener('mousedown', start);
                btn.addEventListener('touchstart', start, {{passive:true}});
                
                ['mouseup', 'mouseleave', 'touchend', 'touchcancel'].forEach(ev => {{
                    btn.addEventListener(ev, end);
                }});
                
                btn.addEventListener('contextmenu', e => e.preventDefault());
            }});
        }}

    </script>
</body>
</html>
    """
    
    html = html.replace("__JSON_DATA__", json_data)
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Built web app: {OUTPUT_HTML}")

if __name__ == "__main__":
    if not INPUT_CSV.exists(): exit(1)
    os.makedirs(OUTPUT_HTML.parent, exist_ok=True)
    generate_html(load_data())
