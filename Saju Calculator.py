import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 상수 정의 ---
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# 사주 월주 계산을 위한 12 주요 절기 (입춘부터 시작)
SAJU_MONTH_TERMS_ORDER = [
    "입춘", "경칩", "청명", "입하", "망종", "소서",
    "입추", "백로", "한로", "입동", "대설", "소한"
]
# 위 절기에 해당하는 월지 (月支)
SAJU_MONTH_BRANCHES = ["인", "묘", "진", "사", "오", "미", "신", "유", "술", "해", "자", "축"]

# 시주 계산을 위한 시간대별 지지 (23:30~01:29 자시 기준)
# (시작시간, 종료시간, 지지명, 지지인덱스) - 종료시간은 다음 시간대 시작 바로 전으로 간주
TIME_BRANCH_MAP = [
    ((23, 30), (1, 29), "자", 0), ((1, 30), (3, 29), "축", 1),
    ((3, 30), (5, 29), "인", 2), ((5, 30), (7, 29), "묘", 3),
    ((7, 30), (9, 29), "진", 4), ((9, 30), (11, 29), "사", 5),
    ((11, 30), (13, 29), "오", 6), ((13, 30), (15, 29), "미", 7),
    ((15, 30), (17, 29), "신", 8), ((17, 30), (19, 29), "유", 9),
    ((19, 30), (21, 29), "술", 10), ((21, 30), (23, 29), "해", 11)
]


# --- 절입일 데이터 로딩 및 처리 ---
@st.cache_data # 데이터 캐싱으로 반복 로딩 방지
def load_solar_terms(uploaded_file_obj):
    """
    업로드된 엑셀 파일에서 절입일 데이터를 읽어 딕셔너리로 구성합니다.
    엑셀 파일은 다음 컬럼들을 포함해야 합니다:
    - '연도' (예: 2023)
    - '절기' (예: "입춘", "경칩")
    - 날짜/시간 정보 컬럼:
        1. '절입일시' (예: "2023-02-04 12:50:00" 또는 "2023/02/04 12:50") - 이 컬럼을 우선 사용
        2. 또는 '절입일' (예: "2023-02-04") 과 '절입시간' (예: "12:50:00" 또는 "12:50") 컬럼들을 조합하여 사용
    """
    try:
        solar_terms_df = pd.read_excel(uploaded_file_obj)
        
        #--- 디버깅용: 실제 읽어온 컬럼명 출력 ---
        st.sidebar.subheader("엑셀에서 읽어온 컬럼명:")
        st.sidebar.caption("(아래 이름과 코드 내 기대하는 이름이 일치해야 합니다.)")
        st.sidebar.write(list(solar_terms_df.columns))
        #--------------------------------------

        term_dict = {}
        processed_rows = 0
        skipped_rows = 0

        for _, row in solar_terms_df.iterrows():
            try:
                year = int(row['연도'])
                term_name = str(row['절기']).strip()
                dt_str = None

                # 1. '절입일시' 컬럼 확인 (가장 우선)
                if '절입일시' in solar_terms_df.columns and pd.notna(row.get('절입일시')):
                    dt_str = str(row['절입일시'])
                # 2. '절입일'과 '절입시간' 컬럼 확인
                elif ('절입일' in solar_terms_df.columns and '절입시간' in solar_terms_df.columns and
                      pd.notna(row.get('절입일')) and pd.notna(row.get('절입시간'))):
                    dt_str = str(row['절입일']) + ' ' + str(row['절입시간'])
                
                if dt_str is None:
                    # st.warning(f"Skipping row (데이터 부족): Year {year}, Term {term_name}") # 너무 많은 경고 방지 위해 주석처리
                    skipped_rows +=1
                    continue

                dt = pd.to_datetime(dt_str, errors='coerce')

                if pd.isna(dt):
                    # st.warning(f"Skipping row (날짜변환실패): Year {year}, Term {term_name}, Value: {dt_str}") # 주석처리
                    skipped_rows +=1
                    continue
                
                if year not in term_dict:
                    term_dict[year] = {}
                term_dict[year][term_name] = dt
                processed_rows += 1

            except Exception as e:
                # st.warning(f"Skipping row (처리 중 에러): Year {row.get('연도', 'N/A')}, Term {row.get('절기', 'N/A')}. Error: {e}") # 주석처리
                skipped_rows +=1
                continue
        
        if skipped_rows > 0:
            st.sidebar.warning(f"절입일 데이터 중 {skipped_rows}개 행이 날짜/시간 정보 부족 또는 오류로 인해 건너뛰어졌습니다.")
        if processed_rows == 0 and skipped_rows > 0:
            st.error("절입일 데이터를 전혀 처리하지 못했습니다. 엑셀 파일의 컬럼명('연도', '절기', '절입일시' 또는 '절입일', '절입시간')과 데이터 형식을 확인해주세요.")
            return None
        if not term_dict:
             st.error("절입일 데이터를 불러왔으나, 처리된 내용이 없습니다. 파일 내용을 확인해주세요.")
             return None

        return term_dict
    except Exception as e:
        st.error(f"엑셀 파일 처리 중 심각한 오류 발생: {e}")
        return None

# --- 사주 명식 계산 함수 ---
def get_saju_year(birth_dt, solar_data):
    """ 사주 연도(절입일 기준) 결정 """
    year = birth_dt.year
    ipchun_this_year = solar_data.get(year, {}).get("입춘")
    if ipchun_this_year:
        return year - 1 if birth_dt < ipchun_this_year else year
    # 입춘 데이터 없을 시 fallback (실제로는 발생하면 안됨)
    st.warning(f"{year}년 입춘 데이터 누락. 현재 연도 사용.")
    return year

def get_ganji_from_index(idx):
    """ 0-59 갑자 인덱스로부터 천간지지 문자열 반환 """
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year_num):
    """ 사주 연도의 간지 계산 """
    # 기준: 서기 4년 갑자년 (idx 0). (year - 4) % 60
    idx = (saju_year_num - 4) % 60
    year_gan = GAN[idx % 10]
    year_ji = JI[idx % 12]
    return year_gan + year_ji, year_gan, year_ji

def get_month_ganji(year_gan_char, birth_dt, solar_data):
    """ 사주 월주의 간지 계산 (오호둔법/월건법 사용) """
    birth_year_calendar = birth_dt.year # 양력 생년
    
    governing_term_name = None
    # 현재 양력년도의 절기들 정렬
    current_year_terms = solar_data.get(birth_year_calendar, {})
    sorted_terms = sorted(
        [(name, dt_val) for name, dt_val in current_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for term_name, term_dt in sorted_terms:
        if birth_dt >= term_dt:
            governing_term_name = term_name
        else:
            break # 다음 절기이므로 현재 절기는 이전 것

    # 만약 현재 양력년도에서 절기를 못찾았거나 (예: 1월생인데 아직 입춘 전)
    # 또는 찾은 절기가 해당년도 첫 절기(입춘)인데 생일이 그 절기시간보다 이를 때 (이전 해의 마지막 절기월에 해당)
    if governing_term_name is None or \
       (governing_term_name == "입춘" and birth_dt < current_year_terms.get("입춘", birth_dt + timedelta(days=1))):
        prev_year_terms = solar_data.get(birth_year_calendar - 1, {})
        sorted_prev_year_terms = sorted(
            [(name, dt_val) for name, dt_val in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
            key=lambda x: x[1]
        )
        # 이전 해의 후반부 절기(대설, 소한)에서 찾음
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

    # 오호둔법 (연간에 따른 월건 시작 결정)
    year_gan_idx = GAN.index(year_gan_char)
    start_wolgan_map = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0} # 갑기->병, 을경->무 ...
    start_gan_idx_for_inwol = start_wolgan_map.get(year_gan_idx)

    if start_gan_idx_for_inwol is None:
        return "오류(연간->월간)", "", ""
    
    # SAJU_MONTH_BRANCHES에서 인월(SAJU_MONTH_BRANCHES[0])을 기준으로 월지까지의 거리만큼 월간 진행
    month_gan_idx = (start_gan_idx_for_inwol + month_branch_saju_idx) % 10
    month_gan_char = GAN[month_gan_idx]
    
    return month_gan_char + month_ji_char, month_gan_char, month_ji_char

def get_day_ganji(year, month, day):
    """ 그레고리력 날짜의 일주 간지 계산 """
    # 기준일: 1899년 12월 31일 = 계해일 (간지번호 59)
    # 다음날인 1900년 1월 1일은 갑자일(간지번호 0)이 되어야 함.
    base_dt = datetime(1899, 12, 31)
    target_dt = datetime(year, month, day)
    days_diff = (target_dt - base_dt).days
    ganji_idx = days_diff % 60 # 1일차이가 갑자(0)
    
    day_gan = GAN[ganji_idx % 10]
    day_ji = JI[ganji_idx % 12]
    return day_gan + day_ji, day_gan, day_ji

def get_time_ganji(day_gan_char, birth_hour, birth_minute):
    """ 생시의 간지(시주) 계산 (시두법 사용) """
    siji_char = None
    siji_idx_universal = -1

    current_time_decimal = birth_hour + birth_minute / 60.0

    for (start_h, start_m), (end_h, end_m), ji_name, ji_idx in TIME_BRANCH_MAP:
        start_decimal = start_h + start_m / 60.0
        end_decimal = end_h + end_m / 60.0 # 실제로는 다음 시간대 시작 바로 전

        # 자시(23:30~) 처리: 전날 밤부터 다음날 새벽까지 이어짐
        if ji_name == "자": # 자시는 23:30 ~ 익일 01:29
            if current_time_decimal >= start_decimal or current_time_decimal <= end_decimal:
                siji_char = ji_name
                siji_idx_universal = ji_idx
                break
        elif start_decimal <= current_time_decimal <= end_decimal + 0.001: # 일반적인 시간대 (부동소수점 오차 감안)
             siji_char = ji_name
             siji_idx_universal = ji_idx
             break
    
    if siji_char is None: # TIME_BRANCH_MAP의 마지막 시간대(해시) 이후의 값 처리 (23:29 이후)
        if current_time_decimal > (TIME_BRANCH_MAP[-1][1][0] + TIME_BRANCH_MAP[-1][1][1]/60.0) and \
           current_time_decimal < (24 + TIME_BRANCH_MAP[0][0][0] + TIME_BRANCH_MAP[0][0][1]/60.0) : # 23:29 ~ 23:30 사이의 짧은 간격
            # 이 경우는 자시에 포함될 가능성이 높음 (경계값 처리)
            # 또는, 자시의 시작을 23:00 으로 하면 좀 더 깔끔해짐. 여기서는 현재 정의대로.
            # 만약 정확히 23:29:xx 이면 해시로 가야하는데, 현재 로직상 자시로 갈 수 있음. 자시 시작을 23:30으로 명확히.
            if current_time_decimal >= 23.5: # 23:30 이후면 자시
                siji_char = TIME_BRANCH_MAP[0][2]
                siji_idx_universal = TIME_BRANCH_MAP[0][3]


    if not siji_char:
        return "오류(시지)", "", ""

    # 시두법 (일간에 따른 시건 시작 결정)
    day_gan_idx = GAN.index(day_gan_char)
    # 일간 갑기 -> 자시의 천간은 갑 (0)
    # 일간 을경 -> 자시의 천간은 병 (2)
    # 일간 병신 -> 자시의 천간은 무 (4)
    # 일간 정임 -> 자시의 천간은 경 (6)
    # 일간 무계 -> 자시의 천간은 임 (8)
    start_sigan_map = {0:0, 5:0, 1:2, 6:2, 2:4, 7:4, 3:6, 8:6, 4:8, 9:8}
    start_gan_idx_for_jasi = start_sigan_map.get(day_gan_idx)

    if start_gan_idx_for_jasi is None:
        return "오류(일간->시간)", "", ""
    
    time_gan_idx = (start_gan_idx_for_jasi + siji_idx_universal) % 10
    time_gan_char = GAN[time_gan_idx]
    
    return time_gan_char + siji_char, time_gan_char, siji_char

# --- 대운, 세운, 월운, 일운 계산 함수 ---
def get_daewoon(year_gan_char, gender, birth_datetime, month_ganji_str, month_gan_char, month_ji_char, solar_data):
    """ 대운 계산 """
    daewoon_pillars = []
    
    # 1. 순행/역행 결정
    is_yang_year = GAN.index(year_gan_char) % 2 == 0 # 갑병무경임 = 양간
    sunhaeng = (is_yang_year and gender == "남성") or (not is_yang_year and gender == "여성")

    # 2. 생월의 절입일시 찾기
    birth_cal_year = birth_datetime.year
    governing_term_datetime = None
    governing_term_name_for_daewoon = None

    # 현재년도 절기 검색
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
    
    # 만약 현재년도에서 못찾았거나 입춘보다 생일이 이르면 (이전해 절기월)
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
        
    # 3. 다음/이전 절기 찾기
    target_term_dt_for_daewoon = None
    current_term_idx_in_saju_order = SAJU_MONTH_TERMS_ORDER.index(governing_term_name_for_daewoon)

    if sunhaeng: # 순행: 다음 절기
        next_term_saju_idx = (current_term_idx_in_saju_order + 1) % 12
        next_term_name = SAJU_MONTH_TERMS_ORDER[next_term_saju_idx]
        # 다음 절기는 현재년도 또는 다음년도에 있을 수 있음
        target_term_dt_for_daewoon = cal_year_terms.get(next_term_name)
        if target_term_dt_for_daewoon is None or target_term_dt_for_daewoon <= governing_term_datetime: # 다음해 입춘 등
            target_term_dt_for_daewoon = solar_data.get(birth_cal_year + 1, {}).get(next_term_name)
    else: # 역행: 현재 월의 시작 절기 (이미 찾은 governing_term_datetime)
        target_term_dt_for_daewoon = governing_term_datetime

    if not target_term_dt_for_daewoon:
        return ["오류(대운 목표절기)"], 0

    # 4. 대운수 계산
    if sunhaeng:
        time_diff_seconds = (target_term_dt_for_daewoon - birth_datetime).total_seconds()
    else: # 역행
        time_diff_seconds = (birth_datetime - target_term_dt_for_daewoon).total_seconds()
    
    days_diff = time_diff_seconds / (24 * 60 * 60)
    if days_diff < 0: days_diff = 0 # 혹시 모를 음수 방지
    
    daewoon_su = round(days_diff / 3.0)
    if daewoon_su == 0: daewoon_su = 1 # 또는 10 (관례) - 여기선 1로

    # 5. 대운 간지 나열
    birth_month_gan_idx = GAN.index(month_gan_char)
    birth_month_ji_idx = JI.index(month_ji_char)
    
    # 월주 간지의 60갑자 인덱스 찾기
    current_gapja_idx = -1
    for i in range(60):
        if GAN[i%10] == month_gan_char and JI[i%12] == month_ji_char:
            current_gapja_idx = i
            break
    if current_gapja_idx == -1: return ["오류(월주->갑자)"], daewoon_su

    for i in range(10): # 10개 대운 표시 (100년)
        age_at_daewoon_start = daewoon_su + (i * 10)
        if sunhaeng:
            daewoon_gapja_idx = (current_gapja_idx + i + 1) % 60
        else: # 역행
            daewoon_gapja_idx = (current_gapja_idx - (i + 1) + 60*10) % 60 # 큰 수를 더해 음수 인덱스 방지

        daewoon_ganji_str = get_ganji_from_index(daewoon_gapja_idx)
        daewoon_pillars.append(f"{age_at_daewoon_start}세: {daewoon_ganji_str}")
        
    return daewoon_pillars, daewoon_su


def get_seun_list(base_analysis_year, count=10):
    """ 해당 년도부터 시작하는 세운 목록 반환 """
    result = []
    for i in range(count):
        year_to_calc = base_analysis_year + i
        idx = (year_to_calc - 4) % 60
        ganji_str = get_ganji_from_index(idx)
        result.append((year_to_calc, ganji_str))
    return result

def get_wolun_list(base_analysis_year, base_analysis_month, solar_data, count=12):
    """ 해당 년월부터 시작하는 월운 목록 반환. 월건은 세운의 연간을 따름. """
    result = []
    for i in range(count):
        current_year_for_wolun = base_analysis_year + (base_analysis_month - 1 + i) // 12
        current_month_for_wolun = (base_analysis_month - 1 + i) % 12 + 1

        # 현재 월운을 계산할 해(current_year_for_wolun)의 세운 연간을 가져옴
        seun_idx_for_wolun_year = (current_year_for_wolun - 4) % 60
        seun_gan_char_for_wolun_year = GAN[seun_idx_for_wolun_year % 10]
        
        # 월운의 간지를 계산하기 위해 해당 월의 15일을 기준으로 get_month_ganji와 유사한 로직 사용
        # 단, 연간은 'seun_gan_char_for_wolun_year'를 사용
        try:
            # 월운 계산시 월의 대표날짜(예:15일)를 사용해 해당월의 절기를 찾음
            wolun_ref_dt = datetime(current_year_for_wolun, current_month_for_wolun, 15)
            
            # get_month_ganji와 동일한 로직으로 월지 찾기
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

                # 오호둔법 적용 (연간 = 현재 세운의 연간)
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
    """ 해당 일자부터 시작하는 일운 목록 반환 """
    result = []
    start_date = datetime(base_analysis_year, base_analysis_month, base_analysis_day)
    for i in range(count):
        current_date = start_date + timedelta(days=i)
        ganji_str, _, _ = get_day_ganji(current_date.year, current_date.month, current_date.day)
        result.append((current_date.strftime("%Y-%m-%d"), ganji_str))
    return result

# --- Streamlit UI 구성 ---
st.set_page_config(layout="wide", page_title="종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

# 사이드바: 절입일 파일 업로드
st.sidebar.header("1. 절입일 데이터 로딩")
uploaded_file = st.sidebar.file_uploader("절입일 엑셀 파일 업로드 (.xlsx)", type="xlsx")
solar_data_global = None # 전역적으로 사용할 solar_data

if uploaded_file:
    solar_data_global = load_solar_terms(uploaded_file)
    if solar_data_global:
        st.sidebar.success("절입일 데이터가 성공적으로 로드되었습니다!")
    else:
        st.sidebar.error("절입일 데이터 로드에 실패했습니다. 메시지를 확인해주세요.")
        st.stop() # 데이터 로드 실패시 중단
else:
    st.info("👈 사이드바에서 절입일 엑셀 파일을 업로드해주세요. 파일 형식은 설명을 참고하세요.")
    st.sidebar.caption("컬럼명 예시: '연도', '절기', '절입일시' 또는 '절입일', '절입시간'")
    st.stop()


# 사이드바: 생년월일시 및 성별 입력
st.sidebar.header("2. 개인 정보 입력")
s_y = st.sidebar.number_input("출생 연도 (양력)", min_value=1900, max_value=2100, value=1999)
s_m = st.sidebar.number_input("출생 월 (양력)", min_value=1, max_value=12, value=11)
s_d = st.sidebar.number_input("출생 일 (양력)", min_value=1, max_value=31, value=8)
s_hour = st.sidebar.number_input("출생 시 (0-23시)", min_value=0, max_value=23, value=14) # 예: 오후 2시
s_minute = st.sidebar.number_input("출생 분 (0-59분)", min_value=0, max_value=59, value=30)
s_gender = st.sidebar.radio("성별", ("남성", "여성"), index=0)

# 사이드바: 운세 기준 시점 입력
st.sidebar.header("3. 운세 기준 시점")
now = datetime.now()
target_y = st.sidebar.number_input("운세 기준 연도", min_value=1900, max_value=2100, value=now.year)
target_m = st.sidebar.number_input("운세 기준 월", min_value=1, max_value=12, value=now.month)
target_d = st.sidebar.number_input("운세 기준 일", min_value=1, max_value=31, value=now.day)

if st.sidebar.button("🧮 계산 실행하기", use_container_width=True):
    if not solar_data_global:
        st.error("절입일 데이터가 로드되지 않았습니다. 파일을 먼저 업로드 해주세요.")
        st.stop()
    
    try:
        birth_datetime_obj = datetime(s_y, s_m, s_d, s_hour, s_minute)
    except ValueError:
        st.error("입력한 생년월일시가 유효하지 않습니다. 다시 확인해주세요.")
        st.stop()

    # --- 1. 사주 명식 (Four Pillars) ---
    st.header("📜 사주 명식")
    saju_year_actual = get_saju_year(birth_datetime_obj, solar_data_global)
    year_pillar_str, yp_gan, yp_ji = get_year_ganji(saju_year_actual)
    month_pillar_str, mp_gan, mp_ji = get_month_ganji(yp_gan, birth_datetime_obj, solar_data_global)
    day_pillar_str, dp_gan, dp_ji = get_day_ganji(s_y, s_m, s_d)
    time_pillar_str, tp_gan, tp_ji = get_time_ganji(dp_gan, s_hour, s_minute)

    myeongshik_data = {
        "구분": ["천간(天干)", "지지(地支)", "간지(干支)"],
        "시주(時柱)": [tp_gan, tp_ji, time_pillar_str],
        "일주(日柱)": [dp_gan, dp_ji, day_pillar_str],
        "월주(月柱)": [mp_gan, mp_ji, month_pillar_str],
        "연주(年柱)": [yp_gan, yp_ji, year_pillar_str]
    }
    myeongshik_df = pd.DataFrame(myeongshik_data).set_index("구분")
    st.table(myeongshik_df)
    st.caption(f"사주 기준 연도: {saju_year_actual}년 ({yp_gan}{yp_ji}년)")

    # --- 2. 대운 (Great Luck Cycle) ---
    st.header(f"運 대운 ({s_gender})")
    if "오류" in month_pillar_str:
        st.warning(f"월주 계산 오류로 대운을 계산할 수 없습니다: {month_pillar_str}")
    else:
        daewoon_list, daewoon_start_age = get_daewoon(yp_gan, s_gender, birth_datetime_obj, month_pillar_str, mp_gan, mp_ji, solar_data_global)
        st.subheader(f"대운 시작 나이: 약 {daewoon_start_age}세")
        if daewoon_list and not daewoon_list[0].startswith("오류"):
            cols = st.columns(len(daewoon_list) if len(daewoon_list) <= 5 else 5) # 한 줄에 최대 5개
            for i, pillar_info in enumerate(daewoon_list):
                age, ganji = pillar_info.split(": ")
                with cols[i % len(cols)]:
                    st.metric(label=age, value=ganji)
        else:
            st.error(daewoon_list[0] if daewoon_list else "대운 정보를 가져올 수 없습니다.")

    # --- 3. 세운 (Annual Luck) ---
    st.header(f"歲 세운 (기준: {target_y}년)")
    seun_data = get_seun_list(target_y, count=5) # 5년치 표시
    seun_df = pd.DataFrame(seun_data, columns=["연도", "간지"])
    st.table(seun_df)

    # --- 4. 월운 (Monthly Luck) ---
    st.header(f"月 월운 (기준: {target_y}년 {target_m}월)")
    wolun_data = get_wolun_list(target_y, target_m, solar_data_global, count=12) # 12개월치 표시
    wolun_df = pd.DataFrame(wolun_data, columns=["연월", "간지"])
    st.table(wolun_df)
    
    # --- 5. 일운 (Daily Luck) ---
    st.header(f"日 일운 (기준: {target_y}년 {target_m}월 {target_d}일)")
    ilun_data = get_ilun_list(target_y, target_m, target_d, count=7) # 7일치 표시
    ilun_df = pd.DataFrame(ilun_data, columns=["날짜", "간지"])
    st.table(ilun_df)

else:
    st.markdown("""
    ### 사용 방법:
    1.  **절입일 데이터 로딩**: 사이드바에서 절입일 정보가 담긴 엑셀 파일을 업로드합니다.
        * 필수 컬럼: `연도`, `절기`
        * 날짜/시간 컬럼 (둘 중 하나):
            * `절입일시` (예: `2023-02-04 17:03:00`)
            * `절입일` (예: `2023-02-04`) 및 `절입시간` (예: `17:03:00`)
        * 컬럼명 오류시 사이드바에 Pandas가 읽은 실제 컬럼명이 표시되니 참고하여 수정하세요.
    2.  **개인 정보 입력**: 출생 연월일시와 성별을 정확히 입력합니다.
    3.  **운세 기준 시점**: 분석하고 싶은 운세의 기준 연월일을 입력합니다.
    4.  **계산 실행하기**: 버튼을 클릭하면 사주 명식과 대운, 세운, 월운, 일운이 표시됩니다.
    """)
