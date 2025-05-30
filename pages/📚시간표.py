import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.header("학교 시간표 조회 (NEIS)")

# NEIS API 기본 정보
API_KEY = st.secrets["neis"]["API_KEY"]
ATPT_OFCDC_SC_CODE = "D10"  # 시도교육청코드 (예: 대구광역시교육청)

# ---- 사이드바로 이동 ----
with st.sidebar:
    # 날짜 선택
    selected_date = st.date_input("날짜 선택", value=datetime.now())
    selected_date_str = selected_date.strftime("%Y%m%d")

    # 학교 선택 (예시로 두 학교 추가)
    school_options = {
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

    # 학년 선택 및 API URL 설정
    if selected_school.endswith("초등학교"):
        optinlist = [1, 2, 3, 4, 5, 6]
        api_url = "https://open.neis.go.kr/hub/elsTimetable?"
    elif selected_school.endswith("중학교"):
        optinlist = [1, 2, 3]
        api_url = "https://open.neis.go.kr/hub/misTimetable?"
    else:
        optinlist = [1, 2, 3]
        api_url = "https://open.neis.go.kr/hub/hisTimetable?"

    selected_grade = st.selectbox("학년 선택", options=optinlist)

# API 요청 URL
url = (
    f"{api_url}"
    f"KEY={API_KEY}"
    f"&Type=json"
    f"&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
    f"&SD_SCHUL_CODE={selected_school_code}"
    f"&ALL_TI_YMD={selected_date_str}"
    f"&GRADE={selected_grade}"
    f"&pIndex=1&pSize=100"
)

# API 호출
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    st.error(f"API 호출 오류: {e}")
    st.stop()

# 데이터 파싱 및 표시
def parse_timetable_data(data):
    try:
        timetable_info = data["hisTimetable"][1]["row"] if not selected_school.endswith("초등학교") else data["elsTimetable"][1]["row"]
        df = pd.DataFrame(timetable_info)
        # 주요 컬럼만 보기 좋게 정리
        df = df[["PERIO", "ITRT_CNTNT", "CLRM_NM" if not selected_school.endswith("초등학교") else "CLASS_NM"]]
        df.columns = ["교시", "수업내용", "강의실명" if not selected_school.endswith("초등학교") else "학급명"]
        return df
    except Exception:
        return None

df_timetable = parse_timetable_data(data)

# Check for duplicates and handle them
if df_timetable is not None and not df_timetable.empty:
    # Group by '교시' and '강의실명' or '학급명' and aggregate '수업내용'
    df_timetable = df_timetable.groupby(['교시', '강의실명' if not selected_school.endswith("초등학교") else '학급명'], as_index=False).agg({'수업내용': ' / '.join})
    
    # 피벗 테이블로 변환하여 출력
    pivot_table = df_timetable.pivot(index="교시", columns="강의실명" if not selected_school.endswith("초등학교") else "학급명", values="수업내용")
    st.dataframe(pivot_table, use_container_width=True, width=1000)
else:
    st.info("선택한 날짜의 시간표 정보가 없습니다.")

st.caption("출처: NEIS 교육정보개방포털 고등학교시간표 OpenAPI") 