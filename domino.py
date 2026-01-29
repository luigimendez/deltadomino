import streamlit as st
import pdfplumber
from docx import Document
import random
import openai

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

PDF_FILE = "tiles.pdf"
DOCX_FILE = "rules.docx"

# ======================================================
# MODO IA / FALLBACK
# ======================================================

USE_AI = True

if "OPENAI_API_KEY" not in st.secrets:
    USE_AI = False
    st.warning(
        "⚠️ OPENAI_API_KEY not found.\n"
        "Running in fallback mode (text-based conceptual matching)."
    )
else:
    openai.api_key = st.secrets["OPENAI_API_KEY"]

# ======================================================
# IA: INFERENCIA DE CONCEPTOS
# ======================================================

def infer_concept(expr):
    if not USE_AI:
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

# ======================================================
# CARGA DE ARCHIVOS
# ======================================================

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

# ======================================================
# TABLERO CONCEPTUAL
# ======================================================

def init_board():
    return {
        "tiles": [],
        "left_concept": None,
        "right_concept": None
    }


def place_tile_on_board(tile, side):
    board = st.session_state.board

    if not board["tiles"]:
        board["tiles"].append(tile)
        board["left_concept"] = tile["a_concept"]
        board["right_concept"] = tile["b_concept"]
        return True, "First tile placed"

    if side == "left":
        if tile["a_concept"] == board["left_concept"]:
            board["tiles"].insert(0, tile)
            board["left_concept"] = tile["b_concept"]
            return True, f"Matched left concept: {tile['a_concept']}"
        if tile["b_concept"] == board["left_concept"]:
            board["tiles"].insert(0, tile)
            board["left_concept"] = tile["a_concept"]
            return True, f"Matched left concept: {tile['b_concept']}"

    if side == "right":
        if tile["a_concept"] == board["right_concept"]:
            board["tiles"].append(tile)
            board["right_concept"] = tile["b_concept"]
            return True, f"Matched right concept: {tile['a_concept']}"
        if tile["b_concept"] == board["right_concept"]:
            board["tiles"].append(tile)
            board["right_concept"] = tile["a_concept"]
            return True, f"Matched right concept: {tile['b_concept']}"

    return False, (
        f"Concept mismatch. Expected "
        f"'{board['left_concept']}' (left) or "
        f"'{board['right_concept']}' (right)."
    )

# ======================================================
# RENDER
# ======================================================

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


def render_board():
    board = st.session_state.board

    if not board["tiles"]:
        st.info("The board is empty.")
        return

    st.markdown("### 🧩 Board")

    cols = st.columns(len(board["tiles"]))
    for col, tile in zip(cols, board["tiles"]):
        with col:
            render_domino(tile)

    st.caption(
        f"⬅️ Left concept: **{board['left_concept']}** | "
        f"Right concept: **{board['right_concept']}** ➡️"
    )

# ======================================================
# APP
# ======================================================

st.set_page_config(page_title="Conceptual Domino", layout="wide")
st.title("🧩 Conceptual Domino – AI & Conceptual Reasoning")

# ---------- MODO PROFESOR ----------

professor_mode = st.sidebar.checkbox("👨‍🏫 Professor mode (full visibility)")

# ---------- SETUP ----------

if "initialized" not in st.session_state:
    st.subheader("⚙️ Game Setup")

    num_players = st.radio("Number of players:", [2, 4], horizontal=True)

    if st.button("Start Game"):
        tiles = load_tiles_from_pdf(PDF_FILE)
        rules = load_rules_from_docx(DOCX_FILE)

        random.shuffle(tiles)
        tiles_per = 14 if num_players == 2 else 7

        players = {}
        for i in range(num_players):
            players[f"Player {i+1}"] = {
                "hand": tiles[i * tiles_per:(i + 1) * tiles_per],
                "score": 0
            }

        st.session_state.players = players
        st.session_state.player_order = list(players.keys())
        st.session_state.turn_index = 0
        st.session_state.board = init_board()
        st.session_state.rules = rules
        st.session_state.initialized = True

    st.stop()

# ---------- REGLAS ----------

with st.expander("📘 Game Rules"):
    for rule in st.session_state.rules:
        st.write("•", rule)

# ---------- TABLERO ----------

render_board()

# ---------- TURNO ----------

current_player = st.session_state.player_order[st.session_state.turn_index]
player = st.session_state.players[current_player]

st.subheader(f"🎮 Turn: {current_player}")

# ---------- MODO PROFESOR: VER TODO ----------

if professor_mode:
    st.markdown("### 👀 Professor View – All Hands")
    for p, data in st.session_state.players.items():
        st.markdown(f"**{p}**")
        for tile in data["hand"]:
            render_domino(tile)

# ---------- MOVIMIENTOS VÁLIDOS ----------

board = st.session_state.board

valid_indices = []
for i, t in enumerate(player["hand"]):
    if not board["tiles"]:
        valid_indices.append(i)
    elif (
        t["a_concept"] in [board["left_concept"], board["right_concept"]] or
        t["b_concept"] in [board["left_concept"], board["right_concept"]]
    ):
        valid_indices.append(i)

if not valid_indices:
    st.warning("No valid conceptual move. Turn passes automatically.")
    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)
    st.stop()

# ---------- SELECCIÓN ----------

idx = st.selectbox(
    "Select a tile:",
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

placement_side = st.radio(
    "Place tile on:",
    ["left", "right"],
    horizontal=True
)

justification = st.text_area(
    "✍️ Conceptual justification (required):",
    placeholder="Explain why this tile matches the concept at the selected board end."
)

# ---------- JUGAR ----------

if st.button("Play tile"):
    if not justification.strip():
        st.error("Justification is mandatory.")
        st.stop()

    success, feedback = place_tile_on_board(tile, placement_side)

    if not success:
        st.error(f"❌ {feedback}")
        st.info("💡 Tip: Check the conceptual label expected at that end of the board.")
        st.stop()

    player["hand"].pop(idx)
    player["score"] += 4

    st.success(f"✔ {feedback}")

    st.session_state.turn_index = (
        st.session_state.turn_index + 1
    ) % len(st.session_state.player_order)

# ---------- SCORES ----------

st.subheader("📊 Scores")
for p, data in st.session_state.players.items():
    st.write(f"**{p}**: {data['score']}")
