import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io
import gspread
import datetime
import re
import urllib.parse
import tempfile
from io import BytesIO
import time

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
                post_file = st.file_uploader("파일 첨부 (선택, 한글포함파일 업로드 불가)", type=["png", "jpg", "jpeg", "pdf", "docx", "xlsx"])
                submit_post = st.form_submit_button("게시")

            if submit_post:
                attachment_id = ""
                if post_file is not None:
                    # 디버깅 정보 추가
                    st.write("--- 디버깅 정보 시작 ---")
                    st.write(f"원본 파일명: {post_file.name}")
                    st.write(f"Streamlit이 감지한 파일 타입: {post_file.type}")

                    # 안전한 파일명 생성 (한글 문제 완전 해결)
                    def create_safe_filename(original_name):
                        # 파일명과 확장자 분리
                        name_parts = original_name.rsplit('.', 1)
                        if len(name_parts) == 2:
                            filename, extension = name_parts
                        else:
                            filename = original_name
                            extension = ""
                        
                        # 타임스탬프 생성 (고유성 보장)
                        timestamp = int(time.time())
                        
                        # 한글이 포함된 경우 완전히 새로운 파일명 생성
                        if re.search(r'[가-힣]', filename):
                            # 한글 파일의 경우 타임스탬프 기반 파일명 사용
                            safe_name = f"file_{timestamp}"
                        else:
                            # 영문 파일의 경우 안전한 문자만 유지
                            safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', filename)
                            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
                            if not safe_name:
                                safe_name = f"file_{timestamp}"
                        
                        # 파일명 길이 제한 (Google Drive 제한 고려)
                        if len(safe_name) > 50:
                            safe_name = safe_name[:50]
                        
                        # 최종 파일명 조합
                        if extension:
                            # 확장자도 안전하게 처리
                            safe_extension = re.sub(r'[^a-zA-Z0-9]', '', extension.lower())
                            return f"{safe_name}.{safe_extension}"
                        else:
                            return safe_name
                    
                    safe_filename = create_safe_filename(post_file.name)
                    st.write(f"생성된 안전한 파일명: {safe_filename}")

                    # 파일 메타데이터 생성 (ASCII 문자만 사용)
                    file_metadata = {
                        'name': safe_filename, 
                        'parents': ['1CF5E6h5ZsXBG__0VB5v1Y54IRBdK3WgC']
                    }
                    st.write(f"파일 메타데이터: {file_metadata}")
                    
                    # 파일 콘텐츠를 메모리에서 읽기
                    try:
                        file_stream = BytesIO(post_file.getvalue())
                        st.write(f"파일 크기: {len(post_file.getvalue())} bytes")
                        
                        # MIME 타입 안전하게 처리
                        mime_type = post_file.type if post_file.type else 'application/octet-stream'
                        st.write(f"MIME 타입: {mime_type}")
                        
                        media = MediaIoBaseUpload(file_stream, mimetype=mime_type)
                        
                        st.write("Google Drive에 파일 생성을 시도합니다...")
                        
                        # API 호출
                        file = drive_service.files().create(
                            body=file_metadata, 
                            media_body=media, 
                            fields='id, name'
                        ).execute()
                        
                        attachment_id = file.get('id')
                        uploaded_name = file.get('name')
                        
                        st.write(f"파일 생성 성공! ID: {attachment_id}")
                        st.write(f"업로드된 파일명: {uploaded_name}")
                        st.success(f'✅ 파일이 성공적으로 업로드되었습니다!')
                        st.info(f"원본: {post_file.name} → 저장됨: {uploaded_name}")
                        
                    except Exception as e:
                        error_message = f"파일 업로드 중 오류 발생: {str(e)}"
                        
                        # Google API 오류 상세 정보 추출
                        if hasattr(e, 'content'):
                            try:
                                error_details = e.content.decode('utf-8')
                                error_message += f"\nAPI 오류 상세: {error_details}"
                            except Exception:
                                pass
                        
                        # HTTP 오류 코드 확인
                        if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                            error_message += f"\nHTTP 상태 코드: {e.resp.status}"
                        
                        st.error(error_message)
                        st.write("--- 디버깅 정보 끝 ---")
                        st.stop()
                        
                    st.write("--- 디버깅 정보 끝 ---")
                else:
                    st.write("파일이 선택되지 않았습니다.")

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
            # 제목(글 내용) 먼저 크게
            st.markdown(f"<div style='font-size:1.1em; font-weight:bold; margin-bottom:2px;'>{record['Text']}</div>", unsafe_allow_html=True)
            # 작성자/작성일을 제목 아래에 작게, 회색으로
            st.markdown(f"<div style='color:#888; font-size:0.9em; margin-bottom:6px;'>작성자: {record['User']} | 작성일: {record['Date']}</div>", unsafe_allow_html=True)
            # URL 및 첨부파일
            if record['URL']:
                st.markdown(f"<div style='margin-bottom:2px;'><a href='{record['URL']}' target='_blank'>{record['URL']}</a></div>", unsafe_allow_html=True)
            if record['Attachment ID']:
                st.markdown(f"<div style='margin-bottom:2px;'><a href='https://drive.google.com/uc?id={record['Attachment ID']}' target='_blank'>[첨부파일 다운로드]</a></div>", unsafe_allow_html=True)
        
        with col2:
            # Add delete button for the author
            if record['User'] == user_email:
                if st.button("삭제", key=f"delete_{index}"):
                    ibec_ws.delete_rows(index + 2)  # Adjust for header row
                    st.success("게시물이 삭제되었습니다.")
                    st.rerun()
        st.markdown("---")



