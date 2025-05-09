# 파일명 예시: saju_app.py
# 실행: streamlit run saju_app.py
# 필요 패키지: pip install streamlit pandas openpyxl

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ───────────────────────────────
# 0. 기본 상수
# ───────────────────────────────
FILE_NAME = "Solar_Terms1905_2100.csv"   # 같은 폴더에 둡니다

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
    """cleaned 엑셀 → {연도: {절기: datetime}}"""
    if not os.path.exists(file_name):
        st.error(f"`{file_name}` 파일을 찾을 수 없습니다. 같은 폴더에 두고 재실행하세요.")
        return None
    df = pd.read_excel(file_name)

    term_dict = {}
    for _, row in df.iterrows():
        year  = int(row["연도"])
        term  = str(row["절기"]).strip()
        dt    = pd.to_datetime(row["iso_datetime"], errors="coerce")
        if pd.isna(dt):
            continue
        term_dict.setdefault(year, {})[term] = dt
    return term_dict

solar_data = load_solar_terms(FILE_NAME)
if solar_data is None:
    st.stop()

# ───────────────────────────────
# 2. 사주/운세 계산 함수
# ───────────────────────────────
def get_saju_year(birth_dt, solar_data_dict):
    year = birth_dt.year
    ipchun = solar_data_dict.get(year, {}).get("입춘")
    return year - 1 if (ipchun and birth_dt < ipchun) else year

def get_ganji_from_index(idx):
    return GAN[idx % 10] + JI[idx % 12]

def get_year_ganji(saju_year):
    idx = (saju_year - 4) % 60
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_month_ganji(year_gan_char, birth_dt, solar_data_dict):
    # governing 절기 찾기
    terms = solar_data_dict.get(birth_dt.year, {})
    governing = None
    for name, dt in sorted(
        [(n,d) for n,d in terms.items() if n in SAJU_MONTH_TERMS_ORDER],
        key=lambda x: x[1]
    ):
        if birth_dt >= dt:
            governing = name
        else:
            break
    if not governing:  # 소한·대설 처리
        prev_terms = solar_data_dict.get(birth_dt.year - 1, {})
        for name, dt in sorted(
            [(n,d) for n,d in prev_terms.items() if n in ["소한","대설"]],
            key=lambda x: x[1],
            reverse=True
        ):
            if birth_dt >= dt:
                governing = name
                break
    if not governing:
        return "오류(월주)", "", ""

    branch_idx = SAJU_MONTH_TERMS_ORDER.index(governing)
    month_ji   = SAJU_MONTH_BRANCHES[branch_idx]

    yg_idx = GAN.index(year_gan_char)
    start_map = {0:2,5:2,1:4,6:4,2:6,7:6,3:8,8:8,4:0,9:0}
    start_gan_idx = start_map.get(yg_idx)
    if start_gan_idx is None:
        return "오류(연간→월간)", "", ""

    month_gan = GAN[(start_gan_idx + branch_idx) % 10]
    return month_gan + month_ji, month_gan, month_ji

def get_day_ganji(year, month, day):
    base = datetime(1899,12,31)
    diff = (datetime(year,month,day) - base).days
    idx  = diff % 60
    return get_ganji_from_index(idx), GAN[idx % 10], JI[idx % 12]

def get_time_ganji(day_gan_char, hour, minute):
    cur = hour + minute/60
    siji_char, siji_idx = None, -1
    for (sh,sm),(eh,em),ji,idx in TIME_BRANCH_MAP:
        s = sh+sm/60; e = eh+em/60
        if ji=="자":
            if cur>=s or cur<=e: siji_char, siji_idx = ji, idx; break
        elif s<=cur<e+(1/60):   siji_char, siji_idx = ji, idx; break
    if siji_char is None:
        return "오류(시지)", "", ""
    dg_idx = GAN.index(day_gan_char)
    start_map = {0:0,5:0,1:2,6:2,2:4,7:4,3:6,8:6,4:8,9:8}
    tg_idx = (start_map[dg_idx] + siji_idx) % 10
    return GAN[tg_idx] + siji_char, GAN[tg_idx], siji_char

def get_daewoon(year_gan_char, gender, birth_dt, month_gan_char, month_ji_char):
    yang_year = GAN.index(year_gan_char) % 2 == 0
    sunhaeng  = (yang_year and gender=="남성") or (not yang_year and gender=="여성")

    # 대운 시작까지 일수/3 계산
    terms_this_year = solar_data.get(birth_dt.year, {})
    governing = None
    for nm, dt in sorted([(n,d) for n,d in terms_this_year.items() if n in SAJU_MONTH_TERMS_ORDER],
                         key=lambda x:x[1]):
        if birth_dt >= dt: governing = nm
        else: break
    if not governing:
        terms_prev = solar_data.get(birth_dt.year-1, {})
        for nm, dt in sorted([(n,d) for n,d in terms_prev.items() if n in ["소한","대설"]],
                             key=lambda x:x[1], reverse=True):
            if birth_dt >= dt: governing = nm; break
    if not governing:
        return ["오류(대운 절기)"], 0

    gov_dt = (terms_this_year if governing in terms_this_year else
              solar_data.get(birth_dt.year-1, {})).get(governing)
    next_term_idx = (SAJU_MONTH_TERMS_ORDER.index(governing)+1)%12
    next_term_nm  = SAJU_MONTH_TERMS_ORDER[next_term_idx]
    next_dt = (terms_this_year.get(next_term_nm) or
               solar_data.get(birth_dt.year+1, {}).get(next_term_nm))
    target_dt = next_dt if sunhaeng else gov_dt
    days = abs((target_dt - birth_dt).total_seconds()) / (24*3600)
    daew_start_age = max(1, round(days/3))

    # 월주 idx
    cur_idx = -1
    for i in range(60):
        if GAN[i%10]==month_gan_char and JI[i%12]==month_ji_char:
            cur_idx=i; break
    if cur_idx==-1:
        return ["오류(월주→갑자)"], daew_start_age

    out=[]
    for i in range(10):
        age = daew_start_age + i*10
        idx = (cur_idx + (i+1) if sunhaeng else cur_idx-(i+1)) % 60
        out.append(f"{age}세: {get_ganji_from_index(idx)}")
    return out, daew_start_age

def get_seun_list(start_year, n=10):
    return [(y, get_ganji_from_index((y-4)%60)) for y in range(start_year, start_year+n)]

def get_wolun_list(base_year, base_month, solar_data_dict, n=12):
    out=[]
    for i in range(n):
        y = base_year + (base_month-1+i)//12
        m = (base_month-1+i)%12 + 1
        seun_gan = GAN[((y-4)%60) % 10]

        # 월운 절기
        ref = datetime(y,m,15)
        terms = solar_data_dict.get(y, {})
        gov=None
        for nm,dt in sorted([(n,d) for n,d in terms.items() if n in SAJU_MONTH_TERMS_ORDER],
                            key=lambda x:x[1]):
            if ref >= dt: gov=nm
            else: break
        if not gov:
            terms_prev = solar_data_dict.get(y-1, {})
            for nm,dt in sorted([(n,d) for n,d in terms_prev.items() if n in ["소한","대설"]],
                                key=lambda x:x[1], reverse=True):
                if ref>=dt: gov=nm; break
        if not gov:
            out.append((f"{y}-{m:02d}","오류"))
            continue

        idx = SAJU_MONTH_TERMS_ORDER.index(gov)
        month_ji = SAJU_MONTH_BRANCHES[idx]
        start_map={0:2,5:2,1:4,6:4,2:6,7:6,3:8,8:8,4:0,9:0}
        start = start_map[GAN.index(seun_gan)]
        month_gan = GAN[(start+idx)%10]
        out.append((f"{y}-{m:02d}", month_gan+month_ji))
    return out

def get_ilun_list(y,m,d,n=10):
    base = datetime(y,m,d)
    return [( (base+timedelta(days=i)).strftime("%Y-%m-%d"),
              get_day_ganji(*(base+timedelta(days=i)).timetuple()[:3])[0] )
             for i in range(n)]

# ───────────────────────────────
# 3. Streamlit UI
# ───────────────────────────────
st.set_page_config(layout="wide", page_title="🔮 종합 사주 명식 계산기")
st.title("🔮 종합 사주 명식 및 운세 계산기")

# 입력
st.sidebar.header("1. 출생 정보")
by = st.sidebar.number_input("연", 1900, 2100, 1999)
bm = st.sidebar.number_input("월", 1, 12, 11)
bd = st.sidebar.number_input("일", 1, 31, 8)
bh = st.sidebar.number_input("시", 0, 23, 14)
bmin = st.sidebar.number_input("분", 0, 59, 30)
gender = st.sidebar.radio("성별", ("남성","여성"), horizontal=True)

st.sidebar.header("2. 운세 기준일")
today = datetime.now()
ty = st.sidebar.number_input("기준 연도", 1900, 2100, today.year)
tm = st.sidebar.number_input("기준 월" , 1, 12, today.month)
td = st.sidebar.number_input("기준 일" , 1, 31, today.day)

if st.sidebar.button("🧮 계산 실행", use_container_width=True, type="primary"):
    try:
        birth_dt = datetime(by,bm,bd,bh,bmin)
    except ValueError:
        st.error("❌ 유효하지 않은 생년월일시입니다.")
        st.stop()

    # ── 명식
    sj_year = get_saju_year(birth_dt, solar_data)
    year_p, yg, yj = get_year_ganji(sj_year)
    month_p, mg, mj = get_month_ganji(yg, birth_dt, solar_data)
    day_p , dg, dj = get_day_ganji(by,bm,bd)
    time_p, tg, tj = get_time_ganji(dg,bh,bmin)

    st.subheader("📜 사주 명식")
    ms_df = pd.DataFrame({
        "구분":["천간","지지","간지"],
        "시주":[tg or "?", tj or "?", time_p],
        "일주":[dg, dj, day_p],
        "월주":[mg or "?", mj or "?", month_p],
        "연주":[yg, yj, year_p]
    }).set_index("구분")
    st.table(ms_df)
    st.caption(f"사주 기준 연도(입춘 기준): {sj_year}년")

    # ── 대운
    st.subheader(f"運 대운 ({gender})")
    if "오류" in month_p:
        st.warning(month_p)
    else:
        dw_list, dw_age = get_daewoon(yg, gender, birth_dt, mg, mj)
        st.text(f"시작 나이: 약 {dw_age}세")
        st.table(pd.DataFrame({"주기(나이)": [x.split(':')[0] for x in dw_list],
                               "간지":[x.split(': ')[1] for x in dw_list]}))

    # 세운·월운·일운
    col1,col2 = st.columns(2)
    with col1:
        st.subheader(f"歲 세운 ({ty}~)")
        st.table(pd.DataFrame(get_seun_list(ty,5), columns=["연도","간지"]))
        st.subheader(f"日 일운 ({ty}-{tm:02d}-{td:02d}~)")
        st.table(pd.DataFrame(get_ilun_list(ty,tm,td,7), columns=["날짜","간지"]))
    with col2:
        st.subheader(f"月 월운 ({ty}-{tm:02d}~)")
        st.table(pd.DataFrame(get_wolun_list(ty,tm,solar_data,12),
                              columns=["연월","간지"]))
else:
    st.markdown(f"""
    **사용 방법**  
    1. 이 파일과 `{FILE_NAME}`(파싱된 24절기 데이터)을 **같은 폴더**에 둡니다.  
    2. 터미널에서 `streamlit run saju_app.py` 실행.  
    3. 왼쪽 사이드바에서 출생 정보·기준일 입력 → **🧮 계산 실행** 클릭.
    """)
