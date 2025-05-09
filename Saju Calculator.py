# 사주 명식 + 대운 + 세운 + 월운 + 일운 계산기

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("사주 명식 및 운세 계산기")

uploaded_file = st.file_uploader("절입일 파일 업로드 (.xlsx)", type="xlsx")

if uploaded_file:
    solar_terms = pd.read_excel(uploaded_file)
    st.success("엑셀 파일이 성공적으로 불러와졌습니다!")
    st.write("첫 줄 미리보기:")
    st.write(solar_terms.head())

    # 24절기 테이블 구성 (dict: 연도 -> 절기 -> datetime)
    def build_solar_terms_dict(df):
        term_dict = {}
        for _, row in df.iterrows():
            year = int(row['연도'])
            name = row['절기']
            dt = pd.to_datetime(str(row['절입일']) + ' ' + str(row['절입시간']))
            if year not in term_dict:
                term_dict[year] = {}
            term_dict[year][name] = dt
        return term_dict

    solar_dict = build_solar_terms_dict(solar_terms)

    def get_day_ganji(y, m, d):
        base = datetime(1899, 12, 31)  # 기준일: 계해일
        target = datetime(y, m, d)
        delta = (target - base).days
        gan = "갑을병정무기경신임계"[delta % 10]
        ji = "자축인묘진사오미신유술해"[delta % 12]
        return gan + ji

    def get_month_ganji(y, m, d):
        dt = datetime(y, m, d)
        terms = solar_dict.get(y, {})
        prev_term = None
        for term, t_date in sorted(terms.items(), key=lambda x: x[1]):
            if dt < t_date:
                break
            prev_term = (term, t_date)
        used_date = prev_term[1] if prev_term else datetime(y, m, d)
        idx = ((used_date.year - 1864) * 12 + list(solar_dict[y].keys()).index(prev_term[0])) % 60
        gan = "갑을병정무기경신임계"[idx % 10]
        ji = "자축인묘진사오미신유술해"[idx % 12]
        return gan + ji

    def get_seun_list(base_y, day_gan):
        idx = (base_y - 4) % 60
        result = []
        for i in range(5):
            y = base_y + i
            gan = "갑을병정무기경신임계"[(idx + i) % 10]
            ji = "자축인묘진사오미신유술해"[(idx + i) % 12]
            result.append((y, gan + ji))
        return result

    def get_wolun_list(base_y, base_m, day_gan):
        result = []
        for i in range(12):
            y = base_y + (base_m - 1 + i) // 12
            m = (base_m - 1 + i) % 12 + 1
            ganji = get_month_ganji(y, m, 15)
            result.append((f"{y}-{m:02}", ganji))
        return result

    def get_ilun_list(year):
        result = []
        for i in range(365):
            try:
                d = datetime(year, 1, 1) + timedelta(days=i)
                ganji = get_day_ganji(d.year, d.month, d.day)
                result.append((d.strftime("%Y-%m-%d"), ganji))
            except:
                continue
        return result

    col1, col2, col3 = st.columns(3)
    y = col1.number_input("출생 연도", min_value=1900, max_value=2100, value=1999)
    m = col2.number_input("출생 월", min_value=1, max_value=12, value=11)
    d = col3.number_input("출생 일", min_value=1, max_value=31, value=8)

    base_year = st.number_input("운세 기준 연도", min_value=1900, max_value=2100, value=2025)
    base_month = st.number_input("운세 기준 월", min_value=1, max_value=12, value=5)

    if st.button("계산하기"):
        day_gan = get_day_ganji(y, m, d)
        st.subheader("일주")
        st.write(day_gan)

        month_gan = get_month_ganji(y, m, d)
        st.subheader("월주")
        st.write(month_gan)

        st.subheader("세운")
        for year, ganji in get_seun_list(base_year, day_gan):
            st.write(f"{year}: {ganji}")

        st.subheader("월운")
        for ym, ganji in get_wolun_list(base_year, base_month, day_gan):
            st.write(f"{ym}: {ganji}")

        st.subheader("일운 (예시)")
        for date, ganji in get_ilun_list(base_year)[:5]:
            st.write(f"{date}: {ganji}")

else:
    st.warning("절입일_1905_2100.xlsx 파일을 업로드해주세요.")
