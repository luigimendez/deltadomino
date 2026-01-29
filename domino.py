import streamlit as st
import pdfplumber
from docx import Document
import random

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ===============================
# LOADERS
# ===============================

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
                    "a": lines[i],
                    "b": lines[i + 1],
                    "orientation": "horizontal"
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

# ===============================
# DOMINO RENDER (STREAMLIT-NATIVE)
# ===============================

def render_domino(tile):
    if tile["orientation"] == "horizontal":
        c1, c2 = st.columns([1, 1])
        with c1:
            st.container(border=True)
            st.latex(tile["a"])
        with c2:
            st.container(border=True)
            st.latex(tile["b"])
    else:
        st.container(border=True)
        st.latex(tile["a"])
        st.divider()
        st.latex(tile["b"])

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
if not st.session_state.board:
    st.info("No tiles placed yet.")
else:
    for t in st.session_state.board:
        render_domino(t)

# ---------- CURRENT PLAYER ----------

current = st.session_state.order[st.session_state.turn]
player = st.session_state.players[current]

st.subheader(f"🎮 Turn: {current}")

# ---------- CHECK IF PLAYER CAN PLAY ----------

valid_indices = [
    i for i, t in enumerate(player["hand"])
    if is_valid_move(t, st.session_state.board[-1] if st.session_state.board else None)
]

if not valid_indices:
    st.warning("No valid tiles available. Turn passes automatically.")
    st.session_state.turn = (st.session_state.turn + 1) % len(st.session_state.order)
    st.stop()

# ---------- PLAYER HAND ----------

for i, tile in enumerate(player["hand"]):
    st.markdown(f"**Tile {i+1}**")
    render_domino(tile)

    if st.button("Rotate", key=f"rot{i}"):
        tile["orientation"] = (
            "vertical" if tile["orientation"] == "horizontal"
            else "horizontal"
        )

# ---------- PLAY ----------

idx = st.selectbox("Select tile:", valid_indices)

justification = st.text_area(
    "✍️ Justify your move (conceptual explanation required):"
)

if st.button("Play tile"):
    if not justification.strip():
        st.error("Justification is mandatory.")
        st.stop()

    tile = player["hand"].pop(idx)
    st.session_state.board.append(tile)
    player["score"] += 4

    st.session_state.turn = (
        st.session_state.turn + 1
    ) % len(st.session_state.order)

    st.success("✔ Move registered")

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, d in st.session_state.players.items():
    st.write(f"**{p}**: {d['score']}")
