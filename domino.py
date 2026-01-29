import streamlit as st
import pdfplumber
from docx import Document
import random
import openai

# ===============================
# SAFE OPENAI CONFIG
# ===============================

if "OPENAI_API_KEY" not in st.secrets:
    st.error(
        "🔑 OPENAI_API_KEY not found.\n\n"
        "Please add it in Streamlit Cloud → Manage app → Secrets."
    )
    st.stop()

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ===============================
# FILES
# ===============================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ===============================
# AI CONCEPT INFERENCE
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

Examples:
derivative, limit, continuity, integral, chain rule, gradient, vector, series
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
# DOMINO RENDER (STREAMLIT NATIVE)
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

st.set_page_config(page_title="Conceptual Domino (AI)", layout="centered")
st.title("🧩 Conceptual Domino – AI-driven")

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

# ---------- CURRENT TURN ----------

current_player = st.session_state.player_order[st.session_state.turn_index]
player_data = st.session_state.players[current_player]

st.subheader(f"🎮 Turn: {current_player}")

last_tile = st.session_state.board[-1] if st.session_state.board else None

valid_indices = [
    i for i, t in enumerate(player_data["hand"])
    if is_valid_move(t, last_tile)
]

# ---------- PASS TURN IF NO MOVE ----------

if not valid_indices:
    st.warning("No valid conceptual move available. Turn passes automatically.")
    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)
    st.stop()

# ---------- SELECT TILE ----------

idx = st.selectbox(
    "Select a tile to play:",
    valid_indices,
    format_func=lambda i: f"Tile {i + 1}"
)

selected_tile = player_data["hand"][idx]
render_domino(selected_tile)

if st.button("Rotate tile"):
    selected_tile["orientation"] = (
        "vertical" if selected_tile["orientation"] == "horizontal"
        else "horizontal"
    )

# ---------- JUSTIFICATION ----------

justification = st.text_area(
    "✍️ Conceptual justification (required):",
    placeholder="Explain why this tile matches the conceptual meaning on the board."
)

# ---------- PLAY ----------

if st.button("Play tile"):
    if not justification.strip():
        st.error("Justification is mandatory.")
        st.stop()

    player_data["hand"].pop(idx)
    st.session_state.board.append(selected_tile)
    player_data["score"] += 4

    st.success(
        f"✔ Concept matched: "
        f"{selected_tile['a_concept']} / {selected_tile['b_concept']}"
    )

    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, data in st.session_state.players.items():
    st.write(f"**{p}**: {data['score']}")
