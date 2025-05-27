import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io

# 구글 서비스 계정 인증
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# 로그인/권한 정보 불러오기
user_role = st.session_state.get("user_role")
# user_email = st.session_state.get("user_email") # 좋아요 삭제로 직접 사용되지 않음

#권한 확인하기
# st.session_state에 board_roles가 없을 경우를 대비한 기본값 설정
if 'board_roles' not in st.session_state or not isinstance(st.session_state['board_roles'], dict):
    st.error("게시판 권한 정보가 올바르게 로드되지 않았습니다. 홈 화면으로 돌아가거나 관리자에게 문의하세요.")
    st.stop()
    data_allowed_roles = [] # 빈 리스트로 초기화하여 이후 코드 실행 방지
else:
    data_allowed_roles = st.session_state['board_roles'].get("자료", [])

st.header("자료실")
if user_role not in data_allowed_roles:
    st.info("권한이 없는 사용자입니다. 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    folder_id = '1ahi_xExDjtil5df7oCyMCH1l7A5aj_w-' 

    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType)"
    ).execute()
    files = results.get('files', [])

    if files:
        col_header1, col_header2 = st.columns([4, 1])
        col_header1.markdown("##파일 이름")
        col_header2.markdown("##다운로드")
        st.markdown("---")

        for file in files:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(file['name'])
            
            with col2:
                mime = file.get('mimeType', '')
                if mime.startswith('application/vnd.google-apps.'):
                    if mime == 'application/vnd.google-apps.folder':
                        st.write("-") # 폴더는 다운로드 제공 안 함
                    else:
                        export_mime_type = 'application/pdf'
                        export_file_name = f"{file['name']}.pdf"
                        try:
                            request = drive_service.files().export_media(fileId=file['id'], mimeType=export_mime_type)
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while not done:
                                _, done = downloader.next_chunk()
                            fh.seek(0)
                            st.download_button(
                                label="PDF로 다운로드",
                                data=fh,
                                file_name=export_file_name,
                                mime=export_mime_type,
                                key=f"export_{file['id']}"
                            )
                        except Exception as e:
                            # st.error(f"Export 오류: {e}") # 상세 오류 대신 간단한 메시지
                            st.write("-") # 오류 시 다운로드 불가 표시
                elif file.get('id'): 
                    try:
                        request = drive_service.files().get_media(fileId=file['id'])
                        fh = io.BytesIO()
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            _, done = downloader.next_chunk()
                        fh.seek(0)
                        st.download_button(
                            label="다운로드",
                            data=fh,
                            file_name=file['name'],
                            mime=mime if mime else 'application/octet-stream',
                            key=f"download_{file['id']}"
                        )
                    except Exception as e:
                        # st.error(f"다운로드 오류: {e}") # 상세 오류 대신 간단한 메시지
                        st.write("-") # 오류 시 다운로드 불가 표시
                else:
                    st.write("-")
            st.markdown("---")

    else:
        st.info("폴더에 파일이 없습니다.")
