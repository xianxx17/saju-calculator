import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re # <--- 정규 표현식 모듈 추가

# --- 상수 정의 ---
# (기존 GAN, JI, SAJU_MONTH_TERMS_ORDER 등 상수는 동일하게 유지)
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

        # ---!!! 중요: 사용자님의 "C열"에 해당하는 실제 컬럼 헤더 이름을 아래에 적어주세요 !!!---
        # 예시: 만약 C열의 헤더가 "모든정보" 라면 -> datetime_column_candidate = '모든정보'
        # 기본값은 '절입일'로 두되, 사용자가 C열 정보를 우선으로 하도록 안내합니다.
        datetime_column_candidate = '절입일' # <--- 여기를 "C열"의 실제 헤더명으로 변경하세요!
                                          # 예를 들어, 만약 C열의 이름이 '종합 정보' 라면 '종합 정보' 로 변경

        st.sidebar.info(f"주요 날짜/시간 정보 컬럼 후보: '{datetime_column_candidate}'")
        st.sidebar.caption(f"만약 C열의 헤더명이 '{datetime_column_candidate}'가 아니라면, 위 코드에서 해당 변수 값을 수정해주세요.")


        for _, row in solar_terms_df.iterrows():
            try:
                year_str = str(row.get('연도', '')).strip()
                term_name_str = str(row.get('절기', '')).strip()

                if not year_str or not term_name_str:
                    skipped_rows +=1
                    continue
                
                year = int(float(year_str))
                term_name = term_name_str
                dt_str = None

                # 1순위: 사용자가 지정한 "C열" (datetime_column_candidate)
                if datetime_column_candidate in actual_column_names and pd.notna(row.get(datetime_column_candidate)):
                    raw_data_from_candidate_column = str(row[datetime_column_candidate])
                    # 정규표현식을 사용하여 YYYY/MM/DD HH:MM 또는 YYYY-MM-DD HH:MM:SS 형식 추출 시도
                    # 예시: "곡우 (穀雨) ... 1905/04/21 02:55 ..." 에서 "1905/04/21 02:55" 추출
                    match = re.search(r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\s+\d{1,2}:\d{1,2}(:\d{1,2})?)', raw_data_from_candidate_column)
                    if match:
                        dt_str = match.group(1)
                        st.write(f"추출된 날짜 문자열 from {datetime_column_candidate}: {dt_str}") # 디버깅용
                    else:
                        # 정규식으로 못찾으면, 원본 문자열을 그대로 사용 (오류 가능성 있음)
                        # 또는 다른 컬럼을 시도하기 위해 dt_str을 None으로 유지할 수도 있음
                        dt_str = raw_data_from_candidate_column # pd.to_datetime이 처리할 수 있는지 시도
                        st.write(f"정규식 매칭 실패, 원본 사용 from {datetime_column_candidate}: {dt_str}") # 디버깅용
                
                # 2순위: '절입일시' 컬럼 (1순위에서 dt_str을 못 얻었을 경우)
                if dt_str is None and '절입일시' in actual_column_names and pd.notna(row.get('절입일시')):
                    dt_str = str(row['절입일시'])
                    st.write(f"추출된 날짜 문자열 from 절입일시: {dt_str}") # 디버깅용

                # 3순위: '절입일'과 '절입시간' 컬럼 조합 (1, 2순위에서 dt_str을 못 얻었을 경우)
                elif dt_str is None and ('절입일' in actual_column_names and '절입시간' in actual_column_names and
                      pd.notna(row.get('절입일')) and pd.notna(row.get('절입시간')) and
                      datetime_column_candidate != '절입일'): # datetime_column_candidate가 '절입일'일 경우 중복 방지
                    date_part = str(row['절입일'])
                    time_part = str(row['절입시간'])
                    dt_str = date_part + " " + time_part # 간단한 조합, 추가 정제 필요할 수 있음
                    st.write(f"추출된 날짜 문자열 from 절입일+절입시간: {dt_str}") # 디버깅용

                if dt_str is None:
                    st.write(f"Skipping row due to missing dt_str: Year={year}, Term={term_name}") # 디버깅용
                    skipped_rows +=1
                    continue

                dt = pd.to_datetime(dt_str, errors='coerce')

                if pd.isna(dt):
                    st.write(f"Skipping row due to pd.to_datetime error: Original dt_str='{dt_str}', Year={year}, Term={term_name}") # 디버깅용
                    skipped_rows +=1
                    continue
                
                if year not in term_dict:
                    term_dict[year] = {}
                term_dict[year][term_name] = dt
                processed_rows += 1

            except Exception as e_inner:
                st.warning(f"데이터 처리 중 행 단위 오류 발생 (연도: {row.get('연도', '알수없음')}, 절기: {row.get('절기', '알수없음')}): {e_inner}")
                skipped_rows +=1
                continue
        
        if skipped_rows > 0:
            st.sidebar.warning(f"절입일 데이터 중 {skipped_rows}개 행이 날짜/시간 정보 부족 또는 오류로 인해 건너뛰어졌습니다.")
        if processed_rows == 0 and solar_terms_df.shape[0] > 0 :
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

# --- (이하 사주 명식, 대운, 세운, 월운, 일운 계산 함수 및 UI 코드는 이전과 동일하게 유지) ---
# ... (get_saju_year 부터 끝까지의 코드를 여기에 붙여넣으시면 됩니다) ...
# (여기에 사용자가 제공한 나머지 모든 함수들: get_saju_year, get_ganji_from_index, ... , get_ilun_list, 그리고 Streamlit UI 코드 전체를 붙여넣으시면 됩니다.)
