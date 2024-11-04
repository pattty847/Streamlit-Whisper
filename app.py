import streamlit as st
import whisper
import moviepy.editor as mp
import os
import yt_dlp
import instaloader
from werkzeug.utils import secure_filename
import tempfile

# Set page configuration
st.set_page_config(page_title="Video Transcription App", layout="centered")

# Initialize session state for the Whisper model
if 'whisper_model' not in st.session_state:
    st.session_state.whisper_model = whisper.load_model("base")

def download_yt_video(url, output_path_base):
    ydl_opts = {
        'outtmpl': output_path_base + '.%(ext)s',
        'format': 'bestvideo+bestaudio/best'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.download([url])
    # Find the file with the final extension
    downloaded_files = [f for f in os.listdir(os.path.dirname(output_path_base)) 
                       if f.startswith(os.path.basename(output_path_base))]
    if downloaded_files:
        return os.path.join(os.path.dirname(output_path_base), downloaded_files[0])
    return None

def download_instagram_video(url, output_path_base):
    L = instaloader.Instaloader(download_videos=True, download_comments=False, 
                              save_metadata=False)
    try:
        post = instaloader.Post.from_shortcode(L.context, url.split('/')[-2])
        L.download_post(post, target=output_path_base)
        # Find the downloaded video file
        downloaded_files = [f for f in os.listdir(output_path_base) 
                          if f.endswith('.mp4')]
        if downloaded_files:
            return os.path.join(output_path_base, downloaded_files[0])
    except Exception as e:
        st.error(f"Error downloading Instagram video: {e}")
    return None

def extract_audio_and_transcribe(video_path):
    with st.spinner('Extracting audio from video...'):
        # Create temporary file for audio
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio_path = temp_audio.name
        
        # Extract audio from video
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(temp_audio_path)
        video.close()
        audio.close()

    with st.spinner('Transcribing audio...'):
        # Transcribe audio
        result = st.session_state.whisper_model.transcribe(temp_audio_path)
        
        # Clean up temporary file
        os.unlink(temp_audio_path)
        
        return result["text"]

def main():
    st.title("Video Transcription App")
    st.write("Upload a video file or provide a URL to get its transcript")

    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["Upload File", "Video URL"])

    with tab1:
        uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'avi', 'mov'])
        if uploaded_file is not None:
            # Create a temporary file to store the uploaded video
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_video.write(uploaded_file.read())
            video_path = temp_video.name
            
            if st.button("Transcribe Uploaded Video"):
                transcript = extract_audio_and_transcribe(video_path)
                
                # Clean up temporary file
                os.unlink(video_path)
                
                # Display results
                st.subheader("Transcript")
                st.text_area("", transcript, height=300)
                
                # Download button
                st.download_button(
                    label="Download Transcript",
                    data=transcript,
                    file_name="transcript.txt",
                    mime="text/plain"
                )

    with tab2:
        video_url = st.text_input("Enter video URL (YouTube, Instagram)")
        if video_url:
            if st.button("Transcribe from URL"):
                with st.spinner('Downloading video...'):
                    # Create temporary directory for downloaded content
                    temp_dir = tempfile.mkdtemp()
                    output_path_base = os.path.join(temp_dir, "downloaded_video")
                    
                    if "instagram.com" in video_url:
                        video_path = download_instagram_video(video_url, temp_dir)
                    else:
                        video_path = download_yt_video(video_url, output_path_base)
                    
                    if video_path:
                        transcript = extract_audio_and_transcribe(video_path)
                        
                        # Clean up temporary files
                        os.unlink(video_path)
                        os.rmdir(temp_dir)
                        
                        # Display results
                        st.subheader("Transcript")
                        st.text_area("", transcript, height=300)
                        
                        # Download button
                        st.download_button(
                            label="Download Transcript",
                            data=transcript,
                            file_name="transcript.txt",
                            mime="text/plain"
                        )
                    else:
                        st.error("Failed to download video")

if __name__ == "__main__":
    main()
