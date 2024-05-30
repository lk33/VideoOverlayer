import os
import sys
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

class VideoProcessor:
    # Supported resolutions
    resolutions = {
        '360p': '640x360',
        '480p': '854x480',
        '720p': '1280x720',
        '1080p': '1920x1080'
    }

    def __init__(self, video_path):
        self.video_path = video_path
        self.is_hdr = self.check_hdr()
        self.duration = self.get_duration()
        self.frame_rate = self.get_frame_rate()

    def check_hdr(self):
        try:
            # Run ffprobe command to get color information
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=color_space,color_transfer,color_primaries',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip().split('\n')
            
            # Check if the video has HDR attributes
            hdr_formats = ['bt2020', 'smpte2084', 'arib-std-b67', 'bt2020nc']  # HDR color formats
            for line in output:
                if any(fmt in line for fmt in hdr_formats):
                    return True
            return False
        except Exception as e:
            print(f"Error checking HDR with ffprobe: {e}")
            return False

    def get_duration(self):
        """
        Get the duration of the video using ffprobe.
        """
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1',
                self.video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            duration = float(result.stdout.decode().strip())
            return duration
        except Exception as e:
            print(f"Error getting duration: {e}")
            return None

    def get_frame_rate(self):
        """
        Get the frame rate of the video using ffprobe.
        """
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=r_frame_rate', '-of', 'default=nw=1:nk=1',
                self.video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            r_frame_rate = result.stdout.decode().strip()
            num, denom = map(int, r_frame_rate.split('/'))
            frame_rate = num / denom
            return frame_rate
        except Exception as e:
            print(f"Error getting frame rate: {e}")
            return None

    def draw_circle(self, color, x, y, radius):
        """
        Create a filter graph to draw a circle using drawtext filter.
        """
        return f"drawtext=text='o':x={x}:y={y}:fontsize={radius*2}:fontcolor={color}:alpha=0.5"

    def transcode_and_overlay(self, resolution, hdr):
        """
        Transcode the video to the specified resolution and overlay a colored circle.
        """
        try:
            width, height = map(int, self.resolutions[resolution].split('x'))
            overlay_color = 'green' if hdr else 'white'
            circle_radius = int(0.07 * height) if hdr else int(0.05 * height)
            overlay_position_x = int(width - circle_radius)
            overlay_position_y = int(height * 0.07) if hdr else int(height - circle_radius)
            
            circle_filter = self.draw_circle(overlay_color, overlay_position_x, overlay_position_y, circle_radius)

            output_filename = f"{os.path.splitext(os.path.basename(self.video_path))[0]}_{resolution}{'_HDR' if hdr else '_SDR'}.mp4"
            output_path = os.path.join('output', output_filename)

            ffmpeg_cmd = [
                'ffmpeg', '-i', self.video_path,
                '-vf', f"scale={width}:{height},{circle_filter}",
                '-c:v', 'libx265', '-crf', '28', '-preset', 'medium',
                '-r', str(self.frame_rate),  # Enforce same frame rate
                '-c:a', 'aac', '-b:a', '128k',
                '-t', str(self.duration),  # Ensure the same duration
                output_path
            ]
            
            result = subprocess.run(ffmpeg_cmd, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"Error during transcoding: {result.stderr.decode()}")
            
            return output_path
        except Exception as e:
            print(f"Error in transcode_and_overlay: {e}")
            return None

class Bento4Packager:
    @staticmethod
    def package(input_paths):
        """
        Package the videos using Bento4 tools for fragmentation and DASH packaging.
        """
        try:
            output_dir = 'output'
            fragmented_paths = []
            for input_path in input_paths:
                fragmented_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}-fragmented.mp4")
                mp4fragment_cmd = f"mp4fragment --fragment-duration 7000 {input_path} {fragmented_path}"
                result = subprocess.run(mp4fragment_cmd, shell=True, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    raise RuntimeError(f"Error during mp4fragment: {result.stderr.decode()}")
                fragmented_paths.append(fragmented_path)
            
            # Debug: print fragmented paths
            print("Fragmented files created:", fragmented_paths)
            
            mp4_files = " ".join(fragmented_paths)
            mp4dash_cmd = f"mp4dash -o {output_dir}/output_dash {mp4_files}"
            result = subprocess.run(mp4dash_cmd, shell=True, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"Error during mp4dash: {result.stderr.decode()}")
        except Exception as e:
            print(f"Error in Bento4Packager: {e}")

def main(video_path):
    """
    Main function to process the video: transcode to different resolutions and package.
    """
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        sys.exit(1)
    
    os.makedirs('output', exist_ok=True)
    
    processor = VideoProcessor(video_path)
    print(f"Is HDR: {processor.is_hdr}")
    
    transcoded_files = []

    with ProcessPoolExecutor() as executor:
        # Submit transcoding tasks
        transcoding_futures = []
        for res in VideoProcessor.resolutions:
            transcoding_futures.append(executor.submit(processor.transcode_and_overlay, res, processor.is_hdr))
            if processor.is_hdr:
                transcoding_futures.append(executor.submit(processor.transcode_and_overlay, res, False))
        
        # Wait for all transcoding tasks to complete
        for future in as_completed(transcoding_futures):
            try:
                result = future.result()
                if result:
                    transcoded_files.append(result)
            except Exception as exc:
                print(f"Error during transcoding: {exc}")

        # Package all transcoded files into a single DASH package
        try:
            Bento4Packager.package(transcoded_files)
        except Exception as exc:
            print(f"Error during packaging: {exc}")

if __name__ == "__main__":
    start_time = time.time()
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_video_file>")
        sys.exit(1)
    video_path = sys.argv[1]
    main(video_path)
    print("duration:",time.time()-start_time)