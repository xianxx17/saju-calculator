# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl lunardate

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math

# --- 음력 변환을 위한 라이브러리 임포트 ---
try:
    from lunardate import LunarDate
except ImportError:
    st.error("음력 변환을 위한 'lunardate' 라이브러리가 설치되지 않았습니다. 터미널에서 `pip install lunardate`를 실행해주세요.")
    st.stop()

# ───────────────────────────────
# 0. 기본 상수 (이전과 동일)
# ───────────────────────────────
FILE_NAME = "Jeolgi_1900_2100_20250513.xlsx" 

GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI  = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

SAJU_MONTH_TERMS_ORDER = [
    "입춘", "경칩", "청명", "입하", "망종", "소서",
    "입추", "백로", "한로", "입동", "대설", "소한"
]
SAJU_MONTH_BRANCHES = ["인","묘","진","사","오","미","신","유","술","해","자","축"]

TIME_BRANCH_MAP = [
    ((23,30),(1,29),"자",0),((1,30),(3,29),"축",1),((3,30),(5,29),"인",2),
    ((5,30),(7,29),"묘",3),((7,30),(9,29),"진",4),((9,30),(11,29),"사",5),
    ((11,30),(13,29),"오",6),((13,30),(15,29),"미",7),((15,30),(17,29),"신",8),
    ((17,30),(19,29),"유",9),((19,30),(21,29),"술",10),((21,30),(23,29),"해",11)
]

# ───────────────────────────────
# 추가 상수 정의 (오행, 지장간, 십신 등)
# (사용자님이 제공해주신 HTML/JS 예제 코드의 상수들을 기반으로 작성되었습니다)
# ───────────────────────────────

GAN_TO_OHENG = {
    "갑": "목", "을": "목", "병": "화", "정": "화", "무": "토",
    "기": "토", "경": "금", "신": "금", "임": "수", "계": "수"
}

# 지지별 지장간 및 비율 (사용자 HTML 예제의 ZW 상수 기반)
# 참고: 이 비율들의 합이 항상 정확히 1.0이 되지는 않을 수 있으며,
#       이는 원본 JS 코드의 로직을 따른 것입니다.
#       더 일반적인 명리 이론의 지장간 비율(예: 여기/중기/정기 배분 일수 기반)과 다를 수 있습니다.
JIJI_JANGGAN = {
    "자": {"계": 1.0},
    "축": {"기": 0.5, "계": 0.3, "신": 0.2},
    "인": {"갑": 0.5, "병": 0.3, "무": 0.2},
    "묘": {"을": 1.0},
    "진": {"무": 0.5, "을": 0.3, "계": 0.2},
    "사": {"병": 0.5, "무": 0.3, "경": 0.2},
    "오": {"정": 0.7, "기": 0.3},
    "미": {"기": 0.5, "정": 0.3, "을": 0.2},
    "신": {"경": 0.5, "임": 0.3, "무": 0.2},
    "유": {"신": 1.0},
    "술": {"무": 0.5, "신": 0.3, "정": 0.2},
    "해": {"임": 0.7, "갑": 0.3}
}

# 각 위치별 가중치 (사용자 HTML 예제의 PW 상수 기반)
POSITIONAL_WEIGHTS = {
    "연간": 0.7, "연지": 0.9, "월간": 0.9, "월지": 2.1,
    "일간": 0.5, "일지": 1.9, "시간": 0.8, "시지": 1.0
}
# 계산 시 사용할 위치 키 목록 (순서대로: 년간, 연지, 월간, 월지, 일간, 일지, 시간, 시지)
POSITION_KEYS_ORDERED = ["연간", "연지", "월간", "월지", "일간", "일지", "시간", "시지"]


# 십신 관계표 (일간 기준) (사용자 HTML 예제의 S 상수 기반)
SIPSHIN_MAP = {
    "갑": {"갑": "비견", "을": "겁재", "병": "식신", "정": "상관", "무": "편재", "기": "정재", "경": "편관", "신": "정관", "임": "편인", "계": "정인"},
    "을": {"갑": "겁재", "을": "비견", "병": "상관", "정": "식신", "무": "정재", "기": "편재", "경": "정관", "신": "편관", "임": "정인", "계": "편인"},
    "병": {"갑": "편인", "을": "정인", "병": "비견", "정": "겁재", "무": "식신", "기": "상관", "경": "편재", "신": "정재", "임": "편관", "계": "정관"},
    "정": {"갑": "정인", "을": "편인", "병": "겁재", "정": "비견", "무": "상관", "기": "식신", "경": "정재", "신": "편재", "임": "정관", "계": "편관"},
    "무": {"갑": "편관", "을": "정관", "병": "편인", "정": "정인", "무": "비견", "기": "겁재", "경": "식신", "신": "상관", "임": "편재", "계": "정재"},
    "기": {"갑": "정관", "을": "편관", "병": "정인", "정": "편인", "무": "겁재", "기": "비견", "경": "상관", "신": "식신", "임": "정재", "계": "편재"},
    "경": {"갑": "편재", "을": "정재", "병": "편관", "정": "정관", "무": "편인", "기": "정인", "경": "비견", "신": "겁재", "임": "식신", "계": "상관"},
    "신": {"갑": "정재", "을": "편재", "병": "정관", "정": "편관", "무": "정인", "기": "편인", "경": "겁재", "신": "비견", "임": "상관", "계": "식신"},
    "임": {"갑": "식신", "을": "상관", "병": "편재", "정": "정재", "무": "편관", "기": "정관", "경": "편인", "신": "정인", "임": "비견", "계": "겁재"},
    "계": {"갑": "상관", "을": "식신", "병": "정재", "정": "편재", "무": "정관", "기": "편관", "경": "정인", "신": "편인", "임": "겁재", "계": "비견"}
}

OHENG_ORDER = ["목", "화", "토", "금", "수"]
SIPSHIN_ORDER = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]

OHENG_TO_HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}
# 오행 기본 설명 (HTML 예제 참고)
OHAENG_DESCRIPTIONS = {
    "목": "성장, 시작, 인자함", "화": "열정, 표현, 예의", "토": "안정, 중재, 신용",
    "금": "결실, 의리, 결단", "수": "지혜, 유연, 저장"
}
# 십신별 색상 (HTML 예제 참고) - CSS 클래스 대신 직접 색상 코드 사용 가능
SIPSHIN_COLORS = {
    "비견": "#1d4ed8", "겁재": "#1d4ed8", # 비겁
    "식신": "#c2410c", "상관": "#c2410c", # 식상
    "편재": "#ca8a04", "정재": "#ca8a04", # 재성
    "편관": "#166534", "정관": "#166534", # 관성
    "편인": "#6b7280", "정인": "#6b7280"  # 인성
}


# ───────────────────────────────
# 오행 및 십신 세력 계산 함수
# ───────────────────────────────
def calculate_ohaeng_sipshin_strengths(saju_8char_details):
    """
    사주팔자의 각 글자를 기반으로 오행 및 십신의 가중치를 계산합니다.
    saju_8char_details: {"year_gan":yg, "year_ji":yj, ..., "day_gan":dg, ...} 형태의 딕셔너리
    반환: (ohaeng_strengths_dict, sipshin_strengths_dict)
    """
    day_master_gan = saju_8char_details["day_gan"]

    # 분석할 8글자 (천간4 + 지지4)와 각 위치 키
    chars_to_analyze = [
        (saju_8char_details["year_gan"], "연간"), (saju_8char_details["year_ji"], "연지"),
        (saju_8char_details["month_gan"], "월간"), (saju_8char_details["month_ji"], "월지"),
        (saju_8char_details["day_gan"], "일간"), (saju_8char_details["day_ji"], "일지"),
        (saju_8char_details["time_gan"], "시간"), (saju_8char_details["time_ji"], "시지")
    ]

    ohaeng_strengths = {oheng: 0.0 for oheng in OHENG_ORDER}
    sipshin_strengths = {sipshin: 0.0 for sipshin in SIPSHIN_ORDER}

    def get_sipshin(dm_gan, other_gan):
        if dm_gan in SIPSHIN_MAP and other_gan in SIPSHIN_MAP[dm_gan]:
            return SIPSHIN_MAP[dm_gan][other_gan]
        return None # 또는 "기타" 반환

    for char_val, position_key in chars_to_analyze:
        weight = POSITIONAL_WEIGHTS.get(position_key, 0.0)
        is_gan = "간" in position_key # 천간인지 지지인지 구분

        if is_gan: # 천간인 경우
            gan_char = char_val
            # 오행 계산
            ohaeng = GAN_TO_OHENG.get(gan_char)
            if ohaeng:
                ohaeng_strengths[ohaeng] += weight
            
            # 십신 계산
            sipshin = get_sipshin(day_master_gan, gan_char)
            if sipshin:
                sipshin_strengths[sipshin] += weight
        
        else: # 지지인 경우
            ji_char = char_val
            if ji_char in JIJI_JANGGAN:
                for janggan_char, proportion in JIJI_JANGGAN[ji_char].items():
                    # 지장간의 오행 계산
                    ohaeng = GAN_TO_OHENG.get(janggan_char)
                    if ohaeng:
                        ohaeng_strengths[ohaeng] += weight * proportion
                    
                    # 지장간의 십신 계산
                    sipshin = get_sipshin(day_master_gan, janggan_char)
                    if sipshin:
                        sipshin_strengths[sipshin] += weight * proportion
    
    # 결과값을 소수점 한 자리까지 반올림 (JS 예제와 동일하게)
    for o in OHENG_ORDER: 
        ohaeng_strengths[o] = round(ohaeng_strengths[o], 1)
    for s in SIPSHIN_ORDER: 
        sipshin_strengths[s] = round(sipshin_strengths[s], 1)
            
    return ohaeng_strengths, sipshin_strengths

# --- 오행 및 십신 설명 생성 함수 (HTML 예제 기반) ---
def get_ohaeng_summary_explanation(ohaeng_counts):
    explanation = "오행 분포는 사주의 에너지 균형을 보여줍니다. "
    threshold = 1.5 # 이 값은 JS 예제에 명시적으로 없었으나, 설명 로직상 유사하게 설정
    strong = []
    weak = []
    # JS 예제에서는 점수 자체를 보여줬으므로, 여기서는 JS의 설명 로직을 따름
    # JS 예제에서는 단순히 강한 오행과 약한 오행을 나열
    # 기준값은 JS 예제처럼 동적으로 하기보다, 전체적인 분포를 보고 서술하는 방식 채택
    
    # 가장 강한 오행과 가장 약한 오행 찾기 (간단 버전)
    if not ohaeng_counts: return explanation + "오행 정보를 계산할 수 없습니다."

    sorted_ohaeng = sorted(ohaeng_counts.items(), key=lambda item: item[1], reverse=True)
    
    if sorted_ohaeng[0][1] > threshold * 1.5 : # JS 예제는 특정 값 이상/이하를 강/약으로 표현하지 않음.
                                            # 대신 상대적 강약을 서술하는 것이 좋아보임.
        explanation += f"특히 {sorted_ohaeng[0][0]}(이)가 {sorted_ohaeng[0][1]}점으로 가장 강한 기운을 가집니다. "
    
    if sorted_ohaeng[-1][1] < threshold / 1.5 and sorted_ohaeng[-1][1] < sorted_ohaeng[0][1] / 2:
         explanation += f"반면, {sorted_ohaeng[-1][0]}(이)가 {sorted_ohaeng[-1][1]}점으로 상대적으로 약한 편입니다. "
    
    explanation += "전체적인 균형과 조화를 이루는 것이 중요합니다."
    return explanation

def get_sipshin_summary_explanation(sipshin_counts, day_master_gan):
    explanation = "십신은 일간(나)을 기준으로 다른 글자와의 관계를 나타내며, 사회적 관계, 성향, 재능 등을 유추해볼 수 있습니다. "
    threshold = 1.5 # JS 예제 참고 (강한 십신 기준)
    strong_sibsins = []
    
    for sibshin_name in SIPSHIN_ORDER:
        if (sipshin_counts.get(sibshin_name, 0.0)) >= threshold:
            strong_sibsins.append(f"{sibshin_name}({sipshin_counts.get(sibshin_name, 0.0)})")
    
    if strong_sibsins:
        explanation += f"이 사주에서는 {', '.join(strong_sibsins)}의 영향력이 두드러질 수 있습니다. "
        # 각 강한 십신에 대한 간략한 설명 추가 (JS 예제처럼)
        temp_explanations = []
        for s_info in strong_sibsins:
            s_name = s_info.split('(')[0]
            if s_name in ["비견", "겁재"]: temp_explanations.append("주체성/독립심/경쟁심")
            elif s_name in ["식신", "상관"]: temp_explanations.append("표현력/창의력/기술 관련 재능")
            elif s_name in ["편재", "정재"]: temp_explanations.append("현실감각/재물운용/활동성")
            elif s_name in ["편관", "정관"]: temp_explanations.append("책임감/명예/조직 적응력")
            elif s_name in ["편인", "정인"]: temp_explanations.append("학문/수용성/직관력")
        
        unique_explanations = list(set(temp_explanations)) # 중복 제거
        if unique_explanations:
            explanation += f" 이는 {', '.join(unique_explanations)} 등이 발달했을 가능성을 시사합니다. "

    else:
        explanation += "특별히 한쪽으로 치우치기보다는 여러 십신의 특성이 비교적 균형 있게 나타날 수 있습니다. "
    
    explanation += "각 십신의 긍정적인 면을 잘 발휘하고 보완하는 것이 중요합니다."
    return explanation

# ... (기존의 다른 함수들 get_saju_year, get_year_ganji 등은 이 아래에 위치) ...

# ───────────────────────────────
# 1. 절입일 데이터 로딩 (이전과 동일)
# ───────────────────────────────
@st.cache_data(show_spinner=False)
def load_solar_terms(file_name: str):
    if not os.path.exists(file_name):
        st.error(f"`{file_name}` 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return None
    try:
        df = pd.read_excel(file_name, engine='openpyxl') 
    except Exception as e:
        st.error(f"엑셀 파일('{file_name}')을 읽는 중 오류 발생: {e}. 'openpyxl' 패키지가 설치되어 있는지 확인하세요.")
        return None
    term_dict = {}
    required_excel_cols = ["절기", "iso_datetime"] 
    if not all(col in df.columns for col in required_excel_cols):
        st.error(f"엑셀 파일에 필요한 컬럼({required_excel_cols})이 없습니다. 현재 컬럼: {df.columns.tolist()}")
        return None
    for _, row in df.iterrows():
        term = str(row["절기"]).strip()
        dt_val = row["iso_datetime"]
        if isinstance(dt_val, str): dt = pd.to_datetime(dt_val, errors="coerce")
        elif isinstance(dt_val, datetime): dt = pd.Timestamp(dt_val)
        elif isinstance(dt_val, pd.Timestamp): dt = dt_val
        else: st.warning(f"'{term}'의 'iso_datetime' 값 ('{dt_val}', 타입: {type(dt_val)})을 datetime으로 변환 불가."); continue
        if pd.isna(dt): st.warning(f"'{term}'의 'iso_datetime' 값 ('{row['iso_datetime']}')을 파싱 불가."); continue
        year = dt.year
        term_dict.setdefault(year, {})[term] = dt
    if not term_dict: st.warning("절기 데이터를 로드하지 못했거나 유효한 데이터가 없습니다."); return None 
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None: 
    st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수 (get_day_ganji는 이전 JD기반 사용, 나머지는 동일)
# ───────────────────────────────
def get_saju_year(birth_dt, solar_data_dict):
    year = birth_dt.year
    ipchun_data = solar_data_dict.get(year, {})
    ipchun = ipchun_data.get("입춘") 
    return year - 1 if (ipchun and birth_dt < ipchun) else year

def get_ganji_from_index(idx):
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year):
    idx = (saju_year - 4 + 60) % 60 
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_month_ganji(year_gan_char, birth_dt, solar_data_dict):
    saju_year_for_month = get_saju_year(birth_dt, solar_data_dict)
    terms_this_saju_year = solar_data_dict.get(saju_year_for_month, {})
    terms_prev_saju_year = solar_data_dict.get(saju_year_for_month - 1, {})
    governing_term_name = None
    sorted_terms_this_year = sorted([(name, dt) for name, dt in terms_this_saju_year.items() if name in SAJU_MONTH_TERMS_ORDER], key=lambda x: x[1])
    for name, dt in sorted_terms_this_year:
        if birth_dt >= dt: governing_term_name = name
        else: break
    if not governing_term_name:
        sorted_prev_year_winter_terms = sorted([(name, dt) for name, dt in terms_prev_saju_year.items() if name in ["소한", "대설"]], key=lambda x: x[1], reverse=True)
        for name, dt in sorted_prev_year_winter_terms:
            if birth_dt >= dt: governing_term_name = name; break
    if not governing_term_name: return "오류(월주절기)", "", ""
    try:
        branch_idx_in_sason = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji  = SAJU_MONTH_BRANCHES[branch_idx_in_sason]
    except ValueError: return f"오류({governing_term_name}없음)", "", ""
    yg_idx = GAN.index(year_gan_char)
    start_map = {0:2,5:2, 1:4,6:4, 2:6,7:6, 3:8,8:8, 4:0,9:0} 
    start_gan_idx_for_in_month = start_map.get(yg_idx)
    if start_gan_idx_for_in_month is None: return "오류(연간->월간맵)", "", ""
    month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    month_gan = GAN[(start_gan_idx_for_in_month + month_order_idx) % 10]
    return month_gan + month_ji, month_gan, month_ji

def date_to_jd(year, month, day):
    y = year; m = month
    if m <= 2: y -= 1; m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    jd_val = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524
    return int(jd_val)

def get_day_ganji(year, month, day):
    jd = date_to_jd(year, month, day)
    day_stem_idx = (jd + 9) % 10 
    day_branch_idx = (jd + 1) % 12
    day_gan_char = GAN[day_stem_idx]
    day_ji_char = JI[day_branch_idx]
    return day_gan_char + day_ji_char, day_gan_char, day_ji_char

def get_time_ganji(day_gan_char, hour, minute):
    cur_time_float = hour + minute/60.0 
    siji_char, siji_order_idx = None, -1 
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0; end_float = eh + em/60.0
        if ji_name == "자": 
            if cur_time_float >= start_float or cur_time_float <= end_float: siji_char,siji_order_idx=ji_name,order_idx;break
        elif start_float <= cur_time_float < end_float: siji_char,siji_order_idx=ji_name,order_idx;break
    if siji_char is None: return "오류(시지판단불가)", "", ""
    dg_idx = GAN.index(day_gan_char) 
    sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: return "오류(일간→시간맵)", "", ""
    time_gan_idx = (start_gan_idx_for_ja_hour + siji_order_idx) % 10 
    return GAN[time_gan_idx] + siji_char, GAN[time_gan_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data_dict):
    is_yang_year = GAN.index(year_gan_char) % 2 == 0 
    is_sunhaeng  = (is_yang_year and gender=="남성") or (not is_yang_year and gender=="여성")
    saju_year_for_daewoon = get_saju_year(birth_dt, solar_data_dict)
    relevant_terms_for_daewoon = []
    for yr_offset in [-1, 0, 1]: 
        year_to_check = saju_year_for_daewoon + yr_offset
        year_terms = solar_data_dict.get(year_to_check, {})
        for term_name, term_dt in year_terms.items():
            if term_name in SAJU_MONTH_TERMS_ORDER: relevant_terms_for_daewoon.append({'name':term_name,'datetime':term_dt})
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime']) 
    if not relevant_terms_for_daewoon: return ["오류(대운절기부족)"],0,is_sunhaeng
    target_term_dt = None
    if is_sunhaeng: 
        for term_info in relevant_terms_for_daewoon:
            if term_info['datetime'] > birth_dt: target_term_dt=term_info['datetime'];break
    else: 
        for term_info in reversed(relevant_terms_for_daewoon): 
            if term_info['datetime'] < birth_dt: target_term_dt=term_info['datetime'];break
    if target_term_dt is None: return ["오류(대운목표절기없음)"],0,is_sunhaeng
    if is_sunhaeng: days_difference=(target_term_dt - birth_dt).total_seconds()/(24*3600)
    else: days_difference=(birth_dt - target_term_dt).total_seconds()/(24*3600)
    daewoon_start_age = max(1, int(round(days_difference / 3))) 
    month_ganji_str = month_gan_char + month_ji_char; current_month_gapja_idx = -1
    for i in range(60):
        if get_ganji_from_index(i) == month_ganji_str: current_month_gapja_idx=i;break
    if current_month_gapja_idx == -1: return ["오류(월주갑자변환실패)"],daewoon_start_age,is_sunhaeng
    daewoon_list_output = []
    for i in range(10): 
        age_display = daewoon_start_age + i * 10; next_gapja_idx = -1
        if is_sunhaeng: next_gapja_idx=(current_month_gapja_idx+(i+1))%60
        else: next_gapja_idx=(current_month_gapja_idx-(i+1)+60)%60 
        daewoon_list_output.append(f"{age_display}세: {get_ganji_from_index(next_gapja_idx)}")
    return daewoon_list_output, daewoon_start_age, is_sunhaeng

def get_seun_list(start_year, n=10): 
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    output_wolun = []
    for i in range(n):
        current_year=base_year+(base_month-1+i)//12; current_month_num=(base_month-1+i)%12+1
        seun_gan_char=get_year_ganji(current_year)[1] 
        dummy_birth_dt_for_wolun=datetime(current_year,current_month_num,15,12,0) 
        wolun_ganji,_,_=get_month_ganji(seun_gan_char,dummy_birth_dt_for_wolun,solar_data_dict)
        output_wolun.append((f"{current_year}-{current_month_num:02d}", wolun_ganji))
    return output_wolun

def get_ilun_list(year_val, month_val, day_val, n=10):
    base_dt = datetime(year_val, month_val, day_val); output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji,_,_ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

# ───────────────────────────────
# 3. Streamlit UI
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

st.sidebar.header("1. 출생 정보")
# --- 달력 유형 선택 (양력/음력) ---
calendar_type = st.sidebar.radio("달력 유형", ("양력", "음력"), index=0, horizontal=True)
is_leap_month = False
if calendar_type == "음력":
    is_leap_month = st.sidebar.checkbox("윤달 (Leap Month)", help="음력 생일이 윤달인 경우 체크해주세요.")

current_year_for_input = datetime.now().year
min_input_year = 1900 # lunardate는 더 넓은 범위를 지원하지만, 절기데이터 시작에 맞춤
max_input_year = 2100 # 절기데이터 끝에 맞춤
if solar_data: # solar_data가 정상 로드되었을때만 min/max 설정
    min_input_year = min(solar_data.keys()) if solar_data else 1900
    max_input_year = max(solar_data.keys()) if solar_data else 2100

by = st.sidebar.number_input("출생 연도", min_input_year, max_input_year, 1990, help=f"{calendar_type} {min_input_year}~{max_input_year}년")
bm = st.sidebar.number_input("출생 월", 1, 12, 6)
bd = st.sidebar.number_input("출생 일", 1, 31, 15)
bh = st.sidebar.number_input("출생 시", 0, 23, 12)
bmin = st.sidebar.number_input("출생 분", 0, 59, 30)
gender = st.sidebar.radio("성별", ("남성","여성"), horizontal=True, index=0)

st.sidebar.header("2. 운세 기준일 (양력)")
today = datetime.now()
# 운세 기준일은 양력으로만 받음 (음력 변환 미적용)
ty = st.sidebar.number_input("기준 연도 ", min_input_year, max_input_year + 10, today.year, help=f"양력 기준년도 ({min_input_year}~{max_input_year+10} 범위)")
tm = st.sidebar.number_input("기준 월  " , 1, 12, today.month) # 공백 추가로 키 중복 방지
td = st.sidebar.number_input("기준 일  " , 1, 31, today.day)  # 공백 추가

# (saju_app.py 파일의 if st.sidebar.button(...) 블록 내부 수정)

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    birth_dt_input_valid = True
    birth_dt = None

    if calendar_type == "양력":
        try:
            birth_dt = datetime(by,bm,bd,bh,bmin)
        except ValueError:
            st.error("❌ 유효하지 않은 양력 날짜/시간입니다. 다시 확인해주세요.")
            birth_dt_input_valid = False
            st.stop()
    else: # 음력인 경우
        try:
            lunar_conv_date = LunarDate(by, bm, bd, is_leap_month)
            solar_equiv_date = lunar_conv_date.toSolarDate()
            birth_dt = datetime(solar_equiv_date.year, solar_equiv_date.month, solar_equiv_date.day, bh, bmin)
            st.sidebar.info(f"음력 {by}년 {bm}월 {bd}일{' (윤달)' if is_leap_month else ''}은 양력 {birth_dt.strftime('%Y-%m-%d')} 입니다.")
        except ValueError as e: 
            st.error(f"❌ 음력 날짜 변환 오류: {e}. 유효한 음력 날짜와 윤달 여부를 확인해주세요.")
            birth_dt_input_valid = False
            st.stop()
        except Exception as e: 
            st.error(f"❌ 음력 날짜 처리 중 알 수 없는 오류: {e}")
            birth_dt_input_valid = False
            st.stop()
    
    if birth_dt_input_valid and birth_dt:
        # --- 사주 명식 계산 (birth_dt는 항상 양력 datetime 객체) ---
        saju_year_val = get_saju_year(birth_dt, solar_data)
        year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
        month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
        day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day)
        time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)

        # --- 명식 기본 정보 표시 ---
        st.subheader("📜 사주 명식")
        ms_data = {
            "구분":["천간","지지","간지"],
            "시주":[time_gan_char if "오류" not in time_pillar_str else "?", time_ji_char if "오류" not in time_pillar_str else "?", time_pillar_str if "오류" not in time_pillar_str else "오류"],
            "일주":[day_gan_char if "오류" not in day_pillar_str else "?", day_ji_char if "오류" not in day_pillar_str else "?", day_pillar_str if "오류" not in day_pillar_str else "오류"],
            "월주":[month_gan_char if "오류" not in month_pillar_str else "?", month_ji_char if "오류" not in month_pillar_str else "?", month_pillar_str if "오류" not in month_pillar_str else "오류"],
            "연주":[year_gan_char if "오류" not in year_pillar_str else "?", year_ji_char if "오류" not in year_pillar_str else "?", year_pillar_str if "오류" not in year_pillar_str else "오류"]
        }
        ms_df = pd.DataFrame(ms_data).set_index("구분")
        st.table(ms_df)
        st.caption(f"사주 기준 연도 (입춘 기준): {saju_year_val}년")

        # --- 오행 및 십신 세력 계산 ---
        saju_8char_for_analysis = {
            "year_gan": year_gan_char, "year_ji": year_ji_char,
            "month_gan": month_gan_char, "month_ji": month_ji_char,
            "day_gan": day_gan_char, "day_ji": day_ji_char,
            "time_gan": time_gan_char, "time_ji": time_ji_char
        }
        
        analysis_possible = True
        # 각 간지 글자가 유효한지 (한 글자인지, GAN 또는 JI 리스트에 있는지) 확인
        for key, val_char in saju_8char_for_analysis.items():
            if not val_char or len(val_char) != 1: # 비어있거나 길이가 1이 아니면 분석 불가
                analysis_possible = False; break
            if key.endswith("_gan") and val_char not in GAN:
                analysis_possible = False; break
            if key.endswith("_ji") and val_char not in JI:
                analysis_possible = False; break
        
        ohaeng_strengths = {}
        sipshin_strengths = {}

        if analysis_possible:
            try:
                ohaeng_strengths, sipshin_strengths = calculate_ohaeng_sipshin_strengths(saju_8char_for_analysis)
            except Exception as e:
                st.warning(f"오행/십신 분석 중 오류 발생: {e}")
                analysis_possible = False # 분석 실패 처리
        else:
            st.warning("사주 기둥 중 일부가 정확히 계산되지 않아 오행 및 십신 분석을 수행할 수 없습니다.")

        # --- 오행 분석 표시 ---
        st.markdown("---") # 구분선
        st.subheader("🌳🔥 오행(五行) 분석")
        if ohaeng_strengths and analysis_possible:
            cols_ohaeng = st.columns(5)
            ohaeng_box_colors = {"목": "#d1fae5", "화": "#fee2e2", "토": "#fef3c7", "금": "#e5e7eb", "수": "#dbeafe"}
            ohaeng_text_colors = {"목": "#065f46", "화": "#991b1b", "토": "#92400e", "금": "#374151", "수": "#1e40af"}

            for i, oheng_name in enumerate(OHENG_ORDER):
                with cols_ohaeng[i]:
                    strength = ohaeng_strengths.get(oheng_name, 0.0)
                    description = OHAENG_DESCRIPTIONS.get(oheng_name, "")
                    hanja = OHENG_TO_HANJA.get(oheng_name, '')
                    bg_color = ohaeng_box_colors.get(oheng_name, "#f0f0f0")
                    text_color = ohaeng_text_colors.get(oheng_name, "#000000")
                    
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; color: {text_color}; padding: 15px; border-radius: 8px; text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <strong style="font-size: 1.1em; margin-bottom: 5px;">{oheng_name}({hanja})</strong>
                        <div style="font-size: 1.4em; font-weight: bold; margin: 5px 0;">{strength}</div>
                        <small style="font-size: 0.85em; line-height: 1.3;">{description}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            ohaeng_summary_exp_text = get_ohaeng_summary_explanation(ohaeng_strengths)
            st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #60a5fa;'>{ohaeng_summary_exp_text}</div>", unsafe_allow_html=True)
        elif analysis_possible: # 계산은 시도했으나 결과가 없는 경우 (거의 발생 안 함)
             st.markdown("오행 강약 정보를 계산 중이거나 표시할 데이터가 없습니다.")
        # (analysis_possible이 False인 경우 이미 위에서 경고 메시지 표시됨)

        # --- 십신 분석 표시 ---
        st.markdown("---") # 구분선
        st.subheader("🌟 십신(十神) 분석")
        if sipshin_strengths and analysis_possible:
            # 10개의 십신을 2행 5열로 표시
            row1_cols_sipshin = st.columns(5)
            row2_cols_sipshin = st.columns(5)
            
            sipshin_display_slots = row1_cols_sipshin + row2_cols_sipshin # 총 10개의 컬럼 객체

            for i, sipshin_name in enumerate(SIPSHIN_ORDER):
                with sipshin_display_slots[i]:
                    strength = sipshin_strengths.get(sipshin_name, 0.0)
                    text_color = SIPSHIN_COLORS.get(sipshin_name, "#333333") # 상수에서 정의한 색상 사용
                    
                    st.markdown(f"""
                    <div style="background-color: #f9fafb; padding: 10px; border-radius: 6px; border: 1px solid #e5e7eb; text-align: center; margin-bottom: 10px; height: 100px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div style="font-weight: 500; font-size: 0.95em; color: {text_color}; margin-bottom: 5px;">{sipshin_name}</div>
                        <div style="font-size: 1.3em; font-weight: bold; color: {text_color};">{strength}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            sipshin_summary_exp_text = get_sipshin_summary_explanation(sipshin_strengths, day_gan_char) # 일간 정보 전달
            st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #7c3aed;'>{sipshin_summary_exp_text}</div>", unsafe_allow_html=True)

        elif analysis_possible:
            st.markdown("십신 강약 정보를 계산 중이거나 표시할 데이터가 없습니다.")
        # (analysis_possible이 False인 경우 이미 위에서 경고 메시지 표시됨)


        # --- 대운, 세운 등 기존 운세 정보 표시 (이전과 동일) ---
        st.markdown("---") # 구분선
        st.subheader(f"運 대운 ({gender})")
        if "오류" in month_pillar_str or not month_gan_char or not month_ji_char :
            st.warning("월주 계산에 오류가 있어 대운을 표시할 수 없습니다.")
        else:
            # is_sunhaeng_val 변수 이름을 명확히 하기 위해 수정 (만약 이전 코드와 다르다면)
            daewoon_text_list, daewoon_start_age_val, is_sunhaeng_val = get_daewoon( 
                year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data
            )
            if isinstance(daewoon_text_list, list) and daewoon_text_list and "오류" in daewoon_text_list[0]: 
                st.warning(daewoon_text_list[0])
            elif isinstance(daewoon_text_list, list) and all(":" in item for item in daewoon_text_list):
                st.text(f"대운 시작 나이: 약 {daewoon_start_age_val}세 ({'순행' if is_sunhaeng_val else '역행'})")
                daewoon_table_data = {
                    "주기(나이)": [item.split(':')[0] for item in daewoon_text_list], 
                    "간지": [item.split(': ')[1] for item in daewoon_text_list]
                }
                st.table(pd.DataFrame(daewoon_table_data))
            else: 
                st.warning("대운 정보를 올바르게 가져오지 못했습니다.")

        st.markdown("---") # 구분선
        st.subheader(f"📅 기준일({ty}년 {tm}월 {td}일) 운세")
        col1,col2 = st.columns(2)
        with col1:
            st.markdown(f"##### 歲 세운 ({ty}년~)")
            st.table(pd.DataFrame(get_seun_list(ty,5), columns=["연도","간지"]))
            st.markdown(f"##### 日 일운 ({ty}-{tm:02d}-{td:02d}~)")
            st.table(pd.DataFrame(get_ilun_list(ty,tm,td,7), columns=["날짜","간지"]))
        with col2:
            st.markdown(f"##### 月 월운 ({ty}년 {tm:02d}월~)")
            st.table(pd.DataFrame(get_wolun_list(ty,tm,solar_data,12), columns=["연월","간지"]))
# (else: st.markdown(...) 부분은 기존과 동일하게 유지)
