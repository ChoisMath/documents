import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pytz

# 구글 서비스 계정 인증 및 스프레드시트 열기 (app.py와 동일)
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(credentials)
SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"  # 실제 사용 중인 시트 ID로 맞추세요
sh = gc.open_by_key(SHEET_ID)

# 로그인/권한 정보 불러오기
user_role = st.session_state.get("user_role")
user_email = st.session_state.get("user_email")

# ------------------- 상담일지 기능 -------------------
counseling_allowed_roles =  st.session_state['board_roles']["상담일지"]
if user_role not in counseling_allowed_roles:
    st.info("상담일지 기능은 허용된 사용자만 접근할 수 있습니다. 필요 및 오류 시 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    import datetime
    
    # 상담일지 시트 열기
    try:
        counseling_ws = sh.worksheet("CounselingLog")
    except Exception:
        counseling_ws = sh.add_worksheet(title="CounselingLog", rows=1000, cols=10)
        counseling_ws.append_row(["email", "date", "title", "content"])

    # 본인 상담일지 불러오기 (맨 위로 이동)
    counseling_data = counseling_ws.get_all_records()
    counseling_df = pd.DataFrame(counseling_data)
    my_logs = counseling_df[counseling_df["email"] == user_email] if not counseling_df.empty else pd.DataFrame()
    
    st.subheader("📋 내 상담일지 기록")
    if not my_logs.empty:
        # 이메일 컬럼 제외하고 date, title, content만 표시
        display_logs = my_logs[["date", "title", "content"]].sort_values("date", ascending=False)
        st.dataframe(display_logs, use_container_width=True)
    else:
        st.info("상담일지 기록이 없습니다.")

    st.markdown("---")  # 구분선

    # 기록과 수정 UI를 탭으로 분리
    tab1, tab2 = st.tabs(["📝 기록", "✏️ 수정"])
    
    with tab1:
        with st.form("counseling_form"):
            title = st.text_input("상담일지 제목")
            content = st.text_area("상담 내용", height=200)
            # 서울 타임존 객체
            seoul_tz = pytz.timezone("Asia/Seoul")  
            # 기본값을 서울 시간으로 설정
            today_seoul = datetime.datetime.now(seoul_tz).date()
            date = st.date_input("상담일", value=today_seoul)
            submitted = st.form_submit_button("💾 저장", type="primary")
            if submitted and title and content:
                counseling_ws.append_row([user_email, str(date), title, content])
                st.success("상담일지가 저장되었습니다.")
                st.rerun()
    
    with tab2:
        if not my_logs.empty:
            # 인덱스를 재설정하여 연속적인 숫자로 만들기
            my_logs_reset = my_logs.reset_index(drop=True)
            
            # selectbox에서 연속적인 인덱스 사용
            selected_index = st.selectbox(
                "수정할 상담일지를 선택하세요", 
                range(len(my_logs_reset)), 
                format_func=lambda x: f"{my_logs_reset.loc[x, 'date']} - {my_logs_reset.loc[x, 'title']}"
            )
            
            with st.form("edit_counseling_form"):
                selected_entry = my_logs_reset.loc[selected_index]
                edit_title = st.text_input("제목", value=selected_entry["title"])
                edit_content = st.text_area("상담 내용", value=selected_entry["content"], height=200)
                # 날짜 입력을 서울 시간 기준으로 변환
                edit_date = st.date_input(
                    "상담일", 
                    value=datetime.datetime.strptime(selected_entry["date"], "%Y-%m-%d").date()
                )
                edit_submitted = st.form_submit_button("💾 수정 저장", type="primary")
                if edit_submitted and edit_title and edit_content:
                    # 원본 DataFrame에서 해당 행의 실제 위치 찾기
                    original_index = my_logs.index[selected_index]
                    # Google Sheet에서의 실제 행 번호 계산 (헤더 + 1-based indexing 고려)
                    sheet_row_index = original_index + 2
                    counseling_ws.update(f"A{sheet_row_index}", [[user_email, str(edit_date), edit_title, edit_content]])
                    st.success("상담일지가 수정되었습니다.")
                    st.rerun()
        else:
            st.info("수정할 상담일지가 없습니다.")




