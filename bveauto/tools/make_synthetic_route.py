"""회귀 테스트용 합성 노선 생성 (BVEParser ApplyRouteData 출력 형식: bve_alignment.txt + 기존 3개 파일 + rail_info.txt)

    python tests/regression_cases/make_synthetic_route.py

BVEParser 의 블록 계산을 그대로 재현한다:
    - 블록 시작점 기록 → 곡선이면 진행방향을 a=0.5*b 회전 → (레일 좌표 기록) → 현 방향으로 c 만큼 전진 → 다시 a 회전
    - 구배: s = d/sqrt(1+p^2), h = s*p, 곡선각 b = s/|R|
    - Rail x 오프셋: 진행방향 우측(+) = (dy*x, -dx*x)
    - RailEnd 이후에도 마지막 오프셋 좌표를 계속 기록 (visible=0)

노선 구성 (3,000m, 블록 121개):
    0~500 직선 / 500~1200 R=600 우곡선(캔트) / 1200~1600 직선 / 1600~2100 R=-250 좌 급곡선 / 이후 직선
    구배 1000~2000 10‰, 교량 700~900, 터널 1800~2300
    Rail 1(상선): 4.4m → 2200~2400 에서 8.8m 로 벌어짐 → 2775 에서 RailEnd
"""
import math
import os

import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'synthetic_route')
BLOCK = 25.0
N_BLOCKS = 121  # 0 ~ 3000m


def radius_at(s):
    if 500 <= s < 1200:
        return 600.0
    if 1600 <= s < 2100:
        return -250.0
    return 0.0


def cant_at(s):
    return 0.08 if radius_at(s) == 600.0 else (0.12 if radius_at(s) == -250.0 else 0.0)


def pitch_at(s):
    return 0.010 if 1000 <= s < 2000 else 0.0


def rail1_offset(s):
    if s < 2200:
        return 4.4
    if s < 2400:
        return 4.4 + (s - 2200) / 200 * 4.4
    return 8.8


RAIL1_END = 2775.0  # 이 블록부터 RailStarted=False


def rotate(d, cos_a, sin_a):
    return (cos_a * d[0] - sin_a * d[1], sin_a * d[0] + cos_a * d[1])


def main():
    os.makedirs(OUT, exist_ok=True)
    pos = [1000.0, 2000.0, 10.0]  # x, (평면)y, 높이
    th0 = math.radians(30)
    d = (math.cos(th0), math.sin(th0))
    coords, curves, pitches, rails = [], [], [], []
    alignment = ['측점,X,Y,Z,Bearing,Radius,Cant,Pitch,height']
    last_rail_x = None
    for i in range(N_BLOCKS):
        s = i * BLOCK
        r, p = radius_at(s), pitch_at(s)
        coords.append(f'{pos[0]}, {pos[1]}, {pos[2]}')
        curves.append(f'{s},{r},{cant_at(s)}')
        pitches.append(f'{s},{p}')

        a, c, h = 0.0, BLOCK, 0.0
        if r != 0.0:
            s_len = BLOCK / math.sqrt(1 + p * p)
            h = s_len * p
            b = s_len / abs(r)
            c = math.sqrt(2 * r * r * (1 - math.cos(b)))
            a = 0.5 * math.copysign(1, r) * b
            d = rotate(d, math.cos(-a), math.sin(-a))
        elif p != 0.0:
            c = BLOCK / math.sqrt(1 + p * p)
            h = c * p

        # bve_alignment.txt: BVEParser 처럼 곡선 반회전 뒤의 진행방향(현 방향)으로 방위 기록
        alignment.append(f'{s},{pos[0]},{pos[1]},{pos[2]},{math.atan2(d[1], d[0])},{r},{cant_at(s)},{p},0.0')

        visible = s < RAIL1_END
        x = rail1_offset(s) if visible else last_rail_x  # RailEnd 이후 마지막 오프셋 유지
        last_rail_x = x
        rails.append(f'{s},1,{pos[0] + d[1] * x},{pos[1] - d[0] * x},{pos[2]},{1 if visible else 0}')

        pos[0] += d[0] * c
        pos[1] += d[1] * c
        pos[2] += h
        if a != 0.0:
            d = rotate(d, math.cos(-a), math.sin(-a))

    for name, lines in (('bve_alignment.txt', alignment), ('bve_coordinates.txt', coords), ('curve_info.txt', curves),
                        ('pitch_info.txt', pitches), ('rail_info.txt', rails)):
        with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')

    with pd.ExcelWriter(os.path.join(OUT, 'structure.xlsx')) as w:
        pd.DataFrame([['교량1', 700, 900, 200]]).to_excel(w, sheet_name='교량', header=False, index=False)
        pd.DataFrame([['터널1', 1800, 2300, 500]]).to_excel(w, sheet_name='터널', header=False, index=False)
    print(f'생성 완료: {OUT}')


if __name__ == '__main__':
    main()
