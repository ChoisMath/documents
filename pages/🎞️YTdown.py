import streamlit as st
import os
import time
import tempfile
import yt_dlp
from pathlib import Path # pathlib을 사용하는 것이 좋습니다.

def main():
    st.set_page_config(
        page_title="ChoisYTD",
        page_icon="🎬",
        layout="centered"
    )
    
    st.title("🎬 YT Downloader by Chois")
    st.write("Youtube 영상을 MP4 파일로 다운로드하세요! 영상 정보를 가져오는데 시간이 조금 걸릴 수 있습니다.")
    
    # Youtube URL 입력
    url = st.text_input("Youtube URL을 입력하세요:")
    
    # 임시 디렉토리 설정
    temp_dir = tempfile.gettempdir()
    
    if url:
        try:
            # 비디오 정보 가져오기
            with st.spinner("영상 정보를 가져오는 중..."):
                video_info = get_video_info(url)
            
            if video_info:
                # 영상 정보 표시
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video_info.get('thumbnail'), width=200, caption="썸네일")
                
                with col2:
                    st.subheader(video_info.get('title', '제목 없음'))
                    st.write(f"**채널:** {video_info.get('uploader', '알 수 없음')}")
                    st.write(f"**길이:** {format_duration(video_info.get('duration', 0))}")
                    if 'view_count' in video_info:
                        st.write(f"**조회수:** {format_views(video_info.get('view_count', 0))}")
                
                # 사용 가능한 형식 표시 및 해상도 리스트 반환
                available_resolutions = show_available_formats(video_info)
                if available_resolutions:
                    selected_resolution = st.selectbox("화질을 선택하세요:", available_resolutions)
                else:
                    st.warning("다운로드 가능한 MP4 화질이 없습니다.")
                    selected_resolution = None
                
                # 다운로드 버튼 (선택된 해상도가 있을 때만 활성화)
                if selected_resolution:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if st.button("파일만들기"):
                            # video_info에서 제목을 가져오되, 없을 경우 기본값 사용
                            video_title = video_info.get('title', 'youtube_video')
                            download_path_str = download_video(url, selected_resolution, temp_dir, video_title)
                            
                            if download_path_str:
                                download_path = Path(download_path_str) # 문자열을 Path 객체로 변환
                                if download_path.exists():
                                    with open(download_path, "rb") as file:
                                        with col2:
                                            st.download_button(
                                                label="MP4 파일 다운로드",
                                                data=file,
                                                file_name=f"{download_path.name}", # Path 객체에서 파일 이름 사용
                                                mime="video/mp4",
                                            )
                                    st.success(f"'{download_path.name}' 다운로드 준비 완료! 위 버튼을 클릭하여 다운로드하세요.")
                                else:
                                    st.error("다운로드된 파일을 찾을 수 없습니다. 다시 시도해 주세요.")
                            else:
                                st.error("선택한 화질로 다운로드할 수 없습니다. 다른 화질을 선택하거나 URL을 확인해 주세요.")
            else:
                # get_video_info에서 이미 오류 메시지를 표시했을 수 있음
                st.warning("영상 정보를 가져오지 못했습니다. URL을 확인하거나 잠시 후 다시 시도해 주세요.")
        
        except Exception as e:
            st.error(f"알 수 없는 오류가 발생했습니다: {str(e)}")
            # 개발/디버깅 목적으로 콘솔에 전체 오류 로깅
            print(f"Main function error: {e}", exc_info=True)

def get_video_info(url):
    """yt-dlp를 사용하여 비디오 정보를 가져옵니다"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True, # 단일 영상 다운로드를 위해 플레이리스트 처리 방지
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except yt_dlp.utils.DownloadError as e:
        st.error(f"영상 정보 로딩 중 오류 발생 (yt-dlp): {str(e)}. URL이 정확한지, 영상이 공개 상태인지 확인해주세요.")
        print(f"yt-dlp DownloadError in get_video_info: {e}") # 서버 로그용
        return None
    except Exception as e:
        st.error(f"영상 정보 로딩 중 알 수 없는 오류 발생: {str(e)}")
        print(f"Unexpected error in get_video_info: {e}") # 서버 로그용
        return None

def show_available_formats(video_info):
    """사용 가능한 MP4 형식을 표시하고, 해상도 리스트를 반환합니다."""
    available_resolutions = []
    displayed_resolutions = set()  # 이미 표시된 해상도를 추적하기 위한 set
    if 'formats' in video_info:
        st.write("---")
        st.write("#### 사용 가능한 MP4 스트림 (비디오+오디오)")
        # 비디오 스트림만 필터링 (오디오가 없어도 됨)
        mp4_formats = [
            f for f in video_info['formats'] 
            if f.get('ext') == 'mp4' and 
               f.get('vcodec') != 'none' and
               f.get('height') is not None
        ]
        if mp4_formats:
            # 높이 기준으로 내림차순 정렬
            sorted_formats = sorted(mp4_formats, key=lambda x: (x.get('height', 0), x.get('filesize', 0) or float('inf')), reverse=True)
            for fmt in sorted_formats:
                resolution = f"{fmt.get('height')}p"
                if resolution not in displayed_resolutions:  # 아직 표시되지 않은 해상도만 처리
                    displayed_resolutions.add(resolution)  # 해상도를 표시된 목록에 추가
                    available_resolutions.append(resolution)
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                    format_note = fmt.get('format_note', '')
                    fps = f", {fmt.get('fps')}fps" if fmt.get('fps') else ""
                    display_text = f"• {resolution} ({format_note}{fps})"
                    if filesize:
                        filesize_str = format_size(filesize)
                        display_text += f", 예상 크기: {filesize_str}"
                    st.write(display_text)
        else:
            st.write("결합된 MP4 형식으로 다운로드할 수 있는 스트림을 찾을 수 없습니다. (영상 또는 오디오만 있는 스트림은 제외됩니다)")
        st.write("---")
    return available_resolutions

def download_video(url, resolution, temp_dir, title):
    """yt-dlp를 사용하여 유튜브 영상을 다운로드합니다"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    resolution_num = resolution.replace('p', '')
    # format_str: 선택한 해상도 이하의 비디오와 오디오를 결합
    format_str = (
        f'bestvideo[height<={resolution_num}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_num}][ext=mp4]'
        f'/best[height<={resolution_num}][ext=mp4]'
        f'/best[ext=mp4]' # 해상도 무관 MP4
        f'/best' # 최후의 수단
    )
    
    # 안전한 파일명 생성 (Pathlib 사용 권장)
    safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else "_" for c in title])
    safe_title = safe_title.replace(' ', '_') # 공백을 밑줄로 변경
    output_filename = f"{safe_title}_{resolution}.mp4"
    output_path = Path(temp_dir) / output_filename # pathlib 사용

    # 이전 다운로드 파일이 있다면 삭제 (선택 사항)
    if output_path.exists():
        try:
            output_path.unlink()
        except OSError as e:
            status_text.warning(f"기존 파일 삭제 실패: {e}. 덮어쓸 수 있습니다.")

    class ProgressHook:
        def __init__(self):
            self.start_time = time.time()
            
        def __call__(self, d):
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                if total_bytes > 0:
                    percentage = downloaded_bytes / total_bytes
                    progress_bar.progress(percentage)
                    
                    elapsed = time.time() - self.start_time
                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                    
                    status_text.text(
                        f"{percentage:.1%} 다운로드 중... "
                        f"({format_size(downloaded_bytes)}/{format_size(total_bytes)}, "
                        f"{format_size(speed)}/s)"
                    )
            elif d['status'] == 'finished':
                status_text.text(f"다운로드 완료! 파일명: {d.get('filename', output_path.name)}. 후처리 중일 수 있습니다...")
                progress_bar.progress(1.0) # Ensure progress bar is full
            elif d['status'] == 'error':
                status_text.error(f"다운로드 중 오류 발생 (yt-dlp hook): {d.get('error', '알 수 없는 오류')}")
                print(f"yt-dlp hook error: {d}") # 서버 로그용

    progress_hook = ProgressHook()
    
    ydl_opts = {
        'format': format_str,
        'outtmpl': str(output_path), # yt-dlp는 문자열 경로를 기대
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'postprocessors': [{ # MP4로 확실히 변환하기 위한 설정
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # 'verbose': True, # 디버깅 시 상세 로그 출력
    }
    
    try:
        status_text.text(f"{resolution} 화질로 다운로드를 시도합니다...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 다운로드가 성공적으로 완료되었는지 확인
        if output_path.exists() and output_path.stat().st_size > 0:
            status_text.success(f"'{output_path.name}' 다운로드 및 처리 완료!")
            return str(output_path)
        else:
            # 이 경우는 yt-dlp가 오류를 발생시키지 않았지만 파일이 생성되지 않은 경우
            status_text.error("다운로드 후 파일이 생성되지 않았거나 파일 크기가 0입니다. 다른 화질을 시도하거나 로그를 확인하세요.")
            if not output_path.exists():
                 print(f"Download finished but output file {output_path} does not exist.")
            elif output_path.stat().st_size == 0:
                 print(f"Download finished but output file {output_path} is empty.")
            return None

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        status_text.error(f"다운로드 실패 (yt-dlp): {error_message}")
        if "ffmpeg" in error_message.lower() or "postprocessing" in error_message.lower():
            st.info("이 오류는 ffmpeg이 설치되지 않았거나 경로가 올바르지 않을 때 발생할 수 있습니다. "
                    "MP4 변환 및 일부 고화질 다운로드에는 ffmpeg이 필요합니다.")
        print(f"yt-dlp DownloadError in download_video: {e}") # 서버 로그용
        return None
    except Exception as e:
        status_text.error(f"다운로드 중 알 수 없는 오류 발생: {str(e)}")
        print(f"Unexpected error in download_video: {e}", exc_info=True) # 서버 로그용
        return None

def format_duration(seconds_total):
    """초를 시:분:초 형식으로 변환"""
    if not isinstance(seconds_total, (int, float)) or seconds_total < 0:
        return "알 수 없음"
    seconds_total = int(seconds_total)
    hours = seconds_total // 3600
    minutes = (seconds_total % 3600) // 60
    seconds = seconds_total % 60
    
    if hours > 0:
        return f"{hours}시간 {minutes}분 {seconds}초"
    elif minutes > 0:
        return f"{minutes}분 {seconds}초"
    else:
        return f"{seconds}초"

def format_views(views):
    """조회수를 읽기 쉬운 형식으로 변환"""
    if not isinstance(views, (int, float)) or views < 0:
        return "알 수 없음"
    views = int(views)
    if views >= 1_000_000_000: # 10억
        return f"{views / 1_000_000_000:.1f}B" # Billion
    if views >= 1_000_000: # 100만
        return f"{views / 1_000_000:.1f}M" # Million
    elif views >= 1_000: # 1천
        return f"{views / 1_000:.1f}K" # Kilo
    else:
        return str(views)

def format_size(size_bytes):
    """바이트를 읽기 쉬운 형식으로 변환"""
    if not isinstance(size_bytes, (int, float)) or size_bytes < 0:
        return "0 B"
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"



if __name__ == "__main__":
    # Streamlit 앱을 실행하려면 터미널에서 `streamlit run your_script_name.py` 명령을 사용하세요.
    # 이 부분은 직접 실행 시에는 동작하지 않으며, Streamlit이 main()을 호출합니다.
    # 로그인/권한 정보 불러오기
    user_role = st.session_state.get("user_role")
    user_email = st.session_state.get("user_email")

# ------------------- 상담일지 기능 -------------------
    data_allowed_roles =  st.session_state['board_roles']["상담일지"]
    if user_role in data_allowed_roles:
        main()
    else:
        st.error("권한이 없습니다.")
