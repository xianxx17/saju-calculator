# 파일명: saju_app_integrated.py
# 실행: streamlit run saju_app_integrated.py
# 필요 패키지: pip install streamlit pandas openpyxl lunardate

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math
import re

# --- 음력 변환을 위한 라이브러리 임포트 ---
try:
    from lunardate import LunarDate
except ImportError:
    st.error("음력 변환을 위한 'lunardate' 라이브러리가 설치되지 않았습니다. 터미널에서 `pip install lunardate`를 실행해주세요.")
    st.stop()

# -------------------------------
# HTML 태그 제거 헬퍼 함수
# -------------------------------
def strip_html_tags(html_string):
    if not isinstance(html_string, str):
        return str(html_string)
    html_string = re.sub(r'<style.*?</style>', '', html_string, flags=re.DOTALL | re.IGNORECASE)
    html_string = re.sub(r'<script.*?</script>', '', html_string, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', '', html_string)
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&amp;', '&')
    lines = [line.strip() for line in clean_text.splitlines()]
    filtered_lines = []
    last_line_was_content = False
    for line in lines:
        if line:
            filtered_lines.append(line)
            last_line_was_content = True
        elif last_line_was_content:
            filtered_lines.append("")
            last_line_was_content = False
    clean_text = '\n'.join(filtered_lines).strip()
    clean_text = re.sub(r'(?<=[א-힣a-zA-Z0-9])\n(?=[א-힣a-zA-Z0-9])', '\n\n', clean_text)
    return clean_text

# --- 만 나이 계산 함수 ---
def calculate_age(birth_dt_obj, current_dt_obj):
    if birth_dt_obj is None:
        return "계산 불가"
    birth_date_only = birth_dt_obj.date()
    current_date_only = current_dt_obj.date()
    age = current_date_only.year - birth_date_only.year
    if (current_date_only.month, current_date_only.day) < (birth_date_only.month, birth_date_only.day):
        age -= 1
    return age

# ───────────────────────────────
# 0. 기본 상수
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
# ───────────────────────────────
GAN_TO_OHENG = {
    "갑": "목", "을": "목", "병": "화", "정": "화", "무": "토",
    "기": "토", "경": "금", "신": "금", "임": "수", "계": "수"
}

JIJI_JANGGAN = {
    "자": {"계": 1.0}, "축": {"기": 0.5, "계": 0.3, "신": 0.2},
    "인": {"갑": 0.5, "병": 0.3, "무": 0.2}, "묘": {"을": 1.0},
    "진": {"무": 0.5, "을": 0.3, "계": 0.2}, "사": {"병": 0.5, "무": 0.3, "경": 0.2},
    "오": {"정": 0.7, "기": 0.3}, "미": {"기": 0.5, "정": 0.3, "을": 0.2},
    "신": {"경": 0.5, "임": 0.3, "무": 0.2}, "유": {"신": 1.0},
    "술": {"무": 0.5, "신": 0.3, "정": 0.2}, "해": {"임": 0.7, "갑": 0.3}
}

POSITIONAL_WEIGHTS = {
    "연간": 0.7, "연지": 0.9, "월간": 0.9, "월지": 2.1,
    "일간": 0.5, "일지": 1.9, "시간": 0.8, "시지": 1.0
}
POSITION_KEYS_ORDERED = ["연간", "연지", "월간", "월지", "일간", "일지", "시간", "시지"]

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
OHAENG_DESCRIPTIONS = {
    "목": "성장, 시작, 인자함", "화": "열정, 표현, 예의", "토": "안정, 중재, 신용",
    "금": "결실, 의리, 결단", "수": "지혜, 유연, 저장"
}
SIPSHIN_COLORS = { # 바 차트 색상 등으로 활용 가능
    "비견": "#1d4ed8", "겁재": "#1d4ed8", "식신": "#c2410c", "상관": "#c2410c",
    "편재": "#ca8a04", "정재": "#ca8a04", "편관": "#166534", "정관": "#166534",
    "편인": "#6b7280", "정인": "#6b7280"
}

# ───────────────────────────────
# 12운성 관련 상수
# ───────────────────────────────
_12_UNSEONG_PHASES_KOR = ["장생", "목욕", "관대", "건록", "제왕", "쇠", "병", "사", "묘", "절", "태", "양"]
_12_UNSEONG_MAP_DATA = {
    "갑": {"해":"장생", "자":"목욕", "축":"관대", "인":"건록", "묘":"제왕", "진":"쇠", "사":"병", "오":"사", "미":"묘", "신":"절", "유":"태", "술":"양"},
    "을": {"오":"장생", "사":"목욕", "진":"관대", "묘":"건록", "인":"제왕", "축":"쇠", "자":"병", "해":"사", "술":"묘", "유":"절", "신":"태", "미":"양"},
    "병": {"인":"장생", "묘":"목욕", "진":"관대", "사":"건록", "오":"제왕", "미":"쇠", "신":"병", "유":"사", "술":"묘", "해":"절", "자":"태", "축":"양"},
    "정": {"유":"장생", "신":"목욕", "미":"관대", "오":"건록", "사":"제왕", "진":"쇠", "묘":"병", "인":"사", "축":"묘", "자":"절", "해":"태", "술":"양"},
    "무": {"인":"장생", "묘":"목욕", "진":"관대", "사":"건록", "오":"제왕", "미":"쇠", "신":"병", "유":"사", "술":"묘", "해":"절", "자":"태", "축":"양"},
    "기": {"유":"장생", "신":"목욕", "미":"관대", "오":"건록", "사":"제왕", "진":"쇠", "묘":"병", "인":"사", "축":"묘", "자":"절", "해":"태", "술":"양"},
    "경": {"사":"장생", "오":"목욕", "미":"관대", "신":"건록", "유":"제왕", "술":"쇠", "해":"병", "자":"사", "축":"묘", "인":"절", "묘":"태", "진":"양"},
    "신": {"자":"장생", "해":"목욕", "술":"관대", "유":"건록", "신":"제왕", "미":"쇠", "오":"병", "사":"사", "진":"묘", "묘":"절", "인":"태", "축":"양"},
    "임": {"신":"장생", "유":"목욕", "술":"관대", "해":"건록", "자":"제왕", "축":"쇠", "인":"병", "묘":"사", "진":"묘", "사":"절", "오":"태", "미":"양"},
    "계": {"묘":"장생", "인":"목욕", "축":"관대", "자":"건록", "해":"제왕", "술":"쇠", "유":"병", "신":"사", "미":"묘", "오":"절", "사":"태", "진":"양"}
}

# ───────────────────────────────
# 신강/신약 및 격국 분석용 상수
# ───────────────────────────────
L_NOK_MAP = {"갑":"인","을":"묘","병":"사","정":"오","무":"사","기":"오","경":"신","신":"유","임":"해","계":"자"}
YANGIN_JI_MAP = {"갑":"묘","병":"오","무":"오","경":"유","임":"자"}
SIPSHIN_TO_GYEOK_MAP = {
    '비견':'비견격', '겁재':'겁재격', '식신':'식신격', '상관':'상관격',
    '편재':'편재격', '정재':'정재격', '편관':'칠살격', '정관':'정관격',
    '편인':'편인격', '정인':'정인격'
}

# ───────────────────────────────
# 합충형해파 분석용 상수
# ───────────────────────────────
CHEONGAN_HAP_RULES = {tuple(sorted(k)):v for k,v in {(("갑","기"),"토"), (("을","경"),"금"), (("병","신"),"수"), (("정","임"),"목"), (("무","계"),"화")}.items()}
JIJI_SAMHAP_RULES = {tuple(sorted(k)):v for k,v in {(("신","자","진"),"수국(水局)"), (("사","유","축"),"금국(金局)"), (("인","오","술"),"화국(火局)"), (("해","묘","미"),"목국(木局)")}.items()}
JIJI_BANHAP_WANGJI_CENTERED_RULES = {"자":["신","진"],"유":["사","축"],"오":["인","술"],"묘":["해","미"]}
JIJI_BANGHAP_RULES = {tuple(sorted(k)):v for k,v in {(("인","묘","진"),"목국(木局)"), (("사","오","미"),"화국(火局)"), (("신","유","술"),"금국(金局)"), (("해","자","축"),"수국(水局)")}.items()}
JIJI_YUKHAP_RULES = {tuple(sorted(k)):v for k,v in {(("자","축"),"토"), (("인","해"),"목"), (("묘","술"),"화"), (("진","유"),"금"), (("사","신"),"수"), (("오","미"),"화/토")}.items()}
CHEONGAN_CHUNG_RULES = [tuple(sorted(p)) for p in [("갑","경"),("을","신"),("병","임"),("정","계")]]
JIJI_CHUNG_RULES = [tuple(sorted(p)) for p in [("자","오"),("축","미"),("인","신"),("묘","유"),("진","술"),("사","해")]]
SAMHYEONG_RULES = {tuple(sorted(k)):v for k,v in {(("인","사","신"),"인사신 삼형(無恩之刑)"), (("축","술","미"),"축술미 삼형(持勢之刑)")}.items()}
SANGHYEONG_RULES = [tuple(sorted(("자","묘")))]
JAHYEONG_CHARS = ["진","오","유","해"]
JIJI_HAE_RULES = [tuple(sorted(p)) for p in [("자","미"),("축","오"),("인","사"),("묘","진"),("신","해"),("유","술")]]
HAE_NAMES = {tuple(sorted(k)):v for k,v in {"자미":"자미해", "축오":"축오해", "인사":"인사회", "묘진":"묘진해", "신해":"신해해", "유술":"유술해"}.items()}
JIJI_PA_RULES = [tuple(sorted(p)) for p in [("자","유"),("축","진"),("인","해"),("묘","오"),("사","신"),("술","미")]]
PA_NAMES = {tuple(sorted(k)):v for k,v in {"자유":"자유파", "축진":"축진파", "인해":"인해파", "묘오":"묘오파", "사신":"사신파", "술미":"술미파"}.items()}
PILLAR_NAMES_KOR_SHORT = ["년", "월", "일", "시"]

# ───────────────────────────────
# 주요 신살 분석용 상수
# ───────────────────────────────
CHEONEULGWIIN_MAP = { "갑":["축","미"],"을":["자","신"],"병":["해","유"],"정":["해","유"],"무":["축","미"],"기":["자","신"],"경":["축","미","인","오"],"신":["인","오"],"임":["사","묘"],"계":["사","묘"]}
MUNCHANGGWIIN_MAP = {"갑":"사","을":"오","병":"신","정":"유","무":"신","기":"유","경":"해","신":"자","임":"인","계":"묘"}
DOHWASAL_MAP = {"해":"자","묘":"자","미":"자","인":"묘","오":"묘","술":"묘","사":"오","유":"오","축":"오","신":"유","자":"유","진":"유"}
YEONGMASAL_MAP = {"해":"사","묘":"사","미":"사","인":"신","오":"신","술":"신","사":"해","유":"해","축":"해","신":"인","자":"인","진":"인"}
HWAGAESAL_MAP = {"해":"미","묘":"미","미":"미","인":"술","오":"술","술":"술","사":"축","유":"축","축":"축","신":"진","자":"진","진":"진"}
GOEGANGSAL_ILJU_LIST = ["경진","경술","임진","임술","무진","무술"]
BAEKHODAESAL_GANJI_LIST = ["갑진","을미","병술","정축","무진","임술","계축"]
GWIMUNGWANSAL_PAIRS = [tuple(sorted(p)) for p in [("자","유"),("축","오"),("인","미"),("묘","신"),("진","해"),("사","술")]]
PILLAR_NAMES_KOR = ["년주", "월주", "일주", "시주"]

# ───────────────────────────────
# 용신/기신 분석용 상수
# ───────────────────────────────
OHENG_HELPER_MAP = {"목":"수","화":"목","토":"화","금":"토","수":"금"}
OHENG_PRODUCES_MAP = {"목":"화","화":"토","토":"금","금":"수","수":"목"}
OHENG_CONTROLS_MAP = {"목":"토","화":"금","토":"수","금":"목","수":"화"}
OHENG_IS_CONTROLLED_BY_MAP = {"목":"금","화":"수","토":"목","금":"화","수":"토"}

# ───────────────────────────────
# 1. 절입일 데이터 로딩 함수
# ───────────────────────────────
@st.cache_data(show_spinner=False)
def load_solar_terms(file_name: str):
    # ... (기존 load_solar_terms 함수 내용과 동일) ...
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
# 2. 사주/운세 계산 함수들
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
    saju_year_of_birth = get_saju_year(birth_dt, solar_data_dict)
    candidate_solar_years = sorted(list(set([birth_dt.year - 1, birth_dt.year, birth_dt.year + 1])))
    all_relevant_terms = []
    for solar_yr in candidate_solar_years:
        year_terms_data = solar_data_dict.get(solar_yr, {})
        for term_name, term_datetime_obj in year_terms_data.items():
            if term_name in SAJU_MONTH_TERMS_ORDER:
                all_relevant_terms.append({'name': term_name, 'datetime': term_datetime_obj})
    if not all_relevant_terms: return f"오류(월주절기데이터부족:{birth_dt.strftime('%Y%m%d')})", "", ""
    all_relevant_terms.sort(key=lambda x: x['datetime'])
    governing_term_name = None
    for term_info in all_relevant_terms:
        if birth_dt >= term_info['datetime']:
            if get_saju_year(term_info['datetime'], solar_data_dict) == saju_year_of_birth:
                governing_term_name = term_info['name']
        else: break
    if not governing_term_name: return f"오류(월주기준절기못찾음:{birth_dt.strftime('%Y%m%d')})", "", ""
    try:
        month_ji_idx = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji = SAJU_MONTH_BRANCHES[month_ji_idx]
    except ValueError: return f"오류(월지변환실패:{governing_term_name})", "", ""
    try: yg_idx = GAN.index(year_gan_char)
    except ValueError: return f"오류(알수없는연간:{year_gan_char})", "", ""
    start_map = {0:2, 5:2, 1:4, 6:4, 2:6, 7:6, 3:8, 8:8, 4:0, 9:0}
    start_gan_idx_for_in_month = start_map.get(yg_idx)
    if start_gan_idx_for_in_month is None: return f"오류(월두법맵핑실패:{year_gan_char})", "", ""
    try: current_month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    except ValueError: return f"오류(알수없는월지:{month_ji})", "", ""
    month_gan_idx = (start_gan_idx_for_in_month + current_month_order_idx) % 10
    month_gan = GAN[month_gan_idx]
    return month_gan + month_ji, month_gan, month_ji

def date_to_jd(year, month, day):
    y = year; m = month
    if m <= 2: y -= 1; m += 12
    a = math.floor(y / 100); b = 2 - a + math.floor(a / 4)
    return int(math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524)

def get_day_ganji(year, month, day):
    jd = date_to_jd(year, month, day)
    day_stem_idx = (jd + 9) % 10; day_branch_idx = (jd + 1) % 12
    return GAN[day_stem_idx] + JI[day_branch_idx], GAN[day_stem_idx], JI[day_branch_idx]

def get_time_ganji(day_gan_char, hour, minute):
    cur_time_float = hour + minute/60.0
    siji_char, siji_order_idx = None, -1
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0; end_float = eh + em/60.0
        if ji_name == "자":
            if cur_time_float >= start_float or cur_time_float <= end_float: siji_char,siji_order_idx=ji_name,order_idx;break
        elif start_float <= cur_time_float < end_float: siji_char,siji_order_idx=ji_name,order_idx;break
    if siji_char is None: return "오류(시지판단불가)", "", ""
    try: dg_idx = GAN.index(day_gan_char)
    except ValueError: return "오류(알수없는일간)", "", ""
    sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: return "오류(일간→시간맵)", "", ""
    time_gan_idx = (start_gan_idx_for_ja_hour + siji_order_idx) % 10
    return GAN[time_gan_idx] + siji_char, GAN[time_gan_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data_dict):
    if not isinstance(birth_dt, datetime): return ["오류(잘못된 생년월일 객체)"], 0, False
    try: gan_index = GAN.index(year_gan_char)
    except ValueError: return [f"오류(알 수 없는 연간: {year_gan_char})"], 0, False
    is_yang_year = gan_index % 2 == 0
    is_sunhaeng = (is_yang_year and gender == "남성") or (not is_yang_year and gender == "여성")
    relevant_terms_for_daewoon = []
    if solar_data_dict is None: return ["오류(절기 데이터 누락)"], 0, is_sunhaeng
    for yr_offset in [-1, 0, 1]:
        year_to_check = birth_dt.year + yr_offset
        year_terms = solar_data_dict.get(year_to_check, {})
        for term_name, term_dt_obj in year_terms.items():
            if term_name in SAJU_MONTH_TERMS_ORDER:
                relevant_terms_for_daewoon.append({'name': term_name, 'datetime': term_dt_obj})
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime'])
    if not relevant_terms_for_daewoon: return ["오류(대운 계산용 절기 부족)"], 0, is_sunhaeng
    target_term_dt = None
    if is_sunhaeng:
        for term_info in relevant_terms_for_daewoon:
            if term_info['datetime'] > birth_dt: target_term_dt = term_info['datetime']; break
    else:
        for term_info in reversed(relevant_terms_for_daewoon):
            if term_info['datetime'] < birth_dt: target_term_dt = term_info['datetime']; break
    if target_term_dt is None: return ["오류(대운 목표 절기 탐색 실패)"], 0, is_sunhaeng
    days_difference = abs((target_term_dt - birth_dt).total_seconds() / (24 * 3600.0))
    daewoon_start_age = max(1, int(round(days_difference / 3.0)))
    if month_gan_char is None or month_ji_char is None: return ["오류(월주 정보 누락)"], daewoon_start_age, is_sunhaeng
    month_ganji_str = month_gan_char + month_ji_char
    current_month_gapja_idx = -1
    for idx in range(60):
        if get_ganji_from_index(idx) == month_ganji_str: current_month_gapja_idx = idx; break
    if current_month_gapja_idx == -1: return ["오류(월주를 60갑자로 변환 실패)"], daewoon_start_age, is_sunhaeng
    daewoon_list_output = []
    birth_year_solar = birth_dt.year
    for i_period in range(10):
        current_daewoon_man_age = daewoon_start_age + (i_period * 10)
        current_daewoon_start_solar_year = birth_year_solar + current_daewoon_man_age
        gapja_offset = i_period + 1
        next_gapja_idx = (current_month_gapja_idx + (gapja_offset if is_sunhaeng else -gapja_offset) + 6000) % 60
        daewoon_ganji_str = get_ganji_from_index(next_gapja_idx)
        daewoon_list_output.append(f"만 {current_daewoon_man_age}세 ({current_daewoon_start_solar_year}년~): {daewoon_ganji_str}")
    return daewoon_list_output, daewoon_start_age, is_sunhaeng

def get_seun_list(start_year, n=10):
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    output_wolun = []
    try: ref_date_for_start_month = datetime(base_year, base_month, 1, 12, 0)
    except ValueError: return [(f"오류: 잘못된 기준월 {base_year}-{base_month}", "계산불가")]
    start_saju_year = get_saju_year(ref_date_for_start_month, solar_data_dict)
    start_year_ganji_full, start_year_gan, _ = get_year_ganji(start_saju_year)
    if "오류" in start_year_ganji_full: return [(f"오류: 시작 사주년도({start_saju_year}) 연간 계산 실패", "계산불가")]
    _, _, start_month_ji = get_month_ganji(start_year_gan, ref_date_for_start_month, solar_data_dict)
    if "오류" in start_month_ji or not start_month_ji: return [(f"오류: 시작월주 계산 실패 (기준일: {base_year}-{base_month}-01)", "계산불가")]
    try: start_month_idx = SAJU_MONTH_BRANCHES.index(start_month_ji)
    except ValueError: return [(f"오류: 알 수 없는 시작월 지지 ({start_month_ji})", "계산불가")]
    month_representative_details = [("인",15,0,2),("묘",15,0,3),("진",15,0,4),("사",15,0,5),("오",15,0,6),("미",15,0,7),("신",15,0,8),("유",15,0,9),("술",15,0,10),("해",15,0,11),("자",15,0,12),("축",15,1,1)]
    for i in range(n):
        current_month_saju_idx = (start_month_idx + i) % 12
        current_saju_year = start_saju_year + (start_month_idx + i) // 12
        current_year_ganji_full, year_gan_for_wolun, _ = get_year_ganji(current_saju_year)
        if "오류" in current_year_ganji_full: output_wolun.append((f"{current_saju_year}-??","오류(연간계산실패)")); continue
        _, representative_day, solar_year_offset, representative_solar_month = month_representative_details[current_month_saju_idx]
        try: dummy_dt_solar_year = current_saju_year + solar_year_offset; dummy_birth_dt_for_wolun = datetime(dummy_dt_solar_year, representative_solar_month, representative_day, 12, 0)
        except ValueError: output_wolun.append((f"{current_saju_year + solar_year_offset}-{representative_solar_month:02d} (오류)","오류(대표날짜생성실패)")); continue
        wolun_ganji, _, _ = get_month_ganji(year_gan_for_wolun, dummy_birth_dt_for_wolun, solar_data_dict)
        display_label = f"{dummy_birth_dt_for_wolun.year}-{dummy_birth_dt_for_wolun.month:02d}"
        actual_wolun_ganji = wolun_ganji if "오류" not in wolun_ganji else wolun_ganji
        output_wolun.append((display_label, actual_wolun_ganji))
    return output_wolun

def get_ilun_list(year_val, month_val, day_val, n=10):
    base_dt = datetime(year_val, month_val, day_val); output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji,_,_ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

def get_12_unseong(cheon_gan, ji_ji):
    if not cheon_gan or not ji_ji or cheon_gan == "?" or ji_ji == "?": return "?"
    if cheon_gan in _12_UNSEONG_MAP_DATA and ji_ji in _12_UNSEONG_MAP_DATA[cheon_gan]:
        return _12_UNSEONG_MAP_DATA[cheon_gan][ji_ji]
    return "계산불가"

# ───────────────────────────────
# 오행, 십신, 신강/신약, 격국, 합충, 신살, 용신/기신 계산 및 설명 함수들
# (이전에 제공된 모든 관련 함수들 여기에 포함: calculate_ohaeng_sipshin_strengths, ..., get_gaewoon_tips_html)
# ───────────────────────────────
def calculate_ohaeng_sipshin_strengths(saju_8char_details):
    day_master_gan = saju_8char_details["day_gan"]
    chars_to_analyze = [(saju_8char_details[pk.replace("간","").replace("지","") + ("_gan" if "간" in pk else "_ji")], pk) for pk in POSITION_KEYS_ORDERED]
    ohaeng_strengths = {o: 0.0 for o in OHENG_ORDER}
    sipshin_strengths = {s: 0.0 for s in SIPSHIN_ORDER}
    def get_sipshin(dm_gan, other_gan): return SIPSHIN_MAP.get(dm_gan, {}).get(other_gan)
    for char_val, position_key in chars_to_analyze:
        weight = POSITIONAL_WEIGHTS.get(position_key, 0.0)
        is_gan = "간" in position_key
        if is_gan:
            ohaeng = GAN_TO_OHENG.get(char_val); sipshin = get_sipshin(day_master_gan, char_val)
            if ohaeng: ohaeng_strengths[ohaeng] += weight
            if sipshin: sipshin_strengths[sipshin] += weight
        else: # 지지
            if char_val in JIJI_JANGGAN:
                for janggan_char, proportion in JIJI_JANGGAN[char_val].items():
                    ohaeng = GAN_TO_OHENG.get(janggan_char); sipshin = get_sipshin(day_master_gan, janggan_char)
                    if ohaeng: ohaeng_strengths[ohaeng] += weight * proportion
                    if sipshin: sipshin_strengths[sipshin] += weight * proportion
    for o in OHENG_ORDER: ohaeng_strengths[o] = round(ohaeng_strengths[o], 1)
    for s in SIPSHIN_ORDER: sipshin_strengths[s] = round(sipshin_strengths[s], 1)
    return ohaeng_strengths, sipshin_strengths

def get_ohaeng_summary_explanation(ohaeng_counts):
    # ... (이전 답변의 함수 내용과 동일)
    explanation = "오행 분포는 사주의 에너지 균형을 보여줍니다. "
    threshold = 1.5 
    if not ohaeng_counts: return explanation + "오행 정보를 계산할 수 없습니다."
    sorted_ohaeng = sorted(ohaeng_counts.items(), key=lambda item: item[1], reverse=True)
    if sorted_ohaeng[0][1] > threshold * 1.5 :
        explanation += f"특히 {sorted_ohaeng[0][0]}(이)가 {sorted_ohaeng[0][1]}점으로 가장 강한 기운을 가집니다. "
    if sorted_ohaeng[-1][1] < threshold / 1.5 and sorted_ohaeng[-1][1] < sorted_ohaeng[0][1] / 2:
        explanation += f"반면, {sorted_ohaeng[-1][0]}(이)가 {sorted_ohaeng[-1][1]}점으로 상대적으로 약한 편입니다. "
    explanation += "전체적인 균형과 조화를 이루는 것이 중요합니다."
    return explanation

def get_sipshin_summary_explanation(sipshin_counts, day_master_gan):
    # ... (이전 답변의 함수 내용과 동일)
    explanation = "십신은 일간(나)을 기준으로 다른 글자와의 관계를 나타내며, 사회적 관계, 성향, 재능 등을 유추해볼 수 있습니다. "
    threshold = 1.5 
    strong_sibsins = []
    for sibshin_name in SIPSHIN_ORDER:
        if (sipshin_counts.get(sibshin_name, 0.0)) >= threshold:
            strong_sibsins.append(f"{sibshin_name}({sipshin_counts.get(sibshin_name, 0.0)})")
    if strong_sibsins:
        explanation += f"이 사주에서는 {', '.join(strong_sibsins)}의 영향력이 두드러질 수 있습니다. "
        temp_explanations = []
        for s_info in strong_sibsins:
            s_name = s_info.split('(')[0]
            if s_name in ["비견", "겁재"]: temp_explanations.append("주체성/독립심/경쟁심")
            elif s_name in ["식신", "상관"]: temp_explanations.append("표현력/창의력/기술 관련 재능")
            elif s_name in ["편재", "정재"]: temp_explanations.append("현실감각/재물운용/활동성")
            elif s_name in ["편관", "정관"]: temp_explanations.append("책임감/명예/조직 적응력")
            elif s_name in ["편인", "정인"]: temp_explanations.append("학문/수용성/직관력")
        unique_explanations = list(set(temp_explanations))
        if unique_explanations:
            explanation += f" 이는 {', '.join(unique_explanations)} 등이 발달했을 가능성을 시사합니다. "
    else:
        explanation += "특별히 한쪽으로 치우치기보다는 여러 십신의 특성이 비교적 균형 있게 나타날 수 있습니다. "
    explanation += "각 십신의 긍정적인 면을 잘 발휘하고 보완하는 것이 중요합니다."
    return explanation

def determine_shinkang_shinyak(sipshin_strengths):
    # ... (이전 답변의 함수 내용과 동일)
    my_energy = sum(sipshin_strengths.get(s, 0.0) for s in ["비견", "겁재", "편인", "정인"])
    opponent_energy = sum(sipshin_strengths.get(s, 0.0) for s in ["식신", "상관", "편재", "정재", "편관", "정관"])
    score_diff = my_energy - opponent_energy
    if score_diff >= 1.5: return "신강"
    elif score_diff <= -1.5: return "신약"
    elif -0.5 <= score_diff <= 0.5: return "중화"
    elif score_diff > 0.5: return "약간 신강"
    else: return "약간 신약"

def get_shinkang_explanation(shinkang_status_str):
    # ... (이전 답변의 함수 내용과 동일)
    explanations = {
        "신강": "일간(자신)의 힘이 강한 편입니다. 주체적이고 독립적인 성향이 강하며, 자신의 의지대로 일을 추진하는 힘이 있습니다. 때로는 자기 주장이 강해 주변과의 마찰이 생길 수 있으니 유연성을 갖추는 것이 좋습니다.",
        "신약": "일간(자신)의 힘이 다소 약한 편입니다. 주변의 도움이나 환경의 영향에 민감하며, 신중하고 사려 깊은 모습을 보일 수 있습니다. 자신감을 갖고 꾸준히 자신의 역량을 키워나가는 것이 중요하며, 좋은 운의 흐름을 잘 활용하는 지혜가 필요합니다.",
        "중화": "일간(자신)의 힘이 비교적 균형을 이루고 있습니다. 상황에 따라 유연하게 대처하는 능력이 있으며, 원만한 대인관계를 맺을 수 있는 좋은 구조입니다. 다만, 때로는 뚜렷한 개성이 부족해 보일 수도 있습니다.",
        "약간 신강": "일간(자신)의 힘이 평균보다 조금 강한 편입니다. 자신의 주관을 가지고 일을 처리하면서도 주변과 협력하는 균형 감각을 발휘할 수 있습니다.",
        "약간 신약": "일간(자신)의 힘이 평균보다 조금 약한 편입니다. 신중하고 주변 상황을 잘 살피며, 인내심을 가지고 목표를 추구하는 경향이 있습니다. 주변의 조언을 경청하는 자세가 도움이 될 수 있습니다."
    }
    return explanations.get(shinkang_status_str, "일간의 강약 상태에 대한 설명을 준비 중입니다.")

def _detect_special_gekuk(day_gan_char, month_ji_char):
    if L_NOK_MAP.get(day_gan_char) == month_ji_char: return "건록격"
    if day_gan_char in YANGIN_JI_MAP and YANGIN_JI_MAP.get(day_gan_char) == month_ji_char: return "양인격"
    return None

def _detect_togan_gekuk(day_gan_char, month_gan_char, month_ji_char):
    if month_ji_char in JIJI_JANGGAN and month_gan_char in JIJI_JANGGAN[month_ji_char]:
        sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(month_gan_char)
        if sipshin_type: return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_month_branch_primary(day_gan_char, month_ji_char):
    if month_ji_char in JIJI_JANGGAN and JIJI_JANGGAN[month_ji_char]:
        primary_hidden_stem = max(JIJI_JANGGAN[month_ji_char].items(), key=lambda item: item[1])[0]
        if primary_hidden_stem:
            sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(primary_hidden_stem)
            if sipshin_type: return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_strengths(sipshin_strengths_dict):
    if not sipshin_strengths_dict: return None
    strongest_sipshin_name = None; max_strength = -1
    for sipshin_name in SIPSHIN_ORDER:
        strength_val = sipshin_strengths_dict.get(sipshin_name, 0.0)
        if strength_val > max_strength: max_strength = strength_val; strongest_sipshin_name = sipshin_name
    if strongest_sipshin_name and max_strength > 0.5: return SIPSHIN_TO_GYEOK_MAP.get(strongest_sipshin_name, strongest_sipshin_name + "격")
    return "일반격 판정 어려움"

def determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths_dict):
    # ... (이전 답변의 함수 내용과 동일)
    special_gekuk = _detect_special_gekuk(day_gan_char, month_ji_char)
    if special_gekuk: return special_gekuk
    togan_gekuk = _detect_togan_gekuk(day_gan_char, month_gan_char, month_ji_char)
    if togan_gekuk: return togan_gekuk
    month_branch_primary_gekuk = _detect_general_gekuk_from_month_branch_primary(day_gan_char, month_ji_char)
    if month_branch_primary_gekuk: return month_branch_primary_gekuk
    strength_based_gekuk = _detect_general_gekuk_from_strengths(sipshin_strengths_dict)
    if strength_based_gekuk and strength_based_gekuk != "일반격 판정 어려움": return strength_based_gekuk
    elif strength_based_gekuk == "일반격 판정 어려움": return strength_based_gekuk
    return "격국 판정 불가"

def get_gekuk_explanation(gekuk_name_str):
    # ... (이전 답변의 함수 내용과 동일)
    explanations = {
        '건록격': '스스로 자립하여 성공하는 자수성가형 리더 타입입니다! 굳건하고 독립적인 성향을 가졌습니다. (주로 월지에 일간의 건록이 있는 경우)',
        '양인격': '강력한 카리스마와 돌파력을 지녔습니다! 때로는 너무 강한 기운으로 인해 조절이 필요할 수 있지만, 큰일을 해낼 수 있는 저력이 있습니다. (주로 월지에 양일간의 양인이 있는 경우)',
        '비견격': '주체성이 강하고 동료들과 협력하며 목표를 향해 나아가는 타입입니다. 독립심과 자존감이 강한 편입니다.',
        '겁재격': '승부욕과 경쟁심이 강하며, 때로는 과감한 도전도 불사하는 적극적인 면모가 있습니다. 주변과의 협력과 조화를 중요시해야 합니다.',
        '식신격': '낙천적이고 창의적인 아이디어가 풍부하며, 표현력이 좋고 예술적 재능을 지녔을 수 있습니다. 안정적인 의식주를 중시하는 경향이 있습니다.',
        '상관격': '새로운 것을 탐구하고 기존의 틀을 깨려는 혁신가적 기질이 있습니다. 비판적이고 날카로운 통찰력을 지녔지만, 때로는 표현 방식에 유의하여 오해를 피하는 것이 좋습니다.',
        '편재격': '활동적이고 사교성이 뛰어나며 사람들과 어울리는 것을 좋아합니다. 재물에 대한 감각과 운용 능력이 뛰어나며, 스케일이 크고 통이 큰 경향이 있습니다.',
        '정재격': '꼼꼼하고 성실하며 안정적인 것을 선호합니다. 신용을 중요하게 생각하고 계획적인 삶을 추구하며, 재물을 안정적으로 관리하는 능력이 있습니다.',
        '칠살격': '명예를 중시하고 리더십이 있으며, 어려운 상황을 극복하고 위기에서 능력을 발휘하는 카리스마가 있습니다. (편관격과 유사)',
        '정관격': '원칙을 지키는 반듯하고 합리적인 성향입니다. 명예와 안정을 추구하며 조직 생활에 잘 적응하고 책임감이 강합니다.',
        '편인격': '직관력과 예지력이 뛰어나며, 독특한 아이디어나 예술, 철학, 종교 등 정신적인 분야에 재능을 보일 수 있습니다. 다소 생각이 많거나 변덕스러울 수 있습니다.',
        '정인격': '학문과 지식을 사랑하고 인정이 많으며 수용성이 좋습니다. 안정적인 환경에서 능력을 발휘하며, 타인에게 도움을 주는 것을 좋아합니다.',
        '일반격 판정 어려움': '사주의 기운이 복합적이거나 특정 십신의 세력이 두드러지게 나타나지 않아, 하나의 주된 격국으로 정의하기 어렵습니다. 다양한 가능성을 가진 사주로 볼 수 있으며, 운의 흐름에 따라 여러 격의 특성이 발현될 수 있습니다.',
        '격국 판정 불가': '사주의 구조상 특정 격국을 명확히 판정하기 어렵습니다. 이 경우, 사주 전체의 오행 및 십신 분포, 운의 흐름 등을 종합적으로 고려하여 판단하는 것이 좋습니다.'
    }
    if gekuk_name_str == '편관격': gekuk_name_str = '칠살격'
    return explanations.get(gekuk_name_str, f"'{gekuk_name_str}'에 대한 설명을 준비 중입니다. 일반적으로 해당 십신의 특성을 참고할 수 있습니다.")

def analyze_hap_chung_interactions(saju_8char_details):
    # ... (이전 답변의 함수 내용과 동일)
    gans = [saju_8char_details["year_gan"], saju_8char_details["month_gan"], saju_8char_details["day_gan"], saju_8char_details["time_gan"]]
    jis = [saju_8char_details["year_ji"], saju_8char_details["month_ji"], saju_8char_details["day_ji"], saju_8char_details["time_ji"]]
    results = {"천간합": [], "지지육합": [], "지지삼합": [], "지지방합": [], "천간충": [], "지지충": [], "형살(刑殺)": [], "해살(害殺)": [], "파살(破殺)": []}
    found_samhap_banhap_combinations = set()
    gans_with_pos = list(enumerate(gans)); jis_with_pos = list(enumerate(jis))
    for (i_idx, i_gan), (j_idx, j_gan) in itertools.combinations(gans_with_pos, 2):
        pair_sorted = tuple(sorted((i_gan, j_gan))); pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}간({i_gan}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}간({j_gan})"
        if pair_sorted in CHEONGAN_HAP_RULES: results["천간합"].append(f"{pos_str} → {CHEONGAN_HAP_RULES[pair_sorted]} 합")
        if pair_sorted in CHEONGAN_CHUNG_RULES: results["천간충"].append(f"{pos_str.replace('+', '↔')} 충")
    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(jis_with_pos, 2):
        pair_sorted = tuple(sorted((i_ji, j_ji))); pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        if pair_sorted in JIJI_YUKHAP_RULES: results["지지육합"].append(f"{pos_str} → {JIJI_YUKHAP_RULES[pair_sorted]} 합")
        if pair_sorted in JIJI_CHUNG_RULES: results["지지충"].append(f"{pos_str.replace('+', '↔')} 충")
        if pair_sorted in JIJI_HAE_RULES: results["해살(害殺)"].append(f"{pos_str} → {HAE_NAMES.get(pair_sorted, '해')}")
        if pair_sorted in JIJI_PA_RULES: results["파살(破殺)"].append(f"{pos_str} → {PA_NAMES.get(pair_sorted, '파')}")
        if pair_sorted in SANGHYEONG_RULES: results["형살(刑殺)"].append(f"{pos_str} → 자묘 상형(無禮之刑)")
    for (i_idx,i_ji),(j_idx,j_ji),(k_idx,k_ji) in itertools.combinations(jis_with_pos,3):
        combo_sorted = tuple(sorted((i_ji,j_ji,k_ji))); pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}), {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji}), {PILLAR_NAMES_KOR_SHORT[k_idx]}지({k_ji})"
        if combo_sorted in JIJI_SAMHAP_RULES: found_samhap_banhap_combinations.add(combo_sorted); results["지지삼합"].append(f"{pos_str} → {JIJI_SAMHAP_RULES[combo_sorted]}")
        if combo_sorted in JIJI_BANGHAP_RULES: results["지지방합"].append(f"{pos_str} → {JIJI_BANGHAP_RULES[combo_sorted]}")
        if combo_sorted in SAMHYEONG_RULES: results["형살(刑殺)"].append(f"{pos_str} → {SAMHYEONG_RULES[combo_sorted]}")
    for (i_idx,i_ji),(j_idx,j_ji) in itertools.combinations(jis_with_pos,2):
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        for wangji, others in JIJI_BANHAP_WANGJI_CENTERED_RULES.items():
            if (i_ji==wangji and j_ji in others) or (j_ji==wangji and i_ji in others):
                full_samhap_group = next((key for key in JIJI_SAMHAP_RULES if wangji in key and i_ji in key and j_ji in key), None)
                if not (full_samhap_group and full_samhap_group in found_samhap_banhap_combinations):
                    banhap_result_str = f"{pos_str} → {wangji} 기준 반합 ({JIJI_SAMHAP_RULES.get(full_samhap_group, '국 형성')})"
                    if not any(banhap_result_str == item for item in results["지지삼합"]): results["지지삼합"].append(banhap_result_str)
                break
    for jahyeong_char in JAHYEONG_CHARS:
        if jis.count(jahyeong_char) >= 2: positions = [f"{PILLAR_NAMES_KOR_SHORT[i]}지({jis[i]})" for i,v in enumerate(jis) if v==jahyeong_char]; results["형살(刑殺)"].append(f"{', '.join(positions)} ({jahyeong_char}{jahyeong_char}) → 자형(自刑)")
    return results

def get_hap_chung_detail_explanation(found_interactions_dict):
    # ... (이전 답변의 함수 내용과 동일)
    if not found_interactions_dict or not any(v for v in found_interactions_dict.values()): return "<p>특별히 두드러지는 합충형해파의 관계가 나타나지 않습니다. 비교적 안정적인 구조일 수 있습니다.</p>"
    explanation_parts = []
    interaction_explanations = {
        "천간합": "정신적, 사회적 관계에서의 연합, 변화 또는 새로운 기운의 생성 가능성을 나타냅니다.", "지지육합": "개인적인 관계, 애정, 또는 비밀스러운 합의나 내부적인 결속을 의미할 수 있습니다.",
        "지지삼합": "강력한 사회적 합으로, 특정 목표를 향한 강력한 추진력이나 세력 형성을 나타냅니다. (반합 포함)", "지지방합": "가족, 지역, 동료 등 혈연이나 지연에 기반한 강한 결속력이나 세력 확장을 의미합니다.",
        "천간충": "생각의 충돌, 가치관의 대립, 또는 외부 환경으로부터의 갑작스러운 변화나 자극, 정신적 스트레스를 암시합니다.", "지지충": "현실적인 변화, 이동, 관계의 단절 또는 새로운 시작, 건강상의 주의 등을 나타낼 수 있습니다. 역동적인 사건의 발생 가능성을 의미합니다.",
        "형살(刑殺)": "조정, 갈등, 법적 문제, 수술, 배신, 또는 내적 갈등과 성장통 등을 나타낼 수 있습니다. 때로는 정교함이나 전문성을 요구하는 일과도 관련됩니다.",
        "해살(害殺)": "관계에서의 방해, 질투, 오해, 또는 건강상의 문제(주로 만성적) 등을 암시합니다. 예기치 않은 손실이나 어려움을 겪을 수 있습니다.",
        "파살(破殺)": "깨짐, 분리, 손상, 계획의 차질, 관계의 갑작스러운 단절 등을 나타낼 수 있습니다. 기존의 것이 깨지고 새로워지는 과정을 의미하기도 합니다."}
    for key, found_list in found_interactions_dict.items():
        if found_list: desc = interaction_explanations.get(key); explanation_parts.append(f"<li><strong>{key}:</strong> {desc}</li>") if desc else None
    if not explanation_parts: return "<p>구체적인 합충형해파 관계에 대한 설명을 준비 중입니다.</p>"
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

def analyze_shinsal(saju_8char_details):
    # ... (이전 답변의 함수 내용과 동일)
    ilgan_char = saju_8char_details["day_gan"]; all_jis = [saju_8char_details[k] for k in ["year_ji","month_ji","day_ji","time_ji"]]
    pillar_ganjis_str = [saju_8char_details[p+"_gan"]+saju_8char_details[p+"_ji"] for p in ["year","month","day","time"]]
    ilju_ganji_str = pillar_ganjis_str[2]; found_shinsals_set = set()
    if ilgan_char in CHEONEULGWIIN_MAP: [found_shinsals_set.add(f"천을귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})") for i,j in enumerate(all_jis) if j in CHEONEULGWIIN_MAP[ilgan_char]]
    if ilgan_char in MUNCHANGGWIIN_MAP: [found_shinsals_set.add(f"문창귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})") for i,j in enumerate(all_jis) if j == MUNCHANGGWIIN_MAP[ilgan_char]]
    yj,dj = saju_8char_details["year_ji"],saju_8char_details["day_ji"]; dowy,dowd = DOHWASAL_MAP.get(yj),DOHWASAL_MAP.get(dj); ymy,ymd=YEONGMASAL_MAP.get(yj),YEONGMASAL_MAP.get(dj); hgy,hgd=HWAGAESAL_MAP.get(yj),HWAGAESAL_MAP.get(dj)
    for i,j in enumerate(all_jis):
        if dowy and j==dowy: found_shinsals_set.add(f"도화살: 연지({yj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
        if dowd and j==dowd and dowd!=dowy: found_shinsals_set.add(f"도화살: 일지({dj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
        if ymy and j==ymy: found_shinsals_set.add(f"역마살: 연지({yj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
        if ymd and j==ymd and ymd!=ymy: found_shinsals_set.add(f"역마살: 일지({dj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
        if hgy and j==hgy: found_shinsals_set.add(f"화개살: 연지({yj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
        if hgd and j==hgd and hgd!=hgy: found_shinsals_set.add(f"화개살: 일지({dj}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})")
    if ilgan_char in YANGIN_JI_MAP: [found_shinsals_set.add(f"양인살: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[i]}지({j})") for i,j in enumerate(all_jis) if j == YANGIN_JI_MAP[ilgan_char]]
    if ilju_ganji_str in GOEGANGSAL_ILJU_LIST: found_shinsals_set.add(f"괴강살: 일주({ilju_ganji_str})")
    for i,pgs in enumerate(pillar_ganjis_str):
        if pgs in BAEKHODAESAL_GANJI_LIST: found_shinsals_set.add(f"백호대살: {PILLAR_NAMES_KOR[i]}({pgs})")
    for (i_idx,i_ji),(j_idx,j_ji) in itertools.combinations(list(enumerate(all_jis)),2):
        if tuple(sorted((i_ji,j_ji))) in GWIMUNGWANSAL_PAIRS: found_shinsals_set.add(f"귀문관살: {PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})")
    try:
        ilgan_idx=GAN.index(ilgan_char); ilji_idx=JI.index(dj)
        ilju_gapja_idx = next((i for i in range(60) if GAN[i%10]==ilgan_char and JI[i%12]==dj), -1)
        if ilju_gapja_idx != -1:
            gongmang_jis = JI[(ilju_gapja_idx+10)%12], JI[(ilju_gapja_idx+11)%12]
            found_shinsals_set.add(f"공망(空亡): 일주({ilju_ganji_str}) 기준 {gongmang_jis[0]}, {gongmang_jis[1]} 공망")
            found_gongmang_pillars = [f"{PILLAR_NAMES_KOR[i]}의 {j}" for i,j in enumerate(all_jis) if j in gongmang_jis]
            if found_gongmang_pillars: found_shinsals_set.add(f"  └ ({', '.join(found_gongmang_pillars)})가 공망에 해당합니다.")
    except IndexError: pass
    return sorted(list(found_shinsals_set))

def get_shinsal_detail_explanation(found_shinsals_list):
    # ... (이전 답변의 함수 내용과 동일)
    if not found_shinsals_list: return "<p>특별히 나타나는 주요 신살이 없습니다.</p>"
    explanation_parts = []; added_explanations_keys = set()
    main_shinsal_explanations = { "천을귀인": "어려울 때 귀인의 도움을 받거나 위기를 넘기는 행운이 따르는 길성 중의 길성입니다.", "문창귀인": "학문, 지혜, 총명함을 나타내며 글재주나 시험운 등에 긍정적인 영향을 줄 수 있습니다.", "도화살": "매력, 인기, 예술적 감각을 의미하며, 이성에게 인기가 많을 수 있으나 때로는 구설을 조심해야 합니다.", "역마살": "활동성, 이동, 변화, 여행, 해외와의 인연 등을 나타냅니다. 한 곳에 정착하기보다 변화를 추구하는 성향일 수 있습니다.", "화개살": "예술, 종교, 학문, 철학 등 정신세계와 관련된 분야에 재능이나 인연이 깊을 수 있습니다. 때로 고독감을 느끼기도 합니다.", "양인살": "강한 에너지, 카리스마, 독립심, 경쟁심을 나타냅니다. 순탄할 때는 큰 성취를 이루지만, 운이 나쁠 때는 과격함이나 사건사고를 조심해야 합니다.", "괴강살": "매우 강한 기운과 리더십, 총명함을 나타냅니다. 극단적인 성향이나 고집을 주의해야 하며, 큰 인물이 될 가능성도 있습니다.", "백호대살": "강한 기운으로 인해 급작스러운 사건, 사고, 질병 등을 경험할 수 있음을 암시하므로 평소 건강과 안전에 유의하는 것이 좋습니다.", "귀문관살": "예민함, 직관력, 영감, 독특한 정신세계를 나타냅니다. 때로는 신경과민, 변덕, 집착 등으로 나타날 수 있어 마음의 안정이 중요합니다.", "공망": "해당 글자의 영향력이 약화되거나 공허함을 의미합니다. 정신적인 활동, 종교, 철학 등에 관심을 두거나, 예상 밖의 결과나 변화를 경험할 수 있습니다."}
    for shinsal_item_str in found_shinsals_list:
        for shinsal_key, desc in main_shinsal_explanations.items():
            if shinsal_key in shinsal_item_str and shinsal_key not in added_explanations_keys: explanation_parts.append(f"<li><strong>{shinsal_key}:</strong> {desc}</li>"); added_explanations_keys.add(shinsal_key)
    if not explanation_parts: return "<p>발견된 신살에 대한 구체적인 설명을 준비 중입니다.</p>"
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

def determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_str):
    # ... (이전 답변의 함수 내용과 동일)
    ilgan_ohaeng = GAN_TO_OHENG.get(day_gan_char)
    if not ilgan_ohaeng: return {"yongshin":[], "gishin":[], "html":"<p>일간의 오행을 알 수 없어 용신/기신을 판단할 수 없습니다.</p>"}
    y_cand, g_cand = [], []
    sik상,jae성,gwan성,in성,bi겁 = OHENG_PRODUCES_MAP.get(ilgan_ohaeng),OHENG_CONTROLS_MAP.get(ilgan_ohaeng),OHENG_IS_CONTROLLED_BY_MAP.get(ilgan_ohaeng),OHENG_HELPER_MAP.get(ilgan_ohaeng),ilgan_ohaeng
    if "신강" in shinkang_status_str:
        if sik상: y_cand.append(sik상);
        if jae성: y_cand.append(jae성);
        if gwan성: y_cand.append(gwan성)
        if in성: g_cand.append(in성);
        if bi겁: g_cand.append(bi겁)
    elif "신약" in shinkang_status_str:
        if in성: y_cand.append(in성);
        if bi겁: y_cand.append(bi겁)
        if sik상: g_cand.append(sik상);
        if jae성: g_cand.append(jae성);
        if gwan성: g_cand.append(gwan성)
    elif "중화" in shinkang_status_str: return {"yongshin":[],"gishin":[],"html":"<p>중화 사주로 판단됩니다...</p>"} # (설명 생략)
    else: return {"yongshin":[],"gishin":[],"html":"<p>일간 강약 상태 불명확...</p>"} # (설명 생략)
    uy,ug = sorted(list(set(y_cand))),sorted(list(set(g_cand)))
    html_parts = []
    if uy: html_parts.append(f"<p>유력한 용신(喜神) 후보 오행: {', '.join([f'<span style=\"color:#15803d; font-weight:bold;\">{o}({OHENG_TO_HANJA.get(o, \"\")})</span>' for o in uy])}</p>")
    else: html_parts.append("<p>용신(喜神)으로 특정할 만한 오행을 명확히 구분하기 어렵습니다.</p>")
    if ug: html_parts.append(f"<p>주의가 필요한 기신(忌神) 후보 오행: {', '.join([f'<span style=\"color:#b91c1c; font-weight:bold;\">{o}({OHENG_TO_HANJA.get(o, \"\")})</span>' for o in ug])}</p>")
    else: html_parts.append("<p>특별히 기신(忌神)으로 강하게 작용할 만한 오행이 두드러지지 않을 수 있습니다.</p>")
    return {"yongshin":uy, "gishin":ug, "html":"".join(html_parts)}

def get_gaewoon_tips_html(yongshin_list):
    # ... (이전 답변의 함수 내용과 동일)
    if not yongshin_list: return ""
    tips_html = "<h5 style='color: #047857; margin-top: 0.8rem; margin-bottom: 0.3rem; font-size:1em;'>🍀 간단 개운법 (용신 활용)</h5><ul style='list-style:none; padding-left:0; font-size:0.9em;'>"
    gaewoon_tips_data = {"목":"<li><strong style='color:#15803d;'>목(木) 용신:</strong> 동쪽 방향, 푸른색/초록색 계열 아이템 활용. 숲이나 공원 산책, 식물 키우기, 교육/문화/기획 관련 활동.</li>", "화":"<li><strong style='color:#15803d;'>화(火) 용신:</strong> 남쪽 방향, 붉은색/분홍색/보라색 계열 아이템 활용. 밝고 따뜻한 환경 조성, 예체능/방송/조명/열정적인 활동.</li>", "토":"<li><strong style='color:#15803d;'>토(土) 용신:</strong> 중앙(거주지 중심), 노란색/황토색/베이지색 계열 아이템 활용. 안정적이고 편안한 환경, 명상, 신용을 중시하는 활동, 등산.</li>", "금":"<li><strong style='color:#15803d;'>금(金) 용신:</strong> 서쪽 방향, 흰색/은색/금색 계열 아이템 활용. 단단하고 정돈된 환경, 금속 액세서리, 결단력과 의리를 지키는 활동, 악기 연주.</li>", "수":"<li><strong style='color:#15803d;'>수(水) 용신:</strong> 북쪽 방향, 검은색/파란색/회색 계열 아이템 활용. 물가나 조용하고 차분한 환경, 지혜를 활용하는 활동, 명상이나 충분한 휴식.</li>"}
    for yo in yongshin_list: tips_html += gaewoon_tips_data.get(yo, f"<li>{yo}({OHENG_TO_HANJA.get(yo,'')}) 용신에 대한 개운법 정보를 준비 중입니다.</li>")
    tips_html += "</ul><p style='font-size:0.8rem; color:#555; margin-top:0.5rem;'>* 위 내용은 일반적인 개운법이며, 개인의 전체 사주 구조와 상황에 따라 다를 수 있습니다. 참고용으로 활용하세요.</p>"
    return tips_html

# ───────────────────────────────
# Streamlit UI 설정 및 실행
# ───────────────────────────────
# (이 부분은 이전 답변에서 제안된 스타일링 및 UI 구조를 그대로 사용합니다.)
# (st.set_page_config, st.markdown(<style>...), st.title, 사이드바 입력, 버튼 클릭 로직, 결과 표시 로직 등)

st.set_page_config(layout="wide", page_title="🔮 마음 우주 히든맵 계산기")

PRIMARY_COLOR = "#8a70d6"; SECONDARY_COLOR = "#ff9ed8"; BACKGROUND_COLOR = "#0c0a1f"
TEXT_COLOR = "#e0e0ff"; TEXT_MUTED_COLOR = "#a5b4fc"; CARD_BG_COLOR = "rgba(25, 22, 48, 0.75)"
BORDER_COLOR = "rgba(138, 112, 214, 0.4)"; HIGHLIGHT_YELLOW = "#fde047"; HIGHLIGHT_ORANGE = "#fb923c"

st.markdown(f"""<style>/* ... (이전 답변의 전체 CSS 내용) ... */</style>""", unsafe_allow_html=True) # CSS 내용 축약
# 이전 답변에서 제공된 CSS 전체를 여기에 복사해 넣어야 합니다.
# 예시로 일부만 남겨두었습니다.
st.markdown(f"""
<style>
    .stApp {{ background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; }}
    h1, h2, h3, h4, h5, h6 {{ color: {SECONDARY_COLOR}; }}
    .st-emotion-cache-10trblm h1 {{
         background: linear-gradient(to right, {PRIMARY_COLOR}, {SECONDARY_COLOR}, {HIGHLIGHT_YELLOW});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;
    }}
    .custom-card {{ background-color: {CARD_BG_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 6px 20px rgba(0,0,0,0.25); }}
    .custom-card h4 {{ color: {HIGHLIGHT_YELLOW}; margin-bottom: 0.8rem;}}
    .custom-card p {{ color: {TEXT_MUTED_COLOR}; font-size: 0.95rem; }}
    .icon-style {{ color: {PRIMARY_COLOR}; margin-right: 8px; }}
    /* ... (나머지 CSS 규칙들) ... */
</style>
""", unsafe_allow_html=True)


st.markdown(f"""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="font-size: 2.8em; font-weight: 700; margin-bottom: 0.3em;
               background: linear-gradient(to right, {PRIMARY_COLOR}, {SECONDARY_COLOR}, {HIGHLIGHT_YELLOW});
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🔮 마음 우주 히든맵 계산기 🌌
    </h1>
    <p style="font-size: 1.2em; color: {TEXT_MUTED_COLOR};">
        당신의 내면 우주를 탐험하고, 숨겨진 코드를 발견하세요!
    </p>
</div>
""", unsafe_allow_html=True)

if 'saju_calculated_once' not in st.session_state: st.session_state.saju_calculated_once = False
if 'interpretation_segments' not in st.session_state: st.session_state.interpretation_segments = []
if 'show_interpretation_guide_on_click' not in st.session_state: st.session_state.show_interpretation_guide_on_click = False

st.sidebar.markdown(f"<h2 style='color:{HIGHLIGHT_YELLOW}; font-size:1.5em;'><i class='fas fa-user-astronaut icon-style'></i>1. 출생 정보 입력</h2>", unsafe_allow_html=True)
calendar_type = st.sidebar.radio("달력 유형", ("양력", "음력"), index=0, horizontal=True, key="cal_type_key")
is_leap_month = False
if calendar_type == "음력": is_leap_month = st.sidebar.checkbox("윤달", help="음력 생일이 윤달인 경우 체크", key="leap_month_key")

current_year_for_input = datetime.now().year
min_year_default, max_year_default = 1900, 2100
min_input_year = min(solar_data.keys()) if solar_data else min_year_default
max_input_year = max(solar_data.keys()) if solar_data else max_year_default

by = st.sidebar.number_input("출생 연도", min_input_year, max_input_year, 1990, help=f"{calendar_type} {min_input_year}~{max_input_year}년", key="birth_year_key")
bm = st.sidebar.number_input("출생 월", 1, 12, 6, key="birth_month_key")
bd = st.sidebar.number_input("출생 일", 1, 31, 15, key="birth_day_key")
bh = st.sidebar.number_input("출생 시", 0, 23, 12, key="birth_hour_key")
bmin = st.sidebar.number_input("출생 분", 0, 59, 30, key="birth_min_key")
gender = st.sidebar.radio("성별", ("남성","여성"), horizontal=True, index=0, key="gender_key")

st.sidebar.markdown(f"<hr style='margin-top:1.5rem; margin-bottom:1.5rem; border-top: 1px solid {BORDER_COLOR};'>", unsafe_allow_html=True)
st.sidebar.markdown(f"<h2 style='color:{HIGHLIGHT_YELLOW}; font-size:1.5em;'><i class='fas fa-calendar-alt icon-style'></i>2. 운세 기준일 (양력)</h2>", unsafe_allow_html=True)
today = datetime.now()
ty = st.sidebar.number_input("기준 연도", min_input_year, max_input_year + 10, today.year, help=f"양력 기준년도 ({min_input_year}~{max_input_year+10} 범위)", key="target_year_key")
tm = st.sidebar.number_input("기준 월", 1, 12, today.month, key="target_month_key_v2")
td = st.sidebar.number_input("기준 일", 1, 31, today.day, key="target_day_key_v2")

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary", key="run_calc_button_key"):
    st.session_state.interpretation_segments = []
    st.session_state.saju_calculated_once = False
    st.session_state.show_interpretation_guide_on_click = False
    birth_dt_input_valid = True
    birth_dt = None
    if calendar_type == "양력":
        try: birth_dt = datetime(by,bm,bd,bh,bmin)
        except ValueError: st.error("❌ 유효하지 않은 양력 날짜/시간입니다."); birth_dt_input_valid=False; st.stop()
    else: # 음력
        try:
            lunar_date = LunarDate(by, bm, bd, is_leap_month)
            solar_date = lunar_date.toSolarDate()
            birth_dt = datetime(solar_date.year, solar_date.month, solar_date.day, bh, bmin)
            st.sidebar.success(f"음력 {by}년 {bm}월 {bd}일{' (윤달)' if is_leap_month else ''} → 양력 {birth_dt.strftime('%Y-%m-%d')}")
        except Exception as e: st.error(f"❌ 음력 날짜 변환 오류: {e}"); birth_dt_input_valid=False; st.stop()

    if birth_dt_input_valid and birth_dt:
        saju_year_val = get_saju_year(birth_dt, solar_data)
        year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
        month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
        day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day)
        time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)

        year_unseong = get_12_unseong(year_gan_char, year_ji_char)
        month_unseong = get_12_unseong(month_gan_char, month_ji_char)
        day_unseong = get_12_unseong(day_gan_char, day_ji_char)
        time_unseong = get_12_unseong(time_gan_char, time_ji_char)

        ilgan_potae_vs_year = get_12_unseong(day_gan_char, year_ji_char) if year_ji_char and year_ji_char not in ["?", "오류"] else "?"
        ilgan_potae_vs_month = get_12_unseong(day_gan_char, month_ji_char) if month_ji_char and month_ji_char not in ["?", "오류"] else "?"
        ilgan_potae_vs_day = day_unseong
        ilgan_potae_vs_time = get_12_unseong(day_gan_char, time_ji_char) if time_ji_char and time_ji_char not in ["?", "오류"] else "?"

        # --- 결과 표시 부분 시작 ---
        st.markdown(f"### <i class='fas fa-user icon-style' style='color:{HIGHLIGHT_YELLOW};'></i> 기본 정보", unsafe_allow_html=True)
        # ... (기본 정보 표시 로직 - 이전 답변의 UI 개선 로직 적용) ...
        basic_info_card_content = f"""<p><strong>입력 생년월일시:</strong> {calendar_type} {by}년 {bm}월 {bd}일{' (윤달)' if calendar_type == "음력" and is_leap_month else ''} {bh:02d}시 {bmin:02d}분 ({gender})</p>"""
        if calendar_type == "음력": basic_info_card_content += f"<p><strong>양력 환산 생일:</strong> {birth_dt.strftime('%Y년 %m월 %d일')}</p>"
        today_date = datetime.now(); age_calculated = calculate_age(birth_dt, today_date)
        basic_info_card_content += f"<p><strong>현재 만 나이:</strong> {age_calculated}세 (기준일: {today_date.strftime('%Y년 %m월 %d일')})</p>"
        st.markdown(f"<div class='custom-card'>{basic_info_card_content}</div>", unsafe_allow_html=True)
        st.session_state.interpretation_segments.append(("👤 기본 정보", strip_html_tags(basic_info_card_content)))

        st.markdown(f"### <i class='fas fa-scroll icon-style' style='color:{HIGHLIGHT_YELLOW};'></i> 사주 명식", unsafe_allow_html=True)
        # ... (사주 명식 테이블 표시 로직 - 이전 답변의 UI 개선 로직 적용) ...
        display_day_gan_for_table = day_gan_char if day_gan_char and day_gan_char not in ["?", "오류"] else "일간"
        ms_data_for_display = {"구분": ["천간","지지","간지","궁위포태",f"일간({display_day_gan_for_table})포태"],
                               "시주": [time_gan_char if "오류" not in time_pillar_str else "?", time_ji_char if "오류" not in time_pillar_str else "?", time_pillar_str if "오류" not in time_pillar_str else "오류", time_unseong, ilgan_potae_vs_time],
                               "일주": [day_gan_char if "오류" not in day_pillar_str else "?", day_ji_char if "오류" not in day_pillar_str else "?", day_pillar_str if "오류" not in day_pillar_str else "오류", day_unseong, ilgan_potae_vs_day],
                               "월주": [month_gan_char if "오류" not in month_pillar_str else "?", month_ji_char if "오류" not in month_pillar_str else "?", month_pillar_str if "오류" not in month_pillar_str else "오류", month_unseong, ilgan_potae_vs_month],
                               "연주": [year_gan_char if "오류" not in year_pillar_str else "?", year_ji_char if "오류" not in year_pillar_str else "?", year_pillar_str if "오류" not in year_pillar_str else "오류", year_unseong, ilgan_potae_vs_year]}
        ms_df_for_display = pd.DataFrame(ms_data_for_display).set_index("구분")
        st.table(ms_df_for_display)
        saju_year_caption_display = f"사주 기준 연도 (입춘 기준): {saju_year_val}년"
        st.caption(saju_year_caption_display)
        st.session_state.interpretation_segments.append(("📜 사주 명식", ms_df_for_display.to_markdown() + "\n" + saju_year_caption_display))

        saju_8char_for_analysis = {"year_gan":year_gan_char,"year_ji":year_ji_char,"month_gan":month_gan_char,"month_ji":month_ji_char,"day_gan":day_gan_char,"day_ji":day_ji_char,"time_gan":time_gan_char,"time_ji":time_ji_char}
        analysis_possible = all(val and len(val)==1 and (val in GAN if k.endswith("_gan") else val in JI) for k,val in saju_8char_for_analysis.items())
        ohaeng_strengths, sipshin_strengths = {}, {}
        shinkang_status_result_val, gekuk_name_result_val = "정보 없음", "정보 없음"

        if analysis_possible:
            try:
                ohaeng_strengths, sipshin_strengths = calculate_ohaeng_sipshin_strengths(saju_8char_for_analysis)
                shinkang_status_result_val = determine_shinkang_shinyak(sipshin_strengths)
                gekuk_name_result_val = determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths)
            except Exception as e: st.warning(f"상세 분석 중 오류: {e}"); analysis_possible = False
        else: st.warning("사주 글자 정보 불완전, 상세 분석 생략.")

        st.markdown("---"); st.markdown(f"### <i class='fas fa-seedling icon-style' style='color:{HIGHLIGHT_ORANGE};'></i> 오행(五行) 분석", unsafe_allow_html=True)
        # ... (오행 분석 UI - 이전 답변 로직 적용) ...
        if analysis_possible and ohaeng_strengths:
            ohaeng_df_chart = pd.DataFrame.from_dict(ohaeng_strengths, orient='index', columns=['세력']).reindex(OHENG_ORDER)
            st.bar_chart(ohaeng_df_chart, height=300, use_container_width=True)
            ohaeng_summary_html = get_ohaeng_summary_explanation(ohaeng_strengths)
            st.markdown(f"<div class='custom-card' style='border-left: 4px solid {PRIMARY_COLOR};'>{ohaeng_summary_html}</div>", unsafe_allow_html=True)
            st.session_state.interpretation_segments.append(("🌳🔥 오행(五行) 분석", strip_html_tags(ohaeng_summary_html)))
            ohaeng_table_data = {"오행":OHENG_ORDER, "세력":[ohaeng_strengths.get(o,0.0) for o in OHENG_ORDER]}
            st.session_state.interpretation_segments.append(("오행 세력표", pd.DataFrame(ohaeng_table_data).to_markdown(index=False)))
        else: st.info("오행 분석 정보 없음"); st.session_state.interpretation_segments.append(("🌳🔥 오행(五行) 분석", "오행 분석 정보 없음"))

        st.markdown("---"); st.markdown(f"### <i class='fas fa-users icon-style' style='color:{HIGHLIGHT_ORANGE};'></i> 십신(十神) 분석", unsafe_allow_html=True)
        # ... (십신 분석 UI - 이전 답변 로직 적용) ...
        if analysis_possible and sipshin_strengths:
            sipshin_df_chart = pd.DataFrame.from_dict(sipshin_strengths, orient='index', columns=['세력']).reindex(SIPSHIN_ORDER)
            st.bar_chart(sipshin_df_chart, height=400, use_container_width=True)
            sipshin_summary_html = get_sipshin_summary_explanation(sipshin_strengths, day_gan_char)
            st.markdown(f"<div class='custom-card' style='border-left: 4px solid {SECONDARY_COLOR};'>{sipshin_summary_html}</div>", unsafe_allow_html=True)
            st.session_state.interpretation_segments.append(("🌟 십신(十神) 분석", strip_html_tags(sipshin_summary_html)))
            sipshin_table_data = {"십신":SIPSHIN_ORDER, "세력":[sipshin_strengths.get(s,0.0) for s in SIPSHIN_ORDER]}
            st.session_state.interpretation_segments.append(("십신 세력표", pd.DataFrame(sipshin_table_data).to_markdown(index=False)))
        else: st.info("십신 분석 정보 없음"); st.session_state.interpretation_segments.append(("🌟 십신(十神) 분석", "십신 분석 정보 없음"))

        st.markdown("---"); st.markdown(f"### <i class='fas fa-balance-scale icon-style' style='color:{HIGHLIGHT_YELLOW};'></i> 일간 강약 및 격국(格局) 분석", unsafe_allow_html=True)
        # ... (신강/신약, 격국 분석 UI - 이전 답변 로직 적용) ...
        if analysis_possible:
            shinkang_exp_html = get_shinkang_explanation(shinkang_status_result_val)
            gekuk_exp_html = get_gekuk_explanation(gekuk_name_result_val)
            col_sk, col_gk = st.columns(2)
            with col_sk: st.markdown(f"<div class='custom-card'><h4 style='color:{HIGHLIGHT_ORANGE};'>일간 강약</h4><p style='font-size:1.3em;font-weight:bold;color:{PRIMARY_COLOR};'>{shinkang_status_result_val}</p><p style='color:{TEXT_MUTED_COLOR};font-size:0.9em;'>{shinkang_exp_html}</p></div>", unsafe_allow_html=True)
            with col_gk: st.markdown(f"<div class='custom-card'><h4 style='color:{HIGHLIGHT_ORANGE};'>격국</h4><p style='font-size:1.3em;font-weight:bold;color:{PRIMARY_COLOR};'>{gekuk_name_result_val}</p><p style='color:{TEXT_MUTED_COLOR};font-size:0.9em;'>{gekuk_exp_html}</p></div>", unsafe_allow_html=True)
            st.session_state.interpretation_segments.append(("💪 일간 강약", f"**{shinkang_status_result_val}**: {strip_html_tags(shinkang_exp_html)}"))
            st.session_state.interpretation_segments.append(("💪 격국(格局)", f"**{gekuk_name_result_val}**: {strip_html_tags(gekuk_exp_html)}"))
        else: st.info("일간 강약/격국 분석 정보 없음"); st.session_state.interpretation_segments.append(("💪 일간 강약 및 격국(格局) 분석", "분석 정보 없음"))

        st.markdown("---"); st.markdown(f"### <i class='fas fa-link icon-style' style='color:{SECONDARY_COLOR};'></i> 합충형해파 분석", unsafe_allow_html=True)
        # ... (합충형해파 분석 UI - 이전 답변 로직 적용) ...
        hap_chung_text_for_seg_full = "합충형해파 정보 없음"
        if analysis_possible:
            hap_chung_res_dict = analyze_hap_chung_interactions(saju_8char_for_analysis)
            if any(v for v in hap_chung_res_dict.values()):
                with st.expander("세부 상호작용 보기", expanded=False):
                    for type_interaction, list_found in hap_chung_res_dict.items():
                        if list_found: st.markdown(f"<h5 style='color:{HIGHLIGHT_ORANGE};'>{type_interaction}</h5><ul>" + "".join([f"<li style='font-size:0.9em;color:{TEXT_MUTED_COLOR};'>{item}</li>" for item in list_found]) + "</ul>", unsafe_allow_html=True)
                hap_chung_exp_html = get_hap_chung_detail_explanation(hap_chung_res_dict)
                st.markdown(f"<div class='custom-card' style='border-left: 4px solid {HIGHLIGHT_YELLOW};'>{hap_chung_exp_html}</div>", unsafe_allow_html=True)
                temp_seg_parts_hc = [f"**{k}**: {', '.join(v)}" for k,v in hap_chung_res_dict.items() if v]
                hap_chung_text_for_seg_full = ("\n".join(temp_seg_parts_hc) + f"\n\n**설명**:\n{strip_html_tags(hap_chung_exp_html)}") if temp_seg_parts_hc else strip_html_tags(hap_chung_exp_html)
            else: st.markdown(f"<p class='custom-card' style='color:{TEXT_MUTED_COLOR};'>특별히 두드러지는 합충형해파 관계가 없습니다.</p>", unsafe_allow_html=True); hap_chung_text_for_seg_full = "특별히 두드러지는 합충형해파 관계가 없습니다."
        st.session_state.interpretation_segments.append(("🤝💥 합충형해파 분석", hap_chung_text_for_seg_full))

        st.markdown("---"); st.markdown(f"### <i class='fas fa-star-of-life icon-style' style='color:{SECONDARY_COLOR};'></i> 주요 신살(神煞) 분석", unsafe_allow_html=True)
        # ... (신살 분석 UI - 이전 답변 로직 적용) ...
        shinsal_text_for_seg_full = "신살 정보 없음"
        if analysis_possible:
            found_shinsals = analyze_shinsal(saju_8char_for_analysis)
            if found_shinsals:
                with st.expander("세부 신살 목록 보기", expanded=False):
                    for item_ss in found_shinsals: st.markdown(f"<li style='font-size:0.9em;color:{TEXT_MUTED_COLOR};list-style-type:none;'>{item_ss}</li>", unsafe_allow_html=True)
                shinsal_exp_html = get_shinsal_detail_explanation(found_shinsals)
                st.markdown(f"<div class='custom-card' style='border-left: 4px solid {PRIMARY_COLOR};'>{shinsal_exp_html}</div>", unsafe_allow_html=True)
                shinsal_text_for_seg_full = "**발견된 신살**:\n" + "\n".join([f"- {s}" for s in found_shinsals]) + f"\n\n**설명**:\n{strip_html_tags(shinsal_exp_html)}"
            else: st.markdown(f"<p class='custom-card' style='color:{TEXT_MUTED_COLOR};'>특별히 나타나는 주요 신살이 없습니다.</p>", unsafe_allow_html=True); shinsal_text_for_seg_full = "특별히 나타나는 주요 신살이 없습니다."
        st.session_state.interpretation_segments.append(("🔮 주요 신살(神煞) 분석", shinsal_text_for_seg_full))

        st.markdown("---"); st.markdown(f"### <i class='fas fa-yin-yang icon-style' style='color:{HIGHLIGHT_YELLOW};'></i> 용신(喜神) 및 기신(忌神) 분석 (간략)", unsafe_allow_html=True)
        # ... (용신/기신 분석 UI - 이전 답변 로직 적용) ...
        yongshin_text_for_seg_full = "용신/기신 정보 없음"; gaewoon_text_for_seg_full = ""
        if analysis_possible and shinkang_status_result_val not in ["분석 정보 없음", "분석 오류", "계산 불가"]:
            yongshin_info = determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_result_val)
            st.markdown(f"<div class='custom-card'>{yongshin_info['html']}</div>", unsafe_allow_html=True)
            gaewoon_html = get_gaewoon_tips_html(yongshin_info["yongshin"])
            if gaewoon_html: st.markdown(f"<div class='custom-card' style='margin-top:1rem; border-left:4px solid #059669;'>{gaewoon_html}</div>", unsafe_allow_html=True)
            yongshin_text_for_seg_full = strip_html_tags(yongshin_info.get("html", "정보 없음"))
            if yongshin_info.get("yongshin"): gaewoon_text_for_seg_full = strip_html_tags(gaewoon_html)
        else: st.info("일간 강약 정보가 명확하지 않아 용신/기신 분석을 수행하기 어렵습니다.")
        yongshin_notice = """<div style="font-size:0.85rem;color:#a5b4fc;margin-top:1.5rem;padding:0.85rem 1rem;background-color:rgba(25,22,48,0.5);border:1px dashed rgba(138,112,214,0.3);border-radius:4px;"><strong style="color:#fde047;">참고:</strong><br> 여기서 제공되는 용신/기신 정보는 간략화된 억부용신 결과입니다. 정밀 판단은 전문가와 상의하세요.</div>"""
        st.markdown(yongshin_notice, unsafe_allow_html=True)
        st.session_state.interpretation_segments.append(("☯️ 용신/기신 분석", yongshin_text_for_seg_full + (f"\n\n{gaewoon_text_for_seg_full}" if gaewoon_text_for_seg_full else "")))
        st.session_state.interpretation_segments.append(("용신/기신 참고", strip_html_tags(yongshin_notice)))
        
        st.markdown("---"); st.markdown(f"### <i class='fas fa-road icon-style' style='color:{HIGHLIGHT_ORANGE};'></i> 運 대운 ({gender})", unsafe_allow_html=True)
        # ... (대운 UI - 이전 답변 로직 적용) ...
        daewoon_seg_full = "대운 정보 없음"
        if "오류" in month_pillar_str or not month_gan_char or not month_ji_char: daewoon_seg_full = "월주 오류로 대운 표시 불가"; st.warning(daewoon_seg_full)
        else:
            daewoon_list, daewoon_age, is_sun = get_daewoon(year_gan_char,gender,birth_dt,month_gan_char,month_ji_char,solar_data)
            if isinstance(daewoon_list,list) and daewoon_list and "오류" in daewoon_list[0]: daewoon_seg_full = daewoon_list[0]; st.warning(daewoon_seg_full)
            elif isinstance(daewoon_list,list) and all(":" in item for item in daewoon_list):
                daewoon_start_txt = f"대운 시작: 약 {daewoon_age}세 ({'순행' if is_sun else '역행'})"
                st.markdown(f"<p style='color:{TEXT_MUTED_COLOR};font-weight:500;'>{daewoon_start_txt}</p>", unsafe_allow_html=True)
                daewoon_data = {"주기(나이)":[item.split(':')[0] for item in daewoon_list], "간지":[item.split(': ')[1] for item in daewoon_list]}
                daewoon_df_table = pd.DataFrame(daewoon_data); st.table(daewoon_df_table)
                daewoon_seg_full = daewoon_start_txt + "\n" + daewoon_df_table.to_markdown(index=False)
            else: daewoon_seg_full = "대운 정보 로드 실패"; st.warning(daewoon_seg_full)
        st.session_state.interpretation_segments.append((f"運 대운 ({gender})", daewoon_seg_full))

        st.markdown("---"); st.markdown(f"### <i class='far fa-calendar-check icon-style' style='color:{HIGHLIGHT_ORANGE};'></i> 기준일({ty}년 {tm}월 {td}일) 운세", unsafe_allow_html=True)
        # ... (세운/월운/일운 UI - 이전 답변 로직 적용) ...
        unse_seg_full = ""
        col_unse_a, col_unse_b = st.columns(2)
        with col_unse_a:
            st.markdown(f"<h5 style='color:{SECONDARY_COLOR};'>歲 세운 ({ty}년~)</h5>", unsafe_allow_html=True); seun_df_table=pd.DataFrame(get_seun_list(ty,5),columns=["연도","간지"]); st.table(seun_df_table); unse_seg_full+=f"**歲 세운 ({ty}년~)**\n{seun_df_table.to_markdown(index=False)}\n\n"
            st.markdown(f"<h5 style='color:{SECONDARY_COLOR};margin-top:1.5rem;'>日 일운 ({ty}-{tm:02d}-{td:02d}~)</h5>", unsafe_allow_html=True); ilun_df_table=pd.DataFrame(get_ilun_list(ty,tm,td,7),columns=["날짜","간지"]); st.table(ilun_df_table); unse_seg_full+=f"**日 일운 ({ty}-{tm:02d}-{td:02d}~)**\n{ilun_df_table.to_markdown(index=False)}\n\n"
        with col_unse_b:
            st.markdown(f"<h5 style='color:{SECONDARY_COLOR};'>月 월운 ({ty}년 {tm:02d}월~)</h5>", unsafe_allow_html=True); wolun_df_table=pd.DataFrame(get_wolun_list(ty,tm,solar_data,12),columns=["연월","간지"]); st.table(wolun_df_table); unse_seg_full+=f"**月 월운 ({ty}년 {tm:02d}월~)**\n{wolun_df_table.to_markdown(index=False)}"
        st.session_state.interpretation_segments.append((f"📅 기준일({ty}년 {tm}월 {td}일) 운세", unse_seg_full.strip()))

        # 클립보드 복사용 지침 텍스트 최종 생성
        guideline_parts_final = []
        for title_seg, content_seg_md in st.session_state.interpretation_segments:
            guideline_parts_final.append(f"## {title_seg}\n{strip_html_tags(content_seg_md) if '세력표' not in title_seg and '운세' not in title_seg and '대운' not in title_seg else content_seg_md}") # 표 데이터는 마크다운 그대로
        guideline_text_to_copy = "\n\n---\n\n".join(guideline_parts_final)
        
        st.markdown("---"); st.markdown(f"### <i class='fas fa-copy icon-style' style='color:{HIGHLIGHT_YELLOW};'></i> 사주 풀이 결과 전체 복사", unsafe_allow_html=True)
        st.text_area("아래 내용을 전체 선택(Ctrl+A 또는 Cmd+A) 후 복사(Ctrl+C 또는 Cmd+C)하세요:", guideline_text_to_copy, height=300, key="final_guideline_text_area_v2")
        
        st.session_state.saju_calculated_once = True
    # --- "if birth_dt_input_valid and birth_dt:" 블록 끝 ---
# --- "if st.sidebar.button(...)" 블록 끝 ---

if st.session_state.get('saju_calculated_once', False):
    st.markdown("---")
    if st.button("📖 전체 풀이 내용 다시 보기 (클릭하여 열기/닫기)", use_container_width=True, key="toggle_interpretation_expander_v5"):
        st.session_state.show_interpretation_guide_on_click = not st.session_state.get('show_interpretation_guide_on_click', False)

    if st.session_state.get('show_interpretation_guide_on_click', False):
        with st.expander("📖 전체 풀이 내용 (텍스트 지침)", expanded=True):
            if st.session_state.get('interpretation_segments') and len(st.session_state.interpretation_segments) > 0:
                current_time_str_final = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                full_text_guide_final = f"# ✨ 종합 사주 풀이 결과 ({current_time_str_final})\n\n"
                for title_final, content_final in st.session_state.interpretation_segments:
                    content_display_final = content_final if content_final and isinstance(content_final, str) else "내용 없음"
                    full_text_guide_final += f"## {title_final}\n\n{content_display_final.strip()}\n\n---\n\n"
                st.markdown(full_text_guide_final)
                st.info("위 내용을 선택하여 복사한 후, 원하시는 곳에 붙여넣어 활용하세요.")
            else: st.markdown("표시할 풀이 내용이 없습니다.")
elif not st.session_state.get('saju_calculated_once', False):
    st.info("화면 왼쪽의 사이드바에서 출생 정보를 입력하고 '🧮 계산 실행' 버튼을 누르면, 사주 명식과 함께 상세 풀이 내용을 이곳에서 확인할 수 있습니다.")

# FontAwesome 아이콘 로드를 위한 HTML (앱 최하단에 한 번만 포함)
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
""", unsafe_allow_html=True)
