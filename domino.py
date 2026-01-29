import streamlit as st
import pdfplumber
from docx import Document
import random

# ===============================
# FILES (repo root)
# ===============================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ===============================
# DATA LOADING
# ===============================

def normalize_latex(text):
    text = text.strip()
    if text.startswith("$") and text.endswith("$"):
        return text
    return f"$${text}$$"


def load_tiles_from_pdf(path):
    tiles = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i in range(0, len(lines) - 1, 2):
                tiles.append({
                    "id": len(tiles),
                    "a": normalize_latex(lines[i]),
                    "b": normalize_latex(lines[i + 1])
                })
    return tiles


def load_rules_from_docx(path):
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

# ===============================
# GAME LOGIC
# ===============================

def is_valid_move(tile, last_tile):
    if last_tile is None:
        return True
    return (
        tile["a"] == last_tile["a"]
        or tile["a"] == last_tile["b"]
        or tile["b"] == last_tile["a"]
        or tile["b"] == last_tile["b"]
    )


def score_update(first_attempt, valid):
    if first_attempt and valid:
        return 4
    if first_attempt and not valid:
        return -2
    return 0

# ===============================
# DOMINO RENDER (TRUE DOMINO)
# ===============================

def render_domino(tile):
    html = f"""
    <div style="
        display:flex;
        width:300px;
        height:130px;
        border:2px solid black;
        border-radius:14px;
        background-color:white;
        box-shadow:2px 2px 6px rgba(0,0,0,0.25);
        margin:10px 0;
        overflow:hidden;
    ">
        <div style="
            width:50%;
            border-right:2px solid black;
            display:flex;
            align-items:center;
            justify-content:center;
            padding:10px;
            text-align:center;
        ">
            {tile['a']}
        </div>
        <div style="
            width:50%;
            display:flex;
            align-items:center;
            justify-content:center;
            padding:10px;
            text-align:center;
        ">
            {tile['b']}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ===============================
# STREAMLIT APP
# ===============================

st.set_page_config(page_title="Conceptual Domino – Calculus", layout="centered")
st.title("🧩 Conceptual Domino – Calculus")

# ---------- GAME SETUP ----------

if "setup_done" not in st.session_state:

    st.subheader("⚙️ Game Setup")

    num_players = st.radio(
        "Select number of players:",
        options=[2, 4],
        horizontal=True
    )

    if st.button("🎮 Start Game"):
        tiles = load_tiles_from_pdf(PDF_FILE)
        rules = load_rules_from_docx(DOCX_FILE)

        if len(tiles) != 28:
            st.error("The game requires exactly 28 tiles.")
            st.stop()

        random.shuffle(tiles)

        tiles_per_player = 14 if num_players == 2 else 7

        players = {}
        for i in range(num_players):
            players[f"Player {i+1}"] = {
                "hand": tiles[i * tiles_per_player:(i + 1) * tiles_per_player],
                "score": 0
            }

        st.session_state.players = players
        st.session_state.num_players = num_players
        st.session_state.current_player = "Player 1"
        st.session_state.board = []
        st.session_state.first_attempt = True
        st.session_state.rules = rules
        st.session_state.setup_done = True

    st.stop()

# ---------- RULES ----------

with st.expander("📘 Game Rules"):
    for rule in st.session_state.rules:
        st.write("•", rule)

# ---------- BOARD ----------

st.subheader("🧠 Board")

if not st.session_state.board:
    st.info("No tiles placed yet.")
else:
    for tile in st.session_state.board:
        render_domino(tile)

# ---------- PLAYER TURN ----------

player = st.session_state.current_player
hand = st.session_state.players[player]["hand"]

st.subheader(f"🎮 Turn: {player}")

if not hand:
    st.success(f"🏆 {player} wins by using all tiles!")
    st.stop()

# ---------- PLAYER HAND ----------

st.write("Your tiles:")

labels = [f"Tile {i+1}" for i in range(len(hand))]
index = st.selectbox("Select a tile to play:", range(len(labels)))
selected_tile = hand[index]

render_domino(selected_tile)

# ---------- PLAY ACTION ----------

if st.button("Play tile"):
    last_tile = st.session_state.board[-1] if st.session_state.board else None
    valid = is_valid_move(selected_tile, last_tile)
    delta = score_update(st.session_state.first_attempt, valid)

    if valid:
        st.session_state.board.append(selected_tile)
        hand.remove(selected_tile)
        st.session_state.players[player]["score"] += delta
        st.success(f"✔ Valid move (+{delta})")
        st.session_state.first_attempt = True

        players = list(st.session_state.players.keys())
        idx = players.index(player)
        st.session_state.current_player = players[
            (idx + 1) % st.session_state.num_players
        ]
    else:
        st.session_state.players[player]["score"] += delta
        st.error(f"✖ Invalid move ({delta})")
        st.session_state.first_attempt = False

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, data in st.session_state.players.items():
    st.write(f"**{p}**: {data['score']}")
