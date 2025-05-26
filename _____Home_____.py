import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 환경변수 또는 secrets.toml에 저장 권장
CLIENT_ID = st.secrets["GOOGLE_n8n"]["CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_n8n"]["CLIENT_SECRET"]
#REDIRECT_URI = "http://localhost:8501/oauth2callback"
REDIRECT_URI = "https:/knuibec.streamlit.app/oauth2callback"

# Google OAuth2 설정
oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token"
)

# 로그인 버튼
if "user" not in st.session_state:
    token = oauth2.authorize_button(
        "Google로 로그인",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile"
    )
    if token:
        # access_token 추출
        access_token = None
        if isinstance(token, dict):
            if "access_token" in token:
                access_token = token["access_token"]
            elif "token" in token and "access_token" in token["token"]:
                access_token = token["token"]["access_token"]

        if access_token:
            userinfo_response = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_response.status_code == 200:
                user_info = userinfo_response.json()
                st.session_state["user"] = user_info
               # Extract and display user's name
                user_name = user_info.get('name', '')
                st.session_state["user_name"] = user_name
            else:
                st.error("사용자 정보를 가져오지 못했습니다.")
        else:
            st.error("access_token이 없습니다.")
    else:
        st.warning("로그인 해주세요.")
else:
    user_info = st.session_state["user"]
    st.success(f"로그인됨: {st.session_state['user_name']}")


# 구글 서비스 계정 인증 및 스프레드시트 열기
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(credentials)

SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"  # 실제 사용 중인 시트 ID로 맞추세요
sh = gc.open_by_key(SHEET_ID)

# 4. 데이터 읽기 (pandas DataFrame으로 변환)
if "sheet_data" not in st.session_state:
    data = sh.sheet1.get_all_records()
    st.session_state["sheet_data"] = data
else:
    data = st.session_state["sheet_data"]
df = pd.DataFrame(data)

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

# board_roles 불러오기
board_roles, board_roles_ws = load_board_roles(sh)
# Store board_roles in session_state for access across pages
st.session_state['board_roles'] = board_roles

# 5. 로그인한 사용자 이메일로 권한 확인

if "user" in st.session_state:
    user_email = st.session_state["user"]["email"]
    user_row = df[df["email"] == user_email]
    if not user_row.empty:
        user_role = user_row.iloc[0]["role"]
        st.session_state["user_role"] = user_role
        st.session_state["user_email"] = user_email
        # 프로필 사진, 이메일, 권한, 로그아웃 버튼
        col1, col2, col3, col4 = st.columns([1,3,3,2])
        with col1:
            if "picture" in user_info:
                st.image(user_info["picture"], width=48)
        with col2:
            st.markdown(f"**ID:** {user_info['email']}")
        with col3:
            st.markdown(f"**권한:** {user_role}")
        with col4:
            if st.button("로그아웃"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    else:
        col1, col2 = st.columns([4,1])
        col1.error(f"{user_email}은 등록되지 않은 사용자입니다. 관리자에게 문의하세요.")
        if col2.button("로그아웃"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        else:
            pass
        st.stop()

# ------------------- 게시판/자료실 UI 및 권한별 접근 제어 -------------------

    # 관리자만 수정 UI 제공
    if user_role == 'admin':
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
    elif user_role == 'teacher' or user_role == 'ibec' or user_role == 'vvip':
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
