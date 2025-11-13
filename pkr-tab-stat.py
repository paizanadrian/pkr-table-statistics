import streamlit as st
st.set_page_config(page_title="Texas Hold'em – statistica", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #0b0f12 !important;
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #151a1f !important;
        color: #e0e0e0 !important;
    }
    </style>
""", unsafe_allow_html=True)

import random, math, pathlib, textwrap
from itertools import combinations
from collections import defaultdict

# ====== CSS loader ======
FALLBACK_CSS = """
.table-wrap{display:flex;justify-content:center;align-items:center;width:100%}
.poker-table{position:relative;width:min(980px,96vw);height:clamp(280px,52vw,560px);border-radius:9999px;margin:8px auto 14px;
  background: radial-gradient(120% 85% at 50% 40%, #187d52 0%, #0f5b3a 40%, #0b3e29 100%);
  box-shadow: inset 0 0 0 14px #3b2f2f, inset 0 0 0 18px rgba(0,0,0,.25), inset 0 6px 22px rgba(0,0,0,.55), 0 12px 40px rgba(0,0,0,.45);
  outline:1px solid rgba(255,255,255,.06)}
@supports (aspect-ratio:16/9){.poker-table{height:auto;aspect-ratio:16/9}}
.poker-table::before{content:"";position:absolute;inset:0;border-radius:inherit;
  box-shadow: inset 0 10px 0 rgba(255,255,255,.06), inset 0 -8px 18px rgba(0,0,0,.35)}
.board-cards{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);white-space:nowrap;text-align:center;padding:4px 8px}
.table-logo{position:absolute;left:50%;top:28%;transform:translateX(-50%);font:600 14px/1.2 system-ui;letter-spacing:.06em;opacity:.28;color:#fff;user-select:none;text-transform:uppercase}
.player-seat{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:6px;z-index:3}
.player-badge{font:600 13px/1.1 system-ui,Segoe UI,sans-serif;color:#eee;background:rgba(0,0,0,.55);padding:4px 10px;border-radius:999px;white-space:nowrap;box-shadow:0 0 6px rgba(0,0,0,.35);user-select:none;backdrop-filter:blur(4px)}
.player-badge.hero{background:#2e7d32;color:#fff;border:2px solid #b4f7b4;box-shadow:0 0 12px rgba(100,255,100,.6)}
.player-cards{background:rgba(0,0,0,.28);padding:4px 8px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.25);display:inline-block}
.dealer-chip{position:absolute;width:28px;height:28px;border-radius:50%;background:#fff;color:#111;font:700 14px/28px system-ui, Segoe UI, sans-serif;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,.35), inset 0 -2px 0 rgba(0,0,0,.12);border:2px solid #f2f2f2;animation: dealerPulse 1.4s ease-in-out infinite, dealerSpin 6s linear infinite;user-select:none;z-index:7;pointer-events:none;transform:translate(-50%,-50%)}
@keyframes dealerPulse{0%{transform:translate(-50%,-50%) scale(1);box-shadow:0 4px 10px rgba(0,0,0,.35),0 0 0 0 rgba(255,255,255,.35)}50%{transform:translate(-50%,-50%) scale(1.06);box-shadow:0 4px 12px rgba(0,0,0,.45),0 0 0 8px rgba(255,255,255,0)}100%{transform:translate(-50%,-50%) scale(1);box-shadow:0 4px 10px rgba(0,0,0,.35),0 0 0 0 rgba(255,255,255,.35)}}
@keyframes dealerSpin{from{filter:hue-rotate(0deg)}to{filter:hue-rotate(360deg)}}
html, body [data-testid="stAppViewContainer"]{background:#0b0f12}
"""

CARD_SCALE_PLAYERS = 2.5
CARD_SCALE_BOARD   = 2.0

def load_css(rel_path="assets/styles.css"):
    base = pathlib.Path(__file__).parent
    css_path = (base / rel_path).resolve()
    try:
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.markdown(f"<style>{FALLBACK_CSS}</style>", unsafe_allow_html=True)

load_css()

# ===== Config inițială (dinamic) =====
if "NUM_PLAYERS" not in st.session_state:
    st.session_state.NUM_PLAYERS = 10
if "HERO" not in st.session_state:
    st.session_state.HERO = 7
if "seed" not in st.session_state:
    st.session_state.seed = None
if "state" not in st.session_state:
    st.session_state.state = {}
# dealer curent + setare rotație
if "dealer_current" not in st.session_state:
    st.session_state.dealer_current = 1  # 1-based
if "rotate_dealer" not in st.session_state:
    st.session_state.rotate_dealer = True
# cache pentru statistici river (inclusiv mâini câștigătoare)
if "river_stats" not in st.session_state:
    st.session_state.river_stats = None

# ===== Sidebar =====
with st.sidebar:
    st.header("🎮 Setări joc")
    num_players = st.slider("Număr de jucători", 2, 10, st.session_state.NUM_PLAYERS)
    hero = st.number_input("Numărul tău (poziția)", min_value=1, max_value=num_players,
                           value=min(st.session_state.HERO, num_players))
    st.markdown("")
    seed_str = st.text_input(
        "Seed (opțional) pentru repetabilitate",
        value="" if st.session_state.seed is None else str(st.session_state.seed)
    )
    if seed_str.strip() == "":
        st.session_state.seed = None
    else:
        try:
            st.session_state.seed = int(seed_str)
        except ValueError:
            st.warning("Seed-ul trebuie să fie un număr întreg sau gol.")
            st.session_state.seed = None

    rotate_dealer = st.checkbox(
    "Dealer rotativ (1 → N → 1)",
    value=st.session_state.rotate_dealer,
    help="După fiecare mână, dealerul trece automat la următorul jucător (ca la masa reală). "
         "Dacă este debifat, dealerul rămâne același la fiecare mână."
)

    st.session_state.rotate_dealer = rotate_dealer

    # aplică în session_state + corectează dealer dacă iese din 1..N
    st.session_state.NUM_PLAYERS = num_players
    st.session_state.HERO = hero
    if st.session_state.dealer_current > num_players:
        st.session_state.dealer_current = 1

    # === SETĂRI în stil poker_helper_v02.py pentru probabilități River ===
    st.markdown("---")
    st.subheader("📊 Setări probabilități (River)")
    total_players = st.number_input(
        "Număr total jucători",
        min_value=2, max_value=10, value=num_players, step=1
    )
    use_mc = st.checkbox("Monte Carlo (deal fără înlocuire)", value=True,
                        help="Simulează mii de mâini posibile (ca în joc real) pentru a aproxima probabilitățile.")
    mc_trials = st.slider(
    "Runde simulare",
    min_value=1_000,
    max_value=100_000,
    value=20_000,
    step=1_000,
    help=(
        "Numărul de simulări Monte Carlo efectuate pentru estimarea probabilităților. "
        "Mai multe runde = rezultate mai precise, dar calcule mai lente. "
        "Recomandat: 20.000 – 50.000."
    )
)


    st.markdown("---")

# alias locale
NUM_PLAYERS = st.session_state.NUM_PLAYERS
HERO = st.session_state.HERO

# ===== Poker logic =====
RANKS = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
SUITS = "♣♦♥♠"
RED_SUITS = {"♦", "♥"}
RANK_VAL = {r: i for i, r in enumerate(RANKS, start=2)}
VAL_RANK = {v: r for r, v in RANK_VAL.items()}

def rank_ro(v: int) -> str:
    return VAL_RANK[v]

def make_deck():
    return [r + s for r in RANKS for s in SUITS]

def riffle_shuffle(deck, rng, times=5):
    for _ in range(times):
        cut = rng.randint(18, 34)
        left, right = deck[:cut], deck[cut:]
        inter = []
        while left or right:
            tl = rng.randint(1, 3); tr = rng.randint(1, 3)
            inter.extend(left[:tl]); left = left[tl:]
            inter.extend(right[:tr]); right = right[tr:]
        deck[:] = inter
        k = rng.randint(5, 15)
        deck[:] = deck[-k:] + deck[:-k]

def burn(deck):
    if deck:
        deck.pop(0)

def seat_order(dealer_pos):
    return [(dealer_pos + 1 + i) % NUM_PLAYERS for i in range(NUM_PLAYERS)]

def deal_hole_cards(deck, num_players, dealer_pos):
    hands = [[] for _ in range(num_players)]
    order = seat_order(dealer_pos)
    for p in order:
        hands[p].append(deck.pop(0))
    for p in order:
        hands[p].append(deck.pop(0))
    return hands

def deal_board(deck):
    burn(deck); flop = [deck.pop(0) for _ in range(3)]
    burn(deck); turn = deck.pop(0)
    burn(deck); river = deck.pop(0)
    return flop, turn, river

# ===== Evaluare =====
def card_vals(cards):
    return sorted([RANK_VAL[c[:-1]] for c in cards], reverse=True)

def is_flush(cards):
    suits = [c[-1] for c in cards]
    for s in SUITS:
        if suits.count(s) == 5:
            return True, s
    return False, None

def is_straight(vals):
    u = sorted(set(vals), reverse=True)
    if 14 in u:
        u.append(1)  # wheel
    for i in range(len(u) - 4):
        seq = u[i:i+5]
        if seq[0] - seq[4] == 4:
            return True, seq[0]
    return False, 0

# 8=SF,7=Four,6=Full,5=Flush,4=Straight,3=Trips,2=TwoPair,1=Pair,0=High
def evaluate_5(cards):
    vals = card_vals(cards)
    freq = {}
    for v in vals:
        freq[v] = freq.get(v, 0) + 1
    groups = sorted(freq.items(), key=lambda x: (x[1], x[0]), reverse=True)
    counts = [g[1] for g in groups]

    flush, flush_suit = is_flush(cards)
    straight, top_st = is_straight(vals)

    if flush:
        flush_vals = card_vals([c for c in cards if c[-1] == flush_suit])
        sf, sf_top = is_straight(flush_vals)
        if sf:
            return (8, sf_top)

    if 4 in counts:
        four = groups[0][0]
        kicker = max([v for v in vals if v != four]) if any(v != four for v in vals) else 0
        return (7, four, kicker)

    if 3 in counts and 2 in counts:
        trips = [v for v, c in groups if c == 3][0]
        pair  = [v for v, c in groups if c == 2][0]
        return (6, trips, pair)

    if flush:
        return (5, sorted(vals, reverse=True))
    if straight:
        return (4, top_st)

    if 3 in counts:
        trips = [v for v, c in groups if c == 3][0]
        kickers = [v for v in vals if v != trips][:2]
        return (3, trips, kickers)

    pairs = [v for v, c in groups if c == 2]
    if len(pairs) >= 2:
        top2 = pairs[:2]
        kicker = [v for v in vals if v not in top2][0]
        return (2, top2, kicker)

    if 2 in counts:
        pair = [v for v, c in groups if c == 2][0]
        kickers = [v for v in vals if v != pair][:3]
        return (1, pair, kickers)

    return (0, vals)

def best_of_seven(cards7):
    best = None
    for combo in combinations(cards7, 5):
        score = evaluate_5(combo)
        if (best is None) or (score > best):
            best = score
    return best

def best_of_seven_with_combo(cards7):
    best_score, best_combo = None, None
    for combo in combinations(cards7, 5):
        score = evaluate_5(combo)
        if (best_score is None) or (score > best_score):
            best_score, best_combo = score, combo
    return best_score, list(best_combo)

HAND_NAMES = {
    8: "Chintă de culoare (Straight Flush)",
    7: "Careu (Four of a Kind)",
    6: "Full (Full House)",
    5: "Culoare (Flush)",
    4: "Chintă (Straight)",
    3: "Trei de un fel / Trips (Three of a Kind)",
    2: "Două perechi (Two Pair)",
    1: "O pereche (One Pair)",
    0: "Carte mare (High Card)",
}

# pentru textul în stil poker_helper_v02.py
RO_LABEL_MAIN = {
    0: "High card",
    1: "Pereche",
    2: "Două perechi",
    3: "Trei de un fel",
    4: "Chintă",
    5: "Culoare",
    6: "Full",
    7: "Careu",
    8: "Chintă de culoare",
}

def straight_str(topv):
    return "5–A" if topv == 5 else "–".join(rank_ro(topv - i) for i in range(5))

def format_hero_score(score: tuple) -> str:
    """Formatare asemănătoare cu poker_helper_v02.py, dar pe schema acestui evaluator."""
    t = score[0]
    rest = score[1:]

    if t == 8:  # Straight flush (8, top_straight)
        return f"la {rank_ro(rest[0])}"
    if t == 7:  # Quads (7, four, kicker)
        return f"(4x {rank_ro(rest[0])} + kicker {rank_ro(rest[1])})"
    if t == 6:  # Full (6, trips, pair)
        return f"({rank_ro(rest[0])} peste {rank_ro(rest[1])})"
    if t == 5:  # Flush (5, [vals...])
        vals = rest[0]
        return " " + " ".join(rank_ro(v) for v in vals[:5])
    if t == 4:  # Straight (4, top_straight)
        return f"la {rank_ro(rest[0])}"
    if t == 3:  # Trips (3, trips, [k1,k2])
        trips = rest[0]
        kickers = rest[1]
        k1, k2 = kickers[0], kickers[1]
        return f"({rank_ro(trips)} + {rank_ro(k1)} {rank_ro(k2)})"
    if t == 2:  # Two pair (2, [p1,p2], kicker)
        p1, p2 = rest[0]
        hi, lo = (p1, p2) if p1 >= p2 else (p2, p1)
        k = rest[1]
        return f"({rank_ro(hi)} și {rank_ro(lo)} + kicker {rank_ro(k)})"
    if t == 1:  # Pair (1, pair, [k1,k2,k3])
        pair = rest[0]
        ks = rest[1]
        return f"({rank_ro(pair)} + " + " ".join(rank_ro(v) for v in ks[:3]) + ")"
    if t == 0:  # High card (0, [vals...])
        vals = rest[0]
        return " " + " ".join(rank_ro(v) for v in vals[:5])
    return ""

def describe_score(score):
    t = score[0]
    if t == 8:
        return f"{HAND_NAMES[t]} – {straight_str(score[1])}"
    if t == 7:
        return f"{HAND_NAMES[t]} – {rank_ro(score[1])} cu kicker {rank_ro(score[2])}"
    if t == 6:
        return f"{HAND_NAMES[t]} – {rank_ro(score[1])} peste {rank_ro(score[2])}"
    if t == 5:
        return f"{HAND_NAMES[t]} – " + " ".join(rank_ro(v) for v in score[1][:5])
    if t == 4:
        return f"{HAND_NAMES[t]} – {straight_str(score[1])}"
    if t == 3:
        return f"{HAND_NAMES[t]} – {rank_ro(score[1])}"
    if t == 2:
        p1, p2 = rank_ro(score[1][0]), rank_ro(score[1][1])
        return f"{HAND_NAMES[t]} – {p1} și {p2}, kicker {rank_ro(score[2])}"
    if t == 1:
        return f"{HAND_NAMES[t]} – {rank_ro(score[1])}"
    return f"{HAND_NAMES[0]} – " + " ".join(rank_ro(v) for v in score[1][:5])

# ===== UI helpers (HTML cards) =====
def card_html(card, big=False, highlight=False, border=False, scale=1.0):
    rank, suit = card[:-1], card[-1]
    color = "#d00" if suit in RED_SUITS else "#111"
    bg = "#f4f71e" if highlight else "#fff"
    # mărimi de bază
    base_pad = (8, 10) if big else (4, 8)
    base_font = 26 if big else 16
    base_margin = 2
    # aplică factorul
    pad = f"{int(base_pad[0]*scale)}px {int(base_pad[1]*scale)}px"
    font_size = int(base_font * scale)
    margin = int(base_margin * scale)
    border_css = "2px solid #2e7d32" if border else "1px solid #bbb"
    return (
        f"<span style='display:inline-block;margin:{margin}px;"
        f"padding:{pad};background:{bg};color:{color};"
        f"border:{border_css};border-radius:{int(6*scale)}px;"
        f"font-size:{font_size}px;line-height:1.0;font-weight:700'>{rank}{suit}</span>"
    )

def hidden_html(big=False, scale=1.0):
    base_pad = (8, 10) if big else (4, 8)
    base_font = 26 if big else 16
    base_margin = 2
    pad = f"{int(base_pad[0]*scale)}px {int(base_pad[1]*scale)}px"
    font_size = int(base_font * scale)
    margin = int(base_margin * scale)
    return (
        f"<span style='display:inline-block;margin:{margin}px;"
        f"padding:{pad};background:#fff;color:#111;"
        f"border:1px solid #bbb;border-radius:{int(6*scale)}px;"
        f"font-size:{font_size}px;line-height:1.0;font-weight:700'>🂠</span>"
    )

def pretty_html(card: str) -> str:
    """Întoarce rank+simbol cu roșu pentru ♥ și ♦, pentru afișare în markdown HTML."""
    rank = card[:-1]
    suit = card[-1]

    # culoare: roșu pentru inimă / romb, altfel culoarea textului principal
    if suit in ("♥", "♦"):
        color = "#ff4b5c"  # roșu frumos, poți schimba dacă vrei
    else:
        color = "#e0e0e0"  # deschis, potrivit cu tema ta dark

    return f"<span style='color:{color}; font-weight:700'>{rank}{suit}</span>"

# ===== Legendă & posibile (doar la River) =====
LEGEND_TEXT = {
    1: "Chintă roială (Royal Flush)",
    2: "Chintă de culoare (Straight Flush)",
    3: "Careu (Four of a Kind)",
    4: "Full (Full House)",
    5: "Culoare (Flush)",
    6: "Chintă (Straight)",
    7: "Trei de un fel / Trips (Three of a Kind)",
    8: "Două perechi (Two Pair)",
    9: "O pereche (One Pair)",
    10: "Carte mare (High Card)",
}

def score_to_legend_ids(score):
    ids = set()
    cls = score[0]
    if cls == 8:
        top = score[1]
        ids.add(1 if top == 14 else 2)
    elif cls == 7:
        ids.add(3)
    elif cls == 6:
        ids.add(4)
    elif cls == 5:
        ids.add(5)
    elif cls == 4:
        ids.add(6)
    elif cls == 3:
        ids.add(7)
    elif cls == 2:
        ids.add(8)
    elif cls == 1:
        ids.add(9)
    elif cls == 0:
        ids.add(10)
    return ids

def legend_possibles_on_river(board5):
    deck = make_deck()
    remaining = [c for c in deck if c not in board5]
    found = set()
    n = len(remaining)  # 47
    for a in range(n):
        for b in range(a+1, n):
            hole = [remaining[a], remaining[b]]
            sc = best_of_seven(board5 + hole)
            found |= score_to_legend_ids(sc)
            if len(found) == 10:
                return sorted(found)
    return sorted(found)

def legend_lines(ids):
    if not ids:
        return "—"
    return "\n".join(f"{i}) {LEGEND_TEXT[i]}" for i in range(1, 11) if i in ids)

# ===== State & acțiuni =====
def new_hand():
    """Generează o mână nouă. Dealerul curent este cel din dealer_current;
       după generare, dacă 'rotate_dealer' este ON, dealer_current avansează pentru mâna următoare."""
    # dealer curent (clamp în 1..NUM_PLAYERS)
    cur = st.session_state.dealer_current
    if cur < 1 or cur > NUM_PLAYERS:
        cur = 1
        st.session_state.dealer_current = 1

    dealer_idx_0 = cur - 1  # 0-based pentru deal_hole_cards

    rng = random.Random(st.session_state.seed)
    deck = make_deck()
    riffle_shuffle(deck, rng)
    hands = deal_hole_cards(deck, NUM_PLAYERS, dealer_idx_0)
    flop, turn, river = deal_board(deck)

    st.session_state.state = {
        "dealer": cur,            # 1-based — dealerul MÂINII CURENTE (folosit în UI)
        "hands": hands,
        "flop": flop,
        "turn": turn,
        "river": river,
        "stage": "flop",
        "show": False,
        "winners": [],
        "winner_descriptions": [],
        "winner_combos": [],
        "possible_river": None,
    }
    # resetăm statistica river
    st.session_state.river_stats = None

    # pregătește dealerul pentru mâna următoare
    if st.session_state.rotate_dealer:
        st.session_state.dealer_current = (cur % NUM_PLAYERS) + 1
    else:
        st.session_state.dealer_current = cur  # rămâne

def winner_details_with_combos(hands, board5):
    scored, combos, best = [], [], None
    for h in hands:
        s, combo = best_of_seven_with_combo(h + board5)
        scored.append(s)
        combos.append(combo)
        if best is None or s > best:
            best = s
    winners = [i for i, s in enumerate(scored) if s == best]
    desc = [describe_score(scored[i]) for i in winners]
    winner_combos = [combos[i] for i in winners]
    return winners, desc, winner_combos

def progress_step():
    s = st.session_state.state
    if s["stage"] == "flop":
        s["stage"] = "turn"
    elif s["stage"] == "turn":
        s["stage"] = "river"
        # calculează "posibile combinații" pe board-ul complet (abia acum avem riverul în state)
        board5 = s["flop"] + [s["turn"], s["river"]]
        s["possible_river"] = legend_possibles_on_river(board5)
    elif s["stage"] == "river":
        s["stage"] = "show"
        s["show"] = True
        board5 = s["flop"] + [s["turn"], s["river"]]
        winners, descriptions, winner_combos = winner_details_with_combos(s["hands"], board5)
        s["winners"] = winners
        s["winner_descriptions"] = descriptions
        s["winner_combos"] = winner_combos

# ===== UI =====

# (Re)generează o mână dacă nu există sau s-a schimbat numărul de jucători
if not st.session_state.state or len(st.session_state.state.get("hands", [])) != NUM_PLAYERS:
    new_hand()

s = st.session_state.state
stage, show = s["stage"], s["show"]
winners_set = set(s.get("winners", []))

top_left, top_center, top_right = st.columns([1, 6, 1], gap="small")

# ---------- COLȚ STÂNGA-SUS: buton + STATISTICI RIVER (la cerere) ----------
with top_left:
    if st.button("Mână nouă", key="btn_new_board", use_container_width=True):
        new_hand()
        st.rerun()

    st.markdown("### 📈 Statistici pe River")

    def render_pie(prob_red: float):
        import matplotlib.pyplot as plt
        prob_red = max(0.0, min(1.0, prob_red))
        prob_green = 1.0 - prob_red
        fig, ax = plt.subplots(figsize=(1.2, 1.2))
        ax.pie(
            [prob_red, prob_green],
            labels=[f"Pierd\n ({prob_red*100:.1f}%)", f"Câștig\n ({prob_green*100:.1f}%)"],
            colors=["#ef4444", "#10b981"],
            startangle=90,
            counterclock=False,
            wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
            labeldistance=1.25,
        )
        for text in ax.texts:
            text.set_fontsize(6)
        ax.axis("equal")
        st.pyplot(fig, use_container_width=False)

    if stage in ("river", "show"):
        # buton care PORNEȘTE calculele grele o singură dată
        if st.button("Calculează statistici", key="btn_calc_stat"):
            hero_hole = s["hands"][HERO-1]
            board5 = s["flop"] + [s["turn"], s["river"]]
            hero_score = best_of_seven(hero_hole + board5)

            deck = make_deck()
            used = set(hero_hole + board5)
            remaining = [c for c in deck if c not in used]

            all_pairs = list(combinations(remaining, 2))
            M = len(all_pairs)
            wins_1 = ties_1 = 0
            wins_by_class = defaultdict(list)  # cls -> list[(a,b)]

            for a, b in all_pairs:
                sc = best_of_seven([a, b] + board5)
                if sc > hero_score:
                    wins_1 += 1
                    cls = sc[0]
                    wins_by_class[cls].append((a, b))
                elif sc == hero_score:
                    ties_1 += 1

            W, T = wins_1, ties_1
            hero_label = RO_LABEL_MAIN[hero_score[0]]

            k_opps = max(0, int(total_players) - 1)
            if M > 0:
                p1_win = W / M
                p1_tie = T / M
            else:
                p1_win = p1_tie = 0.0

            if k_opps > 0:
                p_any_beats_approx = 1 - (1 - p1_win) ** k_opps
                p_any_tieonly_approx = ((1 - p1_win) ** k_opps -
                                        (1 - p1_win - p1_tie) ** k_opps)
            else:
                p_any_beats_approx = 0.0
                p_any_tieonly_approx = 0.0

            p_red = p_any_beats_approx
            p_mc_beats = None
            p_mc_tieonly = None

            # Monte Carlo e mai lent, dar îl facem doar LA CERERE
            if use_mc and k_opps > 0 and M > 0:
                hits = ties_mc = 0
                rem = remaining[:]
                for _ in range(int(mc_trials)):
                    deck_mc = rem[:]
                    random.shuffle(deck_mc)
                    someone_beats = False
                    someone_ties = False
                    for i in range(k_opps):
                        a, b = deck_mc[2 * i], deck_mc[2 * i + 1]
                        sc = best_of_seven([a, b] + board5)
                        if sc > hero_score:
                            someone_beats = True
                            break
                        elif sc == hero_score:
                            someone_ties = True
                    if someone_beats:
                        hits += 1
                    elif someone_ties:
                        ties_mc += 1
                p_mc_beats = hits / mc_trials if mc_trials else 0.0
                p_mc_tieonly = ties_mc / mc_trials if mc_trials else 0.0
                p_red = p_mc_beats

            # salvăm rezultatul ÎN CACHE (inclusiv mâinile câștigătoare pe categorii)
            st.session_state.river_stats = {
                "M": M, "W": W, "T": T,
                "hero_score": hero_score,
                "hero_label": hero_label,
                "p_any_beats_approx": p_any_beats_approx,
                "p_any_tieonly_approx": p_any_tieonly_approx,
                "p_mc_beats": p_mc_beats,
                "p_mc_tieonly": p_mc_tieonly,
                "p_red": p_red,
                "wins_by_class": wins_by_class,   # <--- NOU
            }

        # Afișăm ce avem în cache (indiferent că suntem pe RIVER sau SHOW)
        stats = st.session_state.river_stats
        if stats is None:
            st.markdown("Apasă butonul de mai sus pentru a calcula statisticile.")
        else:
            M = stats["M"]; W = stats["W"]; T = stats["T"]
            hero_score = stats["hero_score"]
            hero_label = stats["hero_label"]
            p_any_beats_approx = stats["p_any_beats_approx"]
            p_any_tieonly_approx = stats["p_any_tieonly_approx"]
            p_mc_beats = stats["p_mc_beats"]
            p_mc_tieonly = stats["p_mc_tieonly"]
            p_red = stats["p_red"]

            st.markdown(
                f"**Combinații posibile pentru 1 adversar:** {M:,}  ·  "
                f"**Te bat:** {W:,}  ·  **Egal:** {T:,}"
            )
                        with st.expander("ℹ️ Ce înseamnă 990?"):
            st.write("""
                Este numărul total de combinații de 2 cărți diferite pe care le poate avea un adversar.

                Formula: **C(n, 2)** – combinații din n cărți.

                Exemplu pentru River:
                - 52 cărți în pachet
                - 7 cunoscute (2 ale tale + 5 board)
                - rămân 45 necunoscute
                - C(45, 2) = 990 combinații posibile pentru un adversar.
            """)
            st.success(f"🃏 Mâna ta pe river: **{hero_label}** {format_hero_score(hero_score)}")

            if use_mc and p_mc_beats is not None:
                st.markdown(
                    f"**Prob. ≥1 adversar te bate:** {p_mc_beats*100:.2f}%  \n"
                    f"**Prob. egal (și nimeni nu te bate):** {p_mc_tieonly*100:.2f}%"
                )
            else:
                st.markdown(
                    f"**Prob. ≥1 adversar te bate (aprox.):** {p_any_beats_approx*100:.2f}%  \n"
                    f"**Prob. egal (și nimeni nu te bate) (aprox.):** {p_any_tieonly_approx*100:.2f}%"
                )

            render_pie(p_red)
    else:
        # înainte de river, nu avem cum calcula
        st.markdown(
            "**Combinații posibile:** –  ·  **Te bat:** –  ·  **Egal:** –  \n\n"
            "**Prob. ≥1 adversar te bate:** –  \n"
            "**Prob. egal (și nimeni nu te bate):** –"
        )

# ---------- CENTRU: masa + board + jucători ----------
with top_center:
    st.markdown("<h1 style='text-align:center;margin:0.5rem 0'>Texas Hold'em</h1>", unsafe_allow_html=True)

    # === Board (cu highlight pe cărțile din combo câștigătoare) ===
    board_highlight_set = set()
    if show and s["winner_combos"]:
        all_board = s["flop"] + [s["turn"], s["river"]]
        for combo in s["winner_combos"]:
            for c in combo:
                if c in all_board:
                    board_highlight_set.add(c)

    parts = []
    for c in s["flop"]:
        parts.append(card_html(c, big=True,
                               highlight=show and c in board_highlight_set,
                               border=show and c in board_highlight_set, scale=CARD_SCALE_BOARD))
    parts.append(
        card_html(s["turn"], big=True,
                  highlight=show and s["turn"] in board_highlight_set,
                  border=show and s["turn"] in board_highlight_set, scale=CARD_SCALE_BOARD)
        if stage in ("turn", "river", "show") else hidden_html(big=True, scale=CARD_SCALE_BOARD)
    )
    parts.append(
        card_html(s["river"], big=True,
                  highlight=show and s["river"] in board_highlight_set,
                  border=show and s["river"] in board_highlight_set, scale=CARD_SCALE_BOARD)
        if stage in ("river", "show") else hidden_html(big=True, scale=CARD_SCALE_BOARD)
    )

    # === Jucători în jurul mesei ===
    player_seats = []
    dealer_chips = []  # chip-urile dealer-ului (plasate pe masă, nu în badge)
    for i in range(NUM_PLAYERS):
        # 0° sus, sens orar; offset -90° ca jos să fie ~270°
        angle = (360 * i / NUM_PLAYERS)
        radius = 46
        x = 50 + radius * math.cos(math.radians(angle - 90))
        y = 50 + radius * math.sin(math.radians(angle - 90))

        is_hero = (i + 1) == HERO
        is_winner = (stage == "show") and (i in winners_set)

        # set pt highlight cărți câștigătoare
        combo_set = set()
        if is_winner and s["winner_combos"]:
            for w_i, w_idx in enumerate(s["winners"]):
                if w_idx == i:
                    combo_set = set(s["winner_combos"][w_i])
                    break

        label = "TU" if is_hero else f"Jucător {i+1}"
        if (i + 1) == s["dealer"]:
            label += " (D)"
        if is_winner:
            label += " 🏆"
        cls = "player-badge hero" if is_hero else "player-badge"

        # cărți vizibile: TU mereu; ceilalți la showdown
        if is_hero or stage == "show":
            cards = s["hands"][i]
            cards_html = " ".join(
                card_html(c, highlight=(is_winner and (c in combo_set)), scale=CARD_SCALE_PLAYERS)
                for c in cards
            )
        else:
            cards_html = " ".join(hidden_html(scale=CARD_SCALE_PLAYERS) for _ in range(2))

        # seat container
        player_seats.append(
            f"<div class='player-seat' style='left:{x}%;top:{y}%'>"
            f"<div class='{cls}'>{label}</div>"
            f"<div class='player-cards'>{cards_html}</div>"
            f"</div>"
        )

        # === Dealer chip: spre interiorul mesei (interpolare către centru) ===
        if (i + 1) == s["dealer"]:
            alpha = 0.70  # 0.78..0.90 — mai mare = mai aproape de scaun; mai mic = mai aproape de centru
            chip_x = 50 * (1 - alpha) + alpha * x
            chip_y = 50 * (1 - alpha) + alpha * y

            # (opțional) mic push suplimentar spre centru
            vec_x = 50 - x
            vec_y = 50 - y
            norm = (vec_x**2 + vec_y**2) ** 0.5 or 1.0
            push_pct = 0.0
            chip_x += (vec_x / norm) * push_pct
            chip_y += (vec_y / norm) * push_pct

            dealer_chips.append(
                f"<div class='dealer-chip' style='left:{chip_x}%;top:{chip_y}%'>D</div>"
            )

    html_table = textwrap.dedent(f"""
    <div class="table-wrap">
      <div class="poker-table">
        <div class="table-logo">Texas Hold'em</div>
        <div class="board-cards">{' '.join(parts)}</div>
        {''.join(player_seats)}
        {''.join(dealer_chips)}
      </div>
    </div>
    """).strip()
    st.markdown(html_table, unsafe_allow_html=True)

# ---------- COLȚ DREAPTA-SUS: progres joc ----------
with top_right:
    label = "Arată Turn" if stage == "flop" else "Arată River" if stage == "turn" else "Arată cărțile"
    if st.button(label, key="btn_prog_board", disabled=show, use_container_width=True):
        progress_step()
        st.rerun()

st.caption(f"**TU:** Jucător {HERO}  .......  **Dealer:** Jucător {s['dealer']}")

st.divider()

# ===== Rezultat la SHOW =====
if stage == "show":
    if len(s["winners"]) == 1:
        w = s["winners"][0]
        desc = s["winner_descriptions"][0] if s["winner_descriptions"] else ""
        st.success(f"🏆 **Câștigător: Jucătorul {w+1}** — {desc}")
    else:
        st.success("🏆 **Câștigători (split):**")
        for w, desc in zip(s["winners"], s["winner_descriptions"]):
            st.write(f"• Jucătorul {w+1} — {desc}")

st.divider()

# ===== Bottom: legendă + posibile (doar la River) =====
left_col, right_col = st.columns(2)
with left_col:
    st.markdown("### Ordinea mâinilor câștigătoare (de la cea mai puternică la cea mai slabă)")
    legend_txt = (
        "1) Chintă roială (Royal Flush) – A-K-Q-J-10, toate de aceeași culoare\n"
        "2) Chintă de culoare (Straight Flush)\n"
        "3) Careu (Four of a Kind)\n"
        "4) Full (Full House)\n"
        "5) Culoare (Flush)\n"
        "6) Chintă (Straight)\n"
        "7) Trei de un fel / Trips (Three of a Kind)\n"
        "8) Două perechi (Two Pair)\n"
        "9) O pereche (One Pair)\n"
        "10) Carte mare (High Card)"
    )
    st.text(legend_txt)
with right_col:
    st.markdown("### Combinații posibile câștigătoare (doar la River)")
    if s.get("possible_river"):
        st.text(legend_lines(s["possible_river"]))
    else:
        st.text("—")

st.divider()

# ===== MÂINI POSIBILE CÂȘTIGĂTOARE – GRUPATE (în stil poker_click_images_full) =====
stats = st.session_state.river_stats
if stage in ("river", "show") and stats is not None and stats.get("wins_by_class"):
    st.subheader("Mâini posibile câștigătoare (1 adversar) – grupate")

    wins_by_class = stats["wins_by_class"]  # dict: cls -> list[(a,b)]
    order_classes = [8, 7, 6, 5, 4, 3, 2, 1, 0]  # de la cea mai puternică la cea mai slabă

    for cls in order_classes:
        hands = wins_by_class.get(cls, [])
        if not hands:
            continue
        ro = RO_LABEL_MAIN[cls]
        st.markdown(f"**{ro} — {len(hands)} combinații**")
        with st.expander("Vezi exemple"):
            show_n = min(120, len(hands))

            # folosim pretty_html pentru a colora ♥ și ♦ în roșu
            txt = ", ".join(
                f"{pretty_html(hands[i][0])} {pretty_html(hands[i][1])}"
                for i in range(show_n)
            )
            if len(hands) > show_n:
                txt += " ..."

            st.markdown(txt, unsafe_allow_html=True)
else:
    st.markdown(
        "*(Mâinile posibile câștigătoare pe categorii vor apărea aici "
        "după ce calculezi statisticile pe River.)*"
    )
