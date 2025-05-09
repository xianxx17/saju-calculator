# 1. 필요한 라이브러리들을 가져옵니다.
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re # <--- 이 줄을 추가해주세요! (정규표현식 사용 위함)

# --- 상수 정의 ---
# (사용자님이 보내주신 GAN, JI, SAJU_MONTH_TERMS_ORDER, SAJU_MONTH_BRANCHES, TIME_BRANCH_MAP 등은 여기에 그대로 유지됩니다.)
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

# --- 절입일 데이터 로딩 및 처리 (수정된 부분) ---
@st.cache_data
def load_solar_terms(uploaded_file_obj):
    try:
        solar_terms_df = pd.read_excel(uploaded_file_obj)
        
        st.sidebar.subheader("엑셀에서 읽어온 컬럼명:")
        actual_column_names = list(solar_terms_df.columns)
        st.sidebar.write(actual_column_names)

        term_dict = {}
        processed_rows = 0
        skipped_rows = 0

        # ---!!! 중요: 사용자님의 "C열"에 해당하는 실제 컬럼 이름을 아래에 적어주세요 !!!---
        # 예시: 만약 C열의 헤더(첫번째 행 이름)가 "전체정보" 라면 -> column_with_all_data = '전체정보'
        # 만약 C열의 헤더가 없다면, 엑셀에서 세 번째 컬럼의 기본 이름 (예: 'Column3')을 사용해야 할 수 있습니다.
        # 또는, 실제 엑셀 파일의 C열에 어떤 이름이 있는지 확인 후 여기에 그 이름을 넣으세요.
        column_with_all_data = '절입일' # <--- 여기를 "C열"의 실제 헤더명으로 변경하세요!
                                       # (예: '데이터', '상세정보', 또는 실제 엑셀에 표시된 C열의 이름)

        st.sidebar.info(f"날짜/시간 정보를 읽으려는 주 대상 컬럼: '{column_with_all_data}'")
        if column_with_all_data not in actual_column_names:
            st.sidebar.warning(
                f"'{column_with_all_data}' 컬럼이 파일에 없습니다. "
                f"실제 파일의 컬럼명을 확인하고 위 코드의 `column_with_all_data` 변수를 수정해주세요."
            )

        for _, row in solar_terms_df.iterrows():
            try:
                year_str = str(row.get('연도', '')).strip() # '연도' 컬럼은 있어야 함
                term_name_str = str(row.get('절기', '')).strip() # '절기' 컬럼은 있어야 함

                if not year_str or not term_name_str:
                    skipped_rows += 1
                    continue
                
                year = int(float(year_str)) # 연도가 숫자로 변환 가능한지 확인
                term_name = term_name_str
                dt_str = None

                # 1순위: 사용자가 지정한 "C열" (column_with_all_data)
                if column_with_all_data in actual_column_names and pd.notna(row.get(column_with_all_data)):
                    raw_text_from_column_c = str(row[column_with_all_data])
                    # 예시: "곡우 (穀雨) ... 1905/04/21 02:55 ..." 에서 "1905/04/21 02:55" 부분 추출
                    match = re.search(r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\s+\d{1,2}:\d{1,2}(:\d{1,2})?)', raw_text_from_column_c)
                    if match:
                        dt_str = match.group(1) # 날짜/시간 부분만 저장
                    else:
                        # 정규식으로 원하는 부분을 찾지 못했을 경우, 원본 문자열을 그대로 사용해봅니다.
                        # 이 경우 pd.to_datetime에서 오류가 발생할 수 있습니다.
                        dt_str = raw_text_from_column_c 
                
                # 2순위: '절입일시' 컬럼 (1순위에서 dt_str을 얻지 못했거나, column_with_all_data가 '절입일시'가 아닐 때)
                elif '절입일시' in actual_column_names and pd.notna(row.get('절입일시')):
                    dt_str = str(row['절입일시'])
                
                # 3순위: '절입일'과 '절입시간' 컬럼 조합
                elif ('절입일' in actual_column_names and '절입시간' in actual_column_names and
                      pd.notna(row.get('절입일')) and pd.notna(row.get('절입시간'))):
                    date_part = str(row['절입일'])
                    time_part = str(row['절입시간'])
                    # 시간을 나타내는 문자열에서 "시", "분" 등을 제거하거나 표준 형식으로 변경 필요할 수 있음
                    # 여기서는 단순 조합만 시도
                    dt_str = f"{date_part} {time_part}"

                if dt_str is None:
                    skipped_rows += 1
                    continue

                # 날짜/시간 문자열을 datetime 객체로 변환
                dt = pd.to_datetime(dt_str, errors='coerce') # errors='coerce'는 변환 실패시 NaT 반환

                if pd.isna(dt): # 변환 실패한 경우 (NaT)
                    skipped_rows += 1
                    continue
                
                if year not in term_dict:
                    term_dict[year] = {}
                term_dict[year][term_name] = dt
                processed_rows += 1

            except Exception as e_inner: # 행 단위 처리 중 발생하는 다른 예외들
                skipped_rows += 1
                # st.sidebar.write(f"행 처리 오류 (연도: {year_str}, 절기: {term_name_str}): {e_inner}") # 필요시 상세 오류 확인
                continue
        
        if skipped_rows > 0:
            st.sidebar.warning(f"절입일 데이터 중 {skipped_rows}개 행이 날짜/시간 정보 부족 또는 오류로 인해 건너뛰어졌습니다.")
        if processed_rows == 0 and not solar_terms_df.empty:
            st.error("절입일 데이터를 전혀 처리하지 못했습니다. "
                     "사이드바의 '엑셀에서 읽어온 컬럼명'과 실제 파일, "
                     f"그리고 코드 내 '{column_with_all_data}' 컬럼명 설정을 확인해주세요.")
            return None
        if not term_dict and not solar_terms_df.empty:
            st.error("처리된 절입일 데이터가 없습니다. 파일 내용 및 컬럼 설정을 확인해주세요.")
            return None

        return term_dict
    except Exception as e_outer: # 파일 전체 처리 중 발생하는 예외
        st.error(f"엑셀 파일 처리 중 심각한 오류 발생: {e_outer}")
        return None

# --- (이하 사주 명식, 대운, 세운, 월운, 일운 계산 함수 및 UI 코드는 이전 답변과 동일하게 유지) ---
# (get_saju_year 부터 끝까지, 사용자님이 보내주신 나머지 모든 코드를 여기에 그대로 유지하시면 됩니다.)
# 예시:
# def get_saju_year(birth_dt, solar_data):
#     ... (기존 코드 내용) ...
#
# (모든 사주계산 함수들)
#
# st.set_page_config(layout="wide", page_title="종합 사주 명식 계산기")
# ... (기존 UI 코드 내용) ...
