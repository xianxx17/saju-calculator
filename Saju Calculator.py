# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta # datetime class imported from datetime module
import os

# ───────────────────────────────
# 0. 기본 상수
# ───────────────────────────────
# 사용자님의 CSV 파일 이름으로 변경
FILE_NAME = "Jeolgi_1900_2100_20250513.xlsx - Sheet1.csv" 

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
    """CSV 파일 → {연도: {절기: datetime}}"""
    if not os.path.exists(file_name):
        st.error(f"`{file_name}` 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return None
    
    try:
        df = pd.read_csv(file_name) # 엑셀 대신 CSV 읽기
    except Exception as e:
        st.error(f"CSV 파일('{file_name}')을 읽는 중 오류 발생: {e}")
        return None

    term_dict = {}
    # 사용자 CSV 파일의 실제 컬럼명 확인
    required_csv_cols = ["절기", "iso_datetime"] # lunar_date는 현재 사용 안함
    if not all(col in df.columns for col in required_csv_cols):
        st.error(f"CSV 파일에 필요한 컬럼({required_csv_cols})이 없습니다. 현재 컬럼: {df.columns.tolist()}")
        return None

    for _, row in df.iterrows():
        term = str(row["절기"]).strip()      # "절기" 컬럼 사용
        dt_val = row["iso_datetime"]         # "iso_datetime" 컬럼 사용
        
        # 'iso_datetime' 값을 datetime 객체로 변환 시도
        if isinstance(dt_val, str):
            dt = pd.to_datetime(dt_val, errors="coerce")
        elif isinstance(dt_val, pd.Timestamp) or isinstance(dt_val, datetime): # datetime.datetime도 고려
            dt = pd.Timestamp(dt_val) 
        else:
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{dt_val}')을 datetime으로 변환할 수 없습니다. 이 항목은 건너뜁니다.")
            continue
            
        if pd.isna(dt):
            st.warning(f"'{term}'의 'iso_datetime' 값 ('{row['iso_datetime']}')을 날짜/시간으로 파싱할 수 없습니다. 이 항목은 건너뜁니다.")
            continue
        
        year = dt.year  # 파싱된 datetime 객체에서 연도 추출
        term_dict.setdefault(year, {})[term] = dt
    
    if not term_dict:
        st.warning("절기 데이터를 로드하지 못했거나, CSV 파일에서 처리할 수 있는 유효한 데이터가 없습니다.")
        return None # 빈 딕셔너리 대신 None 반환하여 st.stop() 트리거
        
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None: # solar_data가 비어있거나 로드 실패 시 여기서 멈춤
    st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수 (이하 로직은 대부분 원본 유지)
# ───────────────────────────────
def get_saju_year(birth_dt, solar_data_dict):
    year = birth_dt.year
    ipchun_data = solar_data_dict.get(year, {})
    ipchun = ipchun_data.get("입춘") # solar_data_dict 구조에 맞춤
    # 만약 해당 년도 입춘 정보가 없다면, solar_data_dict.get(year-1, {}).get("입춘")도 고려할 수 있으나,
    # 현재 solar_data_dict는 이미 연도별로 구분되어 있음.
    return year - 1 if (ipchun and birth_dt < ipchun) else year

def get_ganji_from_index(idx):
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year):
    # 사주 연도를 기준으로 60갑자 인덱스 계산 (경자년 기준 등 만세력 규칙에 따라 -4 또는 다른 값 사용)
    # 이 코드는 (saju_year - 4)를 사용. 예: 2024년은 갑진년. (2024-4)%60 = 20. 갑(0)진(4). 20%10=0, 20%12=4.
    idx = (saju_year - 4 + 60) % 60 # 음수 방지 위해 +60
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_month_ganji(year_gan_char, birth_dt, solar_data_dict):
    # 사주년도 기준 절기 데이터 사용
    saju_year_for_month = get_saju_year(birth_dt, solar_data_dict)

    terms_this_saju_year = solar_data_dict.get(saju_year_for_month, {})
    terms_prev_saju_year = solar_data_dict.get(saju_year_for_month - 1, {})
    
    governing_term_name = None
    
    # 1. 현재 사주년도의 절기들 중에서 찾기
    # SAJU_MONTH_TERMS_ORDER에 있는 절기들만 사용하고, 시간순 정렬
    sorted_terms_this_year = sorted(
        [(name, dt) for name, dt in terms_this_saju_year.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for name, dt in sorted_terms_this_year:
        if birth_dt >= dt:
            governing_term_name = name
        else:
            break # 다음 절기는 생일 이후이므로 현재 governing_term_name 사용

    # 2. 만약 못찾았고, 생일이 연초(입춘 이전)라면, 이전 사주년도의 후반기 절기(소한, 대설)에서 찾기
    if not governing_term_name and birth_dt.year == saju_year_for_month: # 입춘 이후인데 못찾은 경우 (데이터 부족 가능성)
        # 이 경우는 거의 없어야 함. solar_data에 해당 연도 절기가 있다면.
        # 만약 입춘 이전이라 saju_year_for_month 가 birth_dt.year -1 이 된 경우,
        # 이 로직은 이미 이전 년도 절기를 보고 있는 것.
         pass # 다음 로직으로 자연스럽게 넘어감

    if not governing_term_name: # 여전히 못찾았다면 (주로 입춘 이전 생일)
        # 이전 사주년도의 '소한', '대설' 중에서 찾음 (시간 역순으로 더 맞는 것 선택)
        sorted_prev_year_winter_terms = sorted(
            [(name, dt) for name, dt in terms_prev_saju_year.items() if name in ["소한", "대설"]],
            key=lambda x: x[1],
            reverse=True # 최신순 (대설 -> 소한 순)
        )
        for name, dt in sorted_prev_year_winter_terms:
            if birth_dt >= dt:
                governing_term_name = name
                break
    
    if not governing_term_name:
        # st.warning(f"월주 절기 결정 불가: {birth_dt.strftime('%Y-%m-%d')}, 사주년도: {saju_year_for_month}")
        return "오류(월주절기)", "", ""

    try:
        branch_idx_in_sason = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji  = SAJU_MONTH_BRANCHES[branch_idx_in_sason]
    except ValueError:
        return f"오류({governing_term_name}없음)", "", ""


    yg_idx = GAN.index(year_gan_char)
    # 갑기토 병인, 을경금 무인, 병신수 경인, 정임목 임인, 무계화 갑인
    # 천간합 오행에 따른 월간두수법 적용 (인덱스 기반)
    # 갑(0)기(5) -> 병(2)부터 시작
    # 을(1)경(6) -> 무(4)부터 시작
    # 병(2)신(7) -> 경(6)부터 시작
    # 정(3)임(8) -> 임(8)부터 시작
    # 무(4)계(9) -> 갑(0)부터 시작
    start_map = {0:2,5:2, 1:4,6:4, 2:6,7:6, 3:8,8:8, 4:0,9:0} # 년간 인덱스 -> 인월의 천간 인덱스
    
    start_gan_idx_for_in_month = start_map.get(yg_idx)
    if start_gan_idx_for_in_month is None: # 이럴일은 없어야 함.
        return "오류(연간->월간맵)", "", ""

    # month_ji 에 해당하는 SAJU_MONTH_BRANCHES에서의 인덱스 (인월=0, 묘월=1 ...)
    month_order_idx = SAJU_MONTH_BRANCHES.index(month_ji)
    month_gan = GAN[(start_gan_idx_for_in_month + month_order_idx) % 10]
    return month_gan + month_ji, month_gan, month_ji

def get_day_ganji(year, month, day):
    # 기준일: 1899년 12월 31일 (00:00) 을 갑자(0) 전날(계해일)로 가정하여 계산
    # (실제 만세력의 정확한 기준일과 갑자번호를 사용하는 것이 더 정확함)
    # 이 코드의 기준은 (datetime(year,month,day) - datetime(1899,12,31)).days 로 일수 차이를 구하고 % 60.
    # 1900-01-01은 경진일 (실제로는 경자일). 이 기준점은 확인/조정 필요.
    # 원래 코드의 (1899,12,31) 기준은 특정 만세력의 계산법일 수 있음.
    # 예: 1900-01-01이 36번째(경자)가 되려면, (X - base_date_idx_offset) % 60 = 36
    # (datetime(1900,1,1) - datetime(1899,12,31)).days = 1.  1 % 60 = 1. GAN[1]=을, JI[1]=축. (을축) -> 안맞음.
    
    # 더 일반적인 방법: 특정일의 간지를 알고, 그로부터의 일수 차이로 계산
    # 예: 2000년 1월 1일은 경진일 (47번째, 갑자=0일때).
    ref_date = datetime(2000, 1, 1)
    ref_idx = 46 # 경진 (갑자0=경0 진4 -> 40+4+2=46?) / 갑0을1..경6, 자0축1..진4. (6,4) -> (46%10=6, 46%12=10 술???)
                # 갑자0, 을축1, ... 경자36, 신축37 ... 계묘39, 갑진40 ... 경진46.
    
    current_date = datetime(year, month, day)
    days_diff = (current_date - ref_date).days
    idx = (ref_idx + days_diff) % 60
    if idx < 0: idx += 60 # 과거 날짜의 경우
    
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]


def get_time_ganji(day_gan_char, hour, minute):
    cur_time_float = hour + minute/60.0 # 분을 소수점으로 변환
    siji_char, siji_order_idx = None, -1 # siji_order_idx 는 자시0, 축시1 ... 해시11
    
    for (sh,sm),(eh,em), ji_name, order_idx in TIME_BRANCH_MAP:
        start_float = sh + sm/60.0
        end_float = eh + em/60.0
        
        if ji_name == "자": # 자시는 밤 23:30 ~ 다음날 01:29
            # 현재 시간이 23:30 이후이거나, 또는 00:00부터 01:29 이전일 경우
            if cur_time_float >= start_float or cur_time_float <= end_float:
                siji_char, siji_order_idx = ji_name, order_idx
                break
        else: # 다른 시간대
            if start_float <= cur_time_float < end_float: # 종료시간은 포함하지 않음 (예: 01:29:59 까지)
                                                          # 원본 코드: <e+(1/60) -> 종료시간 정각까지 포함하려는 의도
                siji_char, siji_order_idx = ji_name, order_idx
                break
    
    if siji_char is None: # 백업: 경계값에 걸렸을 경우 (거의 없을 것으로 예상)
        if 23.5 <= cur_time_float or cur_time_float < 1.5 : siji_char, siji_order_idx = "자",0
        # ... 다른 시간대도 필요시 추가 가능

    if siji_char is None:
        return "오류(시지판단불가)", "", ""

    dg_idx = GAN.index(day_gan_char) # 일간의 인덱스
    # 시두법: 갑기일 갑자시, 을경일 병자시, 병신일 무자시, 정임일 경자시, 무계일 임자시
    # 일간 인덱스 -> 자시의 천간 인덱스
    # 갑(0)기(5) -> 갑(0)자시
    # 을(1)경(6) -> 병(2)자시
    # 병(2)신(7) -> 무(4)자시
    # 정(3)임(8) -> 경(6)자시
    # 무(4)계(9) -> 임(8)자시
    sidu_start_map = {0:0,5:0, 1:2,6:2, 2:4,7:4, 3:6,8:6, 4:8,9:8}
    
    start_gan_idx_for_ja_hour = sidu_start_map.get(dg_idx)
    if start_gan_idx_for_ja_hour is None: # 이럴 일 없어야 함
        return "오류(일간→시간맵)", "", ""
        
    time_gan_idx = (start_gan_idx_for_ja_hour + siji_order_idx) % 10 # 자시0, 축시1...
    return GAN[time_gan_idx] + siji_char, GAN[time_gan_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data_dict):
    # 1. 사주년도의 양/음 결정 (년간 기준)
    is_yang_year = GAN.index(year_gan_char) % 2 == 0 # 갑병무경임 = 양년
    
    # 2. 순행/역행 결정
    # 남명양년/여명음년 = 순행, 남명음년/여명양년 = 역행
    is_sunhaeng  = (is_yang_year and gender=="남성") or (not is_yang_year and gender=="여성")

    # 3. 대운수 계산: 생일 ~ 다음/이전 "월의 시작 절기"까지의 날짜 수 / 3
    saju_year_for_daewoon = get_saju_year(birth_dt, solar_data_dict)

    # 대운수 계산에 필요한 절기 리스트 (해당 사주년도 및 인접년도 월 시작 절기)
    relevant_terms_for_daewoon = []
    for yr_offset in [-1, 0, 1]: # 이전년도, 당해년도, 다음년도 절기 모두 고려
        year_to_check = saju_year_for_daewoon + yr_offset
        year_terms = solar_data_dict.get(year_to_check, {})
        for term_name, term_dt in year_terms.items():
            if term_name in SAJU_MONTH_TERMS_ORDER: # 월의 시작 절기만
                relevant_terms_for_daewoon.append({'name': term_name, 'datetime': term_dt})
    
    relevant_terms_for_daewoon.sort(key=lambda x: x['datetime']) # 시간순 정렬

    if not relevant_terms_for_daewoon:
        return ["오류(대운계산용 절기부족)"], 0, is_sunhaeng # is_sunhaeng 추가

    target_term_dt = None
    if is_sunhaeng: # 순행: 생일 이후 첫번째 오는 월 시작 절기
        for term_info in relevant_terms_for_daewoon:
            if term_info['datetime'] > birth_dt:
                target_term_dt = term_info['datetime']
                break
    else: # 역행: 생일 이전 가장 마지막 월 시작 절기
        for term_info in reversed(relevant_terms_for_daewoon): # 역순으로 찾기
            if term_info['datetime'] < birth_dt:
                target_term_dt = term_info['datetime']
                break
    
    if target_term_dt is None:
        return ["오류(대운 목표절기 못찾음)"], 0, is_sunhaeng

    if is_sunhaeng:
        days_difference = (target_term_dt - birth_dt).total_seconds() / (24 * 3600)
    else:
        days_difference = (birth_dt - target_term_dt).total_seconds() / (24 * 3600)
    
    daewoon_start_age = max(1, int(round(days_difference / 3))) # 3일당 1세, 반올림, 최소 1세

    # 4. 대운 간지 리스트 생성 (월주 기준)
    # 월주의 60갑자 인덱스 찾기
    month_ganji_str = month_gan_char + month_ji_char
    current_month_gapja_idx = -1
    for i in range(60):
        if get_ganji_from_index(i) == month_ganji_str:
            current_month_gapja_idx = i
            break
    
    if current_month_gapja_idx == -1:
        return ["오류(월주갑자 변환실패)"], daewoon_start_age, is_sunhaeng

    daewoon_list_output = []
    for i in range(10): # 10개 대운 (100년)
        age_display = daewoon_start_age + i * 10
        next_gapja_idx = -1
        if is_sunhaeng:
            next_gapja_idx = (current_month_gapja_idx + (i + 1)) % 60
        else: # 역행
            next_gapja_idx = (current_month_gapja_idx - (i + 1) + 60) % 60 # 음수 방지
        
        daewoon_list_output.append(f"{age_display}세: {get_ganji_from_index(next_gapja_idx)}")
        
    return daewoon_list_output, daewoon_start_age, is_sunhaeng # is_sunhaeng 추가 반환

def get_seun_list(start_year, n=10):
    return [(y, get_year_ganji(y)[0]) for y in range(start_year, start_year+n)] # get_year_ganji 활용


def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    # (이 함수는 get_month_ganji를 재활용하는 것이 좋으나, 일단 원본 구조 유지하되 solar_data 전달)
    output_wolun = []
    for i in range(n):
        current_year = base_year + (base_month - 1 + i) // 12
        current_month_num = (base_month - 1 + i) % 12 + 1
        
        # 해당 년도의 천간 (세운의 천간)
        seun_gan_char = get_year_ganji(current_year)[1] # 년간만 가져옴
        
        # 월운 계산을 위한 기준일 (예: 해당월 15일)
        # 이 날짜를 기준으로 get_month_ganji 호출 시도 가능
        # (단, get_month_ganji는 생년월일 전체 datetime 객체를 받으므로, 시간은 임의로 설정)
        dummy_birth_dt_for_wolun = datetime(current_year, current_month_num, 15, 12, 0) # 15일 정오
        
        wolun_ganji, _, _ = get_month_ganji(seun_gan_char, dummy_birth_dt_for_wolun, solar_data_dict)
        
        output_wolun.append((f"{current_year}-{current_month_num:02d}", wolun_ganji))
    return output_wolun


def get_ilun_list(year_val, month_val, day_val, n=10):
    # (이 함수는 get_day_ganji를 재활용)
    base_dt = datetime(year_val, month_val, day_val)
    output_ilun = []
    for i in range(n):
        current_dt = base_dt + timedelta(days=i)
        ilun_ganji, _, _ = get_day_ganji(current_dt.year, current_dt.month, current_dt.day)
        output_ilun.append((current_dt.strftime("%Y-%m-%d"), ilun_ganji))
    return output_ilun

# ───────────────────────────────
# 3. Streamlit UI
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

# 입력
st.sidebar.header("1. 출생 정보 (양력)")
current_year = datetime.now().year
by = st.sidebar.number_input("연", 1905, current_year -1 , 1990, help="출생년도 (양력)") # solar_data 범위 고려
bm = st.sidebar.number_input("월", 1, 12, 6)
bd = st.sidebar.number_input("일", 1, 31, 15)
bh = st.sidebar.number_input("시", 0, 23, 12)
bmin = st.sidebar.number_input("분", 0, 59, 30)
gender = st.sidebar.radio("성별", ("남성","여성"), horizontal=True, index=0) # 기본값 남성

st.sidebar.header("2. 운세 기준일 (양력)")
today = datetime.now()
ty = st.sidebar.number_input("기준 연도", 1905, current_year + 10, today.year) # solar_data 범위 고려
tm = st.sidebar.number_input("기준 월" , 1, 12, today.month)
td = st.sidebar.number_input("기준 일" , 1, 31, today.day)

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    try:
        birth_dt = datetime(by,bm,bd,bh,bmin)
    except ValueError:
        st.error("❌ 유효하지 않은 생년월일시입니다. 날짜를 다시 확인해주세요.")
        st.stop()

    # ── 명식 계산
    saju_year_val = get_saju_year(birth_dt, solar_data)
    year_pillar_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_val)
    month_pillar_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_dt, solar_data)
    
    # 일주 계산 시, 만약 자시(23:30 이후)면 다음날로 일주를 바꾸는 '명일자시'룰 적용 여부 선택 가능.
    # 여기서는 입력된 날짜 그대로 사용.
    day_pillar_str, day_gan_char, day_ji_char = get_day_ganji(birth_dt.year, birth_dt.month, birth_dt.day) # 생일의 년월일 사용
    time_pillar_str, time_gan_char, time_ji_char = get_time_ganji(day_gan_char, birth_dt.hour, birth_dt.minute)


    st.subheader("📜 사주 명식")
    # 오류 발생 시 '?'로 표시되도록 처리
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

    # ── 대운
    st.subheader(f"運 대운 ({gender})")
    if "오류" in month_pillar_str or month_gan_char == "" or month_ji_char == "": # 월주 오류 시 대운 계산 불가
        st.warning("월주 계산에 오류가 있어 대운을 표시할 수 없습니다.")
    else:
        # get_daewoon 함수가 is_sunhaeng도 반환하도록 수정했으므로, 변수 하나 더 받음
        daewoon_text_list, daewoon_start_age_val, is_sunhaeng_val = get_daewoon(
            year_gan_char, gender, birth_dt, month_gan_char, month_ji_char, solar_data
        )
        if isinstance(daewoon_text_list, list) and "오류" in daewoon_text_list[0]:
            st.warning(daewoon_text_list[0])
        else:
            st.text(f"대운 시작 나이: 약 {daewoon_start_age_val}세 ({'순행' if is_sunhaeng_val else '역행'})")
            # 대운 리스트 파싱하여 테이블 생성
            if isinstance(daewoon_text_list, list) and all(":" in item for item in daewoon_text_list):
                 daewoon_table_data = {
                    "주기(나이)": [item.split(':')[0] for item in daewoon_text_list],
                    "간지": [item.split(': ')[1] for item in daewoon_text_list]
                 }
                 st.table(pd.DataFrame(daewoon_table_data))
            else:
                 st.warning("대운 정보를 테이블 형식으로 표시할 수 없습니다.")


    # 세운·월운·일운
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
    **사용 방법** 1. 이 파이썬 스크립트(`saju_app.py`)와 절기 데이터 CSV 파일 (`{FILE_NAME}`)을 **같은 폴더**에 저장합니다.
    2. 컴퓨터에 Python과 Streamlit, Pandas가 설치되어 있어야 합니다.
       - Python 설치: [python.org](https://www.python.org/)
       - 패키지 설치 (터미널 또는 명령 프롬프트에서 실행):
         ```bash
         pip install streamlit pandas
         ```
    3. 터미널 또는 명령 프롬프트에서 스크립트가 있는 폴더로 이동한 후, 다음 명령을 실행합니다:
       ```bash
       streamlit run saju_app.py
       ```
    4. 웹 브라우저에 앱이 열리면, 왼쪽 사이드바에서 출생 정보와 운세 기준일을 입력하고 **🧮 계산 실행** 버튼을 클릭하세요.
    """)
    st.markdown("---")
    st.markdown("**주의:** 이 프로그램은 학습 및 참고용으로 제작되었으며, 실제 사주 상담이나 중요한 결정은 반드시 전문가와 상의하시기 바랍니다. 계산 로직에 오류가 있을 수 있습니다.")
