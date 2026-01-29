import streamlit as st
import pdfplumber
from docx import Document
import random
import openai

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ===============================
# MODO DUAL IA / NO IA
# ===============================

USE_AI = True

if "OPENAI_API_KEY" not in st.secrets:
    USE_AI = False
    st.warning(
        "⚠️ OPENAI_API_KEY not found.\n"
        "Running in non-AI mode (concepts inferred textually)."
    )
else:
    openai.api_key = st.secrets["OPENAI_API_KEY"]

# ===============================
# IA: INFERENCIA DE CONCEPTOS
# ===============================

def infer_concept(expr):
    """
    Returns a conceptual label for a mathematical expression.
    Uses AI if available, otherwise a deterministic fallback.
    """

    if not USE_AI:
        # Fallback estable y reproducible
        return expr.lower().strip()[:50]

    if "concept_cache" not in st.session_state:
        st.session_state.concept_cache = {}

    if expr in st.session_state.concept_cache:
        return st.session_state.concept_cache[expr]

    prompt = f"""
You are a mathematics education expert.
Given the following mathematical expression, return ONLY the
main underlying mathematical concept as a short lowercase phrase.

Expression:
{expr}

Examples:
derivative, limit, continuity, chain rule, gradient, integral
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    concept = response.choices[0].message["content"].strip().lower()
    st.session_state.concept_cache[expr] = concept
    return concept

# ===============================
# CARGA DE ARCHIVOS
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
# LÓGICA DEL JUEGO
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
# RENDER DE FICHA (STREAMLIT NATIVO)
# ===============================

def render_domino(tile):
    if tile["orientation"] == "horizontal":
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.latex(tile["a"])
        with c2:
            with st.container(border=True):
                st.latex(tile["b"])
    else:
        with st.container(border=True):
            st.latex(tile["a"])
            st.divider()
            st.latex(tile["b"])

# ===============================
# STREAMLIT APP
# ===============================

st.set_page_config(page_title="Conceptual Domino", layout="centered")
st.title("🧩 Conceptual Domino – Conceptual Matching")

# ---------- SETUP ----------

if "initialized" not in st.session_state:
    st.subheader("⚙️ Game Setup")
    num_players = st.radio("Number of players:", [2, 4], horizontal=True)

    if st.button("Start Game"):
        tiles = load_tiles_from_pdf(PDF_FILE)
        rules = load_rules_from_docx(DOCX_FILE)

        random.shuffle(tiles)
        tiles_per_player = 14 if num_players == 2 else 7

        players = {}
        for i in range(num_players):
            players[f"Player {i+1}"] = {
                "hand": tiles[i * tiles_per_player:(i + 1) * tiles_per_player],
                "score": 0
            }

        st.session_state.players = players
        st.session_state.player_order = list(players.keys())
        st.session_state.turn_index = 0
        st.session_state.board = []
        st.session_state.rules = rules
        st.session_state.initialized = True

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

# ---------- TURNO ACTUAL ----------

current_player = st.session_state.player_order[st.session_state.turn_index]
player = st.session_state.players[current_player]

st.subheader(f"🎮 Turn: {current_player}")

last_tile = st.session_state.board[-1] if st.session_state.board else None

valid_indices = [
    i for i, t in enumerate(player["hand"])
    if is_valid_move(t, last_tile)
]

# ---------- PASO AUTOMÁTICO ----------

if not valid_indices:
    st.warning("No valid conceptual move. Turn passes automatically.")
    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)
    st.stop()

# ---------- SELECCIÓN DE FICHA ----------

idx = st.selectbox(
    "Select a tile to play:",
    valid_indices,
    format_func=lambda i: f"Tile {i + 1}"
)

selected_tile = player["hand"][idx]
render_domino(selected_tile)

if st.button("Rotate tile"):
    selected_tile["orientation"] = (
        "vertical" if selected_tile["orientation"] == "horizontal"
        else "horizontal"
    )

# ---------- JUSTIFICACIÓN ----------

justification = st.text_area(
    "✍️ Conceptual justification (required):",
    placeholder="Explain why this tile matches the conceptual meaning on the board."
)

# ---------- JUGAR ----------

if st.button("Play tile"):
    if not justification.strip():
        st.error("Justification is mandatory.")
        st.stop()

    player["hand"].pop(idx)
    st.session_state.board.append(selected_tile)
    player["score"] += 4

    st.success(
        f"✔ Concept matched: "
        f"{selected_tile['a_concept']} / {selected_tile['b_concept']}"
    )

    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)

# ---------- MARCADOR ----------

st.subheader("📊 Scores")
for p, data in st.session_state.players.items():
    st.write(f"**{p}**: {data['score']}")
