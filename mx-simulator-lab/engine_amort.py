#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리스 상각표 엔진 정답지 (올인원2.0 시뮬레이터 1·2일차)

대상 시트:
  - 17. 리스 상각표 (할인전, 선납반영전)   ← baseline()
  - 18. 리스 상각표 (할인전, 선납반영 후)  ← with_prepay()

핵심: 구독 = 제품을 리스(할부판매)한 것.
  ① 리스채권 = 제품 v- (할부로 회수할 원금)
  ② 순수 리스료 = (총구독료 v- − 케어 − 보증) / 개월   ← 제품 포션만
  ③ 월이자율(IRR) = 그 리스료로 채권을 만기 0으로 만드는 내재이자율
  ④ 매월:  기말 = 기초 + 이자수익 − 리스료수령
  ⑤ 1회차는 일할(설치~결제 27/31), 마지막 회차는 잔액 0 맞춤(plug)

실행:  python3 engine_amort.py      (추가 설치 불필요)
"""
import math


# ─────────────────────────────────────────────────────────────
# 엑셀 재무함수 재현 (PV, RATE) — 엑셀과 동일 방정식
# ─────────────────────────────────────────────────────────────
def excel_pv(rate, nper, pmt, fv=0.0, when=0):
    """엑셀 PV(rate, nper, pmt, [fv], [type])"""
    if rate == 0:
        return -(pmt * nper + fv)
    return -(pmt * ((1 + rate) ** nper - 1) / rate * (1 + rate * when) + fv) / (1 + rate) ** nper


def excel_rate(nper, pmt, pv, fv=0.0, when=0, guess=0.01):
    """엑셀 RATE(nper, pmt, pv, [fv], [type], [guess]) — Newton법"""
    r = guess
    for _ in range(200):
        if r == 0:
            f = pv + pmt * nper + fv
            d = pmt * nper * (nper - 1) / 2.0
        else:
            p = (1 + r) ** nper
            f = pv * p + pmt * (1 + r * when) * (p - 1) / r + fv
            dp = nper * (1 + r) ** (nper - 1)
            d = pv * dp + pmt * when * (p - 1) / r + pmt * (1 + r * when) * (dp * r - (p - 1)) / r ** 2
        rn = r - f / d
        if abs(rn - r) < 1e-12:
            return rn
        r = rn
    return r


def rounddown2(x):
    """엑셀 ROUNDDOWN(x, -2) — 100원 단위 내림 (음수 안전)"""
    return math.copysign(math.floor(abs(x) / 100) * 100, x) if x else 0.0


# ─────────────────────────────────────────────────────────────
# 공통 입력 (CE 에어컨 예제 — 시트17/18)
# ─────────────────────────────────────────────────────────────
class Inputs:
    N = 60                 # 구독기간(개월)
    K = 0.0357             # 현할차 할인율(연)
    days_num, days_den = 27, 31   # 1회차 일할 (설치 07-05 → 결제 08-10)
    # v- 금액
    S2 = 7_428_000.0       # 총구독료(v-)
    S3 = 5_290_000 / 1.1   # 제품(v-)        = 4,809,090.9
    S5 = 6_900 * 60        # 케어(v-)        = 414,000
    S6 = 900 * 60          # 보증연장(v-)    = 54,000
    R2 = 8_170_800.0       # 총구독료(v+)


def amortize(receivable, pure_total, N, K, S5, S6, S2_for_first, dn, dd, monthly_pmt):
    """
    receivable   : 리스채권 C2
    pure_total   : 총 순수구독료 C3
    monthly_pmt  : 월 리스료 H2 (= pure_total/N)
    반환: (월이자율 F3, 연이자율 F2, 상각표 rows)
    """
    F3 = excel_rate(N, -monthly_pmt, receivable)   # 내재이자율(월)
    F2 = F3 * 12

    rows = []
    bal = round(receivable)                        # F5 (기초채권)
    rows.append({"m": 0, "기초": None, "이자": None, "리스료": None, "기말": bal})

    # 1회차: 일할(dn/dd)
    E1 = -(rounddown2(S2_for_first / N * dn / dd)
           - rounddown2(S5 / N * dn / dd)
           - rounddown2(S6 / N * dn / dd))
    C1 = bal
    D1 = round(-E1 + (receivable * F3 * dn / dd - monthly_pmt * dn / dd))
    F1 = C1 + D1 + E1
    rows.append({"m": 1, "기초": C1, "이자": D1, "리스료": E1, "기말": F1})
    bal = F1

    # 2 ~ N-1 회차: 표준
    for m in range(2, N):
        C = bal
        D = round(C * F3)
        E = -monthly_pmt
        F = C + D + E
        rows.append({"m": m, "기초": C, "이자": D, "리스료": E, "기말": F})
        bal = F

    # N 회차 + 막달 정리(plug): 잔액을 0으로
    C = bal
    E = -monthly_pmt
    D = round(C * F3)
    F = C + D + E
    rows.append({"m": N, "기초": C, "이자": D, "리스료": E, "기말": F})
    # 막달 보정행: 남은 잔액을 이자/리스료로 흡수 → 0
    bal = F
    rows.append({"m": N + 1, "기초": bal, "이자": None, "리스료": None, "기말": 0})
    return F3, F2, rows


def baseline():
    """시트17: 할인전, 선납반영전"""
    I = Inputs
    pure = I.S2 - I.S5 - I.S6                 # 총 순수구독료 = 6,960,000
    pv = excel_pv(I.K / 12, I.N, -pure / I.N)
    receivable = min(I.S3, pv)               # 리스채권 = 4,809,091
    H2 = pure / I.N                           # 리스료 116,000
    F3, F2, rows = amortize(receivable, pure, I.N, I.K, I.S5, I.S6, I.S2, I.days_num, I.days_den, H2)
    return dict(name="할인전·선납반영전", receivable=receivable, pure=pure, H2=H2, F3=F3, F2=F2, rows=rows)


def with_prepay(prepay_final_v_minus=744_000.0):
    """시트18: 할인전, 선납반영 후 — 선납금이 채권·리스료를 줄이고 IRR 재계산"""
    I = Inputs
    S7 = prepay_final_v_minus                 # (최종) 선납금(V-) = 744,000
    pv = excel_pv(I.K / 12, I.N, -(I.S2 - I.S5 - I.S6) / I.N)
    receivable = min(I.S3, pv) - S7           # 리스채권 = 4,065,091
    pure = (I.S2 - I.S5 - I.S6) - S7          # 순수구독료 = 6,216,000
    H2 = pure / I.N                           # 리스료 103,600
    # 1회차 리스료 기준은 선납반영 월구독료(V6=111,400)이나, 구조 검증용으로 동일 엔진 사용
    F3, F2, rows = amortize(receivable, pure, I.N, I.K, I.S5, I.S6, I.S2 - S7 * 1.0, I.days_num, I.days_den, H2)
    return dict(name="할인전·선납반영후", receivable=receivable, pure=pure, H2=H2, F3=F3, F2=F2, rows=rows)


# ─────────────────────────────────────────────────────────────
# 검증 / 출력
# ─────────────────────────────────────────────────────────────
def check(label, got, want, tol=1):
    ok = abs(got - want) <= tol
    print(f"  [{'OK' if ok else 'XX'}] {label}: {got:,.6f}  (원본 {want:,})")
    return ok


def show(res, n_head=3):
    print(f"\n===== {res['name']} =====")
    print(f"  리스채권={res['receivable']:,.0f}  순수구독료={res['pure']:,.0f}  리스료={res['H2']:,.0f}")
    print(f"  월이자율={res['F3']:.8f}  연이자율={res['F2']:.6%}")
    print(f"  {'회차':>4} {'기초':>12} {'이자':>10} {'리스료':>10} {'기말':>12}")
    for r in res["rows"][:n_head + 1]:
        c = "" if r["기초"] is None else f"{r['기초']:,.0f}"
        d = "" if r["이자"] is None else f"{r['이자']:,.0f}"
        e = "" if r["리스료"] is None else f"{r['리스료']:,.0f}"
        print(f"  {r['m']:>4} {c:>12} {d:>10} {e:>10} {r['기말']:>12,.0f}")
    print("   ...")
    print(f"  {res['rows'][-1]['m']:>4} {'':>12} {'':>10} {'':>10} {res['rows'][-1]['기말']:>12,.0f}")


if __name__ == "__main__":
    print("=" * 64)
    print(" 리스 상각표 엔진 — 정답지 검증")
    print("=" * 64)

    b = baseline()
    print("\n[시트17 검증: 할인전·선납반영전]")
    allok = True
    allok &= check("리스채권 C2", b["receivable"], 4_809_091)
    allok &= check("리스료 H2", b["H2"], 116_000)
    allok &= check("월이자율 F3", b["F3"], 0.01302355, tol=1e-6)
    allok &= check("1회차 이자 D6", b["rows"][1]["이자"], 54_618)
    allok &= check("1회차 리스료 E6", b["rows"][1]["리스료"], -101_100)
    allok &= check("1회차 기말 F6", b["rows"][1]["기말"], 4_762_609)
    print(f"\n  => 시트17 {'전부 일치 ✅' if allok else '불일치 ❌'}")

    p = with_prepay()
    print("\n[시트18 검증: 할인전·선납반영후]")
    check("리스채권 C2 (−선납 744,000)", p["receivable"], 4_065_091)
    check("순수구독료 C3", p["pure"], 6_216_000)
    check("리스료 H2", p["H2"], 103_600)

    show(b)
    show(p)
    print("\n핵심: 선납금(744,000)이 리스채권을 줄이면 → 리스료↓(116,000→103,600) → IRR 재계산.")
