import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials
import io
import gspread

# 구글 서비스 계정 인증
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)
gc = gspread.authorize(credentials)


# 로그인/권한 정보 불러오기
user_role = st.session_state.get("user_role")
user_email = st.session_state.get("user_email")

#권한 확인하기기
data_allowed_roles = st.session_state['board_roles']["자료"]

st.header("자료실")
if user_role not in data_allowed_roles:
    st.info("권한이 없는 사용자입니다. 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    # 폴더 ID 하드코딩
    folder_id = '1ahi_xExDjtil5df7oCyMCH1l7A5aj_w-'

    # 스프레드시트 설정
    SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"
    sh = gc.open_by_key(SHEET_ID)

    # 좋아요 정보 시트 열기
    try:
        likes_ws = sh.worksheet("file_likes")
    except gspread.exceptions.WorksheetNotFound:
        likes_ws = sh.add_worksheet(title="file_likes", rows=100, cols=3)
        likes_ws.append_row(["file_id", "user_email", "user_name"])


    # 파일 목록 조회
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType, webViewLink, webContentLink, thumbnailLink)"
    ).execute()
    files = results.get('files', [])

    if files:
        cols = st.columns(3)  # 3-column grid
        for i, file in enumerate(files):
            col = cols[i % 3]
            with col:
                thumbnail_link = file.get('thumbnailLink', '')
                if thumbnail_link:
                    st.image(thumbnail_link, width=150)
                else:
                    st.write("[썸네일 없음]")  # Placeholder text or image
                st.write(f"**{file['name']}**")
                mime = file.get('mimeType', '')
                if mime.startswith('application/vnd.google-apps.') and mime != 'application/vnd.google-apps.folder':
                    view_link = file.get('webViewLink')
                    if view_link:
                        st.markdown(f"[Google Docs 열기]({view_link})", unsafe_allow_html=True)
                    else:
                        st.write("링크 없음")
                elif file.get('webContentLink'):
                    href = file['webContentLink']
                    if "?" in href:
                        href += "&export=download"
                    else:
                        href += "?export=download"
                    st.markdown(f"[다운로드]({href})", unsafe_allow_html=True)
                else:
                    st.write("다운로드 불가")

                # 좋아요 버튼
                user_email = st.session_state.get("user_email")
                user_name = st.session_state.get("user").get("name") if "user" in st.session_state else "Unknown"
                if user_email:
                    likes = likes_ws.get_all_records()
                    liked_users = [like['user_email'] for like in likes if like['file_id'] == file['id']]
                    if user_email not in liked_users:
                        if st.button(f"좋아요 ({len(liked_users)})", key=f"like_{file['id']}"):
                            likes_ws.append_row([file['id'], user_email, user_name])
                            st.rerun()
                    else:
                        st.write(f"좋아요 ({len(liked_users)})")
                    # 좋아요 누른 사용자 명단
                    # st.write("좋아요 누른 사용자:")
                    # for like in likes:
                    #     if like['file_id'] == file['id']:
                    #         st.write(f"- {like['user_name']} ({like['user_email']})")
                else:
                    st.warning("로그인이 필요합니다.")
    else:
        st.info("폴더에 파일이 없습니다.")

    # 파일 업로드
    st.subheader("파일 업로드")
    uploaded_file = st.file_uploader("업로드할 파일을 선택하세요")
    if uploaded_file is not None:
        media = MediaFileUpload(uploaded_file.name, mimetype=uploaded_file.type, resumable=True)
        file_metadata = {
            'name': uploaded_file.name,
            'parents': [folder_id]
        }
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        drive_service.files().create(
            body=file_metadata,
            media_body=uploaded_file.name,
            fields='id'
        ).execute()
        st.success("파일이 업로드되었습니다.")
        st.rerun()
