import os

def write_transcripts_to_file(directory, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                file_path = os.path.join(directory, filename)
                with open(file_path, 'r', encoding='utf-8') as infile:
                    # Write the video title (filename without extension)
                    video_title = os.path.splitext(filename)[0]
                    outfile.write(f"Title: {video_title}\n")
                    
                    # Write the transcript content
                    transcript = infile.read()
                    outfile.write(transcript + "\n\n")

# Usage
directory_path = 'transcripts/Spencer Benterud/transcripts'
output_file_path = 'Spencer-Benterud-transcripts.txt'
write_transcripts_to_file(directory_path, output_file_path)