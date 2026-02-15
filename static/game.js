/**
 * Yahtzee Web Client — WebSocket-based game interface.
 *
 * Connects to the server, receives state snapshots, and renders the game.
 * All game logic lives on the server; the client is a thin rendering layer.
 */

// ── Category order (must match server) ─────────────────────────────────────

const CATEGORY_ORDER = [
    "Ones", "Twos", "Threes", "Fours", "Fives", "Sixes",
    "3 of a Kind", "4 of a Kind", "Full House",
    "Small Straight", "Large Straight", "Yahtzee", "Chance"
];

const UPPER_CATS = CATEGORY_ORDER.slice(0, 6);
const LOWER_CATS = CATEGORY_ORDER.slice(6);

const OPTIMAL_EXPECTED = 223;

// ── WebSocket connection ───────────────────────────────────────────────────

let ws = null;
let state = null;
let prevState = null;

function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const params = location.search;  // Forward game config params
    ws = new WebSocket(`${proto}//${location.host}/ws${params}`);

    ws.onopen = () => console.log("Connected");
    ws.onclose = () => {
        console.log("Disconnected");
        setTimeout(connect, 2000);
    };
    ws.onerror = (e) => console.error("WebSocket error:", e);

    ws.onmessage = (event) => {
        prevState = state;
        state = JSON.parse(event.data);
        render(state);
    };
}

function sendAction(action, data) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const msg = { action, ...data };
    ws.send(JSON.stringify(msg));
}

// ── Rendering ──────────────────────────────────────────────────────────────

function render(s) {
    applyTheme(s);
    renderRoundInfo(s);
    renderPlayerBar(s);
    renderDice(s);
    renderRollButton(s);
    renderRollStatus(s);
    renderAIReason(s);
    renderTurnLog(s);
    renderScorecard(s);
    renderOverlays(s);
}

function applyTheme(s) {
    document.body.classList.toggle("dark-mode", s.dark_mode);
    document.body.classList.toggle("colorblind", s.colorblind_mode);
}

function renderRoundInfo(s) {
    const el = document.getElementById("round-info");
    let text = `Round ${s.current_round}/13`;
    if (s.has_any_ai) {
        text += ` | Speed: ${capitalize(s.speed)}`;
    }
    el.textContent = text;
}

function renderPlayerBar(s) {
    const el = document.getElementById("player-bar");
    if (!s.multiplayer) { el.innerHTML = ""; return; }

    el.innerHTML = s.player_configs.map((p, i) => {
        const score = s.all_scorecards[i].grand_total;
        const active = (i === s.current_player_index && !s.game_over);
        const cls = active ? "player-chip active" : "player-chip";
        const style = active
            ? `background: ${playerColor(i)}; border-color: ${playerColor(i)};`
            : `border-color: ${playerColor(i)}; color: ${playerColor(i)};`;
        return `<span class="${cls}" style="${style}">${p.name}: ${score}</span>`;
    }).join("");
}

function renderDice(s) {
    const container = document.getElementById("dice-container");
    container.innerHTML = "";

    for (let i = 0; i < 5; i++) {
        const die = s.dice[i];
        const wrapper = document.createElement("div");
        wrapper.className = "die-wrapper";

        const el = document.createElement("div");
        el.className = "die";
        el.dataset.dieIndex = i;  // For event delegation

        if (s.rolls_used === 0 && !s.is_rolling) {
            el.classList.add("in-cup");
            el.innerHTML = '<span class="cup-text">?</span>';
        } else {
            let val = die.value;
            if (s.is_rolling && !die.held) {
                val = Math.floor(Math.random() * 6) + 1;
                el.classList.add("rolling");
            }
            el.dataset.value = val;
            for (let d = 0; d < val; d++) {
                el.appendChild(Object.assign(document.createElement("div"), { className: "dot" }));
            }
            if (die.held) {
                el.classList.add("held");
                const label = document.createElement("span");
                label.className = "held-label";
                label.textContent = "HELD";
                el.appendChild(label);
            }

            // Bounce animation on roll end
            if (prevState && prevState.is_rolling && !s.is_rolling && !die.held) {
                el.classList.add("bounce");
                setTimeout(() => el.classList.remove("bounce"), 300);
            }
        }

        wrapper.appendChild(el);

        const label = document.createElement("span");
        label.className = "die-label";
        label.textContent = `[${i + 1}]`;
        wrapper.appendChild(label);

        container.appendChild(wrapper);
    }
}

function renderRollButton(s) {
    const btn = document.getElementById("roll-btn");
    btn.disabled = !s.can_roll || !s.is_human_turn || s.turn_transition;
}

function renderRollStatus(s) {
    const el = document.getElementById("roll-status");
    if (s.game_over) {
        el.textContent = "";
    } else if (s.rolls_used === 0) {
        el.textContent = "Roll the dice!";
    } else {
        el.textContent = `Rolls left: ${3 - s.rolls_used}`;
    }
}

function renderAIReason(s) {
    const el = document.getElementById("ai-reason");
    el.textContent = s.ai_reason || "";
}

function renderTurnLog(s) {
    const el = document.getElementById("turn-log");
    if (!s.multiplayer || !s.turn_log || s.turn_log.length === 0) {
        el.innerHTML = "";
        return;
    }

    // Show the most recent turns (up to 8 entries to avoid clutter)
    const recent = s.turn_log.slice(-8);
    let html = '<div class="turn-log-header">Recent Turns</div>';
    for (const entry of recent) {
        const rolls = entry.rolls.map(r => "[" + r.join(",") + "]").join(" → ");
        const cat = entry.category || "?";
        const score = entry.score != null ? entry.score : "?";
        const color = playerColor(entry.player_index);
        html += `<div class="turn-log-entry" style="border-left: 3px solid ${color};">`;
        html += `<span class="turn-log-player" style="color: ${color};">${entry.player_name}</span> `;
        if (rolls) {
            html += `<span class="turn-log-rolls">${rolls} →</span> `;
        }
        html += `<span class="turn-log-score">${cat}: ${score}</span>`;
        html += `</div>`;
    }
    el.innerHTML = html;
}

function renderScorecard(s) {
    const tbody = document.getElementById("scorecard-body");
    tbody.innerHTML = "";

    const sc = s.scorecard;
    const potential = s.potential_scores || {};
    const flashCat = s.score_flash ? s.score_flash.category : null;
    const aiChoice = s.ai_score_choice;
    const kbIdx = s.kb_selected_index;

    // Upper section header
    addSectionRow(tbody, "UPPER SECTION");

    UPPER_CATS.forEach((cat, i) => {
        addCategoryRow(tbody, cat, i, sc, potential, flashCat, aiChoice, kbIdx, s);
    });

    // Upper totals
    addTotalRow(tbody, "Subtotal", sc.upper_total);
    addTotalRow(tbody, "Bonus (63+)", sc.upper_bonus);

    // Lower section header
    addSectionRow(tbody, "LOWER SECTION");

    LOWER_CATS.forEach((cat, i) => {
        addCategoryRow(tbody, cat, i + 6, sc, potential, flashCat, aiChoice, kbIdx, s);
    });

    // Grand total
    addTotalRow(tbody, "GRAND TOTAL", sc.grand_total, true);
}

function addSectionRow(tbody, text) {
    const tr = document.createElement("tr");
    tr.className = "section-header";
    tr.innerHTML = `<td colspan="2">${text}</td>`;
    tbody.appendChild(tr);
}

function addTotalRow(tbody, label, value, bold) {
    const tr = document.createElement("tr");
    tr.className = "total-row";
    tr.innerHTML = `<td>${label}</td><td>${bold ? "<strong>" + value + "</strong>" : value}</td>`;
    tbody.appendChild(tr);
}

function addCategoryRow(tbody, cat, idx, sc, potential, flashCat, aiChoice, kbIdx, s) {
    const tr = document.createElement("tr");
    tr.className = "category-row";

    const filled = cat in sc.scores;
    if (filled) tr.classList.add("filled");
    if (cat === flashCat) tr.classList.add("flash");
    if (cat === aiChoice) tr.classList.add("ai-choice");
    if (kbIdx === idx && !filled) tr.classList.add("selected");

    const nameTd = document.createElement("td");
    nameTd.textContent = cat;

    const scoreTd = document.createElement("td");
    if (filled) {
        scoreTd.textContent = sc.scores[cat];
        scoreTd.className = "score-filled";
    } else if (cat in potential) {
        const val = potential[cat];
        scoreTd.textContent = val;
        scoreTd.className = val > 0 ? "score-potential" : "score-zero";
    } else {
        scoreTd.textContent = "—";
        scoreTd.className = "score-zero";
    }

    tr.appendChild(nameTd);
    tr.appendChild(scoreTd);

    // Data attribute for event delegation (click/hover handled on tbody)
    if (!filled) {
        tr.dataset.category = cat;
    }

    tbody.appendChild(tr);
}

// ── Overlays ───────────────────────────────────────────────────────────────

function renderOverlays(s) {
    // Help
    toggle("overlay-help", s.showing_help);

    // History
    toggle("overlay-history", s.showing_history);

    // Replay
    toggle("overlay-replay", s.showing_replay);

    // Zero-confirm
    const confirmEl = document.getElementById("overlay-confirm");
    if (s.confirm_zero_category) {
        confirmEl.classList.remove("hidden");
        document.getElementById("confirm-text").textContent = `Score 0 in ${s.confirm_zero_category}?`;
    } else {
        confirmEl.classList.add("hidden");
    }

    // Turn transition
    const transEl = document.getElementById("overlay-transition");
    if (s.turn_transition && s.multiplayer) {
        transEl.classList.remove("hidden");
        const idx = s.current_player_index;
        const p = s.player_configs[idx];
        const suffix = p.is_human ? "" : ` (${capitalize(p.strategy)} AI)`;
        document.getElementById("transition-text").textContent = `${p.name}'s Turn!${suffix}`;
    } else {
        transEl.classList.add("hidden");
    }

    // Game over
    const goEl = document.getElementById("overlay-gameover");
    if (s.game_over) {
        goEl.classList.remove("hidden");
        renderGameOver(s);
    } else {
        goEl.classList.add("hidden");
    }
}

function renderGameOver(s) {
    const el = document.getElementById("gameover-content");
    let html = "";

    if (s.multiplayer) {
        const totals = s.all_scorecards.map(sc => sc.grand_total);
        const maxScore = Math.max(...totals);
        const winnerIdx = totals.indexOf(maxScore);
        const winnerName = s.player_configs[winnerIdx].name;

        html += `<p class="winner">${winnerName} wins!</p>`;
        html += "<table>";
        s.player_configs.forEach((p, i) => {
            const score = totals[i];
            const marker = i === winnerIdx ? " ★" : "";
            html += `<tr><td>${p.name}</td><td><strong>${score}</strong>${marker}</td></tr>`;
            if (p.is_human) {
                const pct = (score / OPTIMAL_EXPECTED * 100).toFixed(0);
                html += `<tr><td></td><td class="pct-optimal">${pct}% of optimal</td></tr>`;
            }
        });
        html += "</table>";
    } else {
        const score = s.scorecard.grand_total;
        html += `<p class="final-score">${score}</p>`;
        if (!s.has_any_ai) {
            const pct = (score / OPTIMAL_EXPECTED * 100).toFixed(0);
            html += `<p class="pct-optimal">${pct}% of optimal play (${OPTIMAL_EXPECTED} avg)</p>`;
        }
    }

    html += '<p style="margin-top: 16px; color: var(--text-dim);">Press R for replay</p>';
    el.innerHTML = html;
}

function toggle(id, show) {
    document.getElementById(id).classList.toggle("hidden", !show);
}

// ── Keyboard shortcuts ─────────────────────────────────────────────────────

document.addEventListener("keydown", (e) => {
    // Confirm zero dialog intercepts
    if (state && state.confirm_zero_category) {
        if (e.key === "y" || e.key === "Enter") { sendAction("confirm_zero_yes"); e.preventDefault(); }
        else if (e.key === "n" || e.key === "Escape") { sendAction("confirm_zero_no"); e.preventDefault(); }
        return;
    }

    switch (e.key) {
        case " ": sendAction("roll"); e.preventDefault(); break;
        case "1": case "2": case "3": case "4": case "5":
            sendAction("hold", { die_index: parseInt(e.key) - 1 }); break;
        case "Tab":
            e.preventDefault();
            sendAction("navigate_category", { direction: e.shiftKey ? -1 : 1 }); break;
        case "ArrowDown": sendAction("navigate_category", { direction: 1 }); e.preventDefault(); break;
        case "ArrowUp": sendAction("navigate_category", { direction: -1 }); e.preventDefault(); break;
        case "Enter": {
            if (state && state.kb_selected_index !== null) {
                const cat = CATEGORY_ORDER[state.kb_selected_index];
                sendAction("score", { category: cat });
            }
            break;
        }
        case "Escape": {
            if (state && (state.showing_help || state.showing_history || state.showing_replay)) {
                if (state.showing_help) sendAction("toggle_help");
                else if (state.showing_replay) sendAction("toggle_replay");
                else if (state.showing_history) sendAction("toggle_history");
            }
            break;
        }
        case "?": case "F1": sendAction("toggle_help"); break;
        case "h": case "H": sendAction("toggle_history"); break;
        case "r": case "R":
            if (state && state.game_over) sendAction("toggle_replay");
            break;
        case "d": case "D": sendAction("toggle_dark_mode"); break;
        case "c": case "C": sendAction("toggle_colorblind"); break;
        case "s": case "S": sendAction("toggle_sound"); break;
        case "+": case "=": sendAction("speed_up"); break;
        case "-": sendAction("speed_down"); break;
        case "z": case "Z":
            if (e.ctrlKey || e.metaKey) { sendAction("undo"); e.preventDefault(); }
            break;
        case "n": case "N":
            if (state && state.game_over) sendAction("reset");
            break;
        case "p": case "P":
            if (state && state.showing_history) sendAction("cycle_player_filter");
            break;
        case "m": case "M":
            if (state && state.showing_history) sendAction("cycle_mode_filter");
            break;
    }
});

// ── Helpers ─────────────────────────────────────────────────────────────────

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

const PLAYER_COLORS = ["#4682b4", "#b45050", "#50a050", "#a07832"];
function playerColor(i) { return PLAYER_COLORS[i % PLAYER_COLORS.length]; }

// ── Web Audio (simple tones) ───────────────────────────────────────────────

let audioCtx = null;

function ensureAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function playTone(freq, duration, volume) {
    ensureAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.frequency.value = freq;
    gain.gain.value = volume || 0.1;
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.stop(audioCtx.currentTime + duration);
}

// ── Event delegation (persistent handlers on containers) ───────────────────
// Why: renderDice/renderScorecard rebuild the DOM every frame (~30 FPS).
// Attaching click handlers to individual elements doesn't work because
// the element can be destroyed between mousedown and mouseup. Event
// delegation on the stable parent containers avoids this.

// Use mousedown (not click) because click requires mousedown+mouseup on the
// same element, but the DOM is rebuilt between frames so the mousedown target
// may be gone by the time mouseup fires, silently dropping the click.
document.getElementById("dice-container").addEventListener("mousedown", (e) => {
    const dieEl = e.target.closest(".die");
    if (!dieEl || !state) return;
    const idx = parseInt(dieEl.dataset.dieIndex);
    if (isNaN(idx)) return;
    if (state.is_human_turn && !state.is_rolling && !state.game_over && state.rolls_used > 0) {
        sendAction("hold", { die_index: idx });
    }
});

document.getElementById("scorecard-body").addEventListener("mousedown", (e) => {
    const tr = e.target.closest("tr[data-category]");
    if (!tr || !state) return;
    const cat = tr.dataset.category;
    if (state.is_human_turn && !state.game_over && !state.is_rolling && state.rolls_used > 0) {
        sendAction("score", { category: cat });
    }
});

document.getElementById("scorecard-body").addEventListener("mouseenter", (e) => {
    const tr = e.target.closest("tr[data-category]");
    if (tr) sendAction("hover", { category: tr.dataset.category });
}, true);  // useCapture for mouseenter delegation

document.getElementById("scorecard-body").addEventListener("mouseleave", (e) => {
    const tr = e.target.closest("tr[data-category]");
    if (tr) sendAction("clear_hover");
}, true);

// ── Start ──────────────────────────────────────────────────────────────────

connect();
