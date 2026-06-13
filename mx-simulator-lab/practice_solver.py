#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실습 채점 솔버 — 임의 시나리오의 정산 정답을 계산.

검증 기준: 원본 시트 `중도해지_선납+단품+결합할인` (CE 에어컨)
  · 20회차(제품판정일 2028 패턴, 16일) 전체할인 → 위약금 1,899,560 등과 100% 일치.

쓰는 법:
  python3 practice_solver.py            # 검증 + 예제(37개월차 등) 출력
  - solve_termination(month=37, discounts={"선납금","선납할인","결합"}) 처럼 호출
"""
import math
from datetime import date
from calendar import monthrange

# ── 엑셀 반올림 ──
def rdown(x, n):   # ROUNDDOWN(x, n)  n=-2 → 100단위
    f = 10 ** (-n)
    return math.floor(x / f) * f
def rup(x, n):     # ROUNDUP
    f = 10 ** (-n)
    return math.ceil(x / f) * f

# ── 공통 입력 (CE 에어컨) ──
C7  = 72                 # 구독기간(개월)
C8  = 2191               # 구독기간(일) — 비율 분모
C14 = 11_757_600         # 총구독료(v-)
C16 = 12_933_360         # 총구독료(v+)
START = date(2025, 9, 12)   # 1회차 구독개시
# 할인 '최종' 금액 (시트 6단계 산출값, 검증됨)
FINAL = {
    "선납금_Vminus": 3_528_000,   # C22
    "선납금_Vplus":  3_880_800,   # C26
    "선납할인":      475_200,     # C31 (V-)
    "단품":          590_400,     # C41 (V-)
    "결합":          540_000,     # C51 (V-)
}
REG = 100_000            # 등록비(v+ 포함 기준, /1.1)

# ── 달력 ──
def calendar():
    """회차별 (시작G, 종료H, 경과일days) 리스트. 1회차는 09-12~09-30 부분월."""
    cal = []
    g = START
    h = date(2025, 9, 30)
    cal.append((g, h, (h - g).days + 1))      # 1회차 = 19
    for k in range(2, C7 + 1):
        g = date(h.year + (h.month // 12), (h.month % 12) + 1, 1)
        h = date(g.year, g.month, monthrange(g.year, g.month)[1])
        cal.append((g, h, (h - g).days + 1))
    return cal

CAL = calendar()

def reflected_monthly(discounts):
    """선택 할인 반영 월구독료(v-) = (C14 − 선납금/1.1 − Σ활성할인)/C7"""
    base = C14
    if "선납금" in discounts:  base -= FINAL["선납금_Vplus"] / 1.1   # = 3,528,000
    for d in ("선납할인", "단품", "결합"):
        if d in discounts: base -= FINAL[d]
    return round(base / C7)

# ── 중도해지 정산 ──
def solve_termination(month, day_in_month=16, discounts=("선납금", "선납할인", "단품", "결합")):
    """month 회차 중, 시작일+day_in_month 일에 해지(제품판정일). 사용=판정일 전날까지."""
    discounts = set(discounts)
    g, h, _ = CAL[month - 1]
    last_days = day_in_month                      # W = 제품판정일 − G
    sumW = sum(d for (_, _, d) in CAL[:month - 1]) + last_days
    remain = (C8 - sumW) / C8                      # 잔여비율
    elapsed = sumW / C8                            # 경과비율
    R = reflected_monthly(discounts)               # 반영 월구독료

    위약금 = rdown(C16 * remain * 0.20, -1)
    사용분 = rdown(R * last_days / monthrange(h.year, h.month)[1], -2)
    할인회수 = 0
    for d in ("선납할인", "단품", "결합"):
        if d in discounts:
            할인회수 += rdown(FINAL[d] * elapsed, -2)
    선납환불 = -rup(FINAL["선납금_Vminus"] * remain, -2) if "선납금" in discounts else 0
    등록비 = rdown(REG / 1.1 * elapsed, -2)
    net = 위약금 + 사용분 + 할인회수 + 선납환불 + 등록비
    return dict(month=month, sumW=sumW, remain=remain, R=R,
                위약금=위약금, 사용분=사용분, 할인회수=할인회수,
                선납환불=선납환불, 등록비=등록비, 고객순부담=net)

def fmt(v): return f"{v:,.0f}"

def report(r, title):
    print(f"\n── {title} ──")
    print(f"  Σ경과일={r['sumW']}일  잔여비율={1-r['remain']+r['remain']:.0%}→경과{r['sumW']}/{C8}  반영월구독료={fmt(r['R'])}")
    print(f"  ① 위약금        {fmt(r['위약금']):>12}  (고객→회사)")
    print(f"  ② 사용분 청구   {fmt(r['사용분']):>12}  (고객→회사)")
    print(f"  ③ 할인금 회수   {fmt(r['할인회수']):>12}  (고객→회사)")
    print(f"  ④ 선납잔액 환불 {fmt(r['선납환불']):>12}  (회사→고객)")
    print(f"  ⑤ 등록비 청구   {fmt(r['등록비']):>12}  (고객→회사)")
    print(f"  ─────────────────────────────")
    print(f"  ＝ 고객 순부담  {fmt(r['고객순부담']):>12}")


if __name__ == "__main__":
    print("=" * 60)
    print(" 실습 솔버 검증 — 원본 중도해지 시트 대조")
    print("=" * 60)
    base = solve_termination(20, 16, ("선납금", "선납할인", "단품", "결합"))
    ok = (base["위약금"] == 1_899_560 and base["사용분"] == 49_000
          and base["할인회수"] == 426_400 and base["선납환불"] == -2_590_900
          and base["등록비"] == 24_100 and base["R"] == 92_000)
    report(base, "검증: 20회차 전체할인 (원본과 대조)")
    print(f"\n  원본값: 위약금1,899,560 / 사용분49,000 / 할인회수426,400 / 선납환불-2,590,900 / 등록비24,100")
    print(f"  => {'✅ 100% 일치' if ok else '❌ 불일치'}")

    print("\n" + "=" * 60)
    print(" 예제 시나리오 (실습 정답)")
    print("=" * 60)
    # 사용자 예: 선납할인 + 다품목(결합), 37개월차 중도해지
    r37 = solve_termination(37, 16, ("선납금", "선납할인", "결합"))
    report(r37, "예: 선납할인+다품목(결합), 37회차 해지")
    report(solve_termination(12, 16, ("선납금", "선납할인", "단품", "결합")), "12회차 전체할인")
    report(solve_termination(60, 16, ("선납금", "선납할인", "단품", "결합")), "60회차 전체할인")
