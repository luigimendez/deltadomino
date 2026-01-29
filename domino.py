import streamlit as st
import pdfplumber
from docx import Document
import random

# =====================================
# LOAD DATA FROM REPOSITORY FILES
# =====================================

PDF_FILE = "Formato fichas (inglés) - estudiantes.pdf"
DOCX_FILE = "Reglas del juego.docx"


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
                    "b": lines[i + 1]
                })
    return tiles


def load_rules_from_docx(path):
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


# =====================================
# GAME LOGIC
# =====================================

def is_valid_move(tile, last_tile):
    if last_tile is None:
        return True
    return (
        tile["a"] == last_tile["a"] or
        tile["a"] == last_tile["b"] or
        tile["b"] == last_tile["a"] or
        tile["b"] == last_tile["b"]
    )


def score_update(first_attempt, valid):
    if first_attempt and valid:
        return 4
    if first_attempt and not valid:
        return -2
    return 0


# =====================================
# STREAMLIT APP
# =====================================

st.set_page_config(page_title="Conceptual Domino – Calculus", layout="centered")
st.title("🧩 Conceptual Domino – Calculus")

if "initialized" not in st.session_state:
    tiles = load_tiles_from_pdf(PDF_FILE)
    rules = load_rules_from_docx(DOCX_FILE)

    random.shuffle(tiles)

    st.session_state.players = {
        "Player 1": {"hand": tiles[0:7], "score": 0},
        "Player 2": {"hand": tiles[7:14], "score": 0},
        "Player 3": {"hand": tiles[14:21], "score": 0},
        "Player 4": {"hand": tiles[21:28], "score": 0},
    }

    st.session_state.current_player = "Player 1"
    st.session_state.board = []
    st.session_state.first_attempt = True
    st.session_state.rules = rules
    st.session_state.initialized = True


# =====================================
# UI
# =====================================

with st.expander("📘 Game Rules"):
    for rule in st.session_state.rules:
        st.write("•", rule)


st.subheader("🧠 Board")
if not st.session_state.board:
    st.info("No tiles placed yet.")
else:
    for t in st.session_state.board:
        st.markdown(f"**{t['a']} ↔ {t['b']}**")


player = st.session_state.current_player
hand = st.session_state.players[player]["hand"]

st.subheader(f"🎮 Turn: {player}")

if not hand:
    st.success(f"🏆 {player} wins by using all tiles!")
    st.stop()

labels = [f"{t['a']} ↔ {t['b']}" for t in hand]
index = st.selectbox("Select a tile:", range(len(labels)), format_func=lambda i: labels[i])
tile = hand[index]

if st.button("Play tile"):
    last_tile = st.session_state.board[-1] if st.session_state.board else None
    valid = is_valid_move(tile, last_tile)
    delta = score_update(st.session_state.first_attempt, valid)

    if valid:
        st.session_state.board.append(tile)
        hand.remove(tile)
        st.session_state.players[player]["score"] += delta
        st.success(f"✔ Valid move (+{delta})")
        st.session_state.first_attempt = True

        players = list(st.session_state.players.keys())
        idx = players.index(player)
        st.session_state.current_player = players[(idx + 1) % 4]
    else:
        st.session_state.players[player]["score"] += delta
        st.error(f"✖ Invalid move ({delta})")
        st.session_state.first_attempt = False


st.subheader("📊 Scores")
for p, data in st.session_state.players.items():
    st.write(f"**{p}**: {data['score']}")