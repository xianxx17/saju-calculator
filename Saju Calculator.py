import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- Constants ---
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# 12 Major Solar Terms (Jeolgi) that define Saju month boundaries
# Their order is critical.
SAJU_MONTH_TERMS_ORDER = [
    "입춘", "경칩", "청명", "입하", "망종", "소서",
    "입추", "백로", "한로", "입동", "대설", "소한"
]
# Corresponding Earthly Branches for Saju months
SAJU_MONTH_BRANCHES = ["인", "묘", "진", "사", "오", "미", "신", "유", "술", "해", "자", "축"]


# --- File Upload and Solar Term Dictionary ---
# Memoize to avoid reloading and reprocessing the Excel file on every rerun
@st.cache_data
def load_solar_terms(uploaded_file_path):
    try:
        solar_terms_df = pd.read_excel(uploaded_file_path)
        term_dict = {}
        for _, row in solar_terms_df.iterrows():
            year = int(row['연도'])
            name = str(row['절기']).strip()
            try:
                # Handle potential full datetime string or separate date/time
                if '절입일시' in row and pd.notna(row['절입일시']):
                    dt_str = str(row['절입일시'])
                elif '절입일' in row and '절입시간' in row and pd.notna(row['절입일']) and pd.notna(row['절입시간']):
                    dt_str = str(row['절입일']) + ' ' + str(row['절입시간'])
                else:
                    st.warning(f"Skipping row due to missing date/time: Year {year}, Term {name}")
                    continue

                dt = pd.to_datetime(dt_str, errors='coerce')
                if pd.isna(dt):
                    st.warning(f"Could not parse date for: Year {year}, Term {name}, Value: {dt_str}")
                    continue

            except Exception as e:
                st.warning(f"Error parsing date for: Year {year}, Term {name}, Value: {dt_str}. Error: {e}")
                continue

            if year not in term_dict:
                term_dict[year] = {}
            term_dict[year][name] = dt
        return term_dict
    except Exception as e:
        st.error(f"Failed to load or process the Excel file: {e}")
        return None

uploaded_file = st.file_uploader("절입일 데이터 파일 업로드 (.xlsx)", type="xlsx")
solar_dict = None
if uploaded_file:
    # To avoid issues with temporary file paths in Streamlit, save it temporarily
    # This part might need adjustment depending on Streamlit's execution environment
    # For simplicity here, assuming direct read if it works, otherwise save and read.
    try:
        solar_dict = load_solar_terms(uploaded_file)
        if solar_dict:
            st.success("절입일 데이터가 성공적으로 불러와졌습니다!")
        else:
            st.error("절입일 데이터 파일은 불러왔으나, 내용 처리 중 오류가 발생했습니다.")
            st.stop()
    except Exception as e:
        st.error(f"파일 처리 중 오류: {e}")
        st.stop()
else:
    st.info("사주 계산을 위해 '절입일_1905_2100.xlsx'와 같은 형식의 절입일 데이터 파일을 업로드해주세요.")
    st.stop()


# --- Core Saju Calculation Functions ---

def get_saju_year(birth_dt, solar_terms_data):
    """Determines the Saju year based on Ipchun (입춘)."""
    year = birth_dt.year
    ipchun_this_year = solar_terms_data.get(year, {}).get("입춘")

    if ipchun_this_year:
        if birth_dt < ipchun_this_year:
            return year - 1
        else:
            return year
    else:
        # Fallback if Ipchun data is missing for the year (should ideally not happen with good data)
        # This is a simplification; robust handling might check previous year's 소한/대한
        st.warning(f"{year}년 입춘 데이터가 없어 정확한 연주 계산이 어려울 수 있습니다. 현재 연도를 사용합니다.")
        return year

def get_year_ganji(saju_year):
    """Calculates the Gan-Ji for the Saju Year."""
    # (Year - 3) % 60 is a common way if year 4 AD (갑자년) is index 1.
    # Or (Year - 4) % 60 if year 4 AD is index 0.
    # Let's use the common (year_index % 10 for Gan, year_index % 12 for Ji)
    # 1864 was GapJa (갑자). 1864 % 60 = 4. So, reference index is 4.
    # (saju_year - 1864) results in 0 for 1864.
    idx = (saju_year - 4) % 60  # Adjust if your reference is different
    gan = GAN[idx % 10]
    ji = JI[idx % 12]
    return gan + ji, gan, ji

def get_month_ganji(saju_year_gan_char, birth_dt, solar_terms_data):
    """Calculates the Gan-Ji for the Saju Month."""
    birth_year = birth_dt.year
    
    # Determine the governing solar term for the birth month
    current_month_term_name = None
    current_month_term_date = None

    # Check terms in the birth year
    year_terms = solar_terms_data.get(birth_year, {})
    # Sort terms by date to ensure correct processing
    sorted_year_terms = sorted(
        [(name, date) for name, date in year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )

    for term_name, term_date in sorted_year_terms:
        if birth_dt >= term_date:
            current_month_term_name = term_name
            current_month_term_date = term_date # Keep track of the actual term date
        else:
            # Birth date is before this term, so the previous term applies
            break
    
    # If no term found in current year (e.g., birth in Jan before Ipchun)
    # or if birth_dt is before the first Saju month term of its calendar year,
    # check previous year's later terms (e.g. 소한, 대한 for 자월, 축월)
    if current_month_term_name is None or \
       (current_month_term_name == "입춘" and birth_dt < current_month_term_date):
        prev_year_terms = solar_terms_data.get(birth_year - 1, {})
        sorted_prev_year_terms = sorted(
            [(name, date) for name, date in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
            key=lambda x: x[1]
        )
        # Look for 소한 (Sohan) or 대설 (Daeseol) from previous year
        for term_name, term_date in reversed(sorted_prev_year_terms):
            if term_name in ["소한", "대설"] and birth_dt >= term_date: # Check against actual birth_dt
                current_month_term_name = term_name
                current_month_term_date = term_date
                break
    
    if not current_month_term_name:
        return "월주 정보 없음 (절기 부족)", "", ""

    # Determine Month Branch (월지)
    try:
        month_branch_index = SAJU_MONTH_TERMS_ORDER.index(current_month_term_name)
        month_ji_char = SAJU_MONTH_BRANCHES[month_branch_index]
    except ValueError:
        return f"월주 정보 없음 ({current_month_term_name} 절기 순서 오류)", "", ""

    # Determine Month Stem (월간) using 오호둔법 (Ohodunbeop / Wolgeonbeop)
    # Year Stem: 갑기(0,5) -> 병(2) / 을경(1,6) -> 무(4) / 병신(2,7) -> 경(6) / 정임(3,8) -> 임(8) / 무계(4,9) -> 갑(0)
    # The starting stem is for 인월 (Inwol - Tiger month).
    year_gan_idx = GAN.index(saju_year_gan_char)
    
    if year_gan_idx == 0 or year_gan_idx == 5: # 갑, 기
        start_gan_idx = 2 # 병
    elif year_gan_idx == 1 or year_gan_idx == 6: # 을, 경
        start_gan_idx = 4 # 무
    elif year_gan_idx == 2 or year_gan_idx == 7: # 병, 신
        start_gan_idx = 6 # 경
    elif year_gan_idx == 3 or year_gan_idx == 8: # 정, 임
        start_gan_idx = 8 # 임
    elif year_gan_idx == 4 or year_gan_idx == 9: # 무, 계
        start_gan_idx = 0 # 갑
    else:
        return "월간 계산 오류 (연간)", "", ""

    # 인월 is the 0th index for SAJU_MONTH_BRANCHES when aligned with SAJU_MONTH_TERMS_ORDER starting 입춘
    # 인(Tiger) month branch index in JI array is 2.
    # We need the index of month_ji_char within the standard JI array to cycle correctly
    # Example: 인월 is the first Saju month. If start_gan_idx is 병(2), then 인월은 병인.
    # 묘월 (next Saju month) will be 정묘.
    
    # month_branch_index is the index from SAJU_MONTH_BRANCHES (0 for 인, 1 for 묘, ...)
    month_gan_idx = (start_gan_idx + SAJU_MONTH_BRANCHES.index(month_ji_char)) % 10
    month_gan_char = GAN[month_gan_idx]

    return month_gan_char + month_ji_char, month_gan_char, month_ji_char


def get_day_ganji(y, m, d):
    """Calculates the Gan-Ji for a given gregorian date."""
    # 갑자일 기준: 1899년 12월 22일 (동지) 또는 다른 알려진 갑자일
    # 더 간단한 방법: 1900년 1월 1일은 경자일 (36번째 간지)
    # 기준일: 1899년 12월 31일 (일요일)은 계해일 (59번째, 마지막 간지)
    # (target - base).days 계산 시, base 다음날이 0번째 간지(갑자)가 되도록 기준일 설정.
    # 0001-01-01은 갑신일. (idx 0)
    # Or use a known reference date and its GanJi index
    # For example, 2000-01-01 was 경진 (Gyeongjin), index 16 in 0-59 cycle.
    
    # Using Julian Day Number (JDN) method is most robust for GanJi calculation over long periods.
    # Simplified approach: days since a known GanJi date.
    # Let's use a reference: 1900-01-01 was 경자일 (Gyeongja, index 36: GAN[6], JI[0])
    # However, the original code used 1899-12-31 as 계해일. Let's stick to that.
    # 계해일 index is 59 (GAN[9], JI[11]).
    # The day after 계해일 (1900-01-01) should be 갑자일 (index 0).
    
    base_date = datetime(1899, 12, 31) # This was 계해 (Kyehae), index 59
    target_date = datetime(y, m, d)
    delta_days = (target_date - base_date).days
    
    # delta_days = 1 means the day after 계해, which is 갑자 (index 0)
    # So, (delta_days -1) % 60 would be the 0-indexed GanJi.
    # Or, idx = delta_days % 60. If base is index 59, then delta_days=1 is 60 % 60 = 0 (Gapja)
    # This seems to align with how many GanJi calculators work.
    
    ganji_idx = delta_days % 60 # 0 for Gapja, 1 for Eulchuk ... 59 for Gyehae
    
    gan = GAN[ganji_idx % 10]
    ji = JI[ganji_idx % 12]
    return gan + ji, gan, ji

# --- Luck Cycle Functions ---
def get_seun_list(base_analysis_y, count=10):
    """Calculates annual luck (Seun) for 'count' years starting from base_analysis_y."""
    result = []
    for i in range(count):
        year_to_calc = base_analysis_y + i
        # Year GanJi calculation is same as Saju Year GanJi
        idx = (year_to_calc - 4) % 60 # Assuming year 4 AD = Gapja (index 0)
        gan = GAN[idx % 10]
        ji = JI[idx % 12]
        result.append((year_to_calc, gan + ji))
    return result

def get_wolun_list(saju_year_gan_for_wolun_calc, base_analysis_y, base_analysis_m, count=12):
    """
    Calculates monthly luck (Wolun).
    Note: Wolun calculation often uses the Seun's (annual luck) year stem.
    For simplicity, here we'll use the birth Saju Year Gan for the 월건법.
    A more advanced version would use the specific Seun's year stem for each year's Wolun.
    """
    result = []
    # For Wolun, the "year stem" used in Ohodunbeop is typically the stem of the *current Seun (annual luck pillar)*.
    # For simplicity in this example, we'll use the provided saju_year_gan_for_wolun_calc.
    # In a full system, you'd get the Seun for base_analysis_y, use its stem.

    # Find the Gan of the base_analysis_y (this is the Seun's Gan for that year)
    seun_idx_for_wolun_year = (base_analysis_y - 4) % 60
    seun_gan_for_wolun_year = GAN[seun_idx_for_wolun_year % 10]


    for i in range(count):
        current_year = base_analysis_y + (base_analysis_m - 1 + i) // 12
        current_month = (base_analysis_m - 1 + i) % 12 + 1

        # When year changes for Wolun, the Seun's Gan used for Ohodunbeop should also change
        if current_year != base_analysis_y and (base_analysis_m - 1 + i) % 12 == 0 : # if month is January of a new year
            seun_idx_for_wolun_year = (current_year - 4) % 60
            seun_gan_for_wolun_year = GAN[seun_idx_for_wolun_year % 10]

        # We need a representative date within that month to find the governing solar term.
        # Using the 15th is generally safe, but Wolun month changes exactly at solar terms.
        # A more precise Wolun would calculate specific start/end dates for each Wolun month.
        # Here, we simulate getting the Saju month for the 15th of that calendar month.
        # This simplification assumes Wolun months align with Saju birth months.
        
        # Create a datetime object for the 15th of the current_year, current_month
        # to pass to get_month_ganji.
        # The `get_month_ganji` function expects a full datetime object.
        # For Wolun, the day itself doesn't influence the month's GanJi, only the solar term boundary.
        # The critical part is that `get_month_ganji` uses the `seun_gan_for_wolun_year`
        
        # Simplified: Use the `get_month_ganji` structure but pass the SEUN's year stem.
        # This is because 월운의 월건은 그 해 세운의 연간을 기준으로 정해짐.
        try:
            # For Wolun, the day part is not critical for month GanJi, usually 1st or 15th is fine
            # as long as get_month_ganji correctly finds the solar term.
            # The `solar_dict` is used by `get_month_ganji` to find the term.
            wolun_month_dt = datetime(current_year, current_month, 15) # Use 15th as representative
            # Call a modified get_month_ganji or replicate logic with seun_gan_for_wolun_year
            
            # Replicating relevant part of get_month_ganji logic for Wolun:
            # 1. Find the Saju month branch for wolun_month_dt
            current_wolun_month_term_name = None
            year_terms = solar_dict.get(current_year, {})
            sorted_year_terms = sorted(
                [(name, date) for name, date in year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
                key=lambda x: x[1]
            )
            for term_name, term_date in sorted_year_terms:
                if wolun_month_dt >= term_date:
                    current_wolun_month_term_name = term_name
                else:
                    break
            if not current_wolun_month_term_name: # Check previous year for Jan dates before Ipchun
                 prev_year_terms = solar_dict.get(current_year - 1, {})
                 sorted_prev_year_terms = sorted(
                    [(name, date) for name, date in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
                    key=lambda x: x[1]
                )
                 for term_name, term_date in reversed(sorted_prev_year_terms):
                    if term_name in ["소한", "대설"] and wolun_month_dt >= term_date:
                        current_wolun_month_term_name = term_name
                        break
            
            if not current_wolun_month_term_name:
                ganji_str = "정보 없음(월운 절기)"
            else:
                month_branch_idx_in_saju_terms = SAJU_MONTH_TERMS_ORDER.index(current_wolun_month_term_name)
                wolun_month_ji_char = SAJU_MONTH_BRANCHES[month_branch_idx_in_saju_terms]

                # 2. Calculate Wolun Month Stem using seun_gan_for_wolun_year
                year_gan_idx = GAN.index(seun_gan_for_wolun_year)
                if year_gan_idx == 0 or year_gan_idx == 5: start_gan_idx = 2
                elif year_gan_idx == 1 or year_gan_idx == 6: start_gan_idx = 4
                elif year_gan_idx == 2 or year_gan_idx == 7: start_gan_idx = 6
                elif year_gan_idx == 3 or year_gan_idx == 8: start_gan_idx = 8
                elif year_gan_idx == 4 or year_gan_idx == 9: start_gan_idx = 0
                else: raise ValueError("Invalid Seun Gan")

                wolun_month_gan_idx = (start_gan_idx + SAJU_MONTH_BRANCHES.index(wolun_month_ji_char)) % 10
                wolun_month_gan_char = GAN[wolun_month_gan_idx]
                ganji_str = wolun_month_gan_char + wolun_month_ji_char
        except Exception as e:
            # st.error(f"Error in Wolun calc for {current_year}-{current_month:02d}: {e}")
            ganji_str = "계산 오류"

        result.append((f"{current_year}-{current_month:02d}", ganji_str))
    return result


def get_ilun_list(base_analysis_y, base_analysis_m, base_analysis_d, count=10):
    """Calculates daily luck (Ilun) for 'count' days."""
    result = []
    start_date = datetime(base_analysis_y, base_analysis_m, base_analysis_d)
    for i in range(count):
        current_date = start_date + timedelta(days=i)
        ganji_str, _, _ = get_day_ganji(current_date.year, current_date.month, current_date.day)
        result.append((current_date.strftime("%Y-%m-%d"), ganji_str))
    return result

def get_daewoon(year_ganji_str, year_ji_char, gender, birth_datetime, month_ganji_str, solar_terms_data):
    """
    Calculates Daewoon (Great Luck Cycles). THIS IS A COMPLEX FUNCTION.
    Placeholder for Daewoon calculation logic.
    """
    # 1. Determine Sunhaeng (순행) or Yeokhaeng (역행)
    #    - Yang Year Stem (갑병무경임) + Male OR Yin Year Stem (을정기신계) + Female => Sunhaeng
    #    - Yang Year Stem + Female OR Yin Year Stem + Male => Yeokhaeng
    year_gan_char = year_ganji_str[0]
    is_yang_year = GAN.index(year_gan_char) % 2 == 0 # 갑=0, 을=1 ...

    sunhaeng = (is_yang_year and gender == "남성") or (not is_yang_year and gender == "여성")

    # 2. Find birth month's governing solar term (Jeolgi)
    birth_saju_year = get_saju_year(birth_datetime, solar_terms_data) # Saju year for context
    # We need the *exact* datetime of the solar term that started the birth month.
    # This was partially done in get_month_ganji, but we need that specific term's datetime.
    
    current_month_term_name = None
    current_month_term_datetime = None # This is what we need
    
    # Search in birth_datetime.year
    year_terms = solar_terms_data.get(birth_datetime.year, {})
    sorted_year_terms = sorted(
        [(name, date) for name, date in year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    )
    for term_name, term_dt_val in sorted_year_terms:
        if birth_datetime >= term_dt_val:
            current_month_term_name = term_name
            current_month_term_datetime = term_dt_val
        else:
            # This term_dt_val is the NEXT major solar term if sunhaeng
            # Or current_month_term_datetime is PREVIOUS major solar term if yeokhaeng
            break 
            
    # If birth was in Jan before Ipchun, the governing term is from previous year (e.g. 소한, 대한)
    if current_month_term_name is None or \
       (current_month_term_name == "입춘" and birth_datetime < current_month_term_datetime):
        prev_year_terms = solar_terms_data.get(birth_datetime.year - 1, {})
        sorted_prev_year_terms = sorted(
            [(name, date) for name, date in prev_year_terms.items() if name in SAJU_MONTH_TERMS_ORDER],
            key=lambda x: x[1]
        )
        for term_name, term_dt_val in reversed(sorted_prev_year_terms): # Check 소한, 대한
            if term_name in ["소한", "대설"] and birth_datetime >= term_dt_val:
                current_month_term_name = term_name
                current_month_term_datetime = term_dt_val
                break
    
    if not current_month_term_datetime or not current_month_term_name:
        return ["대운 계산 불가: 월 절기 정보를 찾을 수 없습니다."], 0

    # 3. Find next/previous Jeolgi
    target_jeolgi_dt = None
    if sunhaeng: # 순행: 다음 절기까지의 날짜
        # Find the index of current_month_term_name in SAJU_MONTH_TERMS_ORDER
        current_term_idx = SAJU_MONTH_TERMS_ORDER.index(current_month_term_name)
        next_term_idx = (current_term_idx + 1) % 12
        next_term_name = SAJU_MONTH_TERMS_ORDER[next_term_idx]
        
        # Find this next_term_name's datetime. It could be in the same year or next year.
        if next_term_name in year_terms:
             target_jeolgi_dt = year_terms[next_term_name]
        # If next term is 입춘, it might be in the next year's data.
        if next_term_name == "입춘" and (target_jeolgi_dt is None or target_jeolgi_dt <= current_month_term_datetime) :
             target_jeolgi_dt = solar_terms_data.get(birth_datetime.year + 1, {}).get(next_term_name)

    else: # 역행: 이전 절기(현재 월의 시작 절기)까지의 날짜
        target_jeolgi_dt = current_month_term_datetime # This IS the previous (or current start) Jeolgi

    if not target_jeolgi_dt:
        return ["대운 계산 불가: 다음/이전 절기 정보를 찾을 수 없습니다."], 0

    # 4. Calculate Daewoon number (대운수)
    time_diff_seconds = 0
    if sunhaeng:
        if birth_datetime > target_jeolgi_dt: # Should not happen if target_jeolgi_dt is truly the *next*
             # This can happen if 입춘 is the next term, and it's for next year, but birth is AFTER current year's 입춘.
             # It means current_month_term_name was like "소한" and next is "입춘" of the same calendar year.
             # If target_jeolgi_dt is earlier due to year wrap or data issue, needs careful check
             st.warning(f"Sunhaeng Daewoon: Birth datetime {birth_datetime} seems after next Jeolgi {target_jeolgi_dt}. Check logic.")
             # Defaulting to a large diff to avoid negative, but this indicates an issue.
             time_diff_seconds = abs((target_jeolgi_dt.replace(year=target_jeolgi_dt.year + 1) - birth_datetime).total_seconds())

        else:
            time_diff_seconds = (target_jeolgi_dt - birth_datetime).total_seconds()
    else: # Yeokhaeng
        time_diff_seconds = (birth_datetime - target_jeolgi_dt).total_seconds()

    days_diff = time_diff_seconds / (24 * 60 * 60)
    daewoon_su = round(days_diff / 3)
    if daewoon_su == 0 : daewoon_su = 1 # 관례적으로 0이면 1로 혹은 10으로 봄 (여기선 1로)


    # 5. Calculate Daewoon pillars
    daewoon_pillars = []
    # First Daewoon starts from the month pillar, then progresses
    # month_ganji_str is the birth month pillar
    # Find its index in the 60 Gapja cycle
    
    # Convert birth month GanJi to index
    birth_month_gan = month_ganji_str[0]
    birth_month_ji = month_ganji_str[1]
    
    # This is tricky as Gan and Ji cycle independently to make the 60 combo.
    # A direct lookup or a function to convert GanJi string to its 0-59 index is better.
    current_gan_idx = GAN.index(birth_month_gan)
    current_ji_idx = JI.index(birth_month_ji)

    # Finding the combined index (0-59) from Gan and Ji indices
    # This formula works: result = j; while(GAN[result % 10] != g or JI[result % 12] != j_char) result += 12 (no, simpler ways)
    # Or iterate to find the match:
    birth_month_gapja_idx = -1
    for i in range(60):
        if GAN[i%10] == birth_month_gan and JI[i%12] == birth_month_ji:
            birth_month_gapja_idx = i
            break
    
    if birth_month_gapja_idx == -1:
        return ["대운 계산 불가: 월주 간지 인덱스 오류"], daewoon_su

    for i in range(10): # Typically 10 Daewoons are listed
        age_at_daewoon_start = daewoon_su + (i * 10)
        
        if sunhaeng:
            daewoon_gapja_idx = (birth_month_gapja_idx + i + 1) % 60
        else: # Yeokhaeng
            daewoon_gapja_idx = (birth_month_gapja_idx - (i + 1)) % 60
            if daewoon_gapja_idx < 0: # Ensure it's positive
                daewoon_gapja_idx += 60
        
        daewoon_gan = GAN[daewoon_gapja_idx % 10]
        daewoon_ji = JI[daewoon_gapja_idx % 12]
        daewoon_pillars.append(f"{age_at_daewoon_start}세: {daewoon_gan}{daewoon_ji}")

    return daewoon_pillars, daewoon_su


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("사주 명식 및 운세 계산기")

if solar_dict: # Only proceed if solar terms are loaded
    st.sidebar.header("생년월일 입력")
    y = st.sidebar.number_input("출생 연도 (양력)", min_value=1900, max_value=2100, value=1999)
    m = st.sidebar.number_input("출생 월 (양력)", min_value=1, max_value=12, value=11)
    d = st.sidebar.number_input("출생 일 (양력)", min_value=1, max_value=31, value=8)
    # Time is not used for basic pillars other than Si-ju, but needed for some interpretations
    # hour = st.sidebar.number_input("출생 시 (24시 형식)", min_value=0, max_value=23, value=12)
    # minute = st.sidebar.number_input("출생 분", min_value=0, max_value=59, value=30)
    gender = st.sidebar.radio("성별", ("남성", "여성"))


    st.sidebar.header("운세 기준 시점")
    base_y = st.sidebar.number_input("운세 기준 연도", min_value=1900, max_value=2100, value=datetime.now().year)
    base_m = st.sidebar.number_input("운세 기준 월", min_value=1, max_value=12, value=datetime.now().month)
    base_d = st.sidebar.number_input("운세 기준 일", min_value=1, max_value=31, value=datetime.now().day)


    if st.sidebar.button("명식 및 운세 계산하기"):
        try:
            birth_datetime = datetime(y, m, d) # Add hour, minute if Siju is implemented
        except ValueError:
            st.error("입력한 생년월일이 유효하지 않습니다. 다시 확인해주세요.")
            st.stop()

        # 1. 사주 명식 (Saju Myeongshik)
        st.subheader("사주 명식 (四柱命式)")

        saju_year_num = get_saju_year(birth_datetime, solar_dict)
        year_ganji_str, year_gan_char, year_ji_char = get_year_ganji(saju_year_num)
        
        month_ganji_str, month_gan_char, month_ji_char = get_month_ganji(year_gan_char, birth_datetime, solar_dict)
        
        day_ganji_str, day_gan_char, day_ji_char = get_day_ganji(y, m, d)
        
        # 시주 (Time Pillar) - Requires birth time, placeholder for now
        # siju_ganji_str = get_siju_ganji(day_gan_char, hour, minute) # TODO
        siju_ganji_str = "미구현"

        myeongshik_df = pd.DataFrame({
            "구분": ["천간 (天干)", "지지 (地支)", "간지 (干支)"],
            "시주 (時柱)": [siju_ganji_str[0] if len(siju_ganji_str)==2 else "?", siju_ganji_str[1] if len(siju_ganji_str)==2 else "?", siju_ganji_str],
            "일주 (日柱)": [day_gan_char, day_ji_char, day_ganji_str],
            "월주 (月柱)": [month_gan_char, month_ji_char, month_ganji_str],
            "연주 (年柱)": [year_gan_char, year_ji_char, year_ganji_str]
        })
        st.table(myeongshik_df.set_index("구분"))
        st.caption(f"출생 기준 사주 연도: {saju_year_num}년")


        # 2. 대운 (Daewoon)
        st.subheader("대운 (大運)")
        if month_ganji_str.startswith("월주 정보 없음") or month_ganji_str.startswith("정보 없음"):
             st.warning(f"월주 정보를 계산할 수 없어 대운 계산이 불가능합니다: {month_ganji_str}")
        else:
            daewoon_pillars, daewoon_su = get_daewoon(year_ganji_str, year_ji_char, gender, birth_datetime, month_ganji_str, solar_dict)
            st.write(f"대운 시작 나이 (만세력 기준): 약 {daewoon_su}세")
            # Display Daewoon in a more structured way
            if daewoon_pillars and not daewoon_pillars[0].startswith("대운 계산 불가"):
                daewoon_data = {"주기": [], "간지": []}
                for pillar_info in daewoon_pillars:
                    parts = pillar_info.split(": ")
                    daewoon_data["주기"].append(parts[0])
                    daewoon_data["간지"].append(parts[1])
                st.table(pd.DataFrame(daewoon_data))
            else:
                st.write(daewoon_pillars[0] if daewoon_pillars else "대운 정보를 가져올 수 없습니다.")


        # 3. 세운 (Seun - Annual Luck)
        st.subheader(f"세운 (年運) - {base_y}년 기준")
        seun_list = get_seun_list(base_y, count=5) # Show 5 years
        seun_df = pd.DataFrame(seun_list, columns=["연도", "간지"])
        st.table(seun_df)

        # 4. 월운 (Wolun - Monthly Luck)
        st.subheader(f"월운 (月運) - {base_y}년 {base_m}월 기준")
        # For Wolun's Ohodunbeop, the year stem of the *current Seun* is used.
        # We need the Gan of base_y.
        wolun_list = get_wolun_list(year_gan_char, base_y, base_m, count=12) # Show 12 months
        wolun_df = pd.DataFrame(wolun_list, columns=["연월", "간지"])
        st.table(wolun_df)

        # 5. 일운 (Ilun - Daily Luck)
        st.subheader(f"일운 (日運) - {base_y}년 {base_m}월 {base_d}일 기준 (5일치 예시)")
        ilun_list = get_ilun_list(base_y, base_m, base_d, count=5)
        ilun_df = pd.DataFrame(ilun_list, columns=["날짜", "간지"])
        st.table(ilun_df)

else:
    st.warning("절입일 데이터 파일을 먼저 업로드해주세요.")
