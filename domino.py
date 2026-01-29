import streamlit as st
import pdfplumber
from docx import Document
import random
import openai

# ===============================
# CONFIG
# ===============================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ===============================
# IA CONCEPT INFERENCE
# ===============================

def infer_concept(latex_expr):
    if "concept_cache" not in st.session_state:
        st.session_state.concept_cache = {}

    if latex_expr in st.session_state.concept_cache:
        return st.session_state.concept_cache[latex_expr]

    prompt = f"""
You are a mathematics education expert.
Given the following mathematical expression, return ONLY the main underlying concept
as a single lowercase word or short phrase (no explanation).

Expression:
{latex_expr}

Examples of concepts:
derivative, limit, continuity, integral, chain rule, optimization, series, vector, gradient
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    concept = response.choices[0].message["content"].strip().lower()
    st.session_state.concept_cache[latex_expr] = concept
    return concept

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
                a = lines[i]
                b = lines[i + 1]
                tiles.append({
                    "id": len(tiles),
                    "a": a,
                    "b": b,
                    "a_concept": infer_concept(a),
                    "b_concept": infer_concept(b),
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
        tile["a_concept"] == last_tile["a_concept"]
        or tile["a_concept"] == last_tile["b_concept"]
        or tile["b_concept"] == last_tile["a_concept"]
        or tile["b_concept"] == last_tile["b_concept"]
    )

# ===============================
# DOMINO RENDER
# ===============================

def render_domino(tile):
    if tile["orientation"] == "horizontal":
        c1, c2 = st.columns(2)
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
# APP
# ===============================

st.set_page_config("Conceptual Domino", layout="centered")
st.title("🧩 Conceptual Domino – AI-driven")

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

# ---------- TURN ----------

current = st.session_state.order[st.session_state.turn]
player = st.session_state.players[current]

st.subheader(f"🎮 Turn: {current}")

# ---------- VALID MOVES ----------

last = st.session_state.board[-1] if st.session_state.board else None

valid_indices = [
    i for i, t in enumerate(player["hand"])
    if is_valid_move(t, last)
]

if not valid_indices:
    st.warning("No valid conceptual move. Turn passes automatically.")
    st.session_state.turn = (st.session_state.turn + 1) % len(st.session_state.order)
    st.stop()

# ---------- HAND ----------

idx = st.selectbox(
    "Select tile to play:",
    valid_indices,
    format_func=lambda i: f"Tile {i+1}"
)

tile = player["hand"][idx]
render_domino(tile)

if st.button("Rotate tile"):
    tile["orientation"] = (
        "vertical" if tile["orientation"] == "horizontal"
        else "horizontal"
    )

justification = st.text_area(
    "✍️ Conceptual justification (mandatory):"
)

if st.button("Play tile"):
    if not justification.strip():
        st.error("Justification required.")
        st.stop()

    player["hand"].pop(idx)
    st.session_state.board.append(tile)
    player["score"] += 4

    st.session_state.turn = (
        st.session_state.turn + 1
    ) % len(st.session_state.order)

    st.success(
        f"✔ Concept matched: {tile['a_concept']} / {tile['b_concept']}"
    )

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, d in st.session_state.players.items():
    st.write(f"**{p}**: {d['score']}")
