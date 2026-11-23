# Tiny chess engine v1 (readable dev version; will be minified to main.py)
import os, sys, json, random, urllib.request

MATE = 100000
VAL = [0, 100, 320, 330, 500, 900, 0]
KN = [-33, -31, -18, -14, 14, 18, 31, 33]
KI = [-17, -16, -15, -1, 1, 15, 16, 17]
BD = [-17, -15, 15, 17]
RD = [-16, -1, 1, 16]
_rng = random.Random(20261123)
Z = [_rng.randrange(1 << 64) for _ in range(12 * 128 + 1 + 16 + 8)]
ZSIDE = 12 * 128
ZCR = 12 * 128 + 1
ZEP = 12 * 128 + 1 + 16

def zidx(pc, sq):
    return (pc - 1 if pc > 0 else 6 + (-pc - 1)) * 128 + sq

B = [0] * 128
S = 1
CR = 0
EP = -1
KP = [4, 116]
ZH = 0
H = []
HC = {}
N = [0]
LIM = [50000]
TT = {}
KL = [[0, 0] for _ in range(128)]
HI = [0] * (12 * 128)
PVS = [1]
DEP = [0]
NPM = [0]  # non-pawn, non-king material on board

class AB(Exception):
    pass

def uci_sq(s):
    return (ord(s[0]) - 97) + (int(s[1]) - 1) * 16

def sq_uci(s):
    return chr(97 + (s & 7)) + str((s >> 4) + 1)

def uci_m(m):
    s = sq_uci(m & 127) + sq_uci((m >> 7) & 127)
    p = (m >> 14) & 7
    return s + ('nbrq'[p - 2] if p else '')

def parse_uci(u):
    f = uci_sq(u[:2]); t = uci_sq(u[2:4])
    p = 'nbrq'.index(u[4]) + 2 if len(u) == 5 else 0
    return f | (t << 7) | (p << 14)

def zob():
    h = 0
    for i in range(128):
        if i & 0x88:
            continue
        pc = B[i]
        if pc:
            h ^= Z[zidx(pc, i)]
    if S < 0:
        h ^= Z[ZSIDE]
    h ^= Z[ZCR + CR]
    if EP >= 0:
        h ^= Z[ZEP + (EP & 7)]
    return h

def parse_fen(fen):
    global S, CR, EP, ZH
    parts = fen.split()
    for i in range(128):
        B[i] = 0
    NPM[0] = 0
    for r, row in enumerate(parts[0].split('/')):
        f = 0
        rr = 7 - r
        for c in row:
            if c.isdigit():
                f += int(c)
            else:
                pc = 'pnbrqk'.index(c.lower()) + 1
                B[rr * 16 + f] = pc if c.isupper() else -pc
                if pc not in (1, 6):
                    NPM[0] += VAL[pc]
                f += 1
    S = 1 if parts[1] == 'w' else -1
    CR = 0
    if len(parts) > 2:
        for c in parts[2]:
            if c == 'K': CR |= 1
            elif c == 'Q': CR |= 2
            elif c == 'k': CR |= 4
            elif c == 'q': CR |= 8
    EP = uci_sq(parts[3]) if len(parts) > 3 and parts[3] != '-' else -1
    KP[0] = B.index(6); KP[1] = B.index(-6)
    ZH = zob()

def attacked(sq, by):
    if by > 0:
        t = sq - 15
        if not t & 0x88 and B[t] == 1: return True
        t = sq - 17
        if not t & 0x88 and B[t] == 1: return True
    else:
        t = sq + 15
        if not t & 0x88 and B[t] == -1: return True
        t = sq + 17
        if not t & 0x88 and B[t] == -1: return True
    for d in KN:
        t = sq + d
        if not t & 0x88 and B[t] == 2 * by:
            return True
    for d in KI:
        t = sq + d
        if not t & 0x88 and B[t] == 6 * by:
            return True
    for d in BD:
        t = sq + d
        while not t & 0x88:
            pc = B[t]
            if pc:
                if pc == 3 * by or pc == 5 * by:
                    return True
                break
            t += d
    for d in RD:
        t = sq + d
        while not t & 0x88:
            pc = B[t]
            if pc:
                if pc == 4 * by or pc == 5 * by:
                    return True
                break
            t += d
    return False

def in_check():
    return attacked(KP[0] if S > 0 else KP[1], -S)

def gen(caps=False):
    ms = []
    for sq in range(128):
        if sq & 0x88:
            continue
        pc = B[sq]
        if pc == 0 or (pc > 0) != (S > 0):
            continue
        t = abs(pc)
        if t == 1:
            d = 16 if S > 0 else -16
            last = 7 if S > 0 else 0
            r = sq >> 4
            one = sq + d
            if not caps and B[one] == 0:
                if (one >> 4) == last:
                    for p in (5, 4, 3, 2):
                        ms.append(sq | (one << 7) | (p << 14))
                else:
                    ms.append(sq | (one << 7))
                    if r == (1 if S > 0 else 6) and B[one + d] == 0:
                        ms.append(sq | ((one + d) << 7))
            for dd in (d - 1, d + 1):
                tt = sq + dd
                if tt & 0x88:
                    continue
                if B[tt] != 0 and (B[tt] > 0) != (S > 0):
                    if (tt >> 4) == last:
                        for p in (5, 4, 3, 2):
                            ms.append(sq | (tt << 7) | (p << 14))
                    else:
                        ms.append(sq | (tt << 7))
                elif tt == EP:
                    ms.append(sq | (tt << 7))
        elif t == 2 or t == 6:
            for d in (KN if t == 2 else KI):
                tt = sq + d
                if tt & 0x88:
                    continue
                if B[tt] == 0:
                    if not caps:
                        ms.append(sq | (tt << 7))
                elif (B[tt] > 0) != (S > 0):
                    ms.append(sq | (tt << 7))
        else:
            for d in (BD if t == 3 else RD if t == 4 else KI):
                tt = sq + d
                while not tt & 0x88:
                    if B[tt] == 0:
                        if not caps:
                            ms.append(sq | (tt << 7))
                    else:
                        if (B[tt] > 0) != (S > 0):
                            ms.append(sq | (tt << 7))
                        break
                    tt += d
    if not caps:
        k = KP[0] if S > 0 else KP[1]
        if S > 0:
            if CR & 1 and B[5] == 0 and B[6] == 0 and B[7] == 4 and not attacked(4, -1) and not attacked(5, -1) and not attacked(6, -1):
                ms.append(4 | (6 << 7))
            if CR & 2 and B[3] == 0 and B[2] == 0 and B[1] == 0 and B[0] == 4 and not attacked(4, -1) and not attacked(3, -1) and not attacked(2, -1):
                ms.append(4 | (2 << 7))
        else:
            if CR & 4 and B[117] == 0 and B[118] == 0 and B[119] == -4 and not attacked(116, 1) and not attacked(117, 1) and not attacked(118, 1):
                ms.append(116 | (118 << 7))
            if CR & 8 and B[115] == 0 and B[114] == 0 and B[113] == 0 and B[112] == -4 and not attacked(116, 1) and not attacked(115, 1) and not attacked(114, 1):
                ms.append(116 | (114 << 7))
    return ms

def make(m):
    global S, CR, EP, ZH
    f = m & 127; t = (m >> 7) & 127; p = (m >> 14) & 7
    pc = B[f]
    cap = B[t]; csq = t
    if not cap and abs(pc) == 1 and t == EP and (t & 7) != (f & 7):
        csq = t - 16 if S > 0 else t + 16
        cap = B[csq]
    u = (m, cap, csq, CR, EP, ZH, KP[0], KP[1])
    if S < 0:
        ZH ^= Z[ZSIDE]
    ZH ^= Z[ZCR + CR]
    if EP >= 0:
        ZH ^= Z[ZEP + (EP & 7)]
    ZH ^= Z[zidx(pc, f)]
    if cap:
        ZH ^= Z[zidx(cap, csq)]
        B[csq] = 0
        if abs(cap) != 1:
            NPM[0] -= VAL[abs(cap)]
    B[f] = 0
    if p:
        npc = p if S > 0 else -p
        B[t] = npc
        ZH ^= Z[zidx(npc, t)]
        NPM[0] += VAL[p] - 100
    else:
        B[t] = pc
        ZH ^= Z[zidx(pc, t)]
    if abs(pc) == 6:
        KP[0 if S > 0 else 1] = t
        if t - f == 2:
            rk = B[t + 1]
            B[t - 1] = rk; B[t + 1] = 0
            ZH ^= Z[zidx(rk, t + 1)] ^ Z[zidx(rk, t - 1)]
        elif f - t == 2:
            rk = B[t - 2]
            B[t + 1] = rk; B[t - 2] = 0
            ZH ^= Z[zidx(rk, t - 2)] ^ Z[zidx(rk, t + 1)]
    if f == 0 or t == 0: CR &= ~2
    if f == 7 or t == 7: CR &= ~1
    if f == 112 or t == 112: CR &= ~8
    if f == 119 or t == 119: CR &= ~4
    if abs(pc) == 6:
        CR &= ~(3 if S > 0 else 12)
    EP = f + 16 if abs(pc) == 1 and t - f == 32 else f - 16 if abs(pc) == 1 and f - t == 32 else -1
    S = -S
    if S < 0:
        ZH ^= Z[ZSIDE]
    ZH ^= Z[ZCR + CR]
    if EP >= 0:
        ZH ^= Z[ZEP + (EP & 7)]
    if attacked(KP[0] if S < 0 else KP[1], S):
        unmake(u)
        return None
    return u

def unmake(u):
    global S, CR, EP, ZH
    m, cap, csq, cro, epo, zho, kw, kb = u
    f = m & 127; t = (m >> 7) & 127; p = (m >> 14) & 7
    S = -S
    moved = B[t]
    if p:
        B[f] = 1 if S > 0 else -1
        NPM[0] -= VAL[p] - 100
    else:
        B[f] = moved
        if abs(moved) == 6:
            if t - f == 2:
                B[t + 1] = B[t - 1]; B[t - 1] = 0
            elif f - t == 2:
                B[t - 2] = B[t + 1]; B[t + 1] = 0
    if cap:
        B[csq] = cap
        if csq == t:
            pass
        else:
            B[t] = 0
        if abs(cap) != 1:
            NPM[0] += VAL[abs(cap)]
    else:
        B[t] = 0
    KP[0] = kw; KP[1] = kb
    CR = cro; EP = epo; ZH = zho

def evaluate():
    score = 0
    nonpawn = 0
    bishops = [0, 0]
    wmin = [8] * 10
    bmax = [-1] * 10
    king = [0, 0]
    pawns = []
    for sq in range(128):
        if sq & 0x88:
            continue
        pc = B[sq]
        if not pc:
            continue
        t = abs(pc)
        r = sq >> 4; fl = sq & 7
        rel = r * 8 + fl if pc > 0 else (7 - r) * 8 + fl
        rr = rel >> 3; ff = rel & 7
        c = min(ff, 7 - ff) + min(rr, 7 - rr)
        if t == 6:
            king[0 if pc > 0 else 1] = rel
            continue
        if t == 1:
            pawns.append((sq, pc))
            v = 100 + [0, 0, 4, 8, 14, 24, 40, 0][rr] + ([0, 0, 0, 10, 15, 10, 5, 0][rr] if ff in (3, 4) else 0)
            if pc > 0:
                if rr < wmin[fl + 1]: wmin[fl + 1] = rr
            else:
                if r > bmax[fl + 1]: bmax[fl + 1] = r
        elif t == 2:
            v = 320 + 6 * c - 20
        elif t == 3:
            v = 330 + 4 * c - 8
        elif t == 4:
            v = 500 + (15 if rr == 6 else 0) + (5 if rr == 0 and ff in (3, 4) else 0)
        else:
            v = 900 + 2 * c - 6
        score += v if pc > 0 else -v
        if t != 1:
            nonpawn += VAL[t]
        if t == 3:
            bishops[0 if pc > 0 else 1] += 1
    phase = min(nonpawn, 7800)
    for col in (0, 1):
        rel = king[col]
        rr = rel >> 3; ff = rel & 7
        mg = [20, 25, 10, 0, 0, 10, 25, 20][ff] if rr == 0 else max(-50, -15 * rr)
        eg = 8 * (min(ff, 7 - ff) + min(rr, 7 - rr)) - 24
        kv = (mg * phase + eg * (7800 - phase)) // 7800
        score += kv if col == 0 else -kv
    if bishops[0] >= 2: score += 30
    if bishops[1] >= 2: score -= 30
    for sq, pc in pawns:
        r = sq >> 4; fl = sq & 7
        if pc > 0:
            if bmax[fl] < r and bmax[fl + 1] < r and bmax[fl + 2] < r:
                score += [0, 5, 10, 18, 30, 45, 65, 0][r]
        else:
            if wmin[fl] > r and wmin[fl + 1] > r and wmin[fl + 2] > r:
                score -= [0, 5, 10, 18, 30, 45, 65, 0][7 - r]
    return score if S > 0 else -score

def order(ms, ply, ttmove=0):
    def sc(m):
        t = (m >> 7) & 127
        v = B[t]
        s = 0
        if v:
            s = 100000 + 10 * VAL[abs(v)] - VAL[abs(B[m & 127])]
        if (m >> 14) & 7:
            s += 200000 + VAL[(m >> 14) & 7]
        elif not v:
            if m == KL[ply][0]:
                s = 50000
            elif m == KL[ply][1]:
                s = 40000
            else:
                pc = B[m & 127]
                s = min(HI[(pc - 1 if pc > 0 else 6 + (-pc - 1)) * 128 + t], 30000)
        if m == ttmove:
            s = 1000000
        return -s
    ms.sort(key=sc)
    return ms

def qs(a, b, ply):
    N[0] += 1
    if N[0] > LIM[0]:
        raise AB()
    if ply > 100:
        return evaluate()
    chk = in_check()
    if not chk:
        st = evaluate()
        if st >= b:
            return st
        best = st
        if st > a:
            a = st
    else:
        best = -MATE - 1
    ms = gen(caps=not chk)
    order(ms, ply)
    legal = 0
    for m in ms:
        f0 = m & 127; t0 = (m >> 7) & 127
        if not chk and not ((m >> 14) & 7):
            vv = VAL[abs(B[t0])] if B[t0] else (100 if abs(B[f0]) == 1 and t0 == EP and (t0 & 7) != (f0 & 7) else 0)
            if st + vv + 200 < a:
                continue
        u = make(m)
        if u is None:
            continue
        legal += 1
        H.append(ZH); HC[ZH] = HC.get(ZH, 0) + 1
        s = -qs(-b, -a, ply + 1)
        H.pop(); HC[ZH] = HC.get(ZH, 0) - 1
        unmake(u)
        if s > best:
            best = s
        if s > a:
            a = s
        if a >= b:
            break
    if chk and legal == 0:
        return -MATE + ply
    return best

def search(d, a, b, ply):
    global S, EP, ZH
    if ply > 0 and HC.get(ZH, 0) > 1:
        return 0
    if d <= 0:
        return qs(a, b, ply)
    N[0] += 1
    if N[0] > LIM[0]:
        raise AB()
    e = TT.get(ZH)
    ttmove = 0
    if e:
        s = e[1]
        if s > MATE - 200: s -= ply
        elif s < -MATE + 200: s += ply
        if e[0] >= d and (e[3] == 1 or (e[3] == 2 and s >= b) or (e[3] == 3 and s <= a)):
            return s
        ttmove = e[2]
    a0 = a
    chk = in_check()
    if d >= 3 and not chk and NPM[0] > 0:
        st = evaluate()
        if st >= b:
            # null move
            oS = S; oEP = EP; oZH = ZH
            if S < 0:
                ZH ^= Z[ZSIDE]
            if EP >= 0:
                ZH ^= Z[ZEP + (EP & 7)]
            S = -S; EP = -1
            if S < 0:
                ZH ^= Z[ZSIDE]
            H.append(ZH); HC[ZH] = HC.get(ZH, 0) + 1
            ns = -search(d - 3, -b, -b + 1, ply + 1)
            H.pop(); HC[ZH] = HC.get(ZH, 0) - 1
            S = oS; EP = oEP; ZH = oZH
            if ns >= b:
                return b
    ms = gen()
    order(ms, ply, ttmove)
    best = -MATE - 1
    bestm = 0
    legal = 0
    for i, m in enumerate(ms):
        f0 = m & 127; t0 = (m >> 7) & 127
        iscap = B[t0] != 0 or (abs(B[f0]) == 1 and t0 == EP and (t0 & 7) != (f0 & 7))
        u = make(m)
        if u is None:
            continue
        legal += 1
        H.append(ZH); HC[ZH] = HC.get(ZH, 0) + 1
        if i == 0 or not PVS[0]:
            s = -search(d - 1, -b, -a, ply + 1)
        elif d >= 3 and i > 3 and not iscap and not ((m >> 14) & 7) and not chk:
            s = -search(d - 2, -a - 1, -a, ply + 1)
            if s > a:
                s = -search(d - 1, -b, -a, ply + 1)
        else:
            s = -search(d - 1, -a - 1, -a, ply + 1)
            if s > a and s < b:
                s = -search(d - 1, -b, -a, ply + 1)
        H.pop(); HC[ZH] = HC.get(ZH, 0) - 1
        unmake(u)
        if s > best:
            best = s; bestm = m
        if s > a:
            a = s
        if a >= b:
            if not iscap and not ((m >> 14) & 7):
                pc = B[f0]
                HI[(pc - 1 if pc > 0 else 6 + (-pc - 1)) * 128 + t0] += d * d
                KL[ply][1] = KL[ply][0]; KL[ply][0] = m
            break
    if legal == 0:
        return -MATE + ply if in_check() else 0
    if best <= a0:
        flag = 3
    elif best >= b:
        flag = 2
    else:
        flag = 1
    s = best
    if s > MATE - 200: s += ply
    elif s < -MATE + 200: s -= ply
    TT[ZH] = (d, s, bestm, flag)
    return best

def bestmove(legal_uci):
    if len(legal_uci) == 1:
        return legal_uci[0]
    rms = [parse_uci(u) for u in legal_uci]
    if not rms:
        return ''
    scores = [0] * len(rms)
    best = rms[0]
    N[0] = 0
    TT.clear()
    DEP[0] = 0
    for d in range(1, 17):
        sc = scores[:]
        bd = best
        try:
            order2 = sorted(range(len(rms)), key=lambda i: -sc[i])
            a = -MATE - 1
            for i in order2:
                m = rms[i]
                u = make(m)
                if u is None:
                    sc[i] = -MATE
                    continue
                H.append(ZH); HC[ZH] = HC.get(ZH, 0) + 1
                s = -search(d - 1, -MATE - 1, -a, 1)
                H.pop(); HC[ZH] = HC.get(ZH, 0) - 1
                unmake(u)
                sc[i] = s
                if s > a:
                    a = s; bd = m
            scores = sc; best = bd
            DEP[0] = d
            if a >= MATE - 200:
                break
        except AB:
            break
    return uci_m(best)


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(),
                                 headers={'content-type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

URL = os.environ.get('MAKEFUN_ENV_URL') or ''

def play():
    while True:
        g = post('/game', {})
        if g['status'] == 'done':
            print('done:', g, file=sys.stderr)
            break
        while g['status'] == 'your_move':
            parse_fen(g['start_fen'])
            H.clear(); HC.clear()
            H.append(ZH); HC[ZH] = 1
            for mv in g['moves']:
                u = make(parse_uci(mv))
                assert u is not None, mv
                H.append(ZH); HC[ZH] = HC.get(ZH, 0) + 1
            assert ZH == zob(), 'hash mismatch after replay'
            mv = bestmove(g['legal_moves'])
            if mv not in g['legal_moves']:
                mv = g['legal_moves'][0]
            g = post('/move', {'game': g['game'], 'move': mv})
        print(f"game {g['game']}: {g.get('outcome')} by {g.get('reason')}", file=sys.stderr)

if __name__ == '__main__':
    play()
