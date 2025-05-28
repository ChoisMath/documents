import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import pytz
# 서울 타임존 객체
seoul_tz = pytz.timezone("Asia/Seoul")

st.set_page_config(layout="wide")
st.title("Chois Playground")
st.markdown("그냥 놀고있습니다. 급식정보가 제일 유용할까요? 필요하신 거 말씀하시면 되는대로 추가해 볼게요. 처음 로그인 하시면 등록하라고 나올꺼에요. 이름만 작성하셔서 등록눌러주시면 모두 보실 수 있게 해둘게요~ㅎㅎ")

if not st.user.is_logged_in:
    if st.button("Google로 로그인"):
        st.login('google')
else:
    pass

st.session_state["user"] = st.user.to_dict()
#st.write(st.session_state["user"])

# 구글 서비스 계정 인증 및 스프레드시트 열기
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(credentials)

SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"  # 실제 사용 중인 시트 ID로 맞추세요
sh = gc.open_by_key(SHEET_ID)

# board_roles 시트에서 읽기
def load_board_roles(sh):
    try:
        ws = sh.worksheet("board_roles")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="board_roles", rows=10, cols=2)
        ws.append_row(["board", "roles"])
        # 기본값 추가
        ws.append_row(["자료", "admin, vvip, teacher"])
        ws.append_row(["시간표", "admin, teacher, student"])
        ws.append_row(["상담일지", "admin, semiadmin, teacher"])
    records = ws.get_all_records()
    board_roles = {row["board"]: [role.strip() for role in row["roles"].split(",") if role.strip()] for row in records}
    return board_roles, ws

# board_roles 시트에 저장
def save_board_roles(ws, board_roles):
    ws.clear()
    ws.append_row(["board", "roles"])
    for board, roles in board_roles.items():
        ws.append_row([board, ",".join(roles)])

# 등록 신청 시트 관리
def load_registration(sh):
    try:
        ws = sh.worksheet("registration")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="registration", rows=100, cols=5)
        ws.append_row(["신청문구", "email", "name", "신청시간", "처리상태"])
    return ws

def save_registration_request(ws, request_text, email, name):
    # 기본값을 서울 시간으로 설정
    today_seoul = datetime.datetime.now(seoul_tz)
    current_time = today_seoul.strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([request_text, email, name, current_time, "대기중"])
    return True

# board_roles 불러오기
board_roles, board_roles_ws = load_board_roles(sh)
# Store board_roles in session_state for access across pages
st.session_state['board_roles'] = board_roles

# # 5. 로그인한 사용자 이메일로 권한 확인
if st.session_state["user"]["is_logged_in"]:
    user_email = st.session_state["user"]["email"]
    df = pd.DataFrame(sh.worksheet("LoginList").get_all_records())
    user_row = df[df["email"] == user_email]
    if not user_row.empty:
        user_role = user_row.iloc[0]["role"]
        st.session_state["user_role"] = user_role
        st.session_state["user_email"] = user_email
        # 프로필 사진, 이메일, 권한, 로그아웃 버튼
        col1, col2, col3, col4 = st.columns([1,3,3,2])
        user_info = st.session_state["user"]
        with col1:
            if "picture" in user_info:
                st.image(user_info["picture"], width=48)
        with col2:
            st.markdown(f"**ID:** {user_email}")
        with col3:
            st.markdown(f"**권한:** {user_role}")
        with col4:
            if st.button("Log out"):
                st.logout()
    else:
        col1, col2 = st.columns([4,1])
        col1.error(f"{user_email}은 등록되지 않은 사용자입니다.")
        if col2.button("로그아웃"):
            st.logout()
        # 등록 신청 시트 불러오기
        registration_ws = load_registration(sh)
        
        # 등록 신청 섹션
        st.markdown("---")
        st.subheader("📝 등록 신청")
         
        # 등록 신청서 입력
        request_text = st.text_input(
            "선생님 성함 혹은 학생의 학번+이름과 신청사유를 간단히 작성해 주세요.", 
            placeholder="예: IBEC 관리 업무를 위해 시스템 접근 / 권한변경 필요합니다.",
            help="""자료: admin, vvip, teacher ,ibec //
                    공문목록: admin, teacher, ibec //
                    상담일지: admin, teacher,ibec //
                    IBEC: admin, ibec //
                    권한변경 및 등록이 필요한 이유를 한 줄로 작성해주세요.""",
            key="request_text_input"
        )
        
        # 등록 신청 버튼
        if st.button("등록신청", type="primary"):
            if request_text.strip():
                try:
                    # 중복 신청 체크
                    existing_requests = registration_ws.get_all_records()
                    already_requested = any(row.get("email") == user_email for row in existing_requests)
                    if already_requested:
                        st.warning("⚠️ 이미 신청된 아이디입니다. 관리자 승인을 기다려주세요.")
                    else:
                        user_name = st.session_state["user"].get("name", "이름없음")
                        success = save_registration_request(registration_ws, request_text, user_email, user_name)
                        if success:
                            st.success("✅ 등록 신청이 완료되었습니다. 관리자 승인을 기다려주세요.")
                            st.info("💡 승인 후 다시 로그인해주세요.")
                        else:
                            st.error("❌ 등록 신청 중 오류가 발생했습니다.")
                except Exception as e:
                    st.error(f"❌ 등록 신청 중 오류가 발생했습니다: {str(e)}")
            else:
                st.warning("⚠️ 등록 신청 사유를 입력해주세요.")
        
        
        st.stop()

# ------------------- 게시판/자료실 UI 및 권한별 접근 제어 -------------------

    # 관리자만 수정 UI 제공
    if user_role in ['admin', 'semiadmin']:
        st.subheader('게시판 목록')
        st.write('게시판 목록을 확인하고 권한을 설정할 수 있습니다.')
        for board in board_roles:
            options = ['admin', 'semiadmin', 'vvip', 'teacher', 'student', 'ibec']
            selected = st.multiselect(f"'{board}' 허용 등급", options, default=board_roles[board], key=f"edit_{board}")
            if set(selected) != set(board_roles[board]):
                board_roles[board] = selected
                updated = True
        if st.button("권한 변경 저장"):
            save_board_roles(board_roles_ws, board_roles)
            st.success('권한 설정이 저장되었습니다.')
            st.rerun()
    elif user_role in ['teacher', 'ibec', 'vvip', 'student']:
        # Display board_roles in a styled format
        st.subheader('게시판 목록')
        html_content = """
        <style>
            .board-table {
                width: 100%;
                border-collapse: collapse;
            }
            .board-table th, .board-table td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            .board-table th {
                background-color: #f2f2f2;
                color: black;
            }
            .board-table tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .board-table tr:hover {
                background-color: #ddd;
            }
        </style>
        <table class="board-table">
            <thead>
                <tr>
                    <th>Board</th>
                    <th>Roles</th>
                </tr>
            </thead>
            <tbody>
        """
        for board, roles in board_roles.items():
            html_content += f"<tr><td>{board}</td><td>{', '.join(roles)}</td></tr>"
        html_content += """
            </tbody>
        </table>
        """
        st.markdown(html_content, unsafe_allow_html=True)
        
