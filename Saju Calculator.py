import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 상수 정의 ---
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

SAJU_MONTH_TERMS_ORDER = [
    "입춘", "경칩", "청명", "입하", "망종", "소서",
    "입추", "백로", "한로", "입동", "대설", "소한"
]
SAJU_MONTH_BRANCHES = ["인", "묘", "진", "사", "오", "미", "신", "유", "술", "해", "자", "축"]

TIME_BRANCH_MAP = [
    ((23, 30), (1, 29), "자", 0), ((1, 30), (3, 29), "축", 1),
    ((3, 30), (5, 29), "인", 2), ((5, 30), (7, 29), "묘", 3),
    ((7, 30), (9, 29), "진", 4), ((9, 30), (11, 29), "사", 5),
    ((11, 30), (13, 29), "오", 6), ((13, 30), (15, 29), "미", 7),
    ((15, 30), (17, 29), "신", 8), ((17, 30), (19, 29), "유", 9),
    ((19, 30), (21, 29), "술", 10), ((21, 30), (23, 29), "해", 11)
]

# --- 절입일 데이터 로딩 및 처리 ---
@st.cache_data
def load_solar_terms(uploaded_file_obj):
    try:
        solar_terms_df = pd.read_excel(uploaded_file_obj)
        
        st.sidebar.subheader("엑셀에서 읽어온 컬럼명:")
        st.sidebar.caption("파일의 실제 컬럼명과 아래 코드에서 사용하는 이름이 일치해야 합니다.")
        actual_column_names = list(solar_terms_df.columns)
        st.sidebar.write(actual_column_names)

        term_dict = {}
        processed_rows = 0
        skipped_rows = 0

        # 사용자의 설명("절입일에 모든 정보가 몰려있어")을 바탕으로,
        # '절입일' 컬럼이 주요 날짜/시간 정보를 담고 있다고 가정합니다.
        # 이 컬럼의 실제 이름이 다르면 아래 'datetime_column_candidate'를 수정해야 합니다.
        datetime_column_candidate = '절입일' # <--- 사용자 파일의 실제 컬럼명으로 변경 가능

        # 만약 사이드바에 출력된 실제 컬럼명 중 '절입일'이 없다면, 
        # 사용자가 알려준 F열과 유사한 다른 컬럼명으로 대체해야 함.
        # 예: if '실제시간컬럼명' in actual_column_names: datetime_column_candidate = '실제시간컬럼명'

        for _, row in solar_terms_df.iterrows():
            try:
                year_str = str(row.get('연도', '')).strip()
                term_name_str = str(row.get('절기', '')).strip()

                if not year_str or not term_name_str: # 필수 정보 누락 시 건너뛰기
                    skipped_rows +=1
                    continue
                
                year = int(float(year_str)) # 연도가 숫자로 변환 가능한지 확인
                term_name = term_name_str

                dt_str = None

                # 1순위: 사용자가 '모든 정보가 몰려있다'고 한 컬럼 (datetime_column_candidate)
                if datetime_column_candidate in actual_column_names and pd.notna(row.get(datetime_column_candidate)):
                    dt_str = str(row[datetime_column_candidate])
                # 2순위: '절입일시' 컬럼 (일반적인 경우)
                elif '절입일시' in actual_column_names and pd.notna(row.get('절입일시')):
                    dt_str = str(row['절입일시'])
                # 3순위: '절입일'과 '절입시간' 컬럼 조합 (이전 방식)
                elif ('절입일' in actual_column_names and '절입시간' in actual_column_names and
                      pd.notna(row.get('절입일')) and pd.notna(row.get('절입시간')) and
                      datetime_column_candidate != '절입일'): # datetime_column_candidate가 '절입일'일 경우 중복 방지
                    # 이 경우는 '절입일' 컬럼이 날짜'만' 담고, '절입시간' 컬럼이 시간'만' 담고 있을 때 유효
                    date_part = str(row['절입일'])
                    time_part = str(row['절입시간'])
                    # "년,월,일,시,분" 등을 제거하여 pandas가 잘 인식하도록 정제 시도 (더 복잡한 정제 필요할 수 있음)
                    # date_part_clean = date_part.replace("년","-").replace("월","-").replace("일","").split(" ")[0]
                    # time_part_clean = time_part.replace("시",":").replace("분","").strip()
                    # dt_str = f"{date_part_clean} {time_part_clean}"
                    # 위 정제는 매우 기본적인 형태로, 실제 데이터에 따라 더 강력한 정제가 필요할 수 있습니다.
                    # 우선은 사용자의 "절입일에 모든 정보가 몰려있다"는 정보를 신뢰합니다.
                    # 만약 '절입일' 컬럼이 날짜만 있고, '절입시간' 컬럼이 시간만 있고, 그 형식이 복잡하다면,
                    # 아래 pd.to_datetime에서 오류가 날 수 있습니다.
                    dt_str = date_part + " " + time_part


                if dt_str is None:
                    skipped_rows +=1
                    continue

                dt = pd.to_datetime(dt_str, errors='coerce')

                if pd.isna(dt):
                    skipped_rows +=1
                    continue
                
                if year not in term_dict:
                    term_dict[year] = {}
                term_dict[year][term_name] = dt
                processed_rows += 1

            except Exception as e_inner:
                skipped_rows +=1
                continue
        
        if skipped_rows > 0:
            st.sidebar.warning(f"절입일 데이터 중 {skipped_rows}개 행이 날짜/시간 정보 부족 또는 오류로 인해 건너뛰어졌습니다.")
        if processed_rows == 0 and solar_terms_df.shape[0] > 0 : # 데이터프레임에 행은 있지만 처리된게 없을때
            st.error("절입일 데이터를 전혀 처리하지 못했습니다. 사이드바의 '엑셀에서 읽어온 컬럼명'과 실제 파일, 그리고 코드 내 컬럼명 설정을 확인해주세요.")
            st.sidebar.info(f"현재 날짜/시간 정보를 읽으려는 주 대상 컬럼: '{datetime_column_candidate}'")
            return None
        if not term_dict and solar_terms_df.shape[0] > 0:
             st.error("처리된 절입일 데이터가 없습니다. 파일 내용 및 컬럼 설정을 확인해주세요.")
             return None

        return term_dict
    except Exception as e_outer:
        st.error(f"엑셀 파일 처리 중 심각한 오류 발생: {e_outer}")
        return None

# --- (이하 사주 명식, 대운, 세운, 월운, 일운 계산 함수 및 UI 코드는 이전 답변과 동일하게 유지) ---
# ... (이전 답변의 get_saju_year 부터 끝까지의 코드를 여기에 붙여넣으시면 됩니다) ...
# --- 사주 명식 계산 함수 ---
def get_saju_year(birth_dt, solar_data):
    """ 사주 연도(절입일 기준) 결정 """
    year = birth_dt.year
    ipchun_this_year = solar_data.get(year, {}).get("입춘")
    if ipchun_this_year:
        return year - 1 if birth_dt < ipchun_this_year else year
    st.warning(f"{year}년 입춘 데이터 누락. 현재 연도 사용.")
    return year

def get_ganji_from_index(idx):
    """ 0-59 갑자 인덱스로부터 천간지지 문자열 반환 """
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year_num):
    """ 사주 연도의 간지 계산 """
    idx = (saju_year_num - 4) % 60
    year_gan = GAN[idx % 10]
    year_ji = JI[idx % 12]
    return year_gan + year_ji, year_gan, year_ji

def get_month_ganji(year_gan_char, birth_dt, solar_data):
    birth_year_calendar = birth_dt.year
    governing_term_name = None
    current_year_terms = solar_data.get(birth_year_calendar, {})
    sorted_terms = sorted(
        [(name, dt_val) for name, dt_val in current_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for term_name, term_dt in sorted_terms:
        if birth_dt >= term_dt:
            governing_term_name = term_name
        else:
            break
    
    if governing_term_name is None or \
       (governing_term_name == "입춘" and birth_dt < current_year_terms.get("입춘", birth_dt + timedelta(days=1))):
        prev_year_terms = solar_data.get(birth_year_calendar - 1, {})
        sorted_prev_year_terms = sorted(
            [(name, dt_val) for name, dt_val in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
            key=lambda x: x[1]
        )
        for term_name, term_dt in reversed(sorted_prev_year_terms):
            if term_name in ["소한", "대설"] and birth_dt >= term_dt :
                 governing_term_name = term_name
                 break
    
    if not governing_term_name:
        return "오류(월주절기)", "", ""

    try:
        month_branch_saju_idx = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
        month_ji_char = SAJU_MONTH_BRANCHES[month_branch_saju_idx]
    except ValueError:
        return f"오류({governing_term_name}없음)", "", ""

    year_gan_idx = GAN.index(year_gan_char)
    start_wolgan_map = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0}
    start_gan_idx_for_inwol = start_wolgan_map.get(year_gan_idx)

    if start_gan_idx_for_inwol is None:
        return "오류(연간->월간)", "", ""
    
    month_gan_idx = (start_gan_idx_for_inwol + month_branch_saju_idx) % 10
    month_gan_char = GAN[month_gan_idx]
    
    return month_gan_char + month_ji_char, month_gan_char, month_ji_char

def get_day_ganji(year, month, day):
    base_dt = datetime(1899, 12, 31)
    target_dt = datetime(year, month, day)
    days_diff = (target_dt - base_dt).days
    ganji_idx = days_diff % 60
    
    day_gan = GAN[ganji_idx % 10]
    day_ji = JI[ganji_idx % 12]
    return day_gan + day_ji, day_gan, day_ji

def get_time_ganji(day_gan_char, birth_hour, birth_minute):
    siji_char = None
    siji_idx_universal = -1
    current_time_decimal = birth_hour + birth_minute / 60.0

    for (start_h, start_m), (end_h, end_m), ji_name, ji_idx in TIME_BRANCH_MAP:
        start_decimal = start_h + start_m / 60.0
        end_decimal = end_h + end_m / 60.0 
        if ji_name == "자":
            if current_time_decimal >= start_decimal or current_time_decimal <= end_decimal:
                siji_char = ji_name
                siji_idx_universal = ji_idx
                break
        elif start_decimal <= current_time_decimal < end_decimal + (1/60.0) : # 다음 시간 시작 전까지
             siji_char = ji_name
             siji_idx_universal = ji_idx
             break
    
    if siji_char is None: # 마지막 해시(21:30~23:29) 이후 자시 전까지의 예외 처리
        if TIME_BRANCH_MAP[-1][1][0] + TIME_BRANCH_MAP[-1][1][1]/60.0 <= current_time_decimal < 24.0:
             siji_char = TIME_BRANCH_MAP[-1][2] # 해시
             siji_idx_universal = TIME_BRANCH_MAP[-1][3]


    if not siji_char: # 그래도 못찾으면 자시로 간주 (23:30 이전의 밤 11시 등) - 이부분은 좀더 견고한 로직 필요
        # 또는 오류 처리. 현재 TIME_BRANCH_MAP 상으로는 23:29까지 커버. 그 이후는 자시.
        # 사용자가 23시 29분 이후~23시 30분 전을 입력하면 siji_char가 None일 수 있음. 이 경우 자시로.
        if current_time_decimal >= (TIME_BRANCH_MAP[-1][0][0] + TIME_BRANCH_MAP[-1][0][1]/60.0 + 2 - (1/60.0) ) or current_time_decimal < (TIME_BRANCH_MAP[0][1][0] + TIME_BRANCH_MAP[0][1][1]/60.0):
             siji_char = "자"
             siji_idx_universal = 0
        else:
            return "오류(시지찾기실패)", "", ""


    day_gan_idx = GAN.index(day_gan_char)
    start_sigan_map = {0:0, 5:0, 1:2, 6:2, 2:4, 7:4, 3:6, 8:6, 4:8, 9:8}
    start_gan_idx_for_jasi = start_sigan_map.get(day_gan_idx)

    if start_gan_idx_for_jasi is None:
        return "오류(일간->시간)", "", ""
    
    time_gan_idx = (start_gan_idx_for_jasi + siji_idx_universal) % 10
    time_gan_char = GAN[time_gan_idx]
    
    return time_gan_char + siji_char, time_gan_char, siji_char

def get_daewoon(year_gan_char, gender, birth_datetime, month_ganji_str, month_gan_char, month_ji_char, solar_data):
    daewoon_pillars = []
    is_yang_year = GAN.index(year_gan_char) % 2 == 0
    sunhaeng = (is_yang_year and gender == "남성") or (not is_yang_year and gender == "여성")

    birth_cal_year = birth_datetime.year
    governing_term_datetime = None
    governing_term_name_for_daewoon = None

    cal_year_terms = solar_data.get(birth_cal_year, {})
    sorted_cal_year_terms = sorted(
        [(name, dt) for name, dt in cal_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for term_name, term_dt in sorted_cal_year_terms:
        if birth_datetime >= term_dt:
            governing_term_datetime = term_dt
            governing_term_name_for_daewoon = term_name
        else:
            break
    
    if governing_term_datetime is None or \
      (governing_term_name_for_daewoon == "입춘" and birth_datetime < governing_term_datetime):
        prev_cal_year_terms = solar_data.get(birth_cal_year - 1, {})
        sorted_prev_cal_year_terms = sorted(
            [(name, dt) for name, dt in prev_cal_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
            key=lambda x: x[1]
        )
        for term_name, term_dt in reversed(sorted_prev_cal_year_terms):
             if term_name in ["소한", "대설"] and birth_datetime >= term_dt:
                governing_term_datetime = term_dt
                governing_term_name_for_daewoon = term_name
                break
    
    if not governing_term_datetime or not governing_term_name_for_daewoon:
        return ["오류(대운 절기정보)"], 0
        
    target_term_dt_for_daewoon = None
    current_term_idx_in_saju_order = SAJU_MONTH_TERMS_ORDER.index(governing_term_name_for_daewoon)

    if sunhaeng:
        next_term_saju_idx = (current_term_idx_in_saju_order + 1) % 12
        next_term_name = SAJU_MONTH_TERMS_ORDER[next_term_saju_idx]
        target_term_dt_for_daewoon = cal_year_terms.get(next_term_name)
        if target_term_dt_for_daewoon is None or target_term_dt_for_daewoon <= governing_term_datetime:
            target_term_dt_for_daewoon = solar_data.get(birth_cal_year + 1, {}).get(next_term_name)
    else:
        target_term_dt_for_daewoon = governing_term_datetime

    if not target_term_dt_for_daewoon:
        return ["오류(대운 목표절기)"], 0

    if sunhaeng:
        time_diff_seconds = (target_term_dt_for_daewoon - birth_datetime).total_seconds()
    else: 
        time_diff_seconds = (birth_datetime - target_term_dt_for_daewoon).total_seconds()
    
    days_diff = time_diff_seconds / (24 * 60 * 60)
    if days_diff < 0: days_diff = 0 
    
    daewoon_su = round(days_diff / 3.0)
    if daewoon_su == 0: daewoon_su = 1

    current_gapja_idx = -1
    for i in range(60):
        if GAN[i%10] == month_gan_char and JI[i%12] == month_ji_char:
            current_gapja_idx = i
            break
    if current_gapja_idx == -1: return ["오류(월주->갑자)"], daewoon_su

    for i in range(10): 
        age_at_daewoon_start = daewoon_su + (i * 10)
        if sunhaeng:
            daewoon_gapja_idx = (current_gapja_idx + i + 1) % 60
        else: 
            daewoon_gapja_idx = (current_gapja_idx - (i + 1) + 60*10) % 60

        daewoon_ganji_str = get_ganji_from_index(daewoon_gapja_idx)
        daewoon_pillars.append(f"{age_at_daewoon_start}세: {daewoon_ganji_str}")
        
    return daewoon_pillars, daewoon_su

def get_seun_list(base_analysis_year, count=10):
    result = []
    for i in range(count):
        year_to_calc = base_analysis_year + i
        idx = (year_to_calc - 4) % 60
        ganji_str = get_ganji_from_index(idx)
        result.append((year_to_calc, ganji_str))
    return result

def get_wolun_list(base_analysis_year, base_analysis_month, solar_data, count=12):
    result = []
    for i in range(count):
        current_year_for_wolun = base_analysis_year + (base_analysis_month - 1 + i) // 12
        current_month_for_wolun = (base_analysis_month - 1 + i) % 12 + 1

        seun_idx_for_wolun_year = (current_year_for_wolun - 4) % 60
        seun_gan_char_for_wolun_year = GAN[seun_idx_for_wolun_year % 10]
        
        try:
            wolun_ref_dt = datetime(current_year_for_wolun, current_month_for_wolun, 15)
            governing_term_name = None
            current_year_terms = solar_data.get(current_year_for_wolun, {})
            sorted_terms = sorted(
                [(name, dt_val) for name, dt_val in current_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
                key=lambda x: x[1]
            )
            for term_name, term_dt in sorted_terms:
                if wolun_ref_dt >= term_dt: governing_term_name = term_name
                else: break
            
            if governing_term_name is None or \
               (governing_term_name == "입춘" and wolun_ref_dt < current_year_terms.get("입춘", wolun_ref_dt + timedelta(days=1))):
                prev_year_terms = solar_data.get(current_year_for_wolun - 1, {})
                sorted_prev_year_terms = sorted(
                    [(name, dt_val) for name, dt_val in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
                    key=lambda x: x[1]
                )
                for term_name, term_dt in reversed(sorted_prev_year_terms):
                    if term_name in ["소한", "대설"] and wolun_ref_dt >= term_dt :
                         governing_term_name = term_name; break
            
            if not governing_term_name: wolun_ganji_str = "오류(월운절기)"
            else:
                month_branch_saju_idx = SAJU_MONTH_TERMS_ORDER.index(governing_term_name)
                wolun_month_ji_char = SAJU_MONTH_BRANCHES[month_branch_saju_idx]

                year_gan_idx = GAN.index(seun_gan_char_for_wolun_year)
                start_wolgan_map = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0}
                start_gan_idx_for_inwol = start_wolgan_map.get(year_gan_idx)
                
                if start_gan_idx_for_inwol is None: wolun_ganji_str = "오류(세운연간->월운월간)"
                else:
                    wolun_month_gan_idx = (start_gan_idx_for_inwol + month_branch_saju_idx) % 10
                    wolun_month_gan_char = GAN[wolun_month_gan_idx]
                    wolun_ganji_str = wolun_month_gan_char + wolun_month_ji_char
        except Exception as e:
            wolun_ganji_str = f"계산오류"

        result.append((f"{current_year_for_wolun}-{current_month_for_wolun:02d}", wolun_ganji_str))
    return result

def get_ilun_list(base_analysis_year, base_analysis_month, base_analysis_day, count=10):
    result = []
    start_date = datetime(base_analysis_year, base_analysis_month, base_analysis_day)
    for i in range(count):
        current_date = start_date + timedelta(days=i)
        ganji_str, _, _ = get_day_ganji(current_date.year, current_date.month, current_date.day)
        result.append((current_date.strftime("%Y-%m-%d"), ganji_str))
    return result

st.set_page_config(layout="wide", page_title="종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

st.sidebar.header("1. 절입일 데이터 로딩")
uploaded_file = st.sidebar.file_uploader("절입일 엑셀 파일 업로드 (.xlsx)", type="xlsx")
solar_data_global = None

if uploaded_file:
    solar_data_global = load_solar_terms(uploaded_file)
    if solar_data_global:
        st.sidebar.success("절입일 데이터가 성공적으로 로드되었습니다!")
    else:
        st.sidebar.error("절입일 데이터 로드에 실패했습니다. 메시지를 확인해주세요.")
        st.stop()
else:
    st.info("👈 사이드바에서 절입일 엑셀 파일을 업로드해주세요. 파일 형식은 설명을 참고하세요.")
    st.sidebar.caption("컬럼명 예시: '연도', '절기', '절입일시' 또는 '절입일', '절입시간'")
    st.stop()

st.sidebar.header("2. 개인 정보 입력")
s_y = st.sidebar.number_input("출생 연도 (양력)", min_value=1900, max_value=2100, value=1999)
s_m = st.sidebar.number_input("출생 월 (양력)", min_value=1, max_value=12, value=11)
s_d = st.sidebar.number_input("출생 일 (양력)", min_value=1, max_value=31, value=8)
s_hour = st.sidebar.number_input("출생 시 (0-23시)", min_value=0, max_value=23, value=14)
s_minute = st.sidebar.number_input("출생 분 (0-59분)", min_value=0, max_value=59, value=30)
s_gender = st.sidebar.radio("성별", ("남성", "여성"), index=0, horizontal=True)

st.sidebar.header("3. 운세 기준 시점")
now = datetime.now()
target_y = st.sidebar.number_input("운세 기준 연도", min_value=1900, max_value=2100, value=now.year)
target_m = st.sidebar.number_input("운세 기준 월", min_value=1, max_value=12, value=now.month)
target_d = st.sidebar.number_input("운세 기준 일", min_value=1, max_value=31, value=now.day)

if st.sidebar.button("🧮 계산 실행하기", use_container_width=True, type="primary"):
    if not solar_data_global:
        st.error("절입일 데이터가 로드되지 않았습니다. 파일을 먼저 업로드 해주세요.")
        st.stop()
    
    try:
        birth_datetime_obj = datetime(s_y, s_m, s_d, s_hour, s_minute)
    except ValueError:
        st.error("입력한 생년월일시가 유효하지 않습니다. 다시 확인해주세요.")
        st.stop()

    st.header("📜 사주 명식")
    saju_year_actual = get_saju_year(birth_datetime_obj, solar_data_global)
    year_pillar_str, yp_gan, yp_ji = get_year_ganji(saju_year_actual)
    month_pillar_str, mp_gan, mp_ji = get_month_ganji(yp_gan, birth_datetime_obj, solar_data_global)
    day_pillar_str, dp_gan, dp_ji = get_day_ganji(s_y, s_m, s_d)
    time_pillar_str, tp_gan, tp_ji = get_time_ganji(dp_gan, s_hour, s_minute)

    myeongshik_data = {
        "구분": ["천간(天干)", "지지(地支)", "간지(干支)"],
        "시주(時柱)": [tp_gan if tp_gan else "?", tp_ji if tp_ji else "?", time_pillar_str],
        "일주(日柱)": [dp_gan, dp_ji, day_pillar_str],
        "월주(月柱)": [mp_gan if mp_gan else "?", mp_ji if mp_ji else "?", month_pillar_str],
        "연주(年柱)": [yp_gan, yp_ji, year_pillar_str]
    }
    myeongshik_df = pd.DataFrame(myeongshik_data).set_index("구분")
    st.table(myeongshik_df)
    st.caption(f"사주 기준 연도: {saju_year_actual}년 ({yp_gan}{yp_ji}년)")

    st.header(f"運 대운 ({s_gender})")
    if "오류" in month_pillar_str or not mp_gan or not mp_ji : # 월주 자체에 문제있으면 대운 계산 불가
        st.warning(f"월주 계산 오류로 대운을 계산할 수 없습니다: {month_pillar_str}")
    else:
        daewoon_list, daewoon_start_age = get_daewoon(yp_gan, s_gender, birth_datetime_obj, month_pillar_str, mp_gan, mp_ji, solar_data_global)
        st.subheader(f"대운 시작 나이 (만세력 기준): 약 {daewoon_start_age}세")
        if daewoon_list and not daewoon_list[0].startswith("오류"):
            # 대운 표 개선: DataFrame 사용
            daewoon_ages = [item.split(":")[0] for item in daewoon_list]
            daewoon_ganjis = [item.split(": ")[1] for item in daewoon_list]
            daewoon_output_df = pd.DataFrame({"주기(나이)": daewoon_ages, "간지": daewoon_ganjis})
            st.table(daewoon_output_df)
        else:
            st.error(daewoon_list[0] if daewoon_list else "대운 정보를 가져올 수 없습니다.")
            
    col1, col2 = st.columns(2)
    with col1:
        st.header(f"歲 세운 (기준: {target_y}년)")
        seun_data = get_seun_list(target_y, count=5)
        seun_df = pd.DataFrame(seun_data, columns=["연도", "간지"])
        st.table(seun_df)

        st.header(f"日 일운 (기준: {target_y}년 {target_m}월 {target_d}일)")
        ilun_data = get_ilun_list(target_y, target_m, target_d, count=7)
        ilun_df = pd.DataFrame(ilun_data, columns=["날짜", "간지"])
        st.table(ilun_df)
    with col2:
        st.header(f"月 월운 (기준: {target_y}년 {target_m}월)")
        wolun_data = get_wolun_list(target_y, target_m, solar_data_global, count=12)
        wolun_df = pd.DataFrame(wolun_data, columns=["연월", "간지"])
        st.table(wolun_df)

else:
    st.markdown("""
    ### 사용 방법:
    1.  **절입일 데이터 로딩**: 사이드바에서 절입일 정보가 담긴 엑셀 파일을 업로드합니다.
        * 필수 컬럼: `연도`, `절기`
        * 날짜/시간 정보를 담은 컬럼. 프로그램은 다음 순서로 찾습니다:
            1.  **`절입일`**: 이 컬럼에 `YYYY/MM/DD HH:MM` 또는 `YYYY-MM-DD HH:MM:SS` 같은 **표준 형식의 전체 날짜/시간 문자열**이 있는 것을 최우선으로 합니다. (사용자님의 설명에 따라 이 방식을 1순위로 가정)
            2.  `절입일시`: 위와 같은 표준 형식의 전체 날짜/시간 문자열.
            3.  `절입일` (날짜 부분) + `절입시간` (시간 부분): 두 컬럼을 조합. (이 경우 각 컬럼의 데이터 형식이 중요)
        * **중요**: 사이드바에 **"엑셀에서 읽어온 컬럼명"**이 표시됩니다. 이 목록을 보시고, 실제 날짜/시간 정보가 담긴 컬럼의 이름이 코드 내 `datetime_column_candidate` 변수(`현재 '절입일'`로 설정됨)와 일치하는지, 또는 `절입일시`인지 확인하세요. 다르면 코드 수정이 필요할 수 있습니다.
    2.  **개인 정보 입력**: 출생 연월일시와 성별을 정확히 입력합니다.
    3.  **운세 기준 시점**: 분석하고 싶은 운세의 기준 연월일을 입력합니다.
    4.  **계산 실행하기**: 버튼을 클릭하면 사주 명식과 대운, 세운, 월운, 일운이 표시됩니다.
    """)
