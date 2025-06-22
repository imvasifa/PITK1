from flask import Flask, render_template_string, jsonify, request
import json
import os

# Import the Flask app instances from app3 and app4
from app3 import app as app3_app
from app4 import app as app4_app

app = Flask(__name__)

HOME_HTML = """
<!doctype html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>App Dashboard</title>
    <style>
        body {
            background: #15171a;
            color: #e3e6eb;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            min-height: 100vh;
        }
        .dashboard-container {
            position: relative;
            z-index: 1;
            max-width: 900px;
            margin: 50px auto;
            padding: 32px 0;
        }
        .dashboard-title {
            text-align: left;
            font-size: 2.4em;
            font-weight: 700;
            margin-bottom: 36px;
            letter-spacing: -2px;
            color: #00ed64;
        }
        .app-grid {
            position: relative;
            z-index: 1;
            display: flex;
            gap: 32px;
            flex-wrap: wrap;
            justify-content: flex-start;
        }
        .app-card {
            position: relative;
            z-index: 1;
            background: #23272f;
            border-radius: 14px;
            box-shadow: 0 2px 18px rgba(0,0,0,0.18);
            padding: 32px 26px 24px 26px;
            min-width: 260px;
            flex: 1 1 260px;
            max-width: 300px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            margin-bottom: 24px;
            border: 1.5px solid #23272f;
            transition: border 0.2s;
            cursor: grab;
            user-select: none;
            -webkit-user-drag: element;
        }
        .app-card.dragElem {
            opacity: 0.6;
        }
        
        .app-card:hover {
            border: 1.5px solid #00ed64;
        }
        .app-title {
            font-size: 1.4em;
            font-weight: 600;
            margin-bottom: 8px;
            color: #fff;
        }
        .app-desc {
            font-size: 1.01em;
            color: #b9bdc7;
            margin-bottom: 20px;
        }
        .launch-btn {
            background: linear-gradient(90deg, #00ed64 0%, #00b86b 100%);
            color: #15171a;
            font-weight: 700;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1.1em;
            margin-top: auto;
            transition: background 0.18s;
            box-shadow: 0 2px 8px rgba(0,237,100,0.09);
            display: inline-block;
        }
        .launch-btn:hover {
            background: linear-gradient(90deg, #00b86b 0%, #00ed64 100%);
            color: #15171a;
        }
        .footer {
            text-align: center;
            color: #555a66;
            font-size: 1em;
            margin-top: 38px;
            letter-spacing: 0.5px;
        }
        @media (max-width: 900px) {
            .app-grid { flex-direction: column; gap: 0; }
            .app-card { max-width: 100%; }
        }
        /* Railway dot grid background */
        .dot-grid {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            pointer-events: none;
            z-index: 0;
        }
        .dot-grid:before {
            content: '';
            display: block;
            width: 100vw; height: 100vh;
            background:
                radial-gradient(circle, #2a2d34 1.5px, transparent 1.5px) 0 0,
                radial-gradient(circle, #2a2d34 1.5px, transparent 1.5px) 20px 20px;
            background-size: 40px 40px;
            opacity: 0.5;
            animation: dotmove 6s linear infinite;
        }
        @keyframes dotmove {
            from { background-position: 0 0, 20px 20px; }
            to { background-position: 40px 40px, 60px 60px; }
        }
    </style>
</head>
<body>
    <!-- Railway-style animated dot grid background -->
    <div class="dot-grid"></div>
    <div class='dashboard-container'>
        <div class='dashboard-title'>App Dashboard</div>
        <div class='app-grid'>
            {% for card in cards %}
            <div class='app-card' draggable="true">
                <div class='app-title'>{{ card.title }}</div>
                <div class='app-desc'>{{ card.desc | replace('\n', '<br>') | safe }}</div>
                <a class='launch-btn' href='{{ card.url }}' target='_blank'>Open {{ card.title }}</a>
            </div>
{% endfor %}
        </div>
        <div class='footer'>Inspired by Railway/MongoDB UI &mdash; All apps must be running to open them.</div>
    </div>
<script>
// Fully robust drag-and-drop for flexbox
let dragSrcEl = null;
function handleDragStart(e) {
    dragSrcEl = this;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', ''); // Required for Firefox
    this.classList.add('dragElem');
}
function handleDragOver(e) {
    if (e.preventDefault) e.preventDefault();
    this.classList.add('over');
    e.dataTransfer.dropEffect = 'move';
    return false;
}
function handleDragEnter(e) {
    this.classList.add('over');
}
function handleDragLeave(e) {
    this.classList.remove('over');
}
function handleDrop(e) {
    if (e.stopPropagation) e.stopPropagation();
    if (dragSrcEl && dragSrcEl !== this) {
        // Insert before or after depending on mouse position
        let rect = this.getBoundingClientRect();
        let midY = rect.top + rect.height / 2;
        if (e.clientY > midY) {
            this.parentNode.insertBefore(dragSrcEl, this.nextSibling);
        } else {
            this.parentNode.insertBefore(dragSrcEl, this);
        }
        saveOrder();
    }
    this.classList.remove('over');
    return false;
}
function handleDragEnd(e) {
    let cards = document.querySelectorAll('.app-card');
    cards.forEach(card => card.classList.remove('over', 'dragElem'));
}
function addDnDHandlers(elem) {
    elem.addEventListener('dragstart', handleDragStart, false);
    elem.addEventListener('dragenter', handleDragEnter, false);
    elem.addEventListener('dragover', handleDragOver, false);
    elem.addEventListener('dragleave', handleDragLeave, false);
    elem.addEventListener('drop', handleDrop, false);
    elem.addEventListener('dragend', handleDragEnd, false);
}
function saveOrder() {
    let cards = document.querySelectorAll('.app-card');
    let newOrder = [];
    cards.forEach(card => {
        newOrder.push({
            title: card.querySelector('.app-title').innerText,
            desc: card.querySelector('.app-desc').innerHTML.replace(/<br>/g, '\n'),
            url: card.querySelector('.launch-btn').href
        });
    });
    fetch('/cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newOrder)
    });
}
document.addEventListener('DOMContentLoaded', function() {
    let cards = document.querySelectorAll('.app-card');
    cards.forEach(addDnDHandlers);
});
</script>
</body>
</html>
"""

CARDS_FILE = os.path.join(os.path.dirname(__file__), 'cards.json')

# Mount the apps at their respective endpoints
app.mount('/app3', app3_app)
app.mount('/app4', app4_app)

def load_cards():
    try:
        with open(CARDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_cards(cards):
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)

@app.route("/")
def home():
    cards = load_cards()
    return render_template_string(HOME_HTML, cards=cards)

@app.route("/cards", methods=["GET", "POST"])
def cards_api():
    if request.method == "POST":
        cards = request.get_json(force=True)
        save_cards(cards)
        return jsonify({"status": "ok"})
    else:
        return jsonify(load_cards())

if __name__ == "__main__":
    app.run(port=5000, debug=True)
