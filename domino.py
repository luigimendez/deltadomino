import streamlit as st
import pdfplumber
from docx import Document
import random

# ===============================
# FILES
# ===============================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ===============================
# SAFE LOADERS (UTF-8 PROTECTED)
# ===============================

def normalize_latex(text):
    text = text.strip()
    if text.startswith("$"):
        return text
    return f"$${text}$$"


def load_tiles_from_pdf(path):
    tiles = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                text = page.extract_text()
            except Exception:
                continue
            if not text:
                continue
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i in range(0, len(lines) - 1, 2):
                tiles.append({
                    "id": len(tiles),
                    "a": normalize_latex(lines[i]),
                    "b": normalize_latex(lines[i + 1]),
                    "orientation": "horizontal"
                })
    return tiles


def load_rules_from_docx(path):
    doc = Document(path)
    rules = []
    for p in doc.paragraphs:
        try:
            t = p.text.strip()
            if t:
                rules.append(t)
        except Exception:
            pass
    return rules

# ===============================
# DOMINO RENDER
# ===============================

def render_domino(tile):
    if tile["orientation"] == "horizontal":
        html = f"""
        <div style="display:flex;width:300px;height:130px;
        border:2px solid black;border-radius:14px;background:white;
        margin:10px;overflow:hidden;">
            <div style="width:50%;border-right:2px solid black;
            display:flex;align-items:center;justify-content:center;">
                {tile['a']}
            </div>
            <div style="width:50%;
            display:flex;align-items:center;justify-content:center;">
                {tile['b']}
            </div>
        </div>
        """
    else:
        html = f"""
        <div style="display:flex;flex-direction:column;
        width:150px;height:260px;
        border:2px solid black;border-radius:14px;background:white;
        margin:10px;overflow:hidden;">
            <div style="height:50%;border-bottom:2px solid black;
            display:flex;align-items:center;justify-content:center;">
                {tile['a']}
            </div>
            <div style="height:50%;
            display:flex;align-items:center;justify-content:center;">
                {tile['b']}
            </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)

# ===============================
# GAME LOGIC
# ===============================

def is_valid_move(tile, last_tile):
    if last_tile is None:
        return True
    return (
        tile["a"] == last_tile["a"] or
        tile["a"] == last_tile["b"] or
        tile["b"] == last_tile["a"] or
        tile["b"] == last_tile["b"]
    )

# ===============================
# STREAMLIT APP
# ===============================

st.set_page_config("Conceptual Domino", layout="centered")
st.title("🧩 Conceptual Domino – Calculus")

# ---------- SETUP ----------

if "initialized" not in st.session_state:
    st.subheader("⚙️ Game Setup")
    num_players = st.radio("Players:", [2, 4], horizontal=True)

    if st.button("Start Game"):
        tiles = load_tiles_from_pdf(PDF_FILE)
        rules = load_rules_from_docx(DOCX_FILE)

        random.shuffle(tiles)
        tiles_per = 14 if num_players == 2 else 7

        players = {}
        for i in range(num_players):
            players[f"Player {i+1}"] = {
                "hand": tiles[i*tiles_per:(i+1)*tiles_per],
                "score": 0
            }

        st.session_state.players = players
        st.session_state.order = list(players.keys())
        st.session_state.turn = 0
        st.session_state.board = []
        st.session_state.rules = rules
        st.session_state.initialized = True

    st.stop()

# ---------- RULES ----------

with st.expander("📘 Game Rules"):
    for r in st.session_state.rules:
        st.write("•", r)

# ---------- BOARD ----------

st.subheader("🧠 Board")
for t in st.session_state.board:
    render_domino(t)

# ---------- CURRENT PLAYER ----------

current = st.session_state.order[st.session_state.turn]
player = st.session_state.players[current]

st.subheader(f"🎮 Turn: {current}")

# ---------- PLAYER HAND (ONLY VISIBLE HERE) ----------

for i, tile in enumerate(player["hand"]):
    col1, col2 = st.columns([3, 1])
    with col1:
        render_domino(tile)
    with col2:
        if st.button("Rotate", key=f"rot{i}"):
            tile["orientation"] = (
                "vertical" if tile["orientation"] == "horizontal"
                else "horizontal"
            )

# ---------- PLAY ----------

idx = st.selectbox(
    "Select tile to play:",
    range(len(player["hand"]))
)

justification = st.text_area(
    "✍️ Justify your move (conceptual explanation required):"
)

if st.button("Play tile"):
    tile = player["hand"][idx]
    last = st.session_state.board[-1] if st.session_state.board else None

    if not justification.strip():
        st.error("Justification is mandatory.")
        st.stop()

    if is_valid_move(tile, last):
        st.session_state.board.append(tile)
        player["hand"].pop(idx)
        player["score"] += 4
        st.session_state.turn = (
            st.session_state.turn + 1
        ) % len(st.session_state.order)
        st.success("✔ Valid move")
    else:
        player["score"] -= 2
        st.error("✖ Invalid move")

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, d in st.session_state.players.items():
    st.write(f"**{p}**: {d['score']}")
