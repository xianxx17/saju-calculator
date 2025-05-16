# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl lunardate

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math
import re


# import pandas as pd # 등 나머지 코드가 이어집니다.
# ...

# --- 음력 변환을 위한 라이브러리 임포트 ---
try:
    from lunardate import LunarDate
except ImportError:
    st.error("음력 변환을 위한 'lunardate' 라이브러리가 설치되지 않았습니다. 터미널에서 `pip install lunardate`를 실행해주세요.")
    st.stop()

# -------------------------------
# HTML 태그 제거 헬퍼 함수 (이 부분을 추가하거나 확인해주세요)
# -------------------------------
def strip_html_tags(html_string):
    if not isinstance(html_string, str):
        return str(html_string) # 문자열이 아니면 문자열로 변환하여 반환
    # Remove style blocks
    html_string = re.sub(r'<style.*?</style>', '', html_string, flags=re.DOTALL | re.IGNORECASE)
    # Remove script blocks
    html_string = re.sub(r'<script.*?</script>', '', html_string, flags=re.DOTALL | re.IGNORECASE)
    # Remove all other HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_string)
    # Replace common HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&amp;', '&')
    # Remove excessive newlines and whitespace, keep meaningful newlines
    lines = [line.strip() for line in clean_text.splitlines()]
    # Filter out empty lines but keep a single newline for separation if multiple were there
    filtered_lines = []
    last_line_was_content = False
    for line in lines:
        if line:
            filtered_lines.append(line)
            last_line_was_content = True
        elif last_line_was_content: # Keep one empty line if it was separating content
            filtered_lines.append("")
            last_line_was_content = False

    # Join and then strip leading/trailing newlines from the whole block
    clean_text = '\n'.join(filtered_lines).strip()
    # Ensure at least one newline between paragraphs if they were merged by tag removal
    clean_text = re.sub(r'(?<=[א-힣a-zA-Z0-9])\n(?=[א-힣a-zA-Z0-9])', '\n\n', clean_text)
    return clean_text

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 만 나이 계산 함수 (여기에 추가 또는 기존 위치 확인) ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
def calculate_age(birth_dt_obj, current_dt_obj):
    """만 나이를 계산합니다."""
    if birth_dt_obj is None:
        return "계산 불가"  # 혹은 적절한 오류 값
    # 출생 시점의 날짜 정보만 사용 (시간 정보는 만 나이 계산에 영향 없음)
    birth_date_only = birth_dt_obj.date()
    current_date_only = current_dt_obj.date()

    age = current_date_only.year - birth_date_only.year
    # 생일이 지났는지 확인 (월, 일 비교)
    if (current_date_only.month, current_date_only.day) < (birth_date_only.month, birth_date_only.day):
        age -= 1
    return age
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 만 나이 계산 함수 끝 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# 이 아래부터는 기존의 상수 정의 (FILE_NAME = ...) 등이 이어집니다.
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


# ... (기존 OHENG_DESCRIPTIONS, SIPSHIN_COLORS 등 상수 정의 이후) ...

# ───────────────────────────────
# 신강/신약 및 격국 분석용 상수 추가
# ───────────────────────────────

# 건록격 판단용 (HTML 예제 L 상수 기반: 일간 -> 건록에 해당하는 지지)
# 참고: 일반적인 건록 정의(예: 갑->인)와 다를 수 있으나, 제공해주신 JS 코드 기준을 따릅니다.
L_NOK_MAP = {
    "갑": "묘", "을": "인", "병": "사", "정": "오", 
    "무": "진", "기": "축", "경": "유", "신": "신", 
    "임": "해", "계": "자"
}

# 양인격 판단용 (HTML 예제 yangin_map 기반: 양일간 -> 양인에 해당하는 지지)
YANGIN_JI_MAP = {
    "갑": "묘",  # 양일간 갑목의 양인은 묘목
    "병": "오",  # 양일간 병화의 양인은 오화
    "무": "오",  # 양일간 무토의 양인은 오화 (화토동법)
    "경": "유",  # 양일간 경금의 양인은 유금
    "임": "자"   # 양일간 임수의 양인은 자수
} # (음일간은 보통 양인격으로 논하지 않음)

# 십신 이름을 격국 이름으로 매핑 (일반격 판단 시 사용)
SIPSHIN_TO_GYEOK_MAP = {
    '비견':'비견격', '겁재':'겁재격', # 참고: 겁재격은 양인격과 구분되기도 함
    '식신':'식신격', '상관':'상관격',
    '편재':'편재격', '정재':'정재격',
    '편관':'칠살격', '정관':'정관격', # 편관은 칠살격으로도 불림
    '편인':'편인격', '정인':'정인격'
}


# ───────────────────────────────
# 신강/신약 판단 및 설명 함수
# ───────────────────────────────
def determine_shinkang_shinyak(sipshin_strengths):
    """
    십신 세력값을 바탕으로 일간의 신강/신약을 판단합니다.
    (HTML 예제의 shinkang 함수 로직 기반)
    """
    # 일간을 돕는 기운: 비견, 겁재 (나와 같은 오행), 편인, 정인 (나를 생하는 오행)
    my_energy = (sipshin_strengths.get("비견", 0.0) +
                 sipshin_strengths.get("겁재", 0.0) +
                 sipshin_strengths.get("편인", 0.0) +
                 sipshin_strengths.get("정인", 0.0))
    
    # 일간의 힘을 빼는 기운: 식신, 상관 (내가 생하는 오행), 편재, 정재 (내가 극하는 오행), 편관, 정관 (나를 극하는 오행)
    opponent_energy = (sipshin_strengths.get("식신", 0.0) +
                       sipshin_strengths.get("상관", 0.0) +
                       sipshin_strengths.get("편재", 0.0) +
                       sipshin_strengths.get("정재", 0.0) +
                       sipshin_strengths.get("편관", 0.0) +
                       sipshin_strengths.get("정관", 0.0))
    
    score_diff = my_energy - opponent_energy
    
    # HTML 예제 코드의 기준값을 따름
    if score_diff >= 1.5: return "신강"
    elif score_diff <= -1.5: return "신약"
    elif -0.5 <= score_diff <= 0.5: return "중화" 
    elif score_diff > 0.5: return "약간 신강" # 0.5 < score_diff < 1.5
    else: return "약간 신약" # -1.5 < score_diff < -0.5

def get_shinkang_explanation(shinkang_status_str):
    """신강/신약 상태에 대한 설명을 반환합니다."""
    explanations = {
        "신강": "일간(자신)의 힘이 강한 편입니다. 주체적이고 독립적인 성향이 강하며, 자신의 의지대로 일을 추진하는 힘이 있습니다. 때로는 자기 주장이 강해 주변과의 마찰이 생길 수 있으니 유연성을 갖추는 것이 좋습니다.",
        "신약": "일간(자신)의 힘이 다소 약한 편입니다. 주변의 도움이나 환경의 영향에 민감하며, 신중하고 사려 깊은 모습을 보일 수 있습니다. 자신감을 갖고 꾸준히 자신의 역량을 키워나가는 것이 중요하며, 좋은 운의 흐름을 잘 활용하는 지혜가 필요합니다.",
        "중화": "일간(자신)의 힘이 비교적 균형을 이루고 있습니다. 상황에 따라 유연하게 대처하는 능력이 있으며, 원만한 대인관계를 맺을 수 있는 좋은 구조입니다. 다만, 때로는 뚜렷한 개성이 부족해 보일 수도 있습니다.",
        "약간 신강": "일간(자신)의 힘이 평균보다 조금 강한 편입니다. 자신의 주관을 가지고 일을 처리하면서도 주변과 협력하는 균형 감각을 발휘할 수 있습니다.",
        "약간 신약": "일간(자신)의 힘이 평균보다 조금 약한 편입니다. 신중하고 주변 상황을 잘 살피며, 인내심을 가지고 목표를 추구하는 경향이 있습니다. 주변의 조언을 경청하는 자세가 도움이 될 수 있습니다."
    }
    return explanations.get(shinkang_status_str, "일간의 강약 상태에 대한 설명을 준비 중입니다.")

# ───────────────────────────────
# 격국 판단 함수들 (HTML 예제 final_gekuk 및 관련 함수 로직 기반)
# ───────────────────────────────
def _detect_special_gekuk(day_gan_char, month_ji_char):
    """특별격(건록격, 양인격)을 우선적으로 판단합니다."""
    # 건록격: 일간의 건록(祿)이 월지에 있을 때
    if L_NOK_MAP.get(day_gan_char) == month_ji_char:
        return "건록격"
    # 양인격: 양일간의 양인(羊刃)이 월지에 있을 때
    if day_gan_char in YANGIN_JI_MAP and YANGIN_JI_MAP.get(day_gan_char) == month_ji_char:
        return "양인격"
    return None

def _detect_togan_gekuk(day_gan_char, month_gan_char, month_ji_char):
    """월지의 지장간 중에서 월간에 투간(透干)한 것을 기준으로 격을 정합니다."""
    if month_ji_char in JIJI_JANGGAN: # JIJI_JANGGAN는 이미 정의된 상수
        hidden_stems_in_month_ji = JIJI_JANGGAN[month_ji_char]
        if month_gan_char in hidden_stems_in_month_ji: # 월간이 월지 지장간에 포함(투간)된 경우
            # 투간된 월간을 기준으로 일간과의 관계(십신)를 파악하여 격을 정함
            sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(month_gan_char) # SIPSHIN_MAP도 이미 정의
            if sipshin_type:
                return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_month_branch_primary(day_gan_char, month_ji_char):
    """월지 지장간 중 가장 세력이 강한 정기(正氣 또는 本氣)를 기준으로 격을 정합니다."""
    if month_ji_char in JIJI_JANGGAN:
        hidden_stems = JIJI_JANGGAN[month_ji_char]
        if hidden_stems:
            # 지장간 중 비율(세력)이 가장 높은 것을 본기로 간주 (HTML 예제 ZW의 값 비교 로직 참고)
            primary_hidden_stem = None
            max_ratio = -1 # 비율은 항상 0 이상이므로 -1로 시작
            for stem, ratio in hidden_stems.items():
                if ratio > max_ratio:
                    max_ratio = ratio
                    primary_hidden_stem = stem
            
            if primary_hidden_stem:
                sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(primary_hidden_stem)
                if sipshin_type:
                    return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_strengths(sipshin_strengths_dict):
    """위 방법들로 격을 정할 수 없을 때, 사주 전체의 십신 세력 중 가장 강한 것을 기준으로 격을 정합니다. (억부격과 유사)"""
    if not sipshin_strengths_dict: return None
    
    strongest_sipshin_name = None
    max_strength = -1 

    # SIPSHIN_ORDER 순서대로 순회하며 가장 강한 십신을 찾음 (HTML 예제와 동일한 순서로)
    for sipshin_name in SIPSHIN_ORDER: # SIPSHIN_ORDER는 이미 정의된 상수
        strength_val = sipshin_strengths_dict.get(sipshin_name, 0.0)
        if strength_val > max_strength:
            max_strength = strength_val
            strongest_sipshin_name = sipshin_name
            
    if strongest_sipshin_name and max_strength > 0.5: # HTML 예제에서는 0.5를 기준으로 함
        # 비견격/겁재격은 보통 특별격(건록/양인)에 해당하지 않을 때 고려
        # HTML 예제에서는 이들도 일반격으로 매핑함
        return SIPSHIN_TO_GYEOK_MAP.get(strongest_sipshin_name, strongest_sipshin_name + "격")
    return "일반격 판정 어려움" # HTML 예제 참고


def determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths_dict):
    """격국을 판단하는 메인 함수 (HTML 예제 final_gekuk 로직 순서 참고)"""
    # 1. 특별격 (건록격, 양인격) 우선 판단
    special_gekuk = _detect_special_gekuk(day_gan_char, month_ji_char)
    if special_gekuk:
        return special_gekuk
    
    # 2. 월간이 월지 지장간에서 투간했는지 여부로 격 판단
    togan_gekuk = _detect_togan_gekuk(day_gan_char, month_gan_char, month_ji_char)
    if togan_gekuk:
        return togan_gekuk
        
    # 3. 월지 지장간의 본기(정기)를 기준으로 격 판단
    month_branch_primary_gekuk = _detect_general_gekuk_from_month_branch_primary(day_gan_char, month_ji_char)
    if month_branch_primary_gekuk:
        return month_branch_primary_gekuk
        
    # 4. 위 방법으로 격을 정하기 어려울 때, 사주 전체 십신 세력을 기준으로 판단 (HTML 예제 로직)
    strength_based_gekuk = _detect_general_gekuk_from_strengths(sipshin_strengths_dict)
    if strength_based_gekuk and strength_based_gekuk != "일반격 판정 어려움":
        return strength_based_gekuk
    elif strength_based_gekuk == "일반격 판정 어려움":
        return strength_based_gekuk # 이 메시지 자체를 결과로 반환
        
    return "격국 판정 불가" # 모든 조건에 해당하지 않을 경우

def get_gekuk_explanation(gekuk_name_str):
    """격국 이름에 대한 설명을 반환합니다."""
    # HTML 예제의 설명을 기반으로 작성
    explanations = {
        '건록격': '스스로 자립하여 성공하는 자수성가형 리더 타입입니다! 굳건하고 독립적인 성향을 가졌습니다. (주로 월지에 일간의 건록이 있는 경우)',
        '양인격': '강력한 카리스마와 돌파력을 지녔습니다! 때로는 너무 강한 기운으로 인해 조절이 필요할 수 있지만, 큰일을 해낼 수 있는 저력이 있습니다. (주로 월지에 양일간의 양인이 있는 경우)',
        '비견격': '주체성이 강하고 동료들과 협력하며 목표를 향해 나아가는 타입입니다. 독립심과 자존감이 강한 편입니다.',
        '겁재격': '승부욕과 경쟁심이 강하며, 때로는 과감한 도전도 불사하는 적극적인 면모가 있습니다. 주변과의 협력과 조화를 중요시해야 합니다.',
        '식신격': '낙천적이고 창의적인 아이디어가 풍부하며, 표현력이 좋고 예술적 재능을 지녔을 수 있습니다. 안정적인 의식주를 중시하는 경향이 있습니다.',
        '상관격': '새로운 것을 탐구하고 기존의 틀을 깨려는 혁신가적 기질이 있습니다. 비판적이고 날카로운 통찰력을 지녔지만, 때로는 표현 방식에 유의하여 오해를 피하는 것이 좋습니다.',
        '편재격': '활동적이고 사교성이 뛰어나며 사람들과 어울리는 것을 좋아합니다. 재물에 대한 감각과 운용 능력이 뛰어나며, 스케일이 크고 통이 큰 경향이 있습니다.',
        '정재격': '꼼꼼하고 성실하며 안정적인 것을 선호합니다. 신용을 중요하게 생각하고 계획적인 삶을 추구하며, 재물을 안정적으로 관리하는 능력이 있습니다.',
        '칠살격': '명예를 중시하고 리더십이 있으며, 어려운 상황을 극복하고 위기에서 능력을 발휘하는 카리스마가 있습니다. (편관격과 유사)', # 편관격으로 통일해도 무방
        '정관격': '원칙을 지키는 반듯하고 합리적인 성향입니다. 명예와 안정을 추구하며 조직 생활에 잘 적응하고 책임감이 강합니다.',
        '편인격': '직관력과 예지력이 뛰어나며, 독특한 아이디어나 예술, 철학, 종교 등 정신적인 분야에 재능을 보일 수 있습니다. 다소 생각이 많거나 변덕스러울 수 있습니다.',
        '정인격': '학문과 지식을 사랑하고 인정이 많으며 수용성이 좋습니다. 안정적인 환경에서 능력을 발휘하며, 타인에게 도움을 주는 것을 좋아합니다.',
        '일반격 판정 어려움': '사주의 기운이 복합적이거나 특정 십신의 세력이 두드러지게 나타나지 않아, 하나의 주된 격국으로 정의하기 어렵습니다. 다양한 가능성을 가진 사주로 볼 수 있으며, 운의 흐름에 따라 여러 격의 특성이 발현될 수 있습니다.',
        '격국 판정 불가': '사주의 구조상 특정 격국을 명확히 판정하기 어렵습니다. 이 경우, 사주 전체의 오행 및 십신 분포, 운의 흐름 등을 종합적으로 고려하여 판단하는 것이 좋습니다.'
    }
    # 편관격과 칠살격이 같은 의미로 사용될 수 있으므로, 칠살격 요청 시 편관격 설명으로 대체 가능
    if gekuk_name_str == '편관격': gekuk_name_str = '칠살격' # 또는 그 반대
    
    return explanations.get(gekuk_name_str, f"'{gekuk_name_str}'에 대한 설명을 준비 중입니다. 일반적으로 해당 십신의 특성을 참고할 수 있습니다.")

# ... (기존의 다른 함수들 get_saju_year, calculate_ohaeng_sipshin_strengths 등은 이 위 또는 아래에 위치) ...

# ... (기존 get_gekuk_explanation 함수 등 다음 줄에)
import itertools # 조합을 찾기 위해 임포트합니다. 스크립트 상단에 추가해도 됩니다.

# ───────────────────────────────
# 합충형해파 분석용 상수 정의
# (사용자님이 제공해주신 HTML/JS 예제 코드의 규칙들을 기반으로 작성되었습니다)
# ───────────────────────────────

# 천간합 규칙: 합화 오행
CHEONGAN_HAP_RULES = {
    tuple(sorted(("갑", "기"))): "토", tuple(sorted(("을", "경"))): "금",
    tuple(sorted(("병", "신"))): "수", tuple(sorted(("정", "임"))): "목",
    tuple(sorted(("무", "계"))): "화"
}

# 지지 삼합 규칙: 국(局) 형성
JIJI_SAMHAP_RULES = {
    tuple(sorted(("신", "자", "진"))): "수국(水局)", tuple(sorted(("사", "유", "축"))): "금국(金局)",
    tuple(sorted(("인", "오", "술"))): "화국(火局)", tuple(sorted(("해", "묘", "미"))): "목국(木局)"
}
# 지지 반합 규칙 (삼합의 왕지를 중심으로)
# 키: 왕지, 값: [생지, 묘지] (이들과 왕지가 만나면 반합)
JIJI_BANHAP_WANGJI_CENTERED_RULES = {
    "자": ["신", "진"], "유": ["사", "축"],
    "오": ["인", "술"], "묘": ["해", "미"]
}

# 지지 방합 규칙: 국(局) 형성
JIJI_BANGHAP_RULES = {
    tuple(sorted(("인", "묘", "진"))): "목국(木局)", tuple(sorted(("사", "오", "미"))): "화국(火局)",
    tuple(sorted(("신", "유", "술"))): "금국(金局)", tuple(sorted(("해", "자", "축"))): "수국(水局)"
}

# 지지 육합 규칙: 합화 오행 (또는 관계)
JIJI_YUKHAP_RULES = {
    tuple(sorted(("자", "축"))): "토", tuple(sorted(("인", "해"))): "목",
    tuple(sorted(("묘", "술"))): "화", tuple(sorted(("진", "유"))): "금",
    tuple(sorted(("사", "신"))): "수", tuple(sorted(("오", "미"))): "화/토" # 오미합은 화 또는 토로 보거나, 기반 오행에 따라 달라짐
}

# 천간충 규칙
CHEONGAN_CHUNG_RULES = [
    tuple(sorted(("갑", "경"))), tuple(sorted(("을", "신"))),
    tuple(sorted(("병", "임"))), tuple(sorted(("정", "계")))
] # 무토, 기토는 충이 없음 (혹은 무임충, 기계충을 보기도 하나 JS 예제엔 없음)

# 지지충 규칙
JIJI_CHUNG_RULES = [
    tuple(sorted(("자", "오"))), tuple(sorted(("축", "미"))),
    tuple(sorted(("인", "신"))), tuple(sorted(("묘", "유"))),
    tuple(sorted(("진", "술"))), tuple(sorted(("사", "해")))
]

# 지지 형살 규칙
# 삼형
SAMHYEONG_RULES = {
    tuple(sorted(("인", "사", "신"))): "인사신 삼형(無恩之刑)", # 무은지형
    tuple(sorted(("축", "술", "미"))): "축술미 삼형(持勢之刑)"  # 지세지형
}
# 상형 (자묘형)
SANGHYEONG_RULES = [tuple(sorted(("자", "묘")))] # 자묘 상형(無禮之刑)
# 자형 (같은 글자가 2개 이상일 때)
JAHYEONG_CHARS = ["진", "오", "유", "해"]

# 지지 해살(害殺) 규칙
JIJI_HAE_RULES = [
    tuple(sorted(("자", "미"))), tuple(sorted(("축", "오"))),
    tuple(sorted(("인", "사"))), tuple(sorted(("묘", "진"))),
    tuple(sorted(("신", "해"))), tuple(sorted(("유", "술")))
]
HAE_NAMES = {tuple(sorted(k)):v for k,v in {"자미":"자미해", "축오":"축오해", "인사":"인사회", "묘진":"묘진해", "신해":"신해해", "유술":"유술해"}.items()}


# 지지 파살(破殺) 규칙
JIJI_PA_RULES = [
    tuple(sorted(("자", "유"))), tuple(sorted(("축", "진"))),
    tuple(sorted(("인", "해"))), tuple(sorted(("묘", "오"))),
    tuple(sorted(("사", "신"))), tuple(sorted(("술", "미")))
]
PA_NAMES = {tuple(sorted(k)):v for k,v in {"자유":"자유파", "축진":"축진파", "인해":"인해파", "묘오":"묘오파", "사신":"사신파", "술미":"술미파"}.items()}


PILLAR_NAMES_KOR_SHORT = ["년", "월", "일", "시"] # 결과 출력 시 사용


# ───────────────────────────────
# 합충형해파 분석 함수
# ───────────────────────────────
def analyze_hap_chung_interactions(saju_8char_details):
    """
    사주팔자의 천간 및 지지 간의 합, 충, 형, 해, 파 관계를 분석합니다.
    saju_8char_details: {"year_gan":yg, "year_ji":yj, ...} 형태의 딕셔너리
    반환: {"천간합": ["결과 문자열 리스트"], "지지삼합": [], ...} 형태의 딕셔너리
    """
    gans = [saju_8char_details["year_gan"], saju_8char_details["month_gan"], saju_8char_details["day_gan"], saju_8char_details["time_gan"]]
    jis = [saju_8char_details["year_ji"], saju_8char_details["month_ji"], saju_8char_details["day_ji"], saju_8char_details["time_ji"]]

    results = {
        "천간합": [], "지지육합": [], "지지삼합": [], "지지방합": [],  # 합(合)
        "천간충": [], "지지충": [],                               # 충(沖)
        "형살(刑殺)": [], "해살(害殺)": [], "파살(破殺)": []          # 형해파(刑害破)
    }
    
    # 중복 방지를 위한 세트들 (JS 예제 참고)
    found_samhap_banhap_combinations = set() # 삼합, 반합은 같은 지지 조합을 다르게 표현할 수 있으므로 중복 방지

    # 0. 위치 정보와 함께 간/지 리스트 생성
    # (인덱스, 천간/지지 글자, 기둥이름) 형태의 튜플 리스트
    gans_with_pos = list(enumerate(gans)) # [(0, '갑'), (1, '병'), ...]
    jis_with_pos = list(enumerate(jis))   # [(0, '자'), (1, '인'), ...]

    # 1. 천간합 / 천간충 (2개 조합)
    for (i_idx, i_gan), (j_idx, j_gan) in itertools.combinations(gans_with_pos, 2):
        pair_sorted = tuple(sorted((i_gan, j_gan)))
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}간({i_gan}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}간({j_gan})"
        
        if pair_sorted in CHEONGAN_HAP_RULES:
            results["천간합"].append(f"{pos_str} → {CHEONGAN_HAP_RULES[pair_sorted]} 합")
        if pair_sorted in CHEONGAN_CHUNG_RULES:
            results["천간충"].append(f"{pos_str.replace('+', '↔')} 충")

    # 2. 지지육합 / 지지충 / 지지해 / 지지파 (2개 조합)
    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(jis_with_pos, 2):
        pair_sorted = tuple(sorted((i_ji, j_ji)))
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        
        if pair_sorted in JIJI_YUKHAP_RULES:
            results["지지육합"].append(f"{pos_str} → {JIJI_YUKHAP_RULES[pair_sorted]} 합")
        if pair_sorted in JIJI_CHUNG_RULES:
            results["지지충"].append(f"{pos_str.replace('+', '↔')} 충")
        if pair_sorted in JIJI_HAE_RULES:
            results["해살(害殺)"].append(f"{pos_str} → {HAE_NAMES.get(pair_sorted, '해')}")
        if pair_sorted in JIJI_PA_RULES:
            results["파살(破殺)"].append(f"{pos_str} → {PA_NAMES.get(pair_sorted, '파')}")
        
        # 자묘 상형 체크
        if pair_sorted in SANGHYEONG_RULES:
             results["형살(刑殺)"].append(f"{pos_str} → 자묘 상형(無禮之刑)")


    # 3. 지지삼합 / 지지방합 / 지지삼형 (3개 조합)
    for (i_idx, i_ji), (j_idx, j_ji), (k_idx, k_ji) in itertools.combinations(jis_with_pos, 3):
        combo_sorted = tuple(sorted((i_ji, j_ji, k_ji)))
        # 위치 문자열 만들 때, 실제 인덱스 순서대로 표시하는 것이 좋으나, 일단 정렬된 지지 순서대로
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}), {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji}), {PILLAR_NAMES_KOR_SHORT[k_idx]}지({k_ji})"
        
        if combo_sorted in JIJI_SAMHAP_RULES:
            # 삼합이 성립되면, 이 조합을 기록하여 반합 중복 방지에 사용
            found_samhap_banhap_combinations.add(combo_sorted) 
            results["지지삼합"].append(f"{pos_str} → {JIJI_SAMHAP_RULES[combo_sorted]}")
        if combo_sorted in JIJI_BANGHAP_RULES:
            results["지지방합"].append(f"{pos_str} → {JIJI_BANGHAP_RULES[combo_sorted]}")
        if combo_sorted in SAMHYEONG_RULES:
            results["형살(刑殺)"].append(f"{pos_str} → {SAMHYEONG_RULES[combo_sorted]}")

    # 4. 지지반합 (삼합에 포함되지 않은 반합만 찾기, JS 예제 로직 참고)
    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(jis_with_pos, 2):
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        
        for wangji, others in JIJI_BANHAP_WANGJI_CENTERED_RULES.items():
            # 반합 조건: (i_ji가 왕지이고 j_ji가 others에 속함) 또는 (j_ji가 왕지이고 i_ji가 others에 속함)
            if (i_ji == wangji and j_ji in others) or \
               (j_ji == wangji and i_ji in others):
                
                # 이 반합이 이미 발견된 삼합의 일부인지 확인
                is_part_of_samhap = False
                potential_samhap_members = {i_ji, j_ji}
                # 나머지 하나의 삼합 멤버 찾기 (왕지, 생지, 묘지 중 빠진 것)
                full_samhap_group = None
                for samhap_key_tuple in JIJI_SAMHAP_RULES.keys():
                    if wangji in samhap_key_tuple and (i_ji in samhap_key_tuple and j_ji in samhap_key_tuple):
                        full_samhap_group = samhap_key_tuple
                        break
                
                if full_samhap_group and full_samhap_group in found_samhap_banhap_combinations:
                    is_part_of_samhap = True
                    
                if not is_part_of_samhap:
                    # 중복된 반합 문자열 방지 (예: 년지(자)+월지(신) vs 월지(신)+년지(자))
                    # 반합 결과 문자열을 정렬된 기준으로 만들어 중복 체크
                    sorted_banhap_key = tuple(sorted((i_ji, j_ji))) 
                    banhap_result_str = f"{pos_str} → {wangji} 기준 반합 ({JIJI_SAMHAP_RULES.get(full_samhap_group, '국 형성')})"
                    
                    # 반합 결과를 저장하고, 중복을 피하기 위해 found_samhap_banhap_combinations에 (정렬된 키, 결과문자열) 추가
                    # 여기서는 결과 문자열 자체로 중복을 피하기보다, 반합이 발생했다는 사실로 기록
                    if not any(banhap_result_str == item for item in results["지지삼합"]): # 이미 삼합으로 기록된 경우 제외
                         # 삼합의 하위 개념이므로, 삼합 리스트에 "반합"으로 명시하여 추가
                         results["지지삼합"].append(banhap_result_str)
                break # 해당 pair에 대한 반합 찾았으므로 다음 pair로

    # 5. 자형(自刑)
    for jahyeong_char in JAHYEONG_CHARS:
        count = jis.count(jahyeong_char)
        if count >= 2:
            positions = [f"{PILLAR_NAMES_KOR_SHORT[i]}지({jis[i]})" for i, ji_val in enumerate(jis) if ji_val == jahyeong_char]
            results["형살(刑殺)"].append(f"{', '.join(positions)} ({jahyeong_char}{jahyeong_char}) → 자형(自刑)")
            
    return results


def get_hap_chung_detail_explanation(found_interactions_dict):
    """발견된 합충형해파 종류에 따라 간단한 설명을 반환합니다."""
    if not found_interactions_dict or not any(v for v in found_interactions_dict.values()):
        return "<p>특별히 두드러지는 합충형해파의 관계가 나타나지 않습니다. 비교적 안정적인 구조일 수 있습니다.</p>"

    explanation_parts = []
    # HTML 예제의 설명을 기반으로 각 상호작용 타입에 대한 설명 추가
    interaction_explanations = {
        "천간합": "정신적, 사회적 관계에서의 연합, 변화 또는 새로운 기운의 생성 가능성을 나타냅니다.",
        "지지육합": "개인적인 관계, 애정, 또는 비밀스러운 합의나 내부적인 결속을 의미할 수 있습니다.",
        "지지삼합": "강력한 사회적 합으로, 특정 목표를 향한 강력한 추진력이나 세력 형성을 나타냅니다. (반합 포함)",
        "지지방합": "가족, 지역, 동료 등 혈연이나 지연에 기반한 강한 결속력이나 세력 확장을 의미합니다.",
        "천간충": "생각의 충돌, 가치관의 대립, 또는 외부 환경으로부터의 갑작스러운 변화나 자극, 정신적 스트레스를 암시합니다.",
        "지지충": "현실적인 변화, 이동, 관계의 단절 또는 새로운 시작, 건강상의 주의 등을 나타낼 수 있습니다. 역동적인 사건의 발생 가능성을 의미합니다.",
        "형살(刑殺)": "조정, 갈등, 법적 문제, 수술, 배신, 또는 내적 갈등과 성장통 등을 나타낼 수 있습니다. 때로는 정교함이나 전문성을 요구하는 일과도 관련됩니다.",
        "해살(害殺)": "관계에서의 방해, 질투, 오해, 또는 건강상의 문제(주로 만성적) 등을 암시합니다. 예기치 않은 손실이나 어려움을 겪을 수 있습니다.",
        "파살(破殺)": "깨짐, 분리, 손상, 계획의 차질, 관계의 갑작스러운 단절 등을 나타낼 수 있습니다. 기존의 것이 깨지고 새로워지는 과정을 의미하기도 합니다."
    }
    
    for key, found_list in found_interactions_dict.items():
        if found_list: # 해당 상호작용이 하나라도 발견되었다면
            desc = interaction_explanations.get(key)
            if desc:
                explanation_parts.append(f"<li><strong>{key}:</strong> {desc}</li>")
    
    if not explanation_parts:
        return "<p>구체적인 합충형해파 관계에 대한 설명을 준비 중입니다.</p>"
        
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

# ... (기존의 다른 함수들 determine_shinkang_shinyak, determine_gekuk 등은 이 위 또는 아래에 위치) ...
# (saju_app.py 파일에 추가될 내용)

# ... (기존 get_hap_chung_detail_explanation 함수 등 다음 줄에)

# ───────────────────────────────
# 주요 신살(神煞) 분석용 상수 및 함수 정의
# (사용자님이 제공해주신 HTML/JS 예제 코드의 규칙들을 기반으로 작성되었습니다)
# ───────────────────────────────

# 천을귀인 (일간 기준, 해당 지지가 사주 내에 있는지 확인)
CHEONEULGWIIN_MAP = {
    "갑": ["축", "미"], "을": ["자", "신"], "병": ["해", "유"], "정": ["해", "유"],
    "무": ["축", "미"], "기": ["자", "신"], "경": ["축", "미", "인", "오"], # JS 예제는 경: 축미인오, 신: 인오
    "신": ["인", "오"], "임": ["사", "묘"], "계": ["사", "묘"]
}

# 문창귀인 (일간 기준, 해당 지지가 사주 내에 있는지 확인)
MUNCHANGGWIIN_MAP = {
    "갑": "사", "을": "오", "병": "신", "정": "유", "무": "신",
    "기": "유", "경": "해", "신": "자", "임": "인", "계": "묘"
}

# 도화살 (년지 또는 일지 기준 - 삼합 왕지의 다음 글자, 즉 목욕지)
# 기준 지지(삼합의 생지) -> 도화 지지(삼합의 왕지) - JS맵은 왕지를 가리킴. 도화는 목욕지.
# 예: 해묘미(목국) -> 목욕지 '자'. 인오술(화국) -> 목욕지 '묘'.
# JS 예제: {"해":"자", "묘":"자", "미":"자", "인":"묘", "오":"묘", "술":"묘", ... }
# 이 맵은 (삼합의 첫글자 또는 중간글자 또는 끝글자) -> 도화살 지지(목욕지)
DOHWASAL_MAP = {
    # 해묘미 -> 자
    "해": "자", "묘": "자", "미": "자",
    # 인오술 -> 묘
    "인": "묘", "오": "묘", "술": "묘",
    # 사유축 -> 오
    "사": "오", "유": "오", "축": "오",
    # 신자진 -> 유
    "신": "유", "자": "유", "진": "유"
}

# 역마살 (년지 또는 일지 기준 - 삼합 생지를 충(沖)하는 지지)
YEONGMASAL_MAP = {
    # 해묘미(목국) -> 목의 생지 해와 충하는 사
    "해": "사", "묘": "사", "미": "사",
    # 인오술(화국) -> 화의 생지 인과 충하는 신
    "인": "신", "오": "신", "술": "신",
    # 사유축(금국) -> 금의 생지 사와 충하는 해
    "사": "해", "유": "해", "축": "해",
    # 신자진(수국) -> 수의 생지 신과 충하는 인
    "신": "인", "자": "인", "진": "인"
}

# 화개살 (년지 또는 일지 기준 - 삼합의 묘지)
HWAGAESAL_MAP = {
    # 해묘미 -> 미
    "해": "미", "묘": "미", "미": "미",
    # 인오술 -> 술
    "인": "술", "오": "술", "술": "술",
    # 사유축 -> 축
    "사": "축", "유": "축", "축": "축",
    # 신자진 -> 진
    "신": "진", "자": "진", "진": "진"
}

# 양인살 (일간 기준, YANGIN_JI_MAP 재활용 가능 - 격국에서 이미 정의됨)
# YANGIN_JI_MAP = {"갑": "묘", "병": "오", "무": "오", "경": "유", "임": "자"}

# 괴강살 (일주가 해당 간지 조합일 때)
GOEGANGSAL_ILJU_LIST = ["경진", "경술", "임진", "임술", "무진", "무술"] # 갑진, 갑술도 포함하는 경우도 있음, JS예제는 6개.

# 백호대살 (각 기둥의 간지가 해당 조합일 때)
BAEKHODAESAL_GANJI_LIST = ["갑진", "을미", "병술", "정축", "무진", "임술", "계축"]

# 귀문관살 (지지 쌍이 사주 내에 있을 때) - 정렬된 쌍으로 정의
GWIMUNGWANSAL_PAIRS = [
    tuple(sorted(("자", "유"))), tuple(sorted(("축", "오"))), tuple(sorted(("인", "미"))),
    tuple(sorted(("묘", "신"))), tuple(sorted(("진", "해"))), tuple(sorted(("사", "술")))
]

# 공망 (일주 기준)
# (일간 인덱스 - 일지 인덱스) % 12 결과에 따른 공망 지지 쌍
# GAN, JI 리스트는 이미 상단에 정의되어 있음
GONGMANG_MAP_BY_DIFF = {
    # 일간-일지 인덱스 차 (mod 12) : [공망지지1, 공망지지2]
    # 예: 갑자일주 -> 갑(0)-자(0)=0 -> 술,해 공망
    0: ["술", "해"], 10: ["신", "유"], 8: ["오", "미"],
    6: ["진", "사"], 4: ["인", "묘"], 2: ["자", "축"]
    # JS에서는 (일간idx - 일지idx) % 12 값 사용.
    # 갑자(0,0) -> 0. 을축(1,1) -> 0. 병인(2,2) -> 0.
    # 즉, 같은 순번의 간지가 만나면 0. (갑0-자0=0, 을1-축1=0)
    # 갑술(0,10) -> (0-10)%12 = -10%12 = 2.
    # 계해(9,11) -> (9-11)%12 = -2%12 = 10.
}
# PILLAR_NAMES_KOR (전체 기둥 이름) - 신살 결과 표시시 사용
PILLAR_NAMES_KOR = ["년주", "월주", "일주", "시주"]


def analyze_shinsal(saju_8char_details):
    """
    사주팔자를 기반으로 주요 신살을 분석합니다.
    saju_8char_details: {"year_gan":yg, "year_ji":yj, ..., "day_gan":dg, ...}
    반환: ["신살 결과 문자열 리스트"]
    """
    ilgan_char = saju_8char_details["day_gan"]
    all_gans = [saju_8char_details["year_gan"], saju_8char_details["month_gan"], saju_8char_details["day_gan"], saju_8char_details["time_gan"]]
    all_jis = [saju_8char_details["year_ji"], saju_8char_details["month_ji"], saju_8char_details["day_ji"], saju_8char_details["time_ji"]]
    
    # 사주 각 기둥의 간지 문자열 생성
    pillar_ganjis_str = [
        saju_8char_details["year_gan"] + saju_8char_details["year_ji"],
        saju_8char_details["month_gan"] + saju_8char_details["month_ji"],
        saju_8char_details["day_gan"] + saju_8char_details["day_ji"],
        saju_8char_details["time_gan"] + saju_8char_details["time_ji"]
    ]
    ilju_ganji_str = pillar_ganjis_str[2] # 일주 간지

    found_shinsals_set = set() # 중복 방지를 위해 set 사용

    # 1. 천을귀인
    if ilgan_char in CHEONEULGWIIN_MAP:
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char in CHEONEULGWIIN_MAP[ilgan_char]:
                found_shinsals_set.add(f"천을귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    # 2. 문창귀인
    if ilgan_char in MUNCHANGGWIIN_MAP:
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char == MUNCHANGGWIIN_MAP[ilgan_char]:
                found_shinsals_set.add(f"문창귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
    
    # 3. 도화살 (년지 또는 일지 기준)
    yeonji_char = saju_8char_details["year_ji"]
    ilji_char = saju_8char_details["day_ji"]
    dohwa_for_yeonji = DOHWASAL_MAP.get(yeonji_char)
    dohwa_for_ilji = DOHWASAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if dohwa_for_yeonji and ji_char == dohwa_for_yeonji:
            found_shinsals_set.add(f"도화살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if dohwa_for_ilji and ji_char == dohwa_for_ilji and dohwa_for_ilji != dohwa_for_yeonji : # 연지 기준으로 이미 추가된 경우 중복 방지 (일지와 연지가 같을 때)
            found_shinsals_set.add(f"도화살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    # 4. 역마살 (년지 또는 일지 기준)
    yeokma_for_yeonji = YEONGMASAL_MAP.get(yeonji_char)
    yeokma_for_ilji = YEONGMASAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if yeokma_for_yeonji and ji_char == yeokma_for_yeonji:
            found_shinsals_set.add(f"역마살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if yeokma_for_ilji and ji_char == yeokma_for_ilji and yeokma_for_ilji != yeokma_for_yeonji:
            found_shinsals_set.add(f"역마살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
            
    # 5. 화개살 (년지 또는 일지 기준)
    hwagae_for_yeonji = HWAGAESAL_MAP.get(yeonji_char)
    hwagae_for_ilji = HWAGAESAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if hwagae_for_yeonji and ji_char == hwagae_for_yeonji:
            found_shinsals_set.add(f"화개살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if hwagae_for_ilji and ji_char == hwagae_for_ilji and hwagae_for_ilji != hwagae_for_yeonji:
            found_shinsals_set.add(f"화개살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    # 6. 양인살 (일간 기준, YANGIN_JI_MAP은 격국 분석에서 이미 정의됨)
    if ilgan_char in YANGIN_JI_MAP: # YANGIN_JI_MAP이 정의되어 있어야 함
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char == YANGIN_JI_MAP[ilgan_char]:
                found_shinsals_set.add(f"양인살: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
    
    # 7. 괴강살 (일주가 해당 간지일 때)
    if ilju_ganji_str in GOEGANGSAL_ILJU_LIST:
        found_shinsals_set.add(f"괴강살: 일주({ilju_ganji_str})")
        
    # 8. 백호대살 (각 기둥의 간지가 해당될 때)
    for pillar_idx, current_pillar_ganji_str in enumerate(pillar_ganjis_str):
        if current_pillar_ganji_str in BAEKHODAESAL_GANJI_LIST:
            found_shinsals_set.add(f"백호대살: {PILLAR_NAMES_KOR[pillar_idx]}({current_pillar_ganji_str})")
            
    # 9. 귀문관살 (지지 쌍이 사주 내에 있을 때)
    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(list(enumerate(all_jis)), 2):
        pair_sorted = tuple(sorted((i_ji, j_ji)))
        if pair_sorted in GWIMUNGWANSAL_PAIRS:
            found_shinsals_set.add(f"귀문관살: {PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})")

    # 10. 공망 (일주 기준)
    try:
        ilgan_idx = GAN.index(ilgan_char)
        ilji_idx = JI.index(ilji_char) # JI는 한글 지지 리스트 ["자", "축", ...]
        
        # 일주 순번 (0~59, 갑자=0): (일간idx - 일지idx + 12) % 12 -> 이 값은 순중(旬中)을 찾기 위함.
        # 갑자일주(0,0) -> (0-0)%12 = 0 (갑자순)
        # 계해일주(9,11) -> (9-11)%12 = -2%12 = 10 (갑인순)
        # JS 예제: mod(GAN.indexOf(ilgan) - JI_H.indexOf(ilji), 12);
        # 이 diff는 10개의 천간과 12개의 지지가 순환할 때, 60갑자 중 현재 일주가 몇 번째 '순(旬)'에 속하는지를 나타내는 지표 중 하나.
        # 갑자순(0)은 술해가 공망, 갑술순(2)은 신유가 공망... 순서대로 2칸씩 밀림.
        # (일간 idx - 일지 idx + 120) % 12 로 음수 방지. (120은 12의 배수)
        # JS: (일간idx - 일지idx) 로 나온 diff값으로 GONGMANG_MAP_BY_DIFF에서 찾음.
        # diff 값의 범위는 -11 ~ 11. mod 12하면 0 ~ 11.
        # (0-0)%12 = 0
        # (0-1)%12 = 11 (갑자일주면 자가 일지, 갑축일주는 없음. 갑인, 갑묘, 갑진... / 일주가 갑축은 없으므로 (0-1)은 발생 안함)
        # 일주 갑자(0,0) -> diff = 0
        # 일주 을축(1,1) -> diff = 0
        # ...
        # 일주 계유(9,9) -> diff = 0 (갑자순) -> 술해 공망
        # 일주 갑술(0,10) -> diff = (0-10)%12 = -10%12 = 2 (갑술순) -> 신유 공망 (JS맵: 10: 신유, 0: 술해. JS diff는 갑자순일때 0, 갑술순일때 10, 갑신순일때 8...)
        # JS의 diff 계산법: (일간idx - 일지idx) % 12. (갑자:0, 갑술: -10%12=2, 갑신:-8%12=4, 갑오:-6%12=6, 갑진:-4%12=8, 갑인:-2%12=10)
        # 갑자(0,0) -> 0. GONGMANG_MAP_BY_DIFF[0] = ["술","해"] -> 맞음
        # 갑술(0,10) -> (0-10)%12 = 2. GONGMANG_MAP_BY_DIFF[2] = ["자","축"] -> JS맵은 10: 신유.
        # JS의 GONGMANG_MAP_BY_DIFF = { 0: ["술","해"], 10: ["신","유"], 8: ["오","미"], 6: ["진","사"], 4: ["인","묘"], 2: ["자","축"] };
        # 이 맵의 키는 (일간idx - 일지idx + 12) % 12 값으로 보임.
        
        gongmang_key_diff = (ilgan_idx - ilji_idx + 12) % 12 # 0 ~ 11 사이의 값
        # JS 예제와 Python의 % 연산 음수처리 방식 차이 때문에 JS맵 키 직접 사용 어려움.
        # 공망 찾는 표준 방법: 일주 순번(0~59) 찾고, 해당 순(旬)의 공망 찾기.
        # 일주 순번 = (일간idx * 6 + 일지idx - 일간idx + 60) % 60 (다른 방법도 많음)
        # 여기서는 JS 예제의 GONGMANG_MAP_BY_DIFF 키를 Python의 diff 계산 결과에 맞게 조정해야 함.
        # (일간idx - 일지idx + 12) % 12 -> 0:갑자순, 2:갑술순, 4:갑신순, 6:갑오순, 8:갑진순, 10:갑인순
        # JS 예제 map key : 갑자순(0), 갑인순(10), 갑진순(8), 갑오순(6), 갑신순(4), 갑술순(2)

        # JS의 GONGMANG_MAP_BY_DIFF 키는 JS방식의 diff % 12 결과임
        # (일간idx - 일지idx) 를 Python에서 % 12 하면 결과가 다를 수 있으므로,
        # 일주 60갑자 번호를 찾고, 그 번호가 속한 순(旬)의 공망을 찾는 것이 더 표준적.
        # 갑자(0) ~ 계유(9) -> 술해 공망
        # 갑술(10) ~ 계미(19) -> 신유 공망
        # 갑신(20) ~ 계사(29) -> 오미 공망
        # ...
        # 일주 60갑자 인덱스 계산
        ilju_gapja_idx = -1
        for i in range(60):
            if GAN[i % 10] == ilgan_char and JI[i % 12] == ilji_char:
                ilju_gapja_idx = i
                break
        
        if ilju_gapja_idx != -1:
            gongmang_jis = JI[ (ilju_gapja_idx + 10) % 12 ], JI[ (ilju_gapja_idx + 11) % 12 ]
            found_shinsals_set.add(f"공망(空亡): 일주({ilju_ganji_str}) 기준 {gongmang_jis[0]}, {gongmang_jis[1]} 공망")
            
            found_in_pillars = []
            for ji_idx, ji_char_in_saju in enumerate(all_jis):
                if ji_char_in_saju in gongmang_jis:
                    found_in_pillars.append(f"{PILLAR_NAMES_KOR[ji_idx]}의 {ji_char_in_saju}")
            if found_in_pillars:
                found_shinsals_set.add(f"  └ ({', '.join(found_in_pillars)})가 공망에 해당합니다.")

    except IndexError: # GAN.index 또는 JI.index 실패 시 (거의 발생 안 함)
        pass # 공망 계산 실패
        
    return sorted(list(found_shinsals_set))


def get_shinsal_detail_explanation(found_shinsals_list):
    """발견된 신살 종류에 따라 간단한 설명을 반환합니다."""
    if not found_shinsals_list:
        return "<p>특별히 나타나는 주요 신살이 없습니다.</p>"

    explanation_parts = []
    # HTML 예제의 설명을 기반으로 각 신살 타입에 대한 설명 추가
    # 설명은 키워드 기반으로 찾아서 추가 (중복 방지)
    main_shinsal_explanations = {
        "천을귀인": "어려울 때 귀인의 도움을 받거나 위기를 넘기는 행운이 따르는 길성 중의 길성입니다.",
        "문창귀인": "학문, 지혜, 총명함을 나타내며 글재주나 시험운 등에 긍정적인 영향을 줄 수 있습니다.",
        "도화살": "매력, 인기, 예술적 감각을 의미하며, 이성에게 인기가 많을 수 있으나 때로는 구설을 조심해야 합니다.",
        "역마살": "활동성, 이동, 변화, 여행, 해외와의 인연 등을 나타냅니다. 한 곳에 정착하기보다 변화를 추구하는 성향일 수 있습니다.",
        "화개살": "예술, 종교, 학문, 철학 등 정신세계와 관련된 분야에 재능이나 인연이 깊을 수 있습니다. 때로 고독감을 느끼기도 합니다.",
        "양인살": "강한 에너지, 카리스마, 독립심, 경쟁심을 나타냅니다. 순탄할 때는 큰 성취를 이루지만, 운이 나쁠 때는 과격함이나 사건사고를 조심해야 합니다.",
        "괴강살": "매우 강한 기운과 리더십, 총명함을 나타냅니다. 극단적인 성향이나 고집을 주의해야 하며, 큰 인물이 될 가능성도 있습니다.",
        "백호대살": "강한 기운으로 인해 급작스러운 사건, 사고, 질병 등을 경험할 수 있음을 암시하므로 평소 건강과 안전에 유의하는 것이 좋습니다.",
        "귀문관살": "예민함, 직관력, 영감, 독특한 정신세계를 나타냅니다. 때로는 신경과민, 변덕, 집착 등으로 나타날 수 있어 마음의 안정이 중요합니다.",
        "공망": "해당 글자의 영향력이 약화되거나 공허함을 의미합니다. 정신적인 활동, 종교, 철학 등에 관심을 두거나, 예상 밖의 결과나 변화를 경험할 수 있습니다."
    }
    
    added_explanations_keys = set() # 이미 추가된 설명인지 확인

    for shinsal_item_str in found_shinsals_list:
        for shinsal_key, desc in main_shinsal_explanations.items():
            if shinsal_key in shinsal_item_str and shinsal_key not in added_explanations_keys:
                explanation_parts.append(f"<li><strong>{shinsal_key}:</strong> {desc}</li>")
                added_explanations_keys.add(shinsal_key)
    
    if not explanation_parts:
        return "<p>발견된 신살에 대한 구체적인 설명을 준비 중입니다.</p>"
        
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

# ... (기존의 다른 함수들 determine_shinkang_shinyak, get_hap_chung_detail_explanation 등은 이 위 또는 아래에 위치) ...
# (saju_app.py 파일에 추가될 내용)

# ... (기존 get_shinsal_detail_explanation 함수 등 다음 줄에)

# ───────────────────────────────
# 용신/기신 분석용 상수 및 함수 정의
# (사용자님이 제공해주신 HTML/JS 예제 코드의 로직을 기반으로 작성되었습니다)
# ───────────────────────────────

# 일간 오행을 기준으로 각 관계의 오행을 정의 (GAN_TO_OHENG는 이미 정의됨)
# 1. 일간을 생하는 오행 (인성)
OHENG_HELPER_MAP = {"목": "수", "화": "목", "토": "화", "금": "토", "수": "금"}
# 2. 일간이 생하는 오행 (식상)
OHENG_PRODUCES_MAP = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
# 3. 일간이 극하는 오행 (재성)
OHENG_CONTROLS_MAP = {"목": "토", "화": "금", "토": "수", "금": "목", "수": "화"}
# 4. 일간을 극하는 오행 (관성)
OHENG_IS_CONTROLLED_BY_MAP = {"목": "금", "화": "수", "토": "목", "금": "화", "수": "토"}


def determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_str):
    """
    일간, 신강/신약 상태를 바탕으로 간략화된 용신/기신 후보 오행을 판단합니다.
    (HTML 예제의 determine_yongshin_gishin 함수 로직 기반)
    """
    ilgan_ohaeng = GAN_TO_OHENG.get(day_gan_char)
    if not ilgan_ohaeng:
        return {
            "yongshin": [], "gishin": [],
            "html": "<p>일간의 오행을 알 수 없어 용신/기신을 판단할 수 없습니다.</p>"
        }

    yongshin_candidates = []
    gishin_candidates = []

    # 오행 역할 정의 (일간 기준)
    sik상_ohaeng = OHENG_PRODUCES_MAP.get(ilgan_ohaeng)
    jae성_ohaeng = OHENG_CONTROLS_MAP.get(ilgan_ohaeng)
    gwan성_ohaeng = OHENG_IS_CONTROLLED_BY_MAP.get(ilgan_ohaeng)
    in성_ohaeng = OHENG_HELPER_MAP.get(ilgan_ohaeng)
    bi겁_ohaeng = ilgan_ohaeng # 나와 같은 오행 (비견/겁재)

    if "신강" in shinkang_status_str: # 신강 또는 약간 신강 포함
        # 용신 후보: 식상, 재성, 관성 (일간의 힘을 빼거나 적절히 제어하는 오행)
        if sik상_ohaeng: yongshin_candidates.append(sik상_ohaeng)
        if jae성_ohaeng: yongshin_candidates.append(jae성_ohaeng)
        if gwan성_ohaeng: yongshin_candidates.append(gwan성_ohaeng)
        # 기신 후보: 인성, 비겁 (일간의 힘을 더 강하게 하는 오행)
        if in성_ohaeng: gishin_candidates.append(in성_ohaeng)
        if bi겁_ohaeng: gishin_candidates.append(bi겁_ohaeng)

    elif "신약" in shinkang_status_str: # 신약 또는 약간 신약 포함
        # 용신 후보: 인성, 비겁 (일간의 힘을 더해주는 오행)
        if in성_ohaeng: yongshin_candidates.append(in성_ohaeng)
        if bi겁_ohaeng: yongshin_candidates.append(bi겁_ohaeng)
        # 기신 후보: 식상, 재성, 관성 (일간의 힘을 더 빼거나 극하는 오행)
        if sik상_ohaeng: gishin_candidates.append(sik상_ohaeng)
        if jae성_ohaeng: gishin_candidates.append(jae성_ohaeng)
        if gwan성_ohaeng: gishin_candidates.append(gwan성_ohaeng)

    elif "중화" in shinkang_status_str:
        return {
            "yongshin": [], "gishin": [],
            "html": "<p>중화 사주로 판단됩니다. 이 경우 특정 오행을 용신이나 기신으로 엄격히 구분하기보다는, 사주 전체의 균형과 조화를 유지하고 대운의 흐름에 유연하게 대처하는 것이 중요할 수 있습니다. 때로는 사주에 부족하거나 고립된 오행을 보충하는 방향을 고려하기도 합니다.</p>"
        }
    else: # shinkang_status_str이 예상치 못한 값일 경우
        return {
            "yongshin": [], "gishin": [],
            "html": "<p>일간의 강약 상태가 명확하지 않아 용신/기신을 판단하기 어렵습니다.</p>"
        }

    # 중복 제거 및 정렬
    unique_yongshin = sorted(list(set(yongshin_candidates)))
    unique_gishin = sorted(list(set(gishin_candidates)))
    
    # (드물지만) 용신과 기신에 같은 오행이 들어간 경우 제거 (JS 예제 참고)
    # common_elements = [y_el for y_el in unique_yongshin if y_el in unique_gishin]
    # unique_yongshin = [y_el for y_el in unique_yongshin if y_el not in common_elements]
    # unique_gishin = [g_el for g_el in unique_gishin if g_el not in common_elements]
    # -> 현재 로직상으로는 common_elements가 거의 발생하지 않음.

    html_parts = []
    if unique_yongshin:
        yongshin_str = ", ".join([f"<span style='color:#15803d; font-weight:bold;'>{o}({OHENG_TO_HANJA.get(o, '')})</span>" for o in unique_yongshin])
        html_parts.append(f"<p>유력한 용신(喜神) 후보 오행: {yongshin_str}</p>")
    else:
        html_parts.append("<p>용신(喜神)으로 특정할 만한 오행을 명확히 구분하기 어렵습니다. (중화 사주 외)</p>")
    
    if unique_gishin:
        gishin_str = ", ".join([f"<span style='color:#b91c1c; font-weight:bold;'>{o}({OHENG_TO_HANJA.get(o, '')})</span>" for o in unique_gishin])
        html_parts.append(f"<p>주의가 필요한 기신(忌神) 후보 오행: {gishin_str}</p>")
    else:
        html_parts.append("<p>특별히 기신(忌神)으로 강하게 작용할 만한 오행이 두드러지지 않을 수 있습니다.</p>")

    return {"yongshin": unique_yongshin, "gishin": unique_gishin, "html": "".join(html_parts)}


def get_gaewoon_tips_html(yongshin_list):
    """용신 오행에 따른 간단한 개운법 팁 HTML을 반환합니다."""
    if not yongshin_list:
        return ""
    
    tips_html = "<h5 style='color: #047857; margin-top: 0.8rem; margin-bottom: 0.3rem; font-size:1em;'>🍀 간단 개운법 (용신 활용)</h5><ul style='list-style:none; padding-left:0; font-size:0.9em;'>"
    gaewoon_tips_data = {
        "목": "<li><strong style='color:#15803d;'>목(木) 용신:</strong> 동쪽 방향, 푸른색/초록색 계열 아이템 활용. 숲이나 공원 산책, 식물 키우기, 교육/문화/기획 관련 활동.</li>",
        "화": "<li><strong style='color:#15803d;'>화(火) 용신:</strong> 남쪽 방향, 붉은색/분홍색/보라색 계열 아이템 활용. 밝고 따뜻한 환경 조성, 예체능/방송/조명/열정적인 활동.</li>",
        "토": "<li><strong style='color:#15803d;'>토(土) 용신:</strong> 중앙(거주지 중심), 노란색/황토색/베이지색 계열 아이템 활용. 안정적이고 편안한 환경, 명상, 신용을 중시하는 활동, 등산.</li>",
        "금": "<li><strong style='color:#15803d;'>금(金) 용신:</strong> 서쪽 방향, 흰색/은색/금색 계열 아이템 활용. 단단하고 정돈된 환경, 금속 액세서리, 결단력과 의리를 지키는 활동, 악기 연주.</li>",
        "수": "<li><strong style='color:#15803d;'>수(水) 용신:</strong> 북쪽 방향, 검은색/파란색/회색 계열 아이템 활용. 물가나 조용하고 차분한 환경, 지혜를 활용하는 활동, 명상이나 충분한 휴식.</li>"
    }
    for yongshin_ohaeng in yongshin_list:
        tips_html += gaewoon_tips_data.get(yongshin_ohaeng, f"<li>{yongshin_ohaeng}({OHENG_TO_HANJA.get(yongshin_ohaeng,'')}) 용신에 대한 개운법 정보를 준비 중입니다.</li>")
    
    tips_html += "</ul><p style='font-size:0.8rem; color:#555; margin-top:0.5rem;'>* 위 내용은 일반적인 개운법이며, 개인의 전체 사주 구조와 상황에 따라 다를 수 있습니다. 참고용으로 활용하세요.</p>"
    return tips_html

# ... (기존의 다른 함수들 get_shinsal_detail_explanation 등은 이 위 또는 아래에 위치) ...
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

# get_month_ganji 함수의 개선된 절기 검색 로직 (이전 답변 참고 및 일부 강조)
def get_month_ganji(year_gan_char, birth_dt, solar_data_dict):
    # ... (생략) ...
    saju_year_of_birth = get_saju_year(birth_dt, solar_data_dict) # birth_dt의 사주년도

    candidate_solar_years = sorted(list(set([birth_dt.year - 1, birth_dt.year, birth_dt.year + 1]))) # birth_dt의 양력년도 기준 +-1년 탐색

    all_relevant_terms = []
    for solar_yr in candidate_solar_years:
        year_terms_data = solar_data_dict.get(solar_yr, {})
        for term_name, term_datetime_obj in year_terms_data.items():
            if term_name in SAJU_MONTH_TERMS_ORDER:
                all_relevant_terms.append({'name': term_name, 'datetime': term_datetime_obj})

    if not all_relevant_terms:
        return f"오류(월주절기데이터부족:{birth_dt.strftime('%Y%m%d')})", "", ""

    all_relevant_terms.sort(key=lambda x: x['datetime'])

    governing_term_name = None
    for term_info in all_relevant_terms:
        if birth_dt >= term_info['datetime']:
            # 이 절기가 birth_dt가 속한 사주년도(saju_year_of_birth)와 동일한 사주년도에 속하는지 확인
            # 이렇게 하면 다른 사주년도의 절기가 잘못 적용되는 것을 방지할 수 있음
            if get_saju_year(term_info['datetime'], solar_data_dict) == saju_year_of_birth:
                governing_term_name = term_info['name']
            # 만약 위 조건 없이, 단순히 시간상 가장 가까운 과거 절기를 찾는다면,
            # 예를 들어 2025년 사주년 초입(입춘 직후)인데, 실수로 2024년 사주년 말(대한)이 선택될 수도 있음.
            # (위 로직에서는 get_saju_year를 통해 필터링 시도)
            # 더 간단하게는, birth_dt 직전의 절기를 찾으면 됨.
            # governing_term_name = term_info['name'] # 이 로직으로 하면 시간상 가장 가까운 과거 절기.
        else:
            break # birth_dt보다 늦은 절기를 만나면 루프 종료

    if not governing_term_name:
         # birth_dt가 수집된 모든 절기 중 가장 이른 것보다도 빠를 경우 (데이터 시작점 이전)
         # 또는 필터링 조건으로 인해 적합한 절기를 찾지 못한 경우
        return f"오류(월주기준절기못찾음:{birth_dt.strftime('%Y%m%d')})", "", ""

    # ... (이후 월지, 월간 계산 로직은 동일) ...
    try:
        month_ji_idx = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji = SAJU_MONTH_BRANCHES[month_ji_idx]
    except ValueError:
        return f"오류(월지변환실패:{governing_term_name})", "", ""

    # 월간 계산
    try:
        yg_idx = GAN.index(year_gan_char)
    except ValueError:
        return f"오류(알수없는연간:{year_gan_char})", "", ""
        
    start_map = {0:2, 5:2, 1:4, 6:4, 2:6, 7:6, 3:8, 8:8, 4:0, 9:0}
    start_gan_idx_for_in_month = start_map.get(yg_idx)

    if start_gan_idx_for_in_month is None:
        return f"오류(월두법맵핑실패:{year_gan_char})", "", ""

    try:
        current_month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    except ValueError:
         return f"오류(알수없는월지:{month_ji})", "", ""

    month_gan_idx = (start_gan_idx_for_in_month + current_month_order_idx) % 10
    month_gan = GAN[month_gan_idx]

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
    # 입력된 birth_dt (생일)는 datetime 객체여야 합니다.
    if not isinstance(birth_dt, datetime):
        return ["오류(잘못된 생년월일 객체)"], 0, False

    # 1. 순행/역행 결정
    try:
        gan_index = GAN.index(year_gan_char) # 연간이 GAN 리스트에 있는지 확인
    except ValueError:
        return [f"오류(알 수 없는 연간: {year_gan_char})"], 0, False # is_sunhaeng 기본값 False
    
    is_yang_year = gan_index % 2 == 0
    is_sunhaeng = (is_yang_year and gender == "남성") or (not is_yang_year and gender == "여성")

    # 2. 생일(birth_dt) 전후의 절기 찾기
    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 이 변수가 사용되기 전에 반드시 초기화되어야 합니다 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    relevant_terms_for_daewoon = []  # <--- 이 라인이 중요합니다!
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 변수 초기화 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    if solar_data_dict is None: # solar_data_dict가 None이면 .get() 호출 시 오류 발생 방지
        return ["오류(절기 데이터 누락)"], 0, is_sunhaeng

    for yr_offset in [-1, 0, 1]: 
        year_to_check_in_solar_terms = birth_dt.year + yr_offset
        year_terms = solar_data_dict.get(year_to_check_in_solar_terms, {}) # 기본값으로 빈 dict 반환
        if year_terms is None: # 혹시 모를 경우 대비 (get의 기본값이 {}이므로 보통은 필요 없음)
            year_terms = {}
            
        for term_name, term_dt_obj in year_terms.items():
            if term_name in SAJU_MONTH_TERMS_ORDER: 
                relevant_terms_for_daewoon.append({'name': term_name, 'datetime': term_dt_obj})
    
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime'])

    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 사용자님 오류 발생 지점 (line 1267 근처) ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    if not relevant_terms_for_daewoon: 
        return ["오류(대운 계산용 절기 부족)"], 0, is_sunhaeng 
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 여기까지 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    
    target_term_dt = None
    if is_sunhaeng: 
        for term_info in relevant_terms_for_daewoon:
            if term_info['datetime'] > birth_dt:
                target_term_dt = term_info['datetime']
                break
    else: 
        for term_info in reversed(relevant_terms_for_daewoon):
            if term_info['datetime'] < birth_dt:
                target_term_dt = term_info['datetime']
                break
    
    if target_term_dt is None:
        return ["오류(대운 목표 절기 탐색 실패)"], 0, is_sunhaeng

    if is_sunhaeng:
        days_difference = (target_term_dt - birth_dt).total_seconds() / (24 * 3600.0)
    else: 
        days_difference = (birth_dt - target_term_dt).total_seconds() / (24 * 3600.0)
    
    daewoon_start_age = max(1, int(round(days_difference / 3.0)))

    if month_gan_char is None or month_ji_char is None: # 월주 간지 누락 시 오류 처리
        return ["오류(월주 정보 누락)"], daewoon_start_age, is_sunhaeng
        
    month_ganji_str = month_gan_char + month_ji_char
    current_month_gapja_idx = -1
    for idx in range(60): 
        if get_ganji_from_index(idx) == month_ganji_str:
            current_month_gapja_idx = idx
            break
    if current_month_gapja_idx == -1:
        return ["오류(월주를 60갑자로 변환 실패)"], daewoon_start_age, is_sunhaeng

    daewoon_list_output = []
    birth_year_solar = birth_dt.year 

    for i_period in range(10): 
        current_daewoon_man_age = daewoon_start_age + (i_period * 10)
        current_daewoon_start_solar_year = birth_year_solar + current_daewoon_man_age
        
        gapja_offset = i_period + 1 
        next_gapja_idx = -1
        if is_sunhaeng:
            next_gapja_idx = (current_month_gapja_idx + gapja_offset) % 60 
        else: 
            next_gapja_idx = (current_month_gapja_idx - gapja_offset + 6000) % 60 
        
        daewoon_ganji_str = get_ganji_from_index(next_gapja_idx)
        daewoon_list_output.append(f"만 {current_daewoon_man_age}세 ({current_daewoon_start_solar_year}년~): {daewoon_ganji_str}")
        
    return daewoon_list_output, daewoon_start_age, is_sunhaeng        
def get_seun_list(start_year, n=10): 
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    output_wolun = []
    try:
        ref_date_for_start_month = datetime(base_year, base_month, 1, 12, 0)
    except ValueError:
        return [(f"오류: 잘못된 기준월 {base_year}-{base_month}", "계산불가")]

    start_saju_year = get_saju_year(ref_date_for_start_month, solar_data_dict)
    start_year_ganji_full, start_year_gan, _ = get_year_ganji(start_saju_year)
    if "오류" in start_year_ganji_full:
        return [(f"오류: 시작 사주년도({start_saju_year}) 연간 계산 실패", "계산불가")]

    _, _, start_month_ji = get_month_ganji(start_year_gan, ref_date_for_start_month, solar_data_dict)
    if "오류" in start_month_ji or not start_month_ji:
        return [(f"오류: 시작월주 계산 실패 (기준일: {base_year}-{base_month}-01)", "계산불가")]
    try:
        start_month_idx = SAJU_MONTH_BRANCHES.index(start_month_ji)
    except ValueError:
        return [(f"오류: 알 수 없는 시작월 지지 ({start_month_ji})", "계산불가")]

    # 사주월(인덱스) -> 대표 양력월 정보 (월이름, 대표일자, 사주년도 대비 양력년도 오프셋, 대표 양력월 숫자)
    month_representative_details = [
        ("인", 15, 0, 2), ("묘", 15, 0, 3), ("진", 15, 0, 4),
        ("사", 15, 0, 5), ("오", 15, 0, 6), ("미", 15, 0, 7),
        ("신", 15, 0, 8), ("유", 15, 0, 9), ("술", 15, 0, 10),
        ("해", 15, 0, 11),("자", 15, 0, 12),("축", 15, 1, 1)
    ]

    for i in range(n):
        current_month_saju_idx = (start_month_idx + i) % 12
        current_saju_year = start_saju_year + (start_month_idx + i) // 12

        current_year_ganji_full, year_gan_for_wolun, _ = get_year_ganji(current_saju_year)
        if "오류" in current_year_ganji_full:
            # 오류 시 표시할 레이블 (사주년/월로 간략히 또는 연도만)
            target_month_branch_char = SAJU_MONTH_BRANCHES[current_month_saju_idx]
            # display_label_for_error = f"{current_saju_year}년 {target_month_branch_char}월"
            display_label_for_error = f"{current_saju_year}-??" # 숫자 형식 유지 시도
            output_wolun.append((display_label_for_error, "오류(연간계산실패)"))
            continue

        _, representative_day, solar_year_offset, representative_solar_month = month_representative_details[current_month_saju_idx]

        try:
            # 월주 계산을 위한 dummy 날짜 (해당 사주월에 속하는 대표 양력 날짜)
            dummy_dt_solar_year = current_saju_year + solar_year_offset
            dummy_birth_dt_for_wolun = datetime(dummy_dt_solar_year, representative_solar_month, representative_day, 12, 0)
        except ValueError:
            # 오류 시 표시할 레이블
            # target_month_branch_char_err = SAJU_MONTH_BRANCHES[current_month_saju_idx]
            # target_term_name_err = SAJU_MONTH_TERMS_ORDER[current_month_saju_idx]
            # display_label_on_err = f"{current_saju_year}년 {target_month_branch_char_err}월({target_term_name_err})"
            display_label_on_err = f"{current_saju_year + solar_year_offset}-{representative_solar_month:02d} (오류)"
            output_wolun.append((display_label_on_err, "오류(대표날짜생성실패)"))
            continue

        wolun_ganji, _, wolun_ji_calculated = get_month_ganji(year_gan_for_wolun, dummy_birth_dt_for_wolun, solar_data_dict)

        # --- 월운 표시 레이블 수정 ---
        if "오류" in wolun_ganji:
            # 월주 계산 오류 시, 대표 양력 연/월로 표시하고 간지는 오류로 표시
            display_label = f"{dummy_birth_dt_for_wolun.year}-{dummy_birth_dt_for_wolun.month:02d}"
            actual_wolun_ganji = wolun_ganji # "오류(...)" 문자열
        else:
            # 정상 계산 시, dummy_birth_dt_for_wolun (대표 양력 날짜)의 연도와 월을 사용
            display_label = f"{dummy_birth_dt_for_wolun.year}-{dummy_birth_dt_for_wolun.month:02d}"
            actual_wolun_ganji = wolun_ganji

        output_wolun.append((display_label, actual_wolun_ganji))

    return output_wolun
    
def get_ilun_list(year_val, month_val, day_val, n=10):
    base_dt = datetime(year_val, month_val, day_val); output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji,_,_ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

# (이전에 모든 함수 및 상수 정의, 기본 import 문들이 와야 합니다)
# 예: import streamlit as st
#     import pandas as pd
#     from datetime import datetime, timedelta
#     import os
#     import math
#     import re
#     from lunardate import LunarDate # 이미 try-except로 처리됨
#     # from clipboard_component import copy_component # 이 라인은 삭제합니다.

# ───────────────────────────────
# 3. Streamlit UI
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

# --- 세션 상태 초기화 ---
if 'saju_calculated_once' not in st.session_state:
    st.session_state.saju_calculated_once = False
if 'interpretation_segments' not in st.session_state:
    st.session_state.interpretation_segments = [] # "전체 풀이 내용 다시 보기" expander용
if 'show_interpretation_guide_on_click' not in st.session_state:
    st.session_state.show_interpretation_guide_on_click = False # expander 표시 여부

st.sidebar.header("1. 출생 정보")
calendar_type = st.sidebar.radio("달력 유형", ("양력", "음력"), index=0, horizontal=True)
is_leap_month = False
if calendar_type == "음력":
    is_leap_month = st.sidebar.checkbox("윤달 (Leap Month)", help="음력 생일이 윤달인 경우 체크해주세요.")

current_year_for_input = datetime.now().year
min_input_year = 1900
max_input_year = 2100
if solar_data:
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
ty = st.sidebar.number_input("기준 연도 ", min_input_year, max_input_year + 10, today.year, help=f"양력 기준년도 ({min_input_year}~{max_input_year+10} 범위)")
tm = st.sidebar.number_input("기준 월  ", 1, 12, today.month, key="ui_target_month_final")
td = st.sidebar.number_input("기준 일  ", 1, 31, today.day, key="ui_target_day_final")

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    st.session_state.interpretation_segments = []
    st.session_state.saju_calculated_once = False
    st.session_state.show_interpretation_guide_on_click = False

    birth_dt_input_valid = True
    birth_dt = None

    if calendar_type == "양력":
        try:
            birth_dt = datetime(by,bm,bd,bh,bmin)
        except ValueError:
            st.error("❌ 유효하지 않은 양력 날짜/시간입니다. 다시 확인해주세요.")
            birth_dt_input_valid = False
            st.stop()
    else: # 음력
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
        # --- 사주 명식 계산 ---
        saju_year_val = get_saju_year(birth_dt, solar_data)
        year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
        month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
        day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day)
        time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)

        # ==================================================================
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼ 생년월일 및 현재 나이 표시 코드 (여기에 삽입) ▼▼▼▼▼▼▼▼▼▼▼▼▼
        # ==================================================================
        st.subheader("👤 기본 정보")

        # 입력된 생년월일시 정보 (사이드바에서 가져온 값 사용)
        birth_info_display_text = f"{calendar_type} {by}년 {bm}월 {bd}일"
        if calendar_type == "음력" and is_leap_month:
            birth_info_display_text += " (윤달)"
        birth_info_display_text += f" {bh:02d}시 {bmin:02d}분 출생"
        
        st.markdown(f"**입력 생년월일시:** {birth_info_display_text}")

        if calendar_type == "음력":
            # birth_dt는 이미 양력으로 변환된 datetime 객체입니다.
            st.markdown(f"**양력 환산 생일:** {birth_dt.strftime('%Y년 %m월 %d일')}")

        # 현재 만 나이 계산 및 표시
        today_date = datetime.now() # 현재 날짜 및 시간
        # calculate_age 함수는 스크립트 상단에 미리 정의되어 있어야 합니다.
        # birth_dt (양력 datetime 객체)와 today_date를 전달
        age_calculated = calculate_age(birth_dt, today_date) 
        st.markdown(f"**현재 만 나이:** {age_calculated}세 (기준일: {today_date.strftime('%Y년 %m월 %d일')})")
        
        st.markdown("---") # 다음 섹션과의 구분을 위한 선
        # ==================================================================
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 생년월일 및 현재 나이 표시 코드 끝 ▲▲▲▲▲▲▲▲▲▲▲▲▲
        # ==================================================================

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
        saju_year_caption = f"사주 기준 연도 (입춘 기준): {saju_year_val}년"
        st.caption(saju_year_caption)
        st.session_state.interpretation_segments.append(("📜 사주 명식", ms_df.to_markdown() + "\n" + saju_year_caption))

        # --- 분석을 위한 8글자 준비 및 유효성 검사 ---
        saju_8char_for_analysis = {
            "year_gan": year_gan_char, "year_ji": year_ji_char,
            "month_gan": month_gan_char, "month_ji": month_ji_char,
            "day_gan": day_gan_char, "day_ji": day_ji_char,
            "time_gan": time_gan_char, "time_ji": time_ji_char
        }
        analysis_possible = True
        for key, val_char in saju_8char_for_analysis.items():
            if not val_char or len(val_char) != 1 or \
               (key.endswith("_gan") and val_char not in GAN) or \
               (key.endswith("_ji") and val_char not in JI):
                analysis_possible = False; break
        
        ohaeng_strengths, sipshin_strengths = {}, {}
        shinkang_status_result, gekuk_name_result = "분석 정보 없음", "분석 정보 없음"
        shinkang_explanation_html, gekuk_explanation_html = "", ""
        hap_chung_results_dict, found_shinsals_list, yongshin_gishin_info = {}, [], {}

        if analysis_possible:
            try:
                ohaeng_strengths, sipshin_strengths = calculate_ohaeng_sipshin_strengths(saju_8char_for_analysis)
            except Exception as e:
                st.warning(f"오행/십신 분석 중 오류 발생: {e}")
                analysis_possible = False 
        else:
            st.warning("사주 기둥 중 일부가 정확히 계산되지 않아 상세 분석을 수행할 수 없습니다.")

        # --- 오행 분석 표시 ---
        st.markdown("---")
        st.subheader("🌳🔥 오행(五行) 분석")
        ohaeng_summary_exp_text_for_display = "오행 분석 정보 없음"
        ohaeng_analysis_text_for_segment = "오행 분석 정보 없음"
        ohaeng_table_data_for_segment = None
        if ohaeng_strengths and analysis_possible:
            ohaeng_df_for_chart = pd.DataFrame.from_dict(ohaeng_strengths, orient='index', columns=['세력']).reindex(OHENG_ORDER)
            st.bar_chart(ohaeng_df_for_chart, height=300, use_container_width=True)
            ohaeng_summary_exp_text_for_display = get_ohaeng_summary_explanation(ohaeng_strengths)
            st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #60a5fa;'>{ohaeng_summary_exp_text_for_display}</div>", unsafe_allow_html=True)
            ohaeng_analysis_text_for_segment = strip_html_tags(ohaeng_summary_exp_text_for_display)
            ohaeng_table_data = {"오행": OHENG_ORDER, "세력": [ohaeng_strengths.get(o,0.0) for o in OHENG_ORDER]}
            ohaeng_table_data_for_segment = pd.DataFrame(ohaeng_table_data).to_markdown(index=False)
        elif analysis_possible:
            st.markdown("오행 강약 정보를 계산 중이거나 표시할 데이터가 없습니다.")
        st.session_state.interpretation_segments.append(("🌳🔥 오행(五行) 분석", ohaeng_analysis_text_for_segment))
        if ohaeng_table_data_for_segment:
            st.session_state.interpretation_segments.append(("오행 세력표", ohaeng_table_data_for_segment))
        else:
            st.session_state.interpretation_segments.append(("오행 세력표", "세력표 정보 없음"))
        
        # --- 십신 분석 표시 ---
        st.markdown("---")
        st.subheader("🌟 십신(十神) 분석")
        sipshin_summary_exp_text_for_display = "십신 분석 정보 없음"
        sipshin_analysis_text_for_segment = "십신 분석 정보 없음"
        sipshin_table_data_for_segment = None
        if sipshin_strengths and analysis_possible:
            sipshin_df_for_chart = pd.DataFrame.from_dict(sipshin_strengths, orient='index', columns=['세력']).reindex(SIPSHIN_ORDER)
            st.bar_chart(sipshin_df_for_chart, height=400, use_container_width=True)
            sipshin_summary_exp_text_for_display = get_sipshin_summary_explanation(sipshin_strengths, day_gan_char)
            st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #7c3aed;'>{sipshin_summary_exp_text_for_display}</div>", unsafe_allow_html=True)
            sipshin_analysis_text_for_segment = strip_html_tags(sipshin_summary_exp_text_for_display)
            sipshin_table_data = {"십신": SIPSHIN_ORDER, "세력": [sipshin_strengths.get(s,0.0) for s in SIPSHIN_ORDER]}
            sipshin_table_data_for_segment = pd.DataFrame(sipshin_table_data).to_markdown(index=False)
        elif analysis_possible:
            st.markdown("십신 강약 정보를 계산 중이거나 표시할 데이터가 없습니다.")
        st.session_state.interpretation_segments.append(("🌟 십신(十神) 분석", sipshin_analysis_text_for_segment))
        if sipshin_table_data_for_segment:
            st.session_state.interpretation_segments.append(("십신 세력표", sipshin_table_data_for_segment))
        else:
            st.session_state.interpretation_segments.append(("십신 세력표", "세력표 정보 없음"))

        # --- 신강/신약 및 격국 분석 ---
        st.markdown("---")
        st.subheader("💪 일간 강약 및 격국(格局) 분석")
        if analysis_possible and ohaeng_strengths and sipshin_strengths:
            try:
                shinkang_status_result = determine_shinkang_shinyak(sipshin_strengths)
                shinkang_explanation_html = get_shinkang_explanation(shinkang_status_result)
                gekuk_name_result = determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths)
                gekuk_explanation_html = get_gekuk_explanation(gekuk_name_result)
            except Exception as e:
                st.warning(f"신강/신약 또는 격국 분석 중 오류 발생: {e}")
                shinkang_status_result, gekuk_name_result = "분석 오류", "분석 오류"
        # 변수 초기화 보장
        shinkang_status_result = shinkang_status_result if 'shinkang_status_result' in locals() else "분석 정보 없음"
        shinkang_explanation_html = shinkang_explanation_html if 'shinkang_explanation_html' in locals() else ""
        gekuk_name_result = gekuk_name_result if 'gekuk_name_result' in locals() else "분석 정보 없음"
        gekuk_explanation_html = gekuk_explanation_html if 'gekuk_explanation_html' in locals() else ""
        
        col_shinkang, col_gekuk = st.columns(2)
        with col_shinkang:
            st.markdown(f"""<div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 1.25rem; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><h4 style="font-size: 1.05em; font-weight: 600; color: #1f2937; margin-bottom: 0.6rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.4rem;">일간 강약 (신강/신약)</h4><p style="font-size: 1.2em; font-weight: bold; color: #2563eb; margin-bottom: 0.75rem;">{shinkang_status_result}</p><p style="font-size: 0.9em; color: #4b5563; line-height: 1.6;">{shinkang_explanation_html}</p></div>""", unsafe_allow_html=True)
        with col_gekuk:
            st.markdown(f"""<div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 1.25rem; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><h4 style="font-size: 1.05em; font-weight: 600; color: #1f2937; margin-bottom: 0.6rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.4rem;">격국(格局) 분석</h4><p style="font-size: 1.2em; font-weight: bold; color: #059669; margin-bottom: 0.75rem;">{gekuk_name_result}</p><p style="font-size: 0.9em; color: #4b5563; line-height: 1.6;">{gekuk_explanation_html}</p></div>""", unsafe_allow_html=True)
        st.session_state.interpretation_segments.append(("💪 일간 강약", f"**{shinkang_status_result}**\n{strip_html_tags(shinkang_explanation_html)}"))
        st.session_state.interpretation_segments.append(("💪 격국(格局) 분석", f"**{gekuk_name_result}**\n{strip_html_tags(gekuk_explanation_html)}"))

        # --- 합충형해파 분석 ---
        st.markdown("---")
        st.subheader("🤝💥 합충형해파 분석")
        hap_chung_text_for_segment_parts = []
        if analysis_possible and 'day_gan_char' in locals() and day_gan_char: # day_gan_char는 이전 단계에서 정의됨
            try:
                hap_chung_results_dict = analyze_hap_chung_interactions(saju_8char_for_analysis)
                if any(v for v in hap_chung_results_dict.values()):
                    st.markdown("##### 발견된 주요 상호작용:")
                    output_html_parts = []
                    for interaction_type, found_list in hap_chung_results_dict.items():
                        if found_list:
                            output_html_parts.append(f"<h6 style='color: #374151; margin-top: 0.6rem; margin-bottom: 0.2rem; font-size:0.95em;'>{interaction_type}</h6>")
                            items_html = "".join([f"<li style='background-color: #eef2ff; color: #312e81; padding: 0.3rem 0.6rem; border-radius: 0.25rem; margin-bottom: 0.25rem; font-size: 0.9rem;'>{item}</li>" for item in found_list])
                            output_html_parts.append(f"<ul style='list-style: none; padding-left: 0; margin-bottom: 0.5rem;'>{items_html}</ul>")
                            hap_chung_text_for_segment_parts.append(f"**{interaction_type}**\n" + "\n".join([f"- {item}" for item in found_list]))
                    if output_html_parts: st.markdown("".join(output_html_parts), unsafe_allow_html=True)
                    hap_chung_explanation_html_val = get_hap_chung_detail_explanation(hap_chung_results_dict)
                    st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #f59e0b;'>{hap_chung_explanation_html_val}</div>", unsafe_allow_html=True)
                    hap_chung_text_for_segment_parts.append(f"\n**설명:**\n{strip_html_tags(hap_chung_explanation_html_val)}")
                else:
                    msg = "특별히 두드러지는 합충형해파의 관계가 나타나지 않습니다. 비교적 안정적인 구조일 수 있습니다."
                    st.markdown(f"<p style='font-size:0.95rem; color:#4b5563;'>{msg}</p>", unsafe_allow_html=True)
                    hap_chung_text_for_segment_parts.append(msg)
            except Exception as e:
                st.warning(f"합충형해파 분석 중 오류 발생: {e}")
                hap_chung_text_for_segment_parts.append("합충형해파 분석 중 오류 발생")
        else:
            hap_chung_text_for_segment_parts.append("사주 정보가 부족하여 합충형해파 분석을 수행할 수 없습니다.")
        st.session_state.interpretation_segments.append(("🤝💥 합충형해파 분석", "\n\n".join(hap_chung_text_for_segment_parts)))
        
        # --- 주요 신살 분석 ---
        st.markdown("---")
        st.subheader("🔮 주요 신살(神煞) 분석")
        shinsal_text_for_segment_parts = []
        if analysis_possible and 'day_gan_char' in locals() and day_gan_char:
            try:
                found_shinsals_list = analyze_shinsal(saju_8char_for_analysis)
                if found_shinsals_list:
                    st.markdown("##### 발견된 주요 신살:")
                    items_html = "".join([f"<li style='background-color: #eef2ff; color: #312e81; padding: 0.4rem 0.75rem; border-radius: 0.25rem; margin-bottom: 0.3rem; font-size: 0.9rem; line-height: 1.5;'>{item}</li>" for item in found_shinsals_list])
                    st.markdown(f"<ul style='list-style: none; padding-left: 0; margin-bottom: 0.5rem;'>{items_html}</ul>", unsafe_allow_html=True)
                    shinsal_explanation_html_val = get_shinsal_detail_explanation(found_shinsals_list)
                    st.markdown(f"<div style='font-size: 0.95rem; color: #4b5563; margin-top: 1rem; padding: 0.75rem; background-color: #f9fafb; border-radius: 4px; border-left: 3px solid #8b5cf6;'>{shinsal_explanation_html_val}</div>", unsafe_allow_html=True)
                    shinsal_text_for_segment_parts.append("**발견된 주요 신살:**\n" + "\n".join([f"- {item}" for item in found_shinsals_list]))
                    shinsal_text_for_segment_parts.append(f"\n**설명:**\n{strip_html_tags(shinsal_explanation_html_val)}")
                else:
                    msg = "특별히 나타나는 주요 신살이 없습니다."
                    st.markdown(f"<p style='font-size:0.95rem; color:#4b5563;'>{msg}</p>", unsafe_allow_html=True)
                    shinsal_text_for_segment_parts.append(msg)
            except Exception as e:
                st.warning(f"신살 분석 중 오류 발생: {e}")
                shinsal_text_for_segment_parts.append("신살 분석 중 오류 발생")
        else:
            shinsal_text_for_segment_parts.append("사주 정보가 부족하여 신살 분석을 수행할 수 없습니다.")
        st.session_state.interpretation_segments.append(("🔮 주요 신살(神煞) 분석", "\n\n".join(shinsal_text_for_segment_parts)))

        # --- 용신/기신 분석 ---
        st.markdown("---")
        st.subheader("☯️ 용신(喜神) 및 기신(忌神) 분석 (간략)")
        yongshin_text_for_segment = "용신/기신 분석 정보 없음"
        gaewoon_text_for_segment = ""
        if (analysis_possible and
            'shinkang_status_result' in locals() and shinkang_status_result not in ["분석 정보 없음", "분석 오류", "계산 불가"] and
            'day_gan_char' in locals() and day_gan_char):
            try:
                yongshin_gishin_info = determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_result)
                st.markdown(yongshin_gishin_info["html"], unsafe_allow_html=True)
                gaewoon_tips_html_content = get_gaewoon_tips_html(yongshin_gishin_info["yongshin"])
                if gaewoon_tips_html_content:
                    st.markdown(f"<div style='margin-top: 1rem; padding: 0.85rem 1rem; background-color: #e0f2fe; border-left: 4px solid #0284c7; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>{gaewoon_tips_html_content}</div>", unsafe_allow_html=True)
                yongshin_text_for_segment = strip_html_tags(yongshin_gishin_info.get("html", "분석 정보 없음"))
                if yongshin_gishin_info.get("yongshin"):
                    gaewoon_text_for_segment = strip_html_tags(gaewoon_tips_html_content)
            except Exception as e:
                st.warning(f"용신/기신 분석 중 오류 발생: {e}")
        elif not analysis_possible:
            pass 
        else:
            st.info("일간의 강약 정보가 명확하지 않아 용신/기신 분석을 수행하기 어렵습니다.")
        
        yongshin_notice_html = """<div style="font-size: 0.85rem; color: #4b5563; margin-top: 1.5rem; padding: 0.85rem 1rem; background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 4px;"><strong style="color:#374151;">참고 사항:</strong><br> 여기서 제공되는 용신(喜神) 및 기신(忌神) 정보는 사주 당사자의 신강/신약을 기준으로 한 <strong>간략화된 억부용신(抑扶用神) 결과</strong>입니다. 실제 정밀한 용신 판단은 사주 전체의 조후(調候 - 계절의 조화), 통관(通關 - 막힌 기운 소통), 병약(病藥 - 사주의 문제점과 해결책) 등 다양한 요소를 종합적으로 고려해야 하므로, 본 결과는 참고용으로만 활용하시고 중요한 판단은 반드시 사주 전문가와 상의하시기 바랍니다.</div>"""
        st.markdown(yongshin_notice_html, unsafe_allow_html=True)
        st.session_state.interpretation_segments.append(("☯️ 용신(喜神) 및 기신(忌神) 분석 (간략)", yongshin_text_for_segment + ("\n\n" + gaewoon_text_for_segment if gaewoon_text_for_segment else "")))
        st.session_state.interpretation_segments.append(("용신/기신 참고사항", strip_html_tags(yongshin_notice_html)))

        # --- 대운, 세운 등 ---
        st.markdown("---")
        st.subheader(f"運 대운 ({gender})")
        daewoon_text_for_segment_parts = []
        if "오류" in month_pillar_str or not month_gan_char or not month_ji_char :
            msg = "월주 계산에 오류가 있어 대운을 표시할 수 없습니다."
            st.warning(msg)
            daewoon_text_for_segment_parts.append(msg)
        else:
            daewoon_text_list, daewoon_start_age_val, is_sunhaeng_val = get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data)
            if isinstance(daewoon_text_list, list) and daewoon_text_list and "오류" in daewoon_text_list[0]:
                st.warning(daewoon_text_list[0])
                daewoon_text_for_segment_parts.append(daewoon_text_list[0])
            elif isinstance(daewoon_text_list, list) and all(":" in item for item in daewoon_text_list):
                daewoon_start_info = f"대운 시작 나이: 약 {daewoon_start_age_val}세 ({'순행' if is_sunhaeng_val else '역행'})"
                st.text(daewoon_start_info)
                daewoon_table_data = {"주기(나이)": [item.split(':')[0] for item in daewoon_text_list], "간지": [item.split(': ')[1] for item in daewoon_text_list]}
                daewoon_df = pd.DataFrame(daewoon_table_data)
                st.table(daewoon_df)
                daewoon_text_for_segment_parts.append(daewoon_start_info)
                daewoon_text_for_segment_parts.append(daewoon_df.to_markdown(index=False))
            else:
                msg = "대운 정보를 올바르게 가져오지 못했습니다."
                st.warning(msg)
                daewoon_text_for_segment_parts.append(msg)
        st.session_state.interpretation_segments.append((f"運 대운 ({gender})", "\n".join(daewoon_text_for_segment_parts)))

        st.markdown("---")
        st.subheader(f"📅 기준일({ty}년 {tm}월 {td}일) 운세")
        unse_text_for_segment_parts = []
        col_unse1, col_unse2 = st.columns(2)
        with col_unse1:
            st.markdown(f"##### 歲 세운 ({ty}년~)")
            seun_df = pd.DataFrame(get_seun_list(ty,5), columns=["연도","간지"])
            st.table(seun_df)
            unse_text_for_segment_parts.append(f"**歲 세운 ({ty}년~)**\n{seun_df.to_markdown(index=False)}")
            st.markdown(f"##### 日 일운 ({ty}-{tm:02d}-{td:02d}~)")
            ilun_df = pd.DataFrame(get_ilun_list(ty,tm,td,7), columns=["날짜","간지"])
            st.table(ilun_df)
            unse_text_for_segment_parts.append(f"\n**日 일운 ({ty}-{tm:02d}-{td:02d}~)**\n{ilun_df.to_markdown(index=False)}")
        with col_unse2:
            st.markdown(f"##### 月 월운 ({ty}년 {tm:02d}월~)")
            wolun_df = pd.DataFrame(get_wolun_list(ty,tm,solar_data,12), columns=["연월","간지"])
            st.table(wolun_df)
            unse_text_for_segment_parts.append(f"\n**月 월운 ({ty}년 {tm:02d}월~)**\n{wolun_df.to_markdown(index=False)}")
        st.session_state.interpretation_segments.append((f"📅 기준일({ty}년 {tm}월 {td}일) 운세", "\n".join(unse_text_for_segment_parts)))

        # --- ➊ 화면 해설을 모아 클립보드 복사용 지침 문자열을 만든다 ---
        # 이 블록은 위의 모든 분석 결과 변수들이 정의된 후에 실행되어야 하며,
        # 현재 들여쓰기 레벨(if birth_dt_input_valid and birth_dt: 블록 내부)을 유지합니다.
        guideline_parts = []
        # ------------------------------------------------------------------
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼ "guideline_parts"에 기본 정보 추가 시작 ▼▼▼▼▼▼▼▼▼▼▼▼▼
        # ------------------------------------------------------------------
        # '기본 정보' UI 표시 시 사용된 변수들을 여기서 활용합니다.
        # birth_info_display_text, calendar_type, birth_dt, age_calculated, today_for_age
        # 이 변수들은 "기본 정보" UI를 화면에 그릴 때 이미 정의되었습니다.

        # 1. 입력 생년월일시
        #    birth_info_display_text 변수는 "기본 정보" UI를 위해 이미 아래와 같이 생성되었습니다:
        #    _birth_info_ui_text = f"{calendar_type} {by}년 {bm}월 {bd}일"
        #    if calendar_type == "음력" and is_leap_month:
        #        _birth_info_ui_text += " (윤달)"
        #    _birth_info_ui_text += f" {bh:02d}시 {bmin:02d}분 출생"
        #    여기서는 `birth_info_display_text` 변수가 이미 해당 내용을 담고 있다고 가정합니다.
        #    (만약 변수명이 다르거나 접근이 안된다면, 여기서 다시 구성해야 합니다.)
        
        guideline_parts.append(f"입력 생년월일시 ▶ {birth_info_display_text}") # UI용으로 생성된 변수 사용

        # 2. 양력 환산일 (음력으로 입력한 경우)
        if calendar_type == "음력":
            # birth_dt는 양력으로 변환된 datetime 객체입니다.
            guideline_parts.append(f"양력 환산 생일 ▶ {birth_dt.strftime('%Y년 %m월 %d일')}")

        # 3. 현재 만 나이
        #    age_calculated와 today_for_age 변수는 "기본 정보" UI를 위해 이미 계산되었습니다.
        guideline_parts.append(f"현재 만 나이 ▶ {age_calculated}세 (기준일: {today_date.strftime('%Y년 %m월 %d일')})")
        
        # (선택사항) 기본 정보와 사주 명식 사이에 구분자를 추가할 수 있습니다.
        # guideline_parts.append("---") 
        # ------------------------------------------------------------------
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲ "guideline_parts"에 기본 정보 추가 끝 ▲▲▲▲▲▲▲▲▲▲▲▲▲
        # ------------------------------------------------------------------

        if 'year_pillar_str' in locals(): # 명식 정보가 있다면 추가
             guideline_parts.append(f"사주 명식 ▶ 연주 {year_pillar_str}, 월주 {month_pillar_str}, 일주 {day_pillar_str}, 시주 {time_pillar_str}")
        else:
            guideline_parts.append("사주 명식 ▶ 정보 부족")

        if 'shinkang_status_result' in locals() and 'shinkang_explanation_html' in locals():
            guideline_parts.append(f"일간 강약 ▶ {shinkang_status_result}: {strip_html_tags(shinkang_explanation_html)}")
        else:
            guideline_parts.append(f"일간 강약 ▶ {locals().get('shinkang_status_result', '정보 없음')}")
        
        if 'gekuk_name_result' in locals() and 'gekuk_explanation_html' in locals():
            guideline_parts.append(f"격국 ▶ {gekuk_name_result}: {strip_html_tags(gekuk_explanation_html)}")
        else:
            guideline_parts.append(f"격국 ▶ {locals().get('gekuk_name_result', '정보 없음')}")



        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ [ 여기에 아래 디버깅 코드만 넣어주세요 ] ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        st.markdown("---") # 화면에 구분선을 그립니다.
        st.subheader("🐞 코드 디버깅 중 (상태 확인) 🐞") # 디버깅 섹션 제목
        st.caption("이 메시지들은 오행/십신 정보를 복사 내용에 넣기 직전의 중요 변수 값입니다.")

        # 1. 'analysis_possible' 변수가 True인지 False인지 확인합니다.
        debug_analysis_possible = locals().get('analysis_possible', "⚠️ 'analysis_possible' 변수 없음")
        st.info(f"➡️ 분석 가능 상태 (analysis_possible): {debug_analysis_possible}")

        # 2. 'ohaeng_strengths' 변수에 오행별 세력 값이 잘 들어있는지 확인합니다.
        debug_ohaeng_strengths = locals().get('ohaeng_strengths', "⚠️ 'ohaeng_strengths' 변수 없음")
        st.text(f"➡️ 오행 세력 (ohaeng_strengths): {debug_ohaeng_strengths}")

        # 3. 'sipshin_strengths' 변수에 십신별 세력 값이 잘 들어있는지 확인합니다.
        debug_sipshin_strengths = locals().get('sipshin_strengths', "⚠️ 'sipshin_strengths' 변수 없음")
        st.text(f"➡️ 십신 세력 (sipshin_strengths): {debug_sipshin_strengths}")

        # 4. 'day_gan_char' (일간) 변수가 무엇인지 확인합니다. (십신 계산에 중요)
        debug_day_gan_char = locals().get('day_gan_char', "⚠️ 'day_gan_char' 변수 없음")
        st.text(f"➡️ 일간 글자 (day_gan_char): '{debug_day_gan_char}'")
        st.markdown("---") # 화면에 구분선을 그립니다.
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ [ 여기까지가 추가할 디버깅 코드입니다 ] ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲        
        if 'hap_chung_results_dict' in locals() and hap_chung_results_dict:
            has_interaction = False
            for kind, items in hap_chung_results_dict.items():
                if items:
                    guideline_parts.append(f"{kind} ▶ " + ", ".join(items))
                    has_interaction = True
            if not has_interaction:
                 guideline_parts.append("합충형해파 ▶ 특별한 상호작용 없음")
        else:
            guideline_parts.append("합충형해파 ▶ 분석 정보 없음")

        if 'found_shinsals_list' in locals() and found_shinsals_list:
            guideline_parts.append("주요 신살 ▶ " + ", ".join(found_shinsals_list))
        elif 'found_shinsals_list' in locals(): 
             guideline_parts.append("주요 신살 ▶ 특별히 나타나는 신살 없음")
        else:
            guideline_parts.append("주요 신살 ▶ 분석 정보 없음")

        if 'yongshin_gishin_info' in locals() and yongshin_gishin_info:
            yongshin = yongshin_gishin_info.get("yongshin", [])
            gishin  = yongshin_gishin_info.get("gishin", [])
            yongshin_str = ', '.join(yongshin) if yongshin else "해당 없음"
            gishin_str = ', '.join(gishin) if gishin else "해당 없음"
            guideline_parts.append(f"용신 ▶ {yongshin_str}")
            guideline_parts.append(f"기신 ▶ {gishin_str}")
        else:
            guideline_parts.append("용신/기신 ▶ 분석 정보 없음")

        guideline_text = "\n\n".join(guideline_parts)

        
                # --- 대운, 세운, 월운, 일운 정보를 guideline_parts에 추가 ---

        # 7) 대운 정보 추가 (이 부분은 이전 답변에서 수정된 내용 유지)
        daewoon_guideline_text_parts = []
        # gender, daewoon_start_info, daewoon_df 변수가 이전에 정의되어 있다고 가정합니다.
        if 'daewoon_start_info' in locals() and daewoon_start_info:
            daewoon_guideline_text_parts.append(daewoon_start_info)
            if 'daewoon_df' in locals() and isinstance(daewoon_df, pd.DataFrame) and not daewoon_df.empty:
                daewoon_guideline_text_parts.append(daewoon_df.to_string(index=False, header=True))
            
            if daewoon_guideline_text_parts:
                 guideline_parts.append(f"運 대운 ({gender if 'gender' in locals() else ''}) ▶\n" + "\n".join(daewoon_guideline_text_parts))
            else:
                 guideline_parts.append(f"運 대운 ({gender if 'gender' in locals() else ''}) ▶ 상세 정보 없음")
        elif 'month_pillar_str' in locals() and "오류" in month_pillar_str:
            guideline_parts.append(f"運 대운 ({gender if 'gender' in locals() else ''}) ▶ 월주 오류로 대운 정보 생성 불가")
        else:
            guideline_parts.append(f"運 대운 ({gender if 'gender' in locals() else ''}) ▶ 정보 없음 또는 생성 실패")


        # 8) 기준일 운세 (세운, 월운, 일운) 정보 추가 -- 여기가 수정된 부분입니다!
        # ty, tm, td는 st.sidebar.number_input에서 오며, 이 스코프에서 사용 가능하고 정수형이라고 가정합니다.
        
        s_ty = str(ty) # 연도는 그대로 문자열로
        s_tm = f"{tm:02d}" # 월은 2자리 숫자로 포맷 (예: 6 -> "06")
        s_td = f"{td:02d}" # 일도 2자리 숫자로 포맷 (예: 5 -> "05")

        unse_title_for_guideline = f"📅 기준일({s_ty}년 {s_tm}월 {s_td}일) 운세"
        unse_guideline_sub_parts = []

        # seun_df, wolun_df, ilun_df DataFrame 변수들이 이전에 정의되어 있다고 가정합니다.
        if 'seun_df' in locals() and isinstance(seun_df, pd.DataFrame) and not seun_df.empty:
            unse_guideline_sub_parts.append(f"세운 ({s_ty}년~):\n{seun_df.to_string(index=False, header=True)}")
        else:
            unse_guideline_sub_parts.append(f"세운 ({s_ty}년~): 정보 없음")
        
        if 'wolun_df' in locals() and isinstance(wolun_df, pd.DataFrame) and not wolun_df.empty:
            unse_guideline_sub_parts.append(f"월운 ({s_ty}년 {s_tm}월~):\n{wolun_df.to_string(index=False, header=True)}")
        else:
            unse_guideline_sub_parts.append(f"월운 ({s_ty}년 {s_tm}월~): 정보 없음")

        if 'ilun_df' in locals() and isinstance(ilun_df, pd.DataFrame) and not ilun_df.empty:
            unse_guideline_sub_parts.append(f"일운 ({s_ty}-{s_tm}-{s_td}~):\n{ilun_df.to_string(index=False, header=True)}")
        else:
            unse_guideline_sub_parts.append(f"일운 ({s_ty}-{s_tm}-{s_td}~): 정보 없음")
        
        guideline_parts.append(f"{unse_title_for_guideline} ▶\n" + "\n\n".join(unse_guideline_sub_parts))
        # --- 대운/세운 등 정보 추가 끝 ---

        guideline_text = "\n\n".join(guideline_parts)
        
        # --- ➋ 복사용 UI 추가 (수동 복사 방식 st.text_area 사용) ---
        st.markdown("---")
        st.subheader("📋 생성된 사주 상담 지침 (수동 복사)")
        
        if 'guideline_text' in locals() and isinstance(guideline_text, str):
            if guideline_text.strip():
                st.text_area("아래 내용을 전체 선택(Ctrl+A 또는 Cmd+A) 후 복사(Ctrl+C 또는 Cmd+C)하세요:", 
                             guideline_text, 
                             height=300, 
                             key="guideline_text_area_for_manual_copy")
            else:
                st.warning("생성된 지침 내용이 없습니다 (내용이 비어 있음).")
        else: 
            st.error("지침 내용(guideline_text)이 생성되지 않아 표시할 수 없습니다.")

        st.session_state.saju_calculated_once = True
    # --- "if birth_dt_input_valid and birth_dt:" 블록의 끝 ---
# --- "if st.sidebar.button(...)" 블록의 끝 ---


# --- "풀이 내용 지침으로 보기" 버튼 및 결과 표시 (expander) ---
# 이 섹션은 if st.sidebar.button(...) 블록 바깥, 메인 페이지 영역에 위치하며, 들여쓰기 0칸에서 시작합니다.
if st.session_state.get('saju_calculated_once', False):
    st.markdown("---") # 4칸 들여쓰기

    if st.button("📖 전체 풀이 내용 다시 보기 (클릭하여 열기/닫기)", use_container_width=True, key="toggle_interpretation_guide_expander_button_final_v3"): # 4칸 들여쓰기
        st.session_state.show_interpretation_guide_on_click = not st.session_state.get('show_interpretation_guide_on_click', False) # 8칸 들여쓰기

    if st.session_state.get('show_interpretation_guide_on_click', False): # 4칸 들여쓰기
        with st.expander("📖 전체 풀이 내용 (텍스트 지침)", expanded=True): # 8칸 들여쓰기
            if st.session_state.get('interpretation_segments') and len(st.session_state.interpretation_segments) > 0: # 12칸 들여쓰기
                current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 16칸 들여쓰기
                full_text_guide = f"# ✨ 종합 사주 풀이 결과 ({current_time_str})\n\n" # 16칸 들여쓰기

                for title, content in st.session_state.interpretation_segments: # 16칸 들여쓰기
                    content_to_display = content if content and isinstance(content, str) else "내용 없음" # 20칸 들여쓰기
                    full_text_guide += f"## {title}\n\n{content_to_display.strip()}\n\n---\n\n" # 20칸 들여쓰기

                st.markdown(full_text_guide) # 16칸 들여쓰기
                st.info("위 내용을 선택하여 복사한 후, 원하시는 곳에 붙여넣어 활용하세요.") # 16칸 들여쓰기
            else: # 12칸 들여쓰기
                st.markdown("표시할 풀이 내용이 없습니다. '계산 실행' 버튼을 눌러 사주 분석을 먼저 진행해주세요.") # 16칸 들여쓰기

# 앱 하단에 표시될 수 있는 초기 안내 (만약 계산된 내용이 없다면)
if not st.session_state.get('saju_calculated_once', False): # 0칸 들여쓰기
    st.info("화면 왼쪽의 사이드바에서 출생 정보를 입력하고 '🧮 계산 실행' 버튼을 누르면, 사주 명식과 함께 상세 풀이 내용을 이곳에서 확인할 수 있습니다.") # 4칸 들여쓰기
