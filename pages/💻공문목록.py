import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# List of institutions and their codes
institutions = [
    {"name": "대구광역시교육청 대구과학고등학교", "code": "7240060"},
    {"name": "대구광역시교육청 경북여자고등학교", "code": "7240055"},
    {"name": "대구광역시교육청 시지고등학교", "code": "7240065"},
    {"name": "대구광역시교육청 포산고등학교", "code": "7240189"},
    {"name": "대구광역시교육청 성산고등학교", "code": "7240204"},
    {"name": "대구광역시교육청 대곡고등학교", "code": "7240205"},
    {"name": "대구광역시교육청 비슬고등학교", "code": "7240394"},
    {"name": "대구광역시교육청 대구광역시남부교육지원청 대구중학교", "code": "7271009"},
    {"name": "대구광역시교육청 대구광역시남부교육지원청 상인중학교", "code": "7271021"},
    {"name": "대구광역시교육청 대구광역시달성교육지원청 서동중학교", "code": "7281119"},
    {"name": "대구광역시교육청 대구광역시달성교육지원청 포산중학교", "code": "7281009"},
    {"name": "대구광역시교육청 대구광역시서부교육지원청 경운중학교", "code": "7261009"}
    # Add more institutions here
]

# 로그인/권한 정보 불러오기
user_role = st.session_state.get("user_role")
user_email = st.session_state.get("user_email")

#권한 확인하기기
doc_allowed_roles = st.session_state['board_roles']["공문목록"]

st.header("Institution Data Viewer")
if user_role not in doc_allowed_roles:
    st.info("권한이 없는 사용자입니다. 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    st.write("오늘자 공문은 내일 새벽이 되어야 업데이트 되는것 같습니다. 하루전 까지의 데이터를 검색해 주세요.")
    # Institution selection
    selected_institution = st.selectbox(
        "Select Institution",
        options=[inst["name"] for inst in institutions]
    )

    # Find the selected institution code
    selected_code = next(inst["code"] for inst in institutions if inst["name"] == selected_institution)

    # Date selection
    start_date = st.date_input("Start Date", datetime.now()-timedelta(weeks=1))
    end_date = st.date_input("End Date", datetime.now()-timedelta(days=1))

    # Fetch data
    url = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "DNT": "1",
        "Origin": "https://www.open.go.kr",
        "Referer": "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    cookies = {
        "elevisor_for_j2ee_uid": "gq35037aqy3ns",
        "JSESSIONID": "D99uVlZ9LutHlqNqWzB131NvFM9Q5TT6WFBp6XVdmbGyH9w5l94ashancsAVXx71.amV1c19kb21haW4vb3BzcG9ydGFsZXh0MQ==",
        "clientid": "060000502151",
        "keywords": "%uB300%uAD6C%uACFC%uD559%uACE0"
    }
    data = {
        "kwd": "",
        "searchInsttCdNmPop": selected_institution,
        "preKwds": "",
        "reSrchFlag": "off",
        "othbcSeCd": "",
        "insttSeCd": "",
        "eduYn": "Y",
        "startDate": start_date.strftime("%Y%m%d"),
        "endDate": end_date.strftime("%Y%m%d"),
        "insttCdNm": selected_institution,
        "insttCd": selected_code,
        "searchMainYn": "",
        "viewPage": "1",
        "rowPage": "1000",
        "sort": "s",
        "url": "/othicInfo/infoList/orginlInfoList.ajax",
        "callBackFn": "searchFn_callBack"
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=data)

    # Display data
    if response.status_code == 200:
        datalist = response.json().get("result", {}).get('rtnList', [])
        if datalist:
            df = pd.DataFrame(datalist)
            st.dataframe(df[["DOC_NO", "LAST_UPDT_DT", "INFO_SJ", "FILE_NM", "CHARGER_NM"]])
        else:
            st.write("No data found for the selected criteria.")
    else:
        st.write("Failed to fetch data.") 