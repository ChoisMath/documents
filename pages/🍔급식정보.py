import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.header("🍔🍟🌭🍿🌯오늘의 급식🥨🥐🥫🥗🥙")

# NEIS API 기본 정보
API_KEY = st.secrets["neis"]["API_KEY"]
ATPT_OFCDC_SC_CODE = "D10"  # 시도교육청코드 (예: 대구광역시교육청)

col1, col2 = st.columns(2)

with col1:
    # 날짜 선택
    selected_date = st.date_input("날짜 선택", value=datetime.now())
    selected_date_str = selected_date.strftime("%Y%m%d")

# 학교 선택 (예시로 두 학교 추가)
with col2:
    school_options = {
        "사대부중/부고": "7004180",
        "대구과학고등학교": "7240060",
        "경북여자고등학교": "7240055",
        "시지고등학교": "7240065",
        "포산고등학교": "7240189",
        "성산고등학교": "7240204",
        "대곡고등학교": "7240205",
        "비슬고등학교": "7240394",
        "대구중학교": "7271009",
        "상인중학교": "7271021",
        "서동중학교": "7281119",
        "포산중학교": "7281009",
        "경운중학교": "7261009"
    } 
    selected_school = st.selectbox("학교 선택", options=list(school_options.keys()))
    selected_school_code = school_options[selected_school]

# API 요청 URL 업데이트
url = (
    f"https://open.neis.go.kr/hub/mealServiceDietInfo?"
    f"KEY={API_KEY}"
    f"&Type=json"
    f"&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
    f"&SD_SCHUL_CODE={selected_school_code}"
    f"&MLSV_YMD={selected_date_str}"
    f"&pIndex=1&pSize=10"
)

# API 호출
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    st.error(f"API 호출 오류: {e}")
    st.stop()

# 데이터 파싱 및 표시 업데이트
def parse_meal_data(data):
    try:
        meal_info = data["mealServiceDietInfo"][1]["row"]
        df = pd.DataFrame(meal_info)
        # 주요 컬럼만 보기 좋게 정리
        df = df[["MMEAL_SC_NM", "DDISH_NM", "CAL_INFO"]]  # Only keep calorie info
        df.columns = ["급식구분", "요리명(알레르기)", "칼로리"]
        # 요리명에서 <br/> 등 HTML 태그 제거 및 줄바꿈 처리
        df["요리명(알레르기)"] = df["요리명(알레르기)"].str.split("<br/>")
        return df
    except Exception:
        return None

df_meal = parse_meal_data(data)

if df_meal is not None and not df_meal.empty:
    for _, row in df_meal.iterrows():
        with st.expander(f"{row['급식구분']} - {row['칼로리']}", expanded=True):
            st.write("**요리명(알레르기):**")
            for dish in row['요리명(알레르기)']:
                st.write(f"- {dish}")
else:
    st.info("선택한 날짜의 급식 식단 정보가 없습니다.")

st.caption("출처: NEIS 교육정보개방포털 급식식단정보 OpenAPI") 