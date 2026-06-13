"""
MX 구독료 시뮬레이터 — 정답지(Reference Implementation)
======================================================

원본 컨설팅펌 시트 '정상만기_선납+단품+결합(MX)' 를 100% 재현한 검증용 코드.
손으로 엑셀을 만든 뒤, 이 스크립트 결과와 비교해 검증하는 용도.

실행:  python3 answer_key.py
(맥북/어느 PC에서나 추가 설치 없이 표준 라이브러리만으로 동작)
"""
import math, datetime, calendar

# ── 엑셀 반올림 함수 재현 ──────────────────────────────
def roundup(x, n=-2):   # ROUNDUP(x,-2): 100원 단위 올림
    f = 10 ** (-n); return int(math.ceil(x / f - 1e-9) * f)
def rnd(x, n=-2):       # ROUND(x,-2): 100원 단위 반올림
    f = 10 ** (-n); return int(round(x / f) * f)
def rounddown(x, n=-2): # ROUNDDOWN(x,-2): 100원 단위 내림
    f = 10 ** (-n); return int(math.floor(x / f + 1e-9) * f)


def simulate(
    months=48,           # 구독기간(개월)
    total_v_minus=2011200,  # 총구독료(v-)  = 공급가 총액
    damage=115200,       # 파손보험(비과세)  ★MX 전용
    warranty=96000,      # 보증연장(v-)
    care=0,              # 케어서비스(v-)
    prepay_pct=0.30,     # 선납금 비율
    r_prepay_disc=0.04,  # 선납할인율
    r_unit=0.05,         # 단품할인율
    r_combo=0.05,        # 결합할인율
    start=datetime.date(2025, 9, 12),  # 계약 시작일
):
    m = months
    # ── 1) 기본 구독료 ─────────────────────────────────
    product = total_v_minus - damage - warranty - care      # C15 제품 매출인식 기준(v-)
    month_v_minus = total_v_minus / m                       # C17 월구독료(v-)
    # ★MX 핵심: 파손보험은 비과세 → 과세분(제품+보증+케어)만 ×1.1, 파손은 그대로
    total_v_plus = (product + warranty + care) * 1.1 + damage  # C18 총구독료(v+)
    month_v_plus = total_v_plus / m                         # C19 월구독료(v+)
    disc_base = total_v_plus - damage                       # C20 할인기준(파손 제외 v+)

    # ── 2) 선납금 (할인 아님, 미리 낸 돈) ───────────────
    C23 = total_v_plus * prepay_pct          # 선납금(v+)
    C25 = rnd((C23 / 1.1) / m)               # 월 선납금(v-) — ROUND
    prepay_v_minus = C25 * m                 # C26 최종 선납금(v-)
    C30 = total_v_plus - (month_v_plus - C25 * 1.1) * m   # 최종 선납금(v+)

    # ── 3) 할인 6단계 패턴 (선납할인/단품/결합 공통) ─────
    def discount(rate):
        c_vplus = total_v_plus * rate        # ① 할인금(v+) = 총구독료(v+) × 율
        c_vminus = c_vplus / 1.1             # ② v- 환산
        month_d = roundup(c_vminus / m)      # ③ 월할인금(v-) — ROUNDUP
        total_d = month_d * m                # ⑤ 최종 할인금(v-)
        total_d_vplus = (month_d * 1.1) * m  # ⑤' 최종 할인금(v+)
        return month_d, total_d, total_d_vplus

    pd_m, pd_t, pd_tp = discount(r_prepay_disc)   # 선납할인
    ud_m, ud_t, ud_tp = discount(r_unit)          # 단품
    cd_m, cd_t, cd_tp = discount(r_combo)          # 결합

    # ── 4) 전체 합산 월 구독료 ─────────────────────────
    final_month_v_minus = (total_v_minus - C30 / 1.1 - ud_t - pd_t - cd_t) / m   # C61
    final_month_v_plus  = (total_v_plus  - C30 - pd_tp - ud_tp - cd_tp) / m      # C63

    # ── 5) 회차별 청구 테이블 (49회차 = 계약월수 + 1) ───
    periods = []
    g = start
    for i in range(m + 1):              # 막달(remainder) 포함 → m+1 회차
        h = datetime.date(g.year, g.month, calendar.monthrange(g.year, g.month)[1])
        periods.append((i + 1, g, h))
        g = datetime.date(g.year + (g.month == 12), (g.month % 12) + 1, 1)

    table = []
    first_J = None
    for n, g, h in periods:
        days = (h - g).days + 1
        dim = calendar.monthrange(h.year, h.month)[1]
        if n == 1:                              # 1회차: 일할
            J = rounddown((total_v_minus / m) * days / dim)
            L = rounddown((care / m) * days / dim)
            M = rounddown((warranty / m) * days / dim)
            N = rounddown((damage / m) * days / dim)
            first_J = J
        elif n == m + 1:                        # 막달(49회차): 월구독료 − 1회차
            J = month_v_minus - first_J
            L = care / m; M = warranty / m; N = damage / m
        else:                                   # 2~48회차: 풀
            J = month_v_minus; L = care / m; M = warranty / m; N = damage / m
        K = J - L - M - N                        # 제품 = 구독료 − 케어 − 보증 − 파손
        O = (K + L + M) * 1.1 + N                # 월청구(v+): 과세분만 ×1.1 + 파손
        table.append((n, g, h, days, dim, J, K, L, M, N, O))

    return dict(product=product, month_v_minus=month_v_minus,
                total_v_plus=total_v_plus, month_v_plus=month_v_plus,
                disc_base=disc_base, prepay_v_minus=prepay_v_minus, C30=C30,
                pd_m=pd_m, pd_t=pd_t, ud_m=ud_m, ud_t=ud_t, cd_m=cd_m, cd_t=cd_t,
                final_month_v_minus=final_month_v_minus,
                final_month_v_plus=final_month_v_plus, table=table)


if __name__ == "__main__":
    r = simulate()
    print("=" * 60)
    print("MX 정상만기 시뮬레이터 — 정답지")
    print("=" * 60)
    print(f"제품 매출인식 기준(v-)      C15 = {r['product']:>12,.0f}")
    print(f"월구독료(v-)                C17 = {r['month_v_minus']:>12,.0f}")
    print(f"총구독료(v+) ★파손비과세    C18 = {r['total_v_plus']:>12,.0f}")
    print(f"월구독료(v+)                C19 = {r['month_v_plus']:>12,.0f}")
    print(f"할인기준(파손제외 v+)       C20 = {r['disc_base']:>12,.0f}")
    print(f"최종 선납금(v-)             C26 = {r['prepay_v_minus']:>12,.0f}")
    print(f"최종 선납금(v+)             C30 = {r['C30']:>12,.0f}")
    print(f"선납할인 월/총(v-)              = {r['pd_m']:>6,.0f} / {r['pd_t']:>9,.0f}")
    print(f"단품할인 월/총(v-)              = {r['ud_m']:>6,.0f} / {r['ud_t']:>9,.0f}")
    print(f"결합할인 월/총(v-)              = {r['cd_m']:>6,.0f} / {r['cd_t']:>9,.0f}")
    print(f"전체할인 반영 월구독료(v-)  C61 = {r['final_month_v_minus']:>12,.0f}")
    print(f"전체할인 반영 월구독료(v+)  C63 = {r['final_month_v_plus']:>12,.0f}")
    print("-" * 60)
    print("회차 | 시작        종료       | 일수  |   J구독료 |  K제품 | M보증 | N파손 | O월청구(v+)")
    tbl = r["table"]
    for row in tbl[:4] + [tbl[-1]]:
        n, g, h, days, dim, J, K, L, M, N, O = row
        print(f"{n:>3} | {g} {h} | {days:>2}/{dim} | {J:>9,.0f} | {K:>6,.0f} | {M:>5,.0f} | {N:>5,.0f} | {O:>9,.0f}")
    total_J = sum(row[5] for row in tbl)
    print("-" * 60)
    print(f"J열 합계 = {total_J:,.0f}   (총구독료 v- {2011200:,} 와 일치해야 함)")
