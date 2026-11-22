# Tiny Chess — make.fun bounty entry (tiny-chess-01)

A chess engine in **4,076 bytes of Python** (`main.py`), built for the
[make.fun tiny-chess-01 bounty](https://make.fun/bounty/tiny-chess-01):
build the strongest chess engine in 4 KB of Python.

## Engine

- 0x88 board, negamax alpha-beta with iterative deepening
- Quiescence search (captures/promotions; all evasions when in check)
- Transposition table, killer moves, history heuristic, MVV-LVA ordering
- Null-move pruning, late-move reductions, principal-variation search
- Evaluation: material + piece-square tables + bishop pair + passed pawns,
  tapered king safety (middlegame/endgame)
- Fixed 30,000-node budget per move — deterministic, no clock, no randomness
  (seeded Zobrist), stdlib only. Depth 5 completes in the opening at this
  budget; ~1.9 s/move on an idle core, well inside the 10 s/move limit.
- `main.py` is an LZMA + base85 packed payload with a one-line unpacker
  (packing is allowed by the rules; payload + unpacker count toward 4,096)

## Measured strength (local kit gauntlet, trial 0)

Packed `main.py` at 30k nodes: **3 wins / 2 draws / 1 loss, Elo 1279** —
wins vs depth-2 and depth-4 (both by checkmate), draws vs depth-3 and
nodes-500k, loss vs nodes-100k. No time losses (max move 4.1 s), no illegal
moves, trial wall 445 s. Practice entry bar is Elo 1154.

Dev builds scored Elo 1191 at both 30k and 50k nodes, so the lower budget
costs no measured strength while removing timeout risk: at 50k/40k the same
engine lost games on time only when the shared dev VM was running parallel
Solidity compilations (load average 6–10 on a 1.5-CPU VM).

## Interface

`main.py` talks to the environment at `MAKEFUN_ENV_URL`:
`POST /game {}`, `/move {"game": n, "move": "<uci>"}`, `/resign`.
It reads the position (`fen`, `legal_moves`, `start_fen`, `moves`) from the
environment and replies with a UCI move (castling = king move, e.g. `e1g1`).

## Tests

- Perft: all 6 standard positions to depth 3 (startpos, Kiwipete, pos3–6)
- Eval sanity: startpos 0; hash roundtrip make/unmake
- Mate-in-1 (Qxf7#) found instantly; best move from startpos `b1c3`
