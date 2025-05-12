import math # math.floor 사용을 위해 추가

def date_to_jd(year, month, day):
    """양력 날짜를 율리우스 일(정오 기준)로 변환합니다."""
    if month <= 2:
        year -= 1
        month += 12
    
    a = math.floor(year / 100)
    # 그레고리력 적용 (1582년 10월 15일 이후)
    # 간단히 하기 위해 모든 날짜에 그레고리력 규칙을 적용한다고 가정 (현대 날짜 계산이므로 문제 없음)
    b = 2 - a + math.floor(a / 4)
    
    jd = math.floor(365.25 * (year + 4716)) + \
         math.floor(30.6001 * (month + 1)) + \
         day + b - 1524 # 정수 JD (정오 기준)
    return jd

def get_day_ganji(year, month, day):
    jd = date_to_jd(year, month, day)
    
    # JD 기반 일주 계산 (1989-11-17 -> 신사, 2000-01-01 -> 경진이 되도록 하는 상수)
    # 이 상수는 여러 검증된 날짜에 대해 확인 필요.
    # 아래 상수는 1989-11-17이 신사(辛巳: 천간idx 7, 지지idx 5)가 되도록 맞춘 것입니다.
    # Stem: (JD + K_stem) % 10 = 7  => (jd % 10 + K_stem_offset) % 10 = 7
    # Branch: (JD + K_branch) % 12 = 5 => (jd % 12 + K_branch_offset) % 12 = 5
    # JD for 1989-11-17 is 2447848 (정오 UT 기준)
    # 2447848 % 10 = 8. (8 + K_stem_offset) % 10 = 7 => K_stem_offset = -1 or 9.
    # 2447848 % 12 = 4. (4 + K_branch_offset) % 12 = 5 => K_branch_offset = 1.
    
    day_stem_idx = (jd + 9) % 10 # 0=갑, ... 7=신
    day_branch_idx = (jd + 1) % 12 # 0=자, ... 5=사

    day_gan = GAN[day_stem_idx]
    day_ji = JI[day_branch_idx]
    
    # 전체 60갑자 인덱스 (참고용, get_ganji_from_index 함수와는 별개)
    # 이 idx를 get_ganji_from_index에 넣으면 동일한 간지가 나와야 함.
    # k % 10 = day_stem_idx, k % 12 = day_branch_idx
    # (이 부분은 현재 코드에서 직접 사용되지는 않으나, 검증용으로 생각)
    
    return day_gan + day_ji, day_gan, day_ji
