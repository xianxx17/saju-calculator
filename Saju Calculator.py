# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl lunardate

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math
import re # HTML 태그 제거를 위해 추가

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
SIPSHIN_COLORS = {
    "비견": "#1d4ed8", "겁재": "#1d4ed8", # 비겁
    "식신": "#c2410c", "상관": "#c2410c", # 식상
    "편재": "#ca8a04", "정재": "#ca8a04", # 재성
    "편관": "#166534", "정관": "#166534", # 관성
    "편인": "#6b7280", "정인": "#6b7280"  # 인성
}

# ───────────────────────────────
# 신강/신약 및 격국 분석용 상수 추가
# ───────────────────────────────
L_NOK_MAP = {
    "갑": "묘", "을": "인", "병": "사", "정": "오",
    "무": "진", "기": "축", "경": "유", "신": "신",
    "임": "해", "계": "자"
}
YANGIN_JI_MAP = {
    "갑": "묘", "병": "오", "무": "오", "경": "유", "임": "자"
}
SIPSHIN_TO_GYEOK_MAP = {
    '비견':'비견격', '겁재':'겁재격',
    '식신':'식신격', '상관':'상관격',
    '편재':'편재격', '정재':'정재격',
    '편관':'칠살격', '정관':'정관격',
    '편인':'편인격', '정인':'정인격'
}

# ───────────────────────────────
# 신강/신약 판단 및 설명 함수
# ───────────────────────────────
def determine_shinkang_shinyak(sipshin_strengths):
    my_energy = (sipshin_strengths.get("비견", 0.0) +
                 sipshin_strengths.get("겁재", 0.0) +
                 sipshin_strengths.get("편인", 0.0) +
                 sipshin_strengths.get("정인", 0.0))
    opponent_energy = (sipshin_strengths.get("식신", 0.0) +
                       sipshin_strengths.get("상관", 0.0) +
                       sipshin_strengths.get("편재", 0.0) +
                       sipshin_strengths.get("정재", 0.0) +
                       sipshin_strengths.get("편관", 0.0) +
                       sipshin_strengths.get("정관", 0.0))
    score_diff = my_energy - opponent_energy
    if score_diff >= 1.5: return "신강"
    elif score_diff <= -1.5: return "신약"
    elif -0.5 <= score_diff <= 0.5: return "중화"
    elif score_diff > 0.5: return "약간 신강"
    else: return "약간 신약"

def get_shinkang_explanation(shinkang_status_str):
    explanations = {
        "신강": "일간(자신)의 힘이 강한 편입니다. 주체적이고 독립적인 성향이 강하며, 자신의 의지대로 일을 추진하는 힘이 있습니다. 때로는 자기 주장이 강해 주변과의 마찰이 생길 수 있으니 유연성을 갖추는 것이 좋습니다.",
        "신약": "일간(자신)의 힘이 다소 약한 편입니다. 주변의 도움이나 환경의 영향에 민감하며, 신중하고 사려 깊은 모습을 보일 수 있습니다. 자신감을 갖고 꾸준히 자신의 역량을 키워나가는 것이 중요하며, 좋은 운의 흐름을 잘 활용하는 지혜가 필요합니다.",
        "중화": "일간(자신)의 힘이 비교적 균형을 이루고 있습니다. 상황에 따라 유연하게 대처하는 능력이 있으며, 원만한 대인관계를 맺을 수 있는 좋은 구조입니다. 다만, 때로는 뚜렷한 개성이 부족해 보일 수도 있습니다.",
        "약간 신강": "일간(자신)의 힘이 평균보다 조금 강한 편입니다. 자신의 주관을 가지고 일을 처리하면서도 주변과 협력하는 균형 감각을 발휘할 수 있습니다.",
        "약간 신약": "일간(자신)의 힘이 평균보다 조금 약한 편입니다. 신중하고 주변 상황을 잘 살피며, 인내심을 가지고 목표를 추구하는 경향이 있습니다. 주변의 조언을 경청하는 자세가 도움이 될 수 있습니다."
    }
    return explanations.get(shinkang_status_str, "일간의 강약 상태에 대한 설명을 준비 중입니다.")

# ───────────────────────────────
# 격국 판단 함수들
# ───────────────────────────────
def _detect_special_gekuk(day_gan_char, month_ji_char):
    if L_NOK_MAP.get(day_gan_char) == month_ji_char: return "건록격"
    if day_gan_char in YANGIN_JI_MAP and YANGIN_JI_MAP.get(day_gan_char) == month_ji_char: return "양인격"
    return None

def _detect_togan_gekuk(day_gan_char, month_gan_char, month_ji_char):
    if month_ji_char in JIJI_JANGGAN:
        hidden_stems_in_month_ji = JIJI_JANGGAN[month_ji_char]
        if month_gan_char in hidden_stems_in_month_ji:
            sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(month_gan_char)
            if sipshin_type: return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_month_branch_primary(day_gan_char, month_ji_char):
    if month_ji_char in JIJI_JANGGAN:
        hidden_stems = JIJI_JANGGAN[month_ji_char]
        if hidden_stems:
            primary_hidden_stem = max(hidden_stems, key=hidden_stems.get) if hidden_stems else None
            if primary_hidden_stem:
                sipshin_type = SIPSHIN_MAP.get(day_gan_char, {}).get(primary_hidden_stem)
                if sipshin_type: return SIPSHIN_TO_GYEOK_MAP.get(sipshin_type, sipshin_type + "격")
    return None

def _detect_general_gekuk_from_strengths(sipshin_strengths_dict):
    if not sipshin_strengths_dict: return None
    strongest_sipshin_name = None
    max_strength = -1
    for sipshin_name in SIPSHIN_ORDER:
        strength_val = sipshin_strengths_dict.get(sipshin_name, 0.0)
        if strength_val > max_strength:
            max_strength = strength_val
            strongest_sipshin_name = sipshin_name
    if strongest_sipshin_name and max_strength > 0.5:
        return SIPSHIN_TO_GYEOK_MAP.get(strongest_sipshin_name, strongest_sipshin_name + "격")
    return "일반격 판정 어려움"

def determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths_dict):
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

import itertools

# ───────────────────────────────
# 합충형해파 분석용 상수 정의
# ───────────────────────────────
CHEONGAN_HAP_RULES = {
    tuple(sorted(("갑", "기"))): "토", tuple(sorted(("을", "경"))): "금",
    tuple(sorted(("병", "신"))): "수", tuple(sorted(("정", "임"))): "목",
    tuple(sorted(("무", "계"))): "화"
}
JIJI_SAMHAP_RULES = {
    tuple(sorted(("신", "자", "진"))): "수국(水局)", tuple(sorted(("사", "유", "축"))): "금국(金局)",
    tuple(sorted(("인", "오", "술"))): "화국(火局)", tuple(sorted(("해", "묘", "미"))): "목국(木局)"
}
JIJI_BANHAP_WANGJI_CENTERED_RULES = {
    "자": ["신", "진"], "유": ["사", "축"], "오": ["인", "술"], "묘": ["해", "미"]
}
JIJI_BANGHAP_RULES = {
    tuple(sorted(("인", "묘", "진"))): "목국(木局)", tuple(sorted(("사", "오", "미"))): "화국(火局)",
    tuple(sorted(("신", "유", "술"))): "금국(金局)", tuple(sorted(("해", "자", "축"))): "수국(水局)"
}
JIJI_YUKHAP_RULES = {
    tuple(sorted(("자", "축"))): "토", tuple(sorted(("인", "해"))): "목",
    tuple(sorted(("묘", "술"))): "화", tuple(sorted(("진", "유"))): "금",
    tuple(sorted(("사", "신"))): "수", tuple(sorted(("오", "미"))): "화/토"
}
CHEONGAN_CHUNG_RULES = [
    tuple(sorted(("갑", "경"))), tuple(sorted(("을", "신"))),
    tuple(sorted(("병", "임"))), tuple(sorted(("정", "계")))
]
JIJI_CHUNG_RULES = [
    tuple(sorted(("자", "오"))), tuple(sorted(("축", "미"))), tuple(sorted(("인", "신"))),
    tuple(sorted(("묘", "유"))), tuple(sorted(("진", "술"))), tuple(sorted(("사", "해")))
]
SAMHYEONG_RULES = {
    tuple(sorted(("인", "사", "신"))): "인사신 삼형(無恩之刑)",
    tuple(sorted(("축", "술", "미"))): "축술미 삼형(持勢之刑)"
}
SANGHYEONG_RULES = [tuple(sorted(("자", "묘")))]
JAHYEONG_CHARS = ["진", "오", "유", "해"]
JIJI_HAE_RULES = [
    tuple(sorted(("자", "미"))), tuple(sorted(("축", "오"))), tuple(sorted(("인", "사"))),
    tuple(sorted(("묘", "진"))), tuple(sorted(("신", "해"))), tuple(sorted(("유", "술")))
]
HAE_NAMES = {tuple(sorted(k)):v for k,v in {"자미":"자미해", "축오":"축오해", "인사":"인사회", "묘진":"묘진해", "신해":"신해해", "유술":"유술해"}.items()}
JIJI_PA_RULES = [
    tuple(sorted(("자", "유"))), tuple(sorted(("축", "진"))), tuple(sorted(("인", "해"))),
    tuple(sorted(("묘", "오"))), tuple(sorted(("사", "신"))), tuple(sorted(("술", "미")))
]
PA_NAMES = {tuple(sorted(k)):v for k,v in {"자유":"자유파", "축진":"축진파", "인해":"인해파", "묘오":"묘오파", "사신":"사신파", "술미":"술미파"}.items()}
PILLAR_NAMES_KOR_SHORT = ["년", "월", "일", "시"]

# ───────────────────────────────
# 합충형해파 분석 함수
# ───────────────────────────────
def analyze_hap_chung_interactions(saju_8char_details):
    gans = [saju_8char_details["year_gan"], saju_8char_details["month_gan"], saju_8char_details["day_gan"], saju_8char_details["time_gan"]]
    jis = [saju_8char_details["year_ji"], saju_8char_details["month_ji"], saju_8char_details["day_ji"], saju_8char_details["time_ji"]]
    results = {
        "천간합": [], "지지육합": [], "지지삼합": [], "지지방합": [],
        "천간충": [], "지지충": [], "형살(刑殺)": [], "해살(害殺)": [], "파살(破殺)": []
    }
    found_samhap_banhap_combinations = set()
    gans_with_pos = list(enumerate(gans))
    jis_with_pos = list(enumerate(jis))

    for (i_idx, i_gan), (j_idx, j_gan) in itertools.combinations(gans_with_pos, 2):
        pair_sorted = tuple(sorted((i_gan, j_gan)))
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}간({i_gan}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}간({j_gan})"
        if pair_sorted in CHEONGAN_HAP_RULES: results["천간합"].append(f"{pos_str} → {CHEONGAN_HAP_RULES[pair_sorted]} 합")
        if pair_sorted in CHEONGAN_CHUNG_RULES: results["천간충"].append(f"{pos_str.replace('+', '↔')} 충")

    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(jis_with_pos, 2):
        pair_sorted = tuple(sorted((i_ji, j_ji)))
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        if pair_sorted in JIJI_YUKHAP_RULES: results["지지육합"].append(f"{pos_str} → {JIJI_YUKHAP_RULES[pair_sorted]} 합")
        if pair_sorted in JIJI_CHUNG_RULES: results["지지충"].append(f"{pos_str.replace('+', '↔')} 충")
        if pair_sorted in JIJI_HAE_RULES: results["해살(害殺)"].append(f"{pos_str} → {HAE_NAMES.get(pair_sorted, '해')}")
        if pair_sorted in JIJI_PA_RULES: results["파살(破殺)"].append(f"{pos_str} → {PA_NAMES.get(pair_sorted, '파')}")
        if pair_sorted in SANGHYEONG_RULES: results["형살(刑殺)"].append(f"{pos_str} → 자묘 상형(無禮之刑)")

    for (i_idx, i_ji), (j_idx, j_ji), (k_idx, k_ji) in itertools.combinations(jis_with_pos, 3):
        combo_sorted = tuple(sorted((i_ji, j_ji, k_ji)))
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}), {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji}), {PILLAR_NAMES_KOR_SHORT[k_idx]}지({k_ji})"
        if combo_sorted in JIJI_SAMHAP_RULES:
            found_samhap_banhap_combinations.add(combo_sorted)
            results["지지삼합"].append(f"{pos_str} → {JIJI_SAMHAP_RULES[combo_sorted]}")
        if combo_sorted in JIJI_BANGHAP_RULES: results["지지방합"].append(f"{pos_str} → {JIJI_BANGHAP_RULES[combo_sorted]}")
        if combo_sorted in SAMHYEONG_RULES: results["형살(刑殺)"].append(f"{pos_str} → {SAMHYEONG_RULES[combo_sorted]}")

    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(jis_with_pos, 2):
        pos_str = f"{PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})"
        for wangji, others in JIJI_BANHAP_WANGJI_CENTERED_RULES.items():
            if (i_ji == wangji and j_ji in others) or (j_ji == wangji and i_ji in others):
                is_part_of_samhap = False
                full_samhap_group = None
                for samhap_key_tuple in JIJI_SAMHAP_RULES.keys():
                    if wangji in samhap_key_tuple and (i_ji in samhap_key_tuple and j_ji in samhap_key_tuple):
                        full_samhap_group = samhap_key_tuple; break
                if full_samhap_group and full_samhap_group in found_samhap_banhap_combinations: is_part_of_samhap = True
                if not is_part_of_samhap:
                    banhap_result_str = f"{pos_str} → {wangji} 기준 반합 ({JIJI_SAMHAP_RULES.get(full_samhap_group, '국 형성')})"
                    # Check if a similar string already exists to prevent duplicates from different orderings
                    is_already_added_as_banhap = False
                    for existing_item in results["지지삼합"]:
                         if f"{PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji}) + {PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji})" in existing_item and "반합" in existing_item:
                             is_already_added_as_banhap = True
                             break
                    if not is_already_added_as_banhap and not any(banhap_result_str == item for item in results["지지삼합"]):
                         results["지지삼합"].append(banhap_result_str)
                break
    for jahyeong_char in JAHYEONG_CHARS:
        count = jis.count(jahyeong_char)
        if count >= 2:
            positions = [f"{PILLAR_NAMES_KOR_SHORT[i]}지({jis[i]})" for i, ji_val in enumerate(jis) if ji_val == jahyeong_char]
            results["형살(刑殺)"].append(f"{', '.join(positions)} ({jahyeong_char}{jahyeong_char}) → 자형(自刑)")
    return results

def get_hap_chung_detail_explanation(found_interactions_dict):
    if not found_interactions_dict or not any(v for v in found_interactions_dict.values()):
        return "<p>특별히 두드러지는 합충형해파의 관계가 나타나지 않습니다. 비교적 안정적인 구조일 수 있습니다.</p>"
    explanation_parts = []
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
        if found_list:
            desc = interaction_explanations.get(key)
            if desc: explanation_parts.append(f"<li><strong>{key}:</strong> {desc}</li>")
    if not explanation_parts: return "<p>구체적인 합충형해파 관계에 대한 설명을 준비 중입니다.</p>"
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

# ───────────────────────────────
# 주요 신살(神煞) 분석용 상수 및 함수 정의
# ───────────────────────────────
CHEONEULGWIIN_MAP = {
    "갑": ["축", "미"], "을": ["자", "신"], "병": ["해", "유"], "정": ["해", "유"],
    "무": ["축", "미"], "기": ["자", "신"], "경": ["축", "미", "인", "오"],
    "신": ["인", "오"], "임": ["사", "묘"], "계": ["사", "묘"]
}
MUNCHANGGWIIN_MAP = {
    "갑": "사", "을": "오", "병": "신", "정": "유", "무": "신",
    "기": "유", "경": "해", "신": "자", "임": "인", "계": "묘"
}
DOHWASAL_MAP = {
    "해": "자", "묘": "자", "미": "자", "인": "묘", "오": "묘", "술": "묘",
    "사": "오", "유": "오", "축": "오", "신": "유", "자": "유", "진": "유"
}
YEONGMASAL_MAP = {
    "해": "사", "묘": "사", "미": "사", "인": "신", "오": "신", "술": "신",
    "사": "해", "유": "해", "축": "해", "신": "인", "자": "인", "진": "인"
}
HWAGAESAL_MAP = {
    "해": "미", "묘": "미", "미": "미", "인": "술", "오": "술", "술": "술",
    "사": "축", "유": "축", "축": "축", "신": "진", "자": "진", "진": "진"
}
GOEGANGSAL_ILJU_LIST = ["경진", "경술", "임진", "임술", "무진", "무술"]
BAEKHODAESAL_GANJI_LIST = ["갑진", "을미", "병술", "정축", "무진", "임술", "계축"]
GWIMUNGWANSAL_PAIRS = [
    tuple(sorted(("자", "유"))), tuple(sorted(("축", "오"))), tuple(sorted(("인", "미"))),
    tuple(sorted(("묘", "신"))), tuple(sorted(("진", "해"))), tuple(sorted(("사", "술")))
]
PILLAR_NAMES_KOR = ["년주", "월주", "일주", "시주"]

def analyze_shinsal(saju_8char_details):
    ilgan_char = saju_8char_details["day_gan"]
    all_jis = [saju_8char_details["year_ji"], saju_8char_details["month_ji"], saju_8char_details["day_ji"], saju_8char_details["time_ji"]]
    pillar_ganjis_str = [
        saju_8char_details["year_gan"] + saju_8char_details["year_ji"],
        saju_8char_details["month_gan"] + saju_8char_details["month_ji"],
        saju_8char_details["day_gan"] + saju_8char_details["day_ji"],
        saju_8char_details["time_gan"] + saju_8char_details["time_ji"]
    ]
    ilju_ganji_str = pillar_ganjis_str[2]
    found_shinsals_set = set()

    if ilgan_char in CHEONEULGWIIN_MAP:
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char in CHEONEULGWIIN_MAP[ilgan_char]: found_shinsals_set.add(f"천을귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
    if ilgan_char in MUNCHANGGWIIN_MAP:
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char == MUNCHANGGWIIN_MAP[ilgan_char]: found_shinsals_set.add(f"문창귀인: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    yeonji_char = saju_8char_details["year_ji"]; ilji_char = saju_8char_details["day_ji"]
    dohwa_for_yeonji = DOHWASAL_MAP.get(yeonji_char); dohwa_for_ilji = DOHWASAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if dohwa_for_yeonji and ji_char == dohwa_for_yeonji: found_shinsals_set.add(f"도화살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if dohwa_for_ilji and ji_char == dohwa_for_ilji and (yeonji_char != ilji_char or dohwa_for_yeonji != dohwa_for_ilji): found_shinsals_set.add(f"도화살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    yeokma_for_yeonji = YEONGMASAL_MAP.get(yeonji_char); yeokma_for_ilji = YEONGMASAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if yeokma_for_yeonji and ji_char == yeokma_for_yeonji: found_shinsals_set.add(f"역마살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if yeokma_for_ilji and ji_char == yeokma_for_ilji and (yeonji_char != ilji_char or yeokma_for_yeonji != yeokma_for_ilji) : found_shinsals_set.add(f"역마살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    hwagae_for_yeonji = HWAGAESAL_MAP.get(yeonji_char); hwagae_for_ilji = HWAGAESAL_MAP.get(ilji_char)
    for ji_idx, ji_char in enumerate(all_jis):
        if hwagae_for_yeonji and ji_char == hwagae_for_yeonji: found_shinsals_set.add(f"화개살: 연지({yeonji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
        if hwagae_for_ilji and ji_char == hwagae_for_ilji and (yeonji_char != ilji_char or hwagae_for_yeonji != hwagae_for_ilji): found_shinsals_set.add(f"화개살: 일지({ilji_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")

    if ilgan_char in YANGIN_JI_MAP:
        for ji_idx, ji_char in enumerate(all_jis):
            if ji_char == YANGIN_JI_MAP[ilgan_char]: found_shinsals_set.add(f"양인살: 일간({ilgan_char}) 기준 {PILLAR_NAMES_KOR_SHORT[ji_idx]}지({ji_char})")
    if ilju_ganji_str in GOEGANGSAL_ILJU_LIST: found_shinsals_set.add(f"괴강살: 일주({ilju_ganji_str})")
    for pillar_idx, current_pillar_ganji_str in enumerate(pillar_ganjis_str):
        if current_pillar_ganji_str in BAEKHODAESAL_GANJI_LIST: found_shinsals_set.add(f"백호대살: {PILLAR_NAMES_KOR[pillar_idx]}({current_pillar_ganji_str})")
    for (i_idx, i_ji), (j_idx, j_ji) in itertools.combinations(list(enumerate(all_jis)), 2):
        pair_sorted = tuple(sorted((i_ji, j_ji)))
        if pair_sorted in GWIMUNGWANSAL_PAIRS: found_shinsals_set.add(f"귀문관살: {PILLAR_NAMES_KOR_SHORT[i_idx]}지({i_ji}) + {PILLAR_NAMES_KOR_SHORT[j_idx]}지({j_ji})")

    try:
        ilgan_idx = GAN.index(ilgan_char); ilji_idx_val = JI.index(ilji_char)
        ilju_gapja_idx = -1
        for i in range(60):
            if GAN[i % 10] == ilgan_char and JI[i % 12] == ilji_char: ilju_gapja_idx = i; break
        if ilju_gapja_idx != -1:
            gongmang_jis = JI[(ilju_gapja_idx + 10) % 12], JI[(ilju_gapja_idx + 11) % 12]
            found_shinsals_set.add(f"공망(空亡): 일주({ilju_ganji_str}) 기준 {gongmang_jis[0]}, {gongmang_jis[1]} 공망")
            found_in_pillars = []
            for ji_idx, ji_char_in_saju in enumerate(all_jis):
                if ji_char_in_saju in gongmang_jis: found_in_pillars.append(f"{PILLAR_NAMES_KOR[ji_idx]}의 {ji_char_in_saju}")
            if found_in_pillars: found_shinsals_set.add(f"  └ ({', '.join(found_in_pillars)})가 공망에 해당합니다.")
    except (IndexError, ValueError): pass
    return sorted(list(found_shinsals_set))

def get_shinsal_detail_explanation(found_shinsals_list):
    if not found_shinsals_list: return "<p>특별히 나타나는 주요 신살이 없습니다.</p>"
    explanation_parts = []
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
    added_explanations_keys = set()
    for shinsal_item_str in found_shinsals_list:
        for shinsal_key, desc in main_shinsal_explanations.items():
            if shinsal_key in shinsal_item_str and shinsal_key not in added_explanations_keys:
                explanation_parts.append(f"<li><strong>{shinsal_key}:</strong> {desc}</li>")
                added_explanations_keys.add(shinsal_key)
    if not explanation_parts: return "<p>발견된 신살에 대한 구체적인 설명을 준비 중입니다.</p>"
    return "<ul style='list-style-type: disc; margin-left: 20px; padding-left: 0;'>" + "".join(explanation_parts) + "</ul>"

# ───────────────────────────────
# 용신/기신 분석용 상수 및 함수 정의
# ───────────────────────────────
OHENG_HELPER_MAP = {"목": "수", "화": "목", "토": "화", "금": "토", "수": "금"}
OHENG_PRODUCES_MAP = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
OHENG_CONTROLS_MAP = {"목": "토", "화": "금", "토": "수", "금": "목", "수": "화"}
OHENG_IS_CONTROLLED_BY_MAP = {"목": "금", "화": "수", "토": "목", "금": "화", "수": "토"}

def determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_str):
    ilgan_ohaeng = GAN_TO_OHENG.get(day_gan_char)
    if not ilgan_ohaeng: return {"yongshin": [], "gishin": [], "html": "<p>일간의 오행을 알 수 없어 용신/기신을 판단할 수 없습니다.</p>"}
    yongshin_candidates = []; gishin_candidates = []
    sik상_ohaeng = OHENG_PRODUCES_MAP.get(ilgan_ohaeng); jae성_ohaeng = OHENG_CONTROLS_MAP.get(ilgan_ohaeng)
    gwan성_ohaeng = OHENG_IS_CONTROLLED_BY_MAP.get(ilgan_ohaeng); in성_ohaeng = OHENG_HELPER_MAP.get(ilgan_ohaeng)
    bi겁_ohaeng = ilgan_ohaeng
    if "신강" in shinkang_status_str:
        if sik상_ohaeng: yongshin_candidates.append(sik상_ohaeng)
        if jae성_ohaeng: yongshin_candidates.append(jae성_ohaeng)
        if gwan성_ohaeng: yongshin_candidates.append(gwan성_ohaeng)
        if in성_ohaeng: gishin_candidates.append(in성_ohaeng)
        if bi겁_ohaeng: gishin_candidates.append(bi겁_ohaeng)
    elif "신약" in shinkang_status_str:
        if in성_ohaeng: yongshin_candidates.append(in성_ohaeng)
        if bi겁_ohaeng: yongshin_candidates.append(bi겁_ohaeng)
        if sik상_ohaeng: gishin_candidates.append(sik상_ohaeng)
        if jae성_ohaeng: gishin_candidates.append(jae성_ohaeng)
        if gwan성_ohaeng: gishin_candidates.append(gwan성_ohaeng)
    elif "중화" in shinkang_status_str:
        return {"yongshin": [], "gishin": [], "html": "<p>중화 사주로 판단됩니다. 이 경우 특정 오행을 용신이나 기신으로 엄격히 구분하기보다는, 사주 전체의 균형과 조화를 유지하고 대운의 흐름에 유연하게 대처하는 것이 중요할 수 있습니다. 때로는 사주에 부족하거나 고립된 오행을 보충하는 방향을 고려하기도 합니다.</p>"}
    else: return {"yongshin": [], "gishin": [], "html": "<p>일간의 강약 상태가 명확하지 않아 용신/기신을 판단하기 어렵습니다.</p>"}
    unique_yongshin = sorted(list(set(yongshin_candidates))); unique_gishin = sorted(list(set(gishin_candidates)))
    html_parts = []
    if unique_yongshin: html_parts.append(f"<p>유력한 용신(喜神) 후보 오행: {', '.join([f'<span style=\\'color:#15803d; font-weight:bold;\\'>{o}({OHENG_TO_HANJA.get(o, "")})</span>' for o in unique_yongshin])}</p>")
    else: html_parts.append("<p>용신(喜神)으로 특정할 만한 오행을 명확히 구분하기 어렵습니다. (중화 사주 외)</p>")
    if unique_gishin: html_parts.append(f"<p>주의가 필요한 기신(忌神) 후보 오행: {', '.join([f'<span style=\\'color:#b91c1c; font-weight:bold;\\'>{o}({OHENG_TO_HANJA.get(o, "")})</span>' for o in unique_gishin])}</p>")
    else: html_parts.append("<p>특별히 기신(忌神)으로 강하게 작용할 만한 오행이 두드러지지 않을 수 있습니다.</p>")
    return {"yongshin": unique_yongshin, "gishin": unique_gishin, "html": "".join(html_parts)}

def get_gaewoon_tips_html(yongshin_list):
    if not yongshin_list: return ""
    tips_html = "<h5 style='color: #047857; margin-top: 0.8rem; margin-bottom: 0.3rem; font-size:1em;'>🍀 간단 개운법 (용신 활용)</h5><ul style='list-style:none; padding-left:0; font-size:0.9em;'>"
    gaewoon_tips_data = {
        "목": "<li><strong style='color:#15803d;'>목(木) 용신:</strong> 동쪽 방향, 푸른색/초록색 계열 아이템 활용. 숲이나 공원 산책, 식물 키우기, 교육/문화/기획 관련 활동.</li>",
        "화": "<li><strong style='color:#15803d;'>화(火) 용신:</strong> 남쪽 방향, 붉은색/분홍색/보라색 계열 아이템 활용. 밝고 따뜻한 환경 조성, 예체능/방송/조명/열정적인 활동.</li>",
        "토": "<li><strong style='color:#15803d;'>토(土) 용신:</strong> 중앙(거주지 중심), 노란색/황토색/베이지색 계열 아이템 활용. 안정적이고 편안한 환경, 명상, 신용을 중시하는 활동, 등산.</li>",
        "금": "<li><strong style='color:#15803d;'>금(金) 용신:</strong> 서쪽 방향, 흰색/은색/금색 계열 아이템 활용. 단단하고 정돈된 환경, 금속 액세서리, 결단력과 의리를 지키는 활동, 악기 연주.</li>",
        "수": "<li><strong style='color:#15803d;'>수(水) 용신:</strong> 북쪽 방향, 검은색/파란색/회색 계열 아이템 활용. 물가나 조용하고 차분한 환경, 지혜를 활용하는 활동, 명상이나 충분한 휴식.</li>"
    }
    for yongshin_ohaeng in yongshin_list: tips_html += gaewoon_tips_data.get(yongshin_ohaeng, f"<li>{yongshin_ohaeng}({OHENG_TO_HANJA.get(yongshin_ohaeng,'')}) 용신에 대한 개운법 정보를 준비 중입니다.</li>")
    tips_html += "</ul><p style='font-size:0.8rem; color:#555; margin-top:0.5rem;'>* 위 내용은 일반적인 개운법이며, 개인의 전체 사주 구조와 상황에 따라 다를 수 있습니다. 참고용으로 활용하세요.</p>"
    return tips_html

# ───────────────────────────────
# 오행 및 십신 세력 계산 함수
# ───────────────────────────────
def calculate_ohaeng_sipshin_strengths(saju_8char_details):
    day_master_gan = saju_8char_details["day_gan"]
    chars_to_analyze = [
        (saju_8char_details["year_gan"], "연간"), (saju_8char_details["year_ji"], "연지"),
        (saju_8char_details["month_gan"], "월간"), (saju_8char_details["month_ji"], "월지"),
        (saju_8char_details["day_gan"], "일간"), (saju_8char_details["day_ji"], "일지"),
        (saju_8char_details["time_gan"], "시간"), (saju_8char_details["time_ji"], "시지")
    ]
    ohaeng_strengths = {oheng: 0.0 for oheng in OHENG_ORDER}
    sipshin_strengths = {sipshin: 0.0 for sipshin in SIPSHIN_ORDER}
    def get_sipshin(dm_gan, other_gan):
        return SIPSHIN_MAP.get(dm_gan, {}).get(other_gan)

    for char_val, position_key in chars_to_analyze:
        weight = POSITIONAL_WEIGHTS.get(position_key, 0.0)
        is_gan = "간" in position_key
        if is_gan:
            ohaeng = GAN_TO_OHENG.get(char_val)
            if ohaeng: ohaeng_strengths[ohaeng] += weight
            sipshin = get_sipshin(day_master_gan, char_val)
            if sipshin: sipshin_strengths[sipshin] += weight
        else:
            if char_val in JIJI_JANGGAN:
                for janggan_char, proportion in JIJI_JANGGAN[char_val].items():
                    ohaeng = GAN_TO_OHENG.get(janggan_char)
                    if ohaeng: ohaeng_strengths[ohaeng] += weight * proportion
                    sipshin = get_sipshin(day_master_gan, janggan_char)
                    if sipshin: sipshin_strengths[sipshin] += weight * proportion
    for o in OHENG_ORDER: ohaeng_strengths[o] = round(ohaeng_strengths[o], 1)
    for s in SIPSHIN_ORDER: sipshin_strengths[s] = round(sipshin_strengths[s], 1)
    return ohaeng_strengths, sipshin_strengths

def get_ohaeng_summary_explanation(ohaeng_counts):
    explanation = "오행 분포는 사주의 에너지 균형을 보여줍니다. "
    if not ohaeng_counts: return explanation + "오행 정보를 계산할 수 없습니다."
    sorted_ohaeng = sorted(ohaeng_counts.items(), key=lambda item: item[1], reverse=True)
    threshold = 1.5 # Example threshold
    if sorted_ohaeng and sorted_ohaeng[0][1] > threshold * 1.5 :
        explanation += f"특히 {sorted_ohaeng[0][0]}(이)가 {sorted_ohaeng[0][1]}점으로 가장 강한 기운을 가집니다. "
    if sorted_ohaeng and sorted_ohaeng[-1][1] < threshold / 1.5 and sorted_ohaeng[-1][1] < sorted_ohaeng[0][1] / 2:
         explanation += f"반면, {sorted_ohaeng[-1][0]}(이)가 {sorted_ohaeng[-1][1]}점으로 상대적으로 약한 편입니다. "
    explanation += "전체적인 균형과 조화를 이루는 것이 중요합니다."
    return explanation

def get_sipshin_summary_explanation(sipshin_counts, day_master_gan):
    explanation = "십신은 일간(나)을 기준으로 다른 글자와의 관계를 나타내며, 사회적 관계, 성향, 재능 등을 유추해볼 수 있습니다. "
    threshold = 1.5
    strong_sibsins = [f"{s_name}({sipshin_counts.get(s_name, 0.0)})" for s_name in SIPSHIN_ORDER if sipshin_counts.get(s_name, 0.0) >= threshold]
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
        if unique_explanations: explanation += f" 이는 {', '.join(unique_explanations)} 등이 발달했을 가능성을 시사합니다. "
    else: explanation += "특별히 한쪽으로 치우치기보다는 여러 십신의 특성이 비교적 균형 있게 나타날 수 있습니다. "
    explanation += "각 십신의 긍정적인 면을 잘 발휘하고 보완하는 것이 중요합니다."
    return explanation

# ───────────────────────────────
# 1. 절입일 데이터 로딩
# ───────────────────────────────
@st.cache_data(show_spinner=False)
def load_solar_terms(file_name: str):
    if not os.path.exists(file_name):
        st.error(f"`{file_name}` 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return None
    try: df = pd.read_excel(file_name, engine='openpyxl')
    except Exception as e: st.error(f"엑셀 파일('{file_name}')을 읽는 중 오류 발생: {e}. 'openpyxl' 패키지가 설치되어 있는지 확인하세요."); return None
    term_dict = {}
    required_excel_cols = ["절기", "iso_datetime"]
    if not all(col in df.columns for col in required_excel_cols): st.error(f"엑셀 파일에 필요한 컬럼({required_excel_cols})이 없습니다."); return None
    for _, row in df.iterrows():
        term = str(row["절기"]).strip(); dt_val = row["iso_datetime"]
        if isinstance(dt_val, str): dt = pd.to_datetime(dt_val, errors="coerce")
        elif isinstance(dt_val, datetime): dt = pd.Timestamp(dt_val)
        elif isinstance(dt_val, pd.Timestamp): dt = dt_val
        else: st.warning(f"'{term}'의 'iso_datetime' 값 ('{dt_val}')을 datetime으로 변환 불가."); continue
        if pd.isna(dt): st.warning(f"'{term}'의 'iso_datetime' 값 ('{row['iso_datetime']}')을 파싱 불가."); continue
        term_dict.setdefault(dt.year, {})[term] = dt
    if not term_dict: st.warning("절기 데이터를 로드하지 못했거나 유효한 데이터가 없습니다."); return None
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None: st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수
# ───────────────────────────────
def get_saju_year(birth_dt, solar_data_dict):
    year = birth_dt.year; ipchun_data = solar_data_dict.get(year, {}); ipchun = ipchun_data.get("입춘")
    return year - 1 if (ipchun and birth_dt < ipchun) else year

def get_ganji_from_index(idx): return GAN[idx % 10] + JI[idx % 12]
def get_year_ganji(saju_year): idx = (saju_year - 4 + 60) % 60; return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

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
    try: branch_idx_in_sason = SAJU_MONTH_TERMS_ORDER.index(governing_term_name); month_ji = SAJU_MONTH_BRANCHES[branch_idx_in_sason]
    except ValueError: return f"오류({governing_term_name}없음)", "", ""
    yg_idx = GAN.index(year_gan_char); start_map = {0:2,5:2, 1:4,6:4, 2:6,7:6, 3:8,8:8, 4:0,9:0}
    start_gan_idx_for_in_month = start_map.get(yg_idx)
    if start_gan_idx_for_in_month is None: return "오류(연간->월간맵)", "", ""
    month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    month_gan = GAN[(start_gan_idx_for_in_month + month_order_idx) % 10]
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
    cur_time_float = hour + minute/60.0; siji_char, siji_order_idx = None, -1
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0; end_float = eh + em/60.0
        if ji_name == "자":
            if cur_time_float >= start_float or cur_time_float <= end_float: siji_char,siji_order_idx=ji_name,order_idx;break
        elif start_float <= cur_time_float < end_float: siji_char,siji_order_idx=ji_name,order_idx;break
    if siji_char is None: return "오류(시지판단불가)", "", ""
    dg_idx = GAN.index(day_gan_char); sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: return "오류(일간→시간맵)", "", ""
    time_gan_idx = (start_gan_idx_for_ja_hour + siji_order_idx) % 10
    return GAN[time_gan_idx] + siji_char, GAN[time_gan_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data_dict):
    is_yang_year = GAN.index(year_gan_char) % 2 == 0
    is_sunhaeng = (is_yang_year and gender=="남성") or (not is_yang_year and gender=="여성")
    saju_year_for_daewoon = get_saju_year(birth_dt, solar_data_dict)
    relevant_terms_for_daewoon = []
    for yr_offset in [-1, 0, 1]:
        year_terms = solar_data_dict.get(saju_year_for_daewoon + yr_offset, {})
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
    days_difference = (target_term_dt - birth_dt if is_sunhaeng else birth_dt - target_term_dt).total_seconds()/(24*3600)
    daewoon_start_age = max(1, int(round(days_difference / 3)))
    month_ganji_str = month_gan_char + month_ji_char; current_month_gapja_idx = -1
    for i in range(60):
        if get_ganji_from_index(i) == month_ganji_str: current_month_gapja_idx=i;break
    if current_month_gapja_idx == -1: return ["오류(월주갑자변환실패)"],daewoon_start_age,is_sunhaeng
    daewoon_list_output = []
    for i in range(10):
        age_display = daewoon_start_age + i * 10
        next_gapja_idx = (current_month_gapja_idx+(i+1) if is_sunhaeng else current_month_gapja_idx-(i+1)+60)%60
        daewoon_list_output.append(f"{age_display}세: {get_ganji_from_index(next_gapja_idx)}")
    return daewoon_list_output, daewoon_start_age, is_sunhaeng

def get_seun_list(start_year, n=10): return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]
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

# --- 세션 상태 초기화 ---
if 'saju_calculated_once' not in st.session_state:
    st.session_state.saju_calculated_once = False
if 'interpretation_segments' not in st.session_state:
    st.session_state.interpretation_segments = []


st.sidebar.header("1. 출생 정보")
calendar_type = st.sidebar.radio("달력 유형", ("양력", "음력"), index=0, horizontal=True)
is_leap_month = False
if calendar_type == "음력": is_leap_month = st.sidebar.checkbox("윤달", help="음력 생일이 윤달인 경우 체크해주세요.")

current_year_for_input = datetime.now().year
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
tm = st.sidebar.number_input("기준 월  " , 1, 12, today.month)
td = st.sidebar.number_input("기준 일  " , 1, 31, today.day)

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    st.session_state.interpretation_segments = [] # 계산 시마다 초기화
    st.session_state.saju_calculated_once = True

    birth_dt_input_valid = True; birth_dt = None
    if calendar_type == "양력":
        try: birth_dt = datetime(by,bm,bd,bh,bmin)
        except ValueError: st.error("❌ 유효하지 않은 양력 날짜/시간입니다."); birth_dt_input_valid = False; st.stop()
    else: # 음력
        try:
            lunar_conv_date = LunarDate(by, bm, bd, is_leap_month)
            solar_equiv_date = lunar_conv_date.toSolarDate()
            birth_dt = datetime(solar_equiv_date.year, solar_equiv_date.month, solar_equiv_date.day, bh, bmin)
            st.sidebar.info(f"음력 {by}년 {bm}월 {bd}일{' (윤달)' if is_leap_month else ''}은 양력 {birth_dt.strftime('%Y-%m-%d')} 입니다.")
        except ValueError as e: st.error(f"❌ 음력 날짜 변환 오류: {e}."); birth_dt_input_valid = False; st.stop()
        except Exception as e: st.error(f"❌ 음력 날짜 처리 중 알 수 없는 오류: {e}"); birth_dt_input_valid = False; st.stop()

    if birth_dt_input_valid and birth_dt:
        saju_year_val = get_saju_year(birth_dt, solar_data)
        year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
        month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
        day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day)
        time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)

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


        saju_8char_for_analysis = {
            "year_gan": year_gan_char, "year_ji": year_ji_char, "month_gan": month_gan_char, "month_ji": month_ji_char,
            "day_gan": day_gan_char, "day_ji": day_ji_char, "time_gan": time_gan_char, "time_ji": time_ji_char
        }
        analysis_possible = all(val_char and len(val_char) == 1 and ((key.endswith("_gan") and val_char in GAN) or (key.endswith("_ji") and val_char in JI)) for key, val_char in saju_8char_for_analysis.items())
        
        ohaeng_strengths, sipshin_strengths = {}, {}
        if analysis_possible:
            try: ohaeng_strengths, sipshin_strengths = calculate_ohaeng_sipshin_strengths(saju_8char_for_analysis)
            except Exception as e: st.warning(f"오행/십신 분석 중 오류: {e}"); analysis_possible = False
        else: st.warning("사주 기둥 오류로 오행/십신 분석 불가.")

        st.markdown("---"); st.subheader("🌳🔥 오행(五行) 분석")
        if ohaeng_strengths and analysis_possible:
            ohaeng_df_for_chart = pd.DataFrame.from_dict(ohaeng_strengths, orient='index', columns=['세력']).reindex(OHENG_ORDER)
            st.bar_chart(ohaeng_df_for_chart, height=300)
            ohaeng_summary_exp_text_html = get_ohaeng_summary_explanation(ohaeng_strengths)
            st.markdown(f"<div style='font-size: 0.95rem; ...'>{ohaeng_summary_exp_text_html}</div>", unsafe_allow_html=True) # 스타일 생략
            st.session_state.interpretation_segments.append(("🌳🔥 오행(五行) 분석", strip_html_tags(ohaeng_summary_exp_text_html)))
            ohaeng_table_data = {"오행": OHENG_ORDER, "세력": [ohaeng_strengths.get(o, 0.0) for o in OHENG_ORDER]}
            st.session_state.interpretation_segments.append(("오행 세력표", pd.DataFrame(ohaeng_table_data).to_markdown(index=False)))

        st.markdown("---"); st.subheader("🌟 십신(十神) 분석")
        if sipshin_strengths and analysis_possible:
            sipshin_df_for_chart = pd.DataFrame.from_dict(sipshin_strengths, orient='index', columns=['세력']).reindex(SIPSHIN_ORDER)
            st.bar_chart(sipshin_df_for_chart, height=400)
            sipshin_summary_exp_text_html = get_sipshin_summary_explanation(sipshin_strengths, day_gan_char)
            st.markdown(f"<div style='font-size: 0.95rem; ...'>{sipshin_summary_exp_text_html}</div>", unsafe_allow_html=True) # 스타일 생략
            st.session_state.interpretation_segments.append(("🌟 십신(十神) 분석", strip_html_tags(sipshin_summary_exp_text_html)))
            sipshin_table_data = {"십신": SIPSHIN_ORDER, "세력": [sipshin_strengths.get(s, 0.0) for s in SIPSHIN_ORDER]}
            st.session_state.interpretation_segments.append(("십신 세력표", pd.DataFrame(sipshin_table_data).to_markdown(index=False)))


        st.markdown("---"); st.subheader("💪 일간 강약 및 격국(格局) 분석")
        shinkang_status_result, shinkang_explanation_html = "분석 정보 없음", ""
        gekuk_name_result, gekuk_explanation_html = "분석 정보 없음", ""
        if analysis_possible and ohaeng_strengths and sipshin_strengths:
            try:
                shinkang_status_result = determine_shinkang_shinyak(sipshin_strengths)
                shinkang_explanation_html = get_shinkang_explanation(shinkang_status_result)
                gekuk_name_result = determine_gekuk(day_gan_char, month_gan_char, month_ji_char, sipshin_strengths)
                gekuk_explanation_html = get_gekuk_explanation(gekuk_name_result)
            except Exception as e: st.warning(f"신강/격국 분석 중 오류: {e}")
        
        col_shinkang, col_gekuk = st.columns(2)
        with col_shinkang: st.markdown(f"""<div style="..."><h4>일간 강약</h4><p>{shinkang_status_result}</p><p>{shinkang_explanation_html}</p></div>""", unsafe_allow_html=True) # 스타일 생략
        with col_gekuk: st.markdown(f"""<div style="..."><h4>격국 분석</h4><p>{gekuk_name_result}</p><p>{gekuk_explanation_html}</p></div>""", unsafe_allow_html=True) # 스타일 생략
        st.session_state.interpretation_segments.append(("💪 일간 강약", f"**{shinkang_status_result}**\n{strip_html_tags(shinkang_explanation_html)}"))
        st.session_state.interpretation_segments.append(("💪 격국(格局) 분석", f"**{gekuk_name_result}**\n{strip_html_tags(gekuk_explanation_html)}"))

        st.markdown("---"); st.subheader("🤝💥 합충형해파 분석")
        if analysis_possible and day_gan_char:
            try:
                hap_chung_results_dict = analyze_hap_chung_interactions(saju_8char_for_analysis)
                hap_chung_text_parts = []
                if any(v for v in hap_chung_results_dict.values()):
                    output_html_parts = []
                    for interaction_type, found_list in hap_chung_results_dict.items():
                        if found_list:
                            output_html_parts.append(f"<h6 style='...'>{interaction_type}</h6>") # 스타일 생략
                            items_html = "".join([f"<li style='...'>{item}</li>" for item in found_list]) # 스타일 생략
                            output_html_parts.append(f"<ul style='...'>{items_html}</ul>") # 스타일 생략
                            hap_chung_text_parts.append(f"**{interaction_type}**\n" + "\n".join([f"- {item}" for item in found_list]))
                    st.markdown("".join(output_html_parts), unsafe_allow_html=True)
                    hap_chung_explanation_html_val = get_hap_chung_detail_explanation(hap_chung_results_dict)
                    st.markdown(f"<div style='...'>{hap_chung_explanation_html_val}</div>", unsafe_allow_html=True) # 스타일 생략
                    hap_chung_text_parts.append(f"\n**설명:**\n{strip_html_tags(hap_chung_explanation_html_val)}")
                else: 
                    no_hapchung_msg = "특별히 두드러지는 합충형해파의 관계가 나타나지 않습니다."
                    st.markdown(f"<p>{no_hapchung_msg}</p>", unsafe_allow_html=True)
                    hap_chung_text_parts.append(no_hapchung_msg)
                st.session_state.interpretation_segments.append(("🤝💥 합충형해파 분석", "\n\n".join(hap_chung_text_parts)))
            except Exception as e: st.warning(f"합충형해파 분석 중 오류: {e}")
        
        st.markdown("---"); st.subheader("🔮 주요 신살(神煞) 분석")
        if analysis_possible and day_gan_char:
            try:
                found_shinsals_list = analyze_shinsal(saju_8char_for_analysis)
                shinsal_text_parts = []
                if found_shinsals_list:
                    items_html = "".join([f"<li style='...'>{item}</li>" for item in found_shinsals_list]) # 스타일 생략
                    st.markdown(f"<h6>발견된 주요 신살:</h6><ul style='...'>{items_html}</ul>", unsafe_allow_html=True) # 스타일 생략
                    shinsal_explanation_html_val = get_shinsal_detail_explanation(found_shinsals_list)
                    st.markdown(f"<div style='...'>{shinsal_explanation_html_val}</div>", unsafe_allow_html=True) # 스타일 생략
                    shinsal_text_parts.append("**발견된 주요 신살:**\n" + "\n".join([f"- {item}" for item in found_shinsals_list]))
                    shinsal_text_parts.append(f"\n**설명:**\n{strip_html_tags(shinsal_explanation_html_val)}")
                else:
                    no_shinsal_msg = "특별히 나타나는 주요 신살이 없습니다."
                    st.markdown(f"<p>{no_shinsal_msg}</p>", unsafe_allow_html=True)
                    shinsal_text_parts.append(no_shinsal_msg)
                st.session_state.interpretation_segments.append(("🔮 주요 신살(神煞) 분석", "\n\n".join(shinsal_text_parts)))
            except Exception as e: st.warning(f"신살 분석 중 오류: {e}")

        st.markdown("---"); st.subheader("☯️ 용신(喜神) 및 기신(忌神) 분석 (간략)")
        if analysis_possible and shinkang_status_result not in ["분석 정보 없음", "분석 오류"] and day_gan_char:
            try:
                yongshin_gishin_info = determine_yongshin_gishin_simplified(day_gan_char, shinkang_status_result)
                st.markdown(yongshin_gishin_info["html"], unsafe_allow_html=True)
                gaewoon_tips_html_content = get_gaewoon_tips_html(yongshin_gishin_info["yongshin"])
                if gaewoon_tips_html_content: st.markdown(f"<div style='...'>{gaewoon_tips_html_content}</div>", unsafe_allow_html=True) # 스타일 생략
                
                yongshin_text = strip_html_tags(yongshin_gishin_info["html"])
                gaewoon_text = strip_html_tags(gaewoon_tips_html_content) if gaewoon_tips_html_content else ""
                st.session_state.interpretation_segments.append(("☯️ 용신(喜神) 및 기신(忌神) 분석 (간략)", yongshin_text + ("\n\n" + gaewoon_text if gaewoon_text else "")))

            except Exception as e: st.warning(f"용신/기신 분석 중 오류: {e}")
        st.markdown("""<div style="..."><strong >참고 사항:</strong><br>...</div>""", unsafe_allow_html=True) # 스타일 생략, 내용은 이전과 동일
        st.session_state.interpretation_segments.append(("용신/기신 참고사항", strip_html_tags("""<div><strong>참고 사항:</strong><br> 여기서 제공되는 용신(喜神) 및 기신(忌神) 정보는 사주 당사자의 신강/신약을 기준으로 한 <strong>간략화된 억부용신(抑扶用神) 결과</strong>입니다. 실제 정밀한 용신 판단은 사주 전체의 조후(調候 - 계절의 조화), 통관(通關 - 막힌 기운 소통), 병약(病藥 - 사주의 문제점과 해결책) 등 다양한 요소를 종합적으로 고려해야 하므로, 본 결과는 참고용으로만 활용하시고 중요한 판단은 반드시 사주 전문가와 상의하시기 바랍니다.</div>""")))


        st.markdown("---"); st.subheader(f"運 대운 ({gender})")
        daewoon_text_for_copy = []
        if "오류" in month_pillar_str or not month_gan_char or not month_ji_char :
            st.warning("월주 오류로 대운 표시 불가.")
            daewoon_text_for_copy.append("월주 오류로 대운 표시 불가.")
        else:
            daewoon_text_list, daewoon_start_age_val, is_sunhaeng_val = get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data)
            if isinstance(daewoon_text_list, list) and daewoon_text_list and "오류" in daewoon_text_list[0]:
                st.warning(daewoon_text_list[0])
                daewoon_text_for_copy.append(daewoon_text_list[0])
            elif isinstance(daewoon_text_list, list) and all(":" in item for item in daewoon_text_list):
                daewoon_start_info = f"대운 시작 나이: 약 {daewoon_start_age_val}세 ({'순행' if is_sunhaeng_val else '역행'})"
                st.text(daewoon_start_info)
                daewoon_table_data = {"주기(나이)": [item.split(':')[0] for item in daewoon_text_list], "간지": [item.split(': ')[1] for item in daewoon_text_list]}
                daewoon_df = pd.DataFrame(daewoon_table_data)
                st.table(daewoon_df)
                daewoon_text_for_copy.append(daewoon_start_info)
                daewoon_text_for_copy.append(daewoon_df.to_markdown(index=False))
            else: 
                st.warning("대운 정보 로드 실패.")
                daewoon_text_for_copy.append("대운 정보 로드 실패.")
        st.session_state.interpretation_segments.append((f"運 대운 ({gender})", "\n".join(daewoon_text_for_copy)))


        st.markdown("---"); st.subheader(f"📅 기준일({ty}년 {tm}월 {td}일) 운세")
        unse_text_for_copy = []
        col1,col2 = st.columns(2)
        with col1:
            st.markdown(f"##### 歲 세운 ({ty}년~)")
            seun_df = pd.DataFrame(get_seun_list(ty,5), columns=["연도","간지"])
            st.table(seun_df)
            unse_text_for_copy.append(f"**歲 세운 ({ty}년~)**\n{seun_df.to_markdown(index=False)}")

            st.markdown(f"##### 日 일운 ({ty}-{tm:02d}-{td:02d}~)")
            ilun_df = pd.DataFrame(get_ilun_list(ty,tm,td,7), columns=["날짜","간지"])
            st.table(ilun_df)
            unse_text_for_copy.append(f"\n**日 일운 ({ty}-{tm:02d}-{td:02d}~)**\n{ilun_df.to_markdown(index=False)}")
        with col2:
            st.markdown(f"##### 月 월운 ({ty}년 {tm:02d}월~)")
            wolun_df = pd.DataFrame(get_wolun_list(ty,tm,solar_data,12), columns=["연월","간지"])
            st.table(wolun_df)
            unse_text_for_copy.append(f"\n**月 월운 ({ty}년 {tm:02d}월~)**\n{wolun_df.to_markdown(index=False)}")
        st.session_state.interpretation_segments.append((f"📅 기준일({ty}년 {tm}월 {td}일) 운세", "\n".join(unse_text_for_copy)))


# --- "풀이 내용 지침으로 보기" 버튼 및 결과 표시 ---
if st.session_state.saju_calculated_once:
    st.markdown("---")
    if st.button("📋 풀이 내용 지침으로 보기", use_container_width=True):
        st.session_state.show_interpretation_guide = True # 버튼 클릭 시 표시 플래그

    if st.session_state.get('show_interpretation_guide', False): # 버튼이 클릭되었을 때만 실행
        with st.expander("📖 전체 풀이 내용 (텍스트 지침)", expanded=True):
            if st.session_state.interpretation_segments:
                full_text_guide = ""
                for title, content in st.session_state.interpretation_segments:
                    full_text_guide += f"## {title}\n\n{content}\n\n---\n\n"
                
                st.markdown(full_text_guide)
                st.info("위 내용을 복사하여 활용하세요.")
            else:
                st.markdown("표시할 풀이 내용이 없습니다. 먼저 '계산 실행'을 해주세요.")
        # 가이드 표시 후에는 다시 숨기도록 플래그를 초기화 할 수 있음 (선택적)
        # st.session_state.show_interpretation_guide = False 
else:
    st.info("출생 정보를 입력하고 '계산 실행' 버튼을 누르면 사주 명식과 풀이 내용을 확인할 수 있습니다.")
