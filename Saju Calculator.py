# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math # 추가

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
        if isinstance(dt_val, str):
            dt = pd.to_datetime(dt_val, errors="coerce")
        elif isinstance(dt_val, datetime): 
             dt = pd.Timestamp(dt_val)
        elif isinstance(dt_val, pd.Timestamp):
            dt = dt_val
        else:
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{dt_val}', 타입: {type(dt_val)})을 datetime으로 변환할 수 없습니다.")
            continue
        if pd.isna(dt):
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{row['iso_datetime']}')을 날짜/시간으로 파싱할 수 없습니다.")
            continue
        year = dt.year
        term_dict.setdefault(year, {})[term] = dt
    if not term_dict:
        st.warning("절기 데이터를 로드하지 못했거나, 엑셀 파일에서 처리할 수 있는 유효한 데이터가 없습니다.")
        return None 
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None: 
    st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수
# ───────────────────────────────
def get_saju_year(birth_dt, solar_data_dict): # (이전과 동일)
    year = birth_dt.year
    ipchun_data = solar_data_dict.get(year, {})
    ipchun = ipchun_data.get("입춘") 
    return year - 1 if (ipchun and birth_dt < ipchun) else year

def get_ganji_from_index(idx): # (이전과 동일)
     # 이 함수는 60갑자 전체 인덱스(0~59)를 받아 간지를 반환하는데,
     # 수정된 get_day_ganji는 이 함수를 직접 사용하지 않고 간/지를 별도 반환.
     # 하지만 다른 곳(세운 등)에서 사용될 수 있으므로 유지.
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year): # (이전과 동일)
    idx = (saju_year - 4 + 60) % 60 
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_month_ganji(year_gan_char, birth_dt, solar_data_dict): # (이전과 동일)
    saju_year_for_month = get_saju_year(birth_dt, solar_data_dict)
    terms_this_saju_year = solar_data_dict.get(saju_year_for_month, {})
    terms_prev_saju_year = solar_data_dict.get(saju_year_for_month - 1, {})
    governing_term_name = None
    sorted_terms_this_year = sorted(
        [(name, dt) for name, dt in terms_this_saju_year.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for name, dt in sorted_terms_this_year:
        if birth_dt >= dt: governing_term_name = name
        else: break
    if not governing_term_name:
        sorted_prev_year_winter_terms = sorted(
            [(name, dt) for name, dt in terms_prev_saju_year.items() if name in ["소한", "대설"]],
            key=lambda x: x[1], reverse=True 
        )
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

# --- 일주 계산 함수 수정 ---
def date_to_jd(year, month, day):
    """양력 날짜를 율리우스 일(정오 UT 기준)로 변환합니다."""
    y = year
    m = month
    if m <= 2:
        y -= 1
        m += 12
    
    # 그레고리력인지 여부 판단 (1582년 10월 15일 이후)
    # 여기서는 입력 날짜가 항상 그레고리력이라고 가정 (현대 사주이므로)
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    
    jd_val = math.floor(365.25 * (y + 4716)) + \
             math.floor(30.6001 * (m + 1)) + \
             day + b - 1524 # 정수부분만 사용 (정오 기준 JD)
    return int(jd_val)

def get_day_ganji(year, month, day):
    """율리우스 일을 사용하여 일주(일간, 일지)를 계산합니다."""
    jd = date_to_jd(year, month, day)
    
    # 이 상수는 천문학적 JD와 60간지 사이클의 기준점에 따라 달라집니다.
    # (JD + 9) % 10 for Stem (0=갑)
    # (JD + 1) % 12 for Branch (0=자)
    # 이 조합이 1989-11-17을 신사(辛巳)로 만듭니다.
    # 辛: (jd + 9)%10 = (2447848+9)%10 = 2447857 % 10 = 7 (GAN[7] = '신')
    # 巳: (jd + 1)%12 = (2447848+1)%12 = 2447849 % 12 = 5 (JI[5] = '사')
    
    day_stem_idx = (jd + 9) % 10 
    day_branch_idx = (jd + 1) % 12

    day_gan_char = GAN[day_stem_idx]
    day_ji_char = JI[day_branch_idx]
    
    return day_gan_char + day_ji_char, day_gan_char, day_ji_char
# --- 일주 계산 함수 수정 완료 ---

def get_time_ganji(day_gan_char, hour, minute): # (이전과 동일)
    cur_time_float = hour + minute/60.0 
    siji_char, siji_order_idx = None, -1 
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0
        end_float = eh + em/60.0
        if ji_name == "자": 
            if cur_time_float >= start_float or cur_time_float <= end_float:
                siji_char, siji_order_idx = ji_name, order_idx; break
        else: 
            if start_float <= cur_time_float < end_float: 
                siji_char, siji_order_idx = ji_name, order_idx; break
    if siji_char is None: return "오류(시지판단불가)", "", ""
    dg_idx = GAN.index(day_gan_char) 
    sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: return "오류(일간→시간맵)", "", ""
    time_gan_idx = (start_gan_idx_for_ja_hour + siji_order_idx) % 10 
    return GAN[time_gan_idx] + siji_char, GAN[time_gan_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data_dict): # (이전과 동일)
    is_yang_year = GAN.index(year_gan_char) % 2 == 0 
    is_sunhaeng  = (is_yang_year and gender=="남성") or (not is_yang_year and gender=="여성")
    saju_year_for_daewoon = get_saju_year(birth_dt, solar_data_dict)
    relevant_terms_for_daewoon = []
    for yr_offset in [-1, 0, 1]: 
        year_to_check = saju_year_for_daewoon + yr_offset
        year_terms = solar_data_dict.get(year_to_check, {})
        for term_name, term_dt in year_terms.items():
            if term_name in SAJU_MONTH_TERMS_ORDER: 
                relevant_terms_for_daewoon.append({'name': term_name, 'datetime': term_dt})
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime']) 
    if not relevant_terms_for_daewoon: return ["오류(대운계산용 절기부족)"], 0, is_sunhaeng
    target_term_dt = None
    if is_sunhaeng: 
        for term_info in relevant_terms_for_daewoon:
            if term_info['datetime'] > birth_dt: target_term_dt = term_info['datetime']; break
    else: 
        for term_info in reversed(relevant_terms_for_daewoon): 
            if term_info['datetime'] < birth_dt: target_term_dt = term_info['datetime']; break
    if target_term_dt is None: return ["오류(대운 목표절기 못찾음)"], 0, is_sunhaeng
    if is_sunhaeng: days_difference = (target_term_dt - birth_dt).total_seconds() / (24 * 3600)
    else: days_difference = (birth_dt - target_term_dt).total_seconds() / (24 * 3600)
    daewoon_start_age = max(1, int(round(days_difference / 3))) 
    month_ganji_str = month_gan_char + month_ji_char
    current_month_gapja_idx = -1
    for i in range(60): # get_ganji_from_index를 사용하여 월주의 60갑자 인덱스를 찾음
        if get_ganji_from_index(i) == month_ganji_str: current_month_gapja_idx = i; break
    if current_month_gapja_idx == -1: return ["오류(월주갑자 변환실패)"], daewoon_start_age, is_sunhaeng
    daewoon_list_output = []
    for i in range(10): 
        age_display = daewoon_start_age + i * 10
        next_gapja_idx = -1
        if is_sunhaeng: next_gapja_idx = (current_month_gapja_idx + (i + 1)) % 60
        else: next_gapja_idx = (current_month_gapja_idx - (i + 1) + 60) % 60 
        daewoon_list_output.append(f"{age_display}세: {get_ganji_from_index(next_gapja_idx)}")
    return daewoon_list_output, daewoon_start_age, is_sunhaeng

def get_seun_list(start_year, n=10): # (이전과 동일)
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12): # (이전과 동일)
    output_wolun = []
    for i in range(n):
        current_year = base_year + (base_month - 1 + i) // 12
        current_month_num = (base_month - 1 + i) % 12 + 1
        seun_gan_char = get_year_ganji(current_year)[1] 
        dummy_birth_dt_for_wolun = datetime(current_year, current_month_num, 15, 12, 0) 
        wolun_ganji, _, _ = get_month_ganji(seun_gan_char, dummy_birth_dt_for_wolun, solar_data_dict)
        output_wolun.append((f"{current_year}-{current_month_num:02d}", wolun_ganji))
    return output_wolun

def get_ilun_list(year_val, month_val, day_val, n=10): # (get_day_ganji 수정에 따라 자동 반영)
    base_dt = datetime(year_val, month_val, day_val)
    output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji, _, _ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

# ───────────────────────────────
# 3. Streamlit UI (이전과 거의 동일, 입력범위 약간 수정)
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

st.sidebar.header("1. 출생 정보 (양력)")
current_year_for_input = datetime.now().year
min_input_year = 1905 # JD 계산은 넓은 범위를 지원하지만, 절기 데이터 범위에 맞추는 것이 좋음
max_input_year = 2100 # solar_data의 최대 연도에 맞추는 것이 좋음
if solar_data:
    min_input_year = min(solar_data.keys()) if solar_data else 1905
    max_input_year = max(solar_data.keys()) if solar_data else 2100

by = st.sidebar.number_input("연", min_input_year, max_input_year, 1989, help=f"출생년도 (양력, {min_input_year}~{max_input_year} 범위)")
bm = st.sidebar.number_input("월", 1, 12, 11)
bd = st.sidebar.number_input("일", 1, 31, 17)
bh = st.sidebar.number_input("시", 0, 23, 20)
bmin = st.sidebar.number_input("분", 0, 59, 0)
gender = st.sidebar.radio("성별", ("남성","여성"), horizontal=True, index=0)

st.sidebar.header("2. 운세 기준일 (양력)")
today = datetime.now()
ty = st.sidebar.number_input("기준 연도", min_input_year, max_input_year + 10, today.year, help=f"운세 기준년도 ({min_input_year}~{max_input_year+10} 범위)")
tm = st.sidebar.number_input("기준 월" , 1, 12, today.month)
td = st.sidebar.number_input("기준 일" , 1, 31, today.day)

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    try:
        birth_dt = datetime(by,bm,bd,bh,bmin)
    except ValueError:
        st.error("❌ 유효하지 않은 생년월일시입니다. 날짜를 다시 확인해주세요.")
        st.stop()

    saju_year_val = get_saju_year(birth_dt, solar_data)
    year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
    month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
    day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day) # 수정된 함수 사용
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
    st.caption(f"사주 기준 연도 (입춘 기준): {saju_year_val}년")

    st.subheader(f"運 대운 ({gender})")
    if "오류" in month_pillar_str or not month_gan_char or not month_ji_char :
        st.warning("월주 계산에 오류가 있어 대운을 표시할 수 없습니다.")
    else:
        daewoon_text_list, daewoon_start_age_val, is_sunhaeng_val = get_daewoon( year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data)
        if isinstance(daewoon_text_list, list) and daewoon_text_list and "오류" in daewoon_text_list[0]: st.warning(daewoon_text_list[0])
        elif isinstance(daewoon_text_list, list) and all(":" in item for item in daewoon_text_list):
            st.text(f"대운 시작 나이: 약 {daewoon_start_age_val}세 ({'순행' if is_sunhaeng_val else '역행'})")
            daewoon_table_data = {"주기(나이)": [item.split(':')[0] for item in daewoon_text_list], "간지": [item.split(': ')[1] for item in daewoon_text_list]}
            st.table(pd.DataFrame(daewoon_table_data))
        else: st.warning("대운 정보를 올바르게 가져오지 못했습니다.")

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
else:
    st.markdown(f"""
    **사용 방법**
    1. 이 파이썬 스크립트(`saju_app.py`)와 절기 데이터 엑셀 파일 (`{FILE_NAME}`)을 **같은 폴더**에 저장합니다.
    2. 컴퓨터에 Python과 Streamlit, Pandas, openpyxl이 설치되어 있어야 합니다. (터미널에서 `pip install streamlit pandas openpyxl`)
    3. 터미널에서 스크립트가 있는 폴더로 이동 후, `streamlit run saju_app.py` 명령 실행.
    4. 웹 브라우저에서 정보 입력 후 **🧮 계산 실행** 버튼 클릭.
    """)
    st.markdown("---"); st.markdown("**주의:** 학습 및 참고용이며, 중요한 결정은 전문가와 상의하세요.")
