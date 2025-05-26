import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io
import gspread
import datetime

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
data_allowed_roles = st.session_state['board_roles']["IBEC"]

st.header("IBEC 관련자료")
if user_role not in data_allowed_roles:
    st.info("권한이 없는 사용자입니다. 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    st.write("IBEC에 관련된 자료를 연결하겠습니다.")

    # Check or create the IBEC sheet
    SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"
    try:
        ibec_ws = gc.open_by_key(SHEET_ID).worksheet("IBEC")
    except gspread.exceptions.WorksheetNotFound:
        ibec_ws = gc.open_by_key(SHEET_ID).add_worksheet(title="IBEC", rows=100, cols=5)
        ibec_ws.append_row(["User", "Text", "URL", "Attachment ID", "Date"])

    # Form for posting
    with st.expander("IBEC 새글작성"):
        if user_role in data_allowed_roles:
            with st.form("ibec_post_form"):
                post_text = st.text_area("글 내용")
                post_url = st.text_input("URL (선택)")
                post_file = st.file_uploader("파일 첨부 (선택)", type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx"])
                submit_post = st.form_submit_button("게시")

            if submit_post:
                # Upload file to Google Drive
                attachment_id = ""
                if post_file is not None:
                    # Determine the MIME type
                    mime_type = post_file.type if post_file.type else 'application/octet-stream'
                    file_metadata = {'name': post_file.name, 'parents': ['1CF5E6h5ZsXBG__0VB5v1Y54IRBdK3WgC']}
                    file_stream = io.BytesIO(post_file.read())
                    media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
                    try:
                        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        attachment_id = file.get('id')
                    except Exception as e:
                        st.error(f"파일 업로드 중 오류가 발생했습니다: {e}")

                # Append post to Google Sheet with current date
                current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                ibec_ws.append_row([user_email, post_text, post_url, attachment_id, current_date])
                st.success("게시물이 저장되었습니다.")
                st.rerun()

    # Display posts
    st.subheader("게시물 목록")
    st.markdown("---")
    ibec_records = ibec_ws.get_all_records()
    # Reverse the order to show the most recent posts first
    for index, record in enumerate(reversed(ibec_records)):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**작성자:** {record['User']}")
            st.markdown(f"**작성일:** {record['Date']}")
            st.info(f"**{record['Text']}**")
            if record['URL']:
                st.markdown(f"[{record['URL']}]({record['URL']})")
            if record['Attachment ID']:
                st.markdown(f"[첨부파일 다운로드](https://drive.google.com/uc?id={record['Attachment ID']})")
        
        with col2:
            # Add delete button for the author
            if record['User'] == user_email:
                if st.button("삭제", key=f"delete_{index}"):
                    ibec_ws.delete_rows(index + 2)  # Adjust for header row
                    st.success("게시물이 삭제되었습니다.")
                    st.rerun()
        st.markdown("---")



