# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta # datetime class imported from datetime module
import os

# ───────────────────────────────
# 0. 기본 상수
# ───────────────────────────────
# 사용자님의 정확한 엑셀 파일 이름으로 변경
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
# 1. 절입일 데이터 로딩
# ───────────────────────────────
@st.cache_data(show_spinner=False)
def load_solar_terms(file_name: str):
    """엑셀 파일 → {연도: {절기: datetime}}"""
    if not os.path.exists(file_name):
        st.error(f"`{file_name}` 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return None
    
    try:
        # 엑셀 파일을 읽습니다. 기본적으로 첫 번째 시트를 읽습니다.
        # 특정 시트 이름이 있다면 engine='openpyxl', sheet_name='시트이름' 추가 가능
        df = pd.read_excel(file_name, engine='openpyxl') 
    except Exception as e:
        st.error(f"엑셀 파일('{file_name}')을 읽는 중 오류 발생: {e}. 'openpyxl' 패키지가 설치되어 있는지 확인하세요.")
        return None

    term_dict = {}
    # 사용자 엑셀 파일의 실제 컬럼명 확인 (이전에 '절기', 'iso_datetime' 알려주심)
    required_excel_cols = ["절기", "iso_datetime"] 
    if not all(col in df.columns for col in required_excel_cols):
        st.error(f"엑셀 파일에 필요한 컬럼({required_excel_cols})이 없습니다. 현재 컬럼: {df.columns.tolist()}")
        return None

    for _, row in df.iterrows():
        term = str(row["절기"]).strip()      # "절기" 컬럼 사용
        dt_val = row["iso_datetime"]         # "iso_datetime" 컬럼 사용
        
        # 'iso_datetime' 값을 datetime 객체로 변환 시도
        if isinstance(dt_val, str): # 문자열 형태일 경우
            dt = pd.to_datetime(dt_val, errors="coerce")
        elif isinstance(dt_val, datetime): # 파이썬 datetime 객체일 경우 (엑셀에서 이미 변환된 경우)
             dt = pd.Timestamp(dt_val) # pandas Timestamp로 통일
        elif isinstance(dt_val, pd.Timestamp): # 이미 pandas Timestamp 객체일 경우
            dt = dt_val
        else:
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{dt_val}', 타입: {type(dt_val)})을 datetime으로 변환할 수 없습니다. 이 항목은 건너뜁니다.")
            continue
            
        if pd.isna(dt):
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{row['iso_datetime']}')을 날짜/시간으로 파싱할 수 없습니다. 이 항목은 건너뜁니다.")
            continue
        
        year = dt.year  # 파싱된 datetime 객체에서 연도 추출
        term_dict.setdefault(year, {})[term] = dt
    
    if not term_dict:
        st.warning("절기 데이터를 로드하지 못했거나, 엑셀 파일에서 처리할 수 있는 유효한 데이터가 없습니다.")
        return None 
        
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None: 
    st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수 (이하 로직은 이전과 거의 동일)
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
    
    sorted_terms_this_year = sorted(
        [(name, dt) for name, dt in terms_this_saju_year.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for name, dt in sorted_terms_this_year:
        if birth_dt >= dt:
            governing_term_name = name
        else:
            break
    if not governing_term_name:
        sorted_prev_year_winter_terms = sorted(
            [(name, dt) for name, dt in terms_prev_saju_year.items() if name in ["소한", "대설"]],
            key=lambda x: x[1],
            reverse=True 
        )
        for name, dt in sorted_prev_year_winter_terms:
            if birth_dt >= dt:
                governing_term_name = name
                break
    if not governing_term_name:
        return "오류(월주절기)", "", ""
    try:
        branch_idx_in_sason = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji  = SAJU_MONTH_BRANCHES[branch_idx_in_sason]
    except ValueError:
        return f"오류({governing_term_name}없음)", "", ""
    yg_idx = GAN.index(year_gan_char)
    start_map = {0:2,5:2, 1:4,6:4, 2:6,7:6, 3:8,8:8, 4:0,9:0} 
    start_gan_idx_for_in_month = start_map.get(yg_idx)
    if start_gan_idx_for_in_month is None:
        return "오류(연간->월간맵)", "", ""
    month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    month_gan = GAN[(start_gan_idx_for_in_month + month_order_idx) % 10]
    return month_gan + month_ji, month_gan, month_ji

def get_day_ganji(year, month, day):
    ref_date = datetime(2000, 1, 1) # 기준일: 2000년 1월 1일 (경진일)
    ref_idx = 46 # 경진일의 60갑자 인덱스 (갑자=0)
    current_date = datetime(year, month, day)
    days_diff = (current_date - ref_date).days
    idx = (ref_idx + days_diff % 60 + 60) % 60 # days_diff가 음수일 수 있으므로 +60 추가
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_time_ganji(day_gan_char, hour, minute):
    cur_time_float = hour + minute/60.0 
    siji_char, siji_order_idx = None, -1 
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0
        end_float = eh + em/60.0
        if ji_name == "자": 
            if cur_time_float >= start_float or cur_time_float <= end_float: # 자시는 23:30 ~ 익일 01:29
                siji_char, siji_order_idx = ji_name, order_idx
                break
        else: 
            if start_float <= cur_time_float < end_float: 
                siji_char, siji_order_idx = ji_name, order_idx
                break
    if siji_char is None:
        return "오류(시지판단불가)", "", ""
    dg_idx = GAN.index(day_gan_char) 
    sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: 
        return "오류(일간→시간맵)", "", ""
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
            if term_name in SAJU_MONTH_TERMS_ORDER: 
                relevant_terms_for_daewoon.append({'name': term_name, 'datetime': term_dt})
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime']) 
    if not relevant_terms_for_daewoon:
        return ["오류(대운계산용 절기부족)"], 0, is_sunhaeng
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
        return ["오류(대운 목표절기 못찾음)"], 0, is_sunhaeng
    if is_sunhaeng:
        days_difference = (target_term_dt - birth_dt).total_seconds() / (24 * 3600)
    else:
        days_difference = (birth_dt - target_term_dt).total_seconds() / (24 * 3600)
    daewoon_start_age = max(1, int(round(days_difference / 3))) 
    month_ganji_str = month_gan_char + month_ji_char
    current_month_gapja_idx = -1
    for i in range(60):
        if get_ganji_from_index(i) == month_ganji_str:
            current_month_gapja_idx = i
            break
    if current_month_gapja_idx == -1:
        return ["오류(월주갑자 변환실패)"], daewoon_start_age, is_sunhaeng
    daewoon_list_output = []
    for i in range(10): 
        age_display = daewoon_start_age + i * 10
        next_gapja_idx = -1
        if is_sunhaeng:
            next_gapja_idx = (current_month_gapja_idx + (i + 1)) % 60
        else: 
            next_gapja_idx = (current_month_gapja_idx - (i + 1) + 60) % 60 
        daewoon_list_output.append(f"{age_display}세: {get_ganji_from_index(next_gapja_idx)}")
    return daewoon_list_output, daewoon_start_age, is_sunhaeng

def get_seun_list(start_year, n=10):
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    output_wolun = []
    for i in range(n):
        current_year = base_year + (base_month - 1 + i) // 12
        current_month_num = (base_month - 1 + i) % 12 + 1
        seun_gan_char = get_year_ganji(current_year)[1] 
        dummy_birth_dt_for_wolun = datetime(current_year, current_month_num, 15, 12, 0) 
        wolun_ganji, _, _ = get_month_ganji(seun_gan_char, dummy_birth_dt_for_wolun, solar_data_dict)
        output_wolun.append((f"{current_year}-{current_month_num:02d}", wolun_ganji))
    return output_wolun

def get_ilun_list(year_val, month_val, day_val, n=10):
    base_dt = datetime(year_val, month_val, day_val)
    output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji, _, _ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

# ───────────────────────────────
# 3. Streamlit UI (이전과 동일)
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

st.sidebar.header("1. 출생 정보 (양력)")
current_year_for_input = datetime.now().year
# solar_data의 min/max year를 확인하여 input 범위 설정하면 더 좋음
min_input_year = min(solar_data.keys()) if solar_data else 1900
max_input_year = max(solar_data.keys()) if solar_data else current_year_for_input

by = st.sidebar.number_input("연", min_input_year, max_input_year, 1990, help=f"출생년도 (양력, {min_input_year}~{max_input_year} 범위)")
bm = st.sidebar.number_input("월", 1, 12, 6)
bd = st.sidebar.number_input("일", 1, 31, 15)
bh = st.sidebar.number_input("시", 0, 23, 12)
bmin = st.sidebar.number_input("분", 0, 59, 30)
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
    day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day)
    time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)

    st.subheader("📜 사주 명식")
    ms_data = {
        "구분":["천간","지지","간지"],
        "시주":[time_gan_char if "오류" not in time_pillar_str else "?", 
               time_ji_char if "오류" not in time_pillar_str else "?", 
               time_pillar_str if "오류" not in time_pillar_str else "오류"],
        "일주":[day_gan_char if "오류" not in day_pillar_str else "?", 
               day_ji_char if "오류" not in day_pillar_str else "?", 
               day_pillar_str if "오류" not in day_pillar_str else "오류"],
        "월주":[month_gan_char if "오류" not in month_pillar_str else "?", 
               month_ji_char if "오류" not in month_pillar_str else "?", 
               month_pillar_str if "오류" not in month_pillar_str else "오류"],
        "연주":[year_gan_char if "오류" not in year_pillar_str else "?", 
               year_ji_char if "오류" not in year_pillar_str else "?", 
               year_pillar_str if "오류" not in year_pillar_str else "오류"]
    }
    ms_df = pd.DataFrame(ms_data).set_index("구분")
    st.table(ms_df)
    st.caption(f"사주 기준 연도 (입춘 기준): {saju_year_val}년")

    st.subheader(f"運 대운 ({gender})")
    if "오류" in month_pillar_str or month_gan_char == "" or month_ji_char == "":
        st.warning("월주 계산에 오류가 있어 대운을 표시할 수 없습니다.")
    else:
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

    st.subheader(f"📅 기준일({ty}년 {tm}월 {td}일) 운세")
    col1,col2 = st.columns(2)
    with col1:
        st.markdown(f"##### 歲 세운 ({ty}년~)")
        seun_data = get_seun_list(ty,5)
        st.table(pd.DataFrame(seun_data, columns=["연도","간지"]))
        st.markdown(f"##### 日 일운 ({ty}-{tm:02d}-{td:02d}~)")
        ilun_data = get_ilun_list(ty,tm,td,7)
        st.table(pd.DataFrame(ilun_data, columns=["날짜","간지"]))
    with col2:
        st.markdown(f"##### 月 월운 ({ty}년 {tm:02d}월~)")
        wolun_data = get_wolun_list(ty,tm,solar_data,12)
        st.table(pd.DataFrame(wolun_data, columns=["연월","간지"]))
else:
    st.markdown(f"""
    **사용 방법**
    1. 이 파이썬 스크립트(`saju_app.py`)와 절기 데이터 엑셀 파일 (`{FILE_NAME}`)을 **같은 폴더**에 저장합니다.
    2. 컴퓨터에 Python과 Streamlit, Pandas, openpyxl이 설치되어 있어야 합니다.
       - Python 설치: [python.org](https://www.python.org/)
       - 패키지 설치 (터미널 또는 명령 프롬프트에서 실행):
         ```bash
         pip install streamlit pandas openpyxl
         ```
    3. 터미널 또는 명령 프롬프트에서 스크립트가 있는 폴더로 이동한 후, 다음 명령을 실행합니다:
       ```bash
       streamlit run saju_app.py
       ```
    4. 웹 브라우저에 앱이 열리면, 왼쪽 사이드바에서 출생 정보와 운세 기준일을 입력하고 **🧮 계산 실행** 버튼을 클릭하세요.
    """)
    st.markdown("---")
    st.markdown("**주의:** 이 프로그램은 학습 및 참고용으로 제작되었으며, 실제 사주 상담이나 중요한 결정은 반드시 전문가와 상의하시기 바랍니다. 계산 로직에 오류가 있을 수 있습니다.")
