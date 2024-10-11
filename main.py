import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import os
import cv2
import numpy as np
import threading
import librosa
import soundfile as sf
import tempfile
import shutil

class TkinterDnDCustomTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class VideoSegmentExtractor(TkinterDnDCustomTk):
    def __init__(self):
        super().__init__()
        self.title("JayaVcut")
        self.geometry("800x900")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.local_video_path = None
        self.segments = []
        self.temp_dir = None
        
        self.create_widgets()





    
    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        
        # Drop area
        self.drop_frame = ctk.CTkFrame(self)
        self.drop_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.drop_frame.grid_columnconfigure(0, weight=1)
        
        self.video_file_label = ctk.CTkLabel(self.drop_frame, text="Drag and drop a video file here", height=100)
        self.video_file_label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        # Make the label a drop target
        self.video_file_label.drop_target_register(DND_FILES)
        self.video_file_label.dnd_bind('<<Drop>>', self.drop)
        
        # Buttons
        self.generate_button = ctk.CTkButton(self, text="Generates", command=self.start_processing)
        self.generate_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(self, text="", text_color="blue")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)
        
        # Sliders
        self.motion_threshold_slider = ctk.CTkSlider(self, from_=0, to=1, number_of_steps=100, command=self.update_motion_threshold)
        self.motion_threshold_slider.grid(row=3, column=0, padx=20, pady=10)
        self.motion_threshold_slider.set(0.5)
        
        self.motion_threshold_label = ctk.CTkLabel(self, text="Motion Threshold: 0.50")
        self.motion_threshold_label.grid(row=4, column=0, padx=20, pady=5)
        
        self.audio_threshold_slider = ctk.CTkSlider(self, from_=0, to=1, number_of_steps=100, command=self.update_audio_threshold)
        self.audio_threshold_slider.grid(row=5, column=0, padx=20, pady=10)
        self.audio_threshold_slider.set(0.05)
        
        self.audio_threshold_label = ctk.CTkLabel(self, text="Audio Threshold: 0.05")
        self.audio_threshold_label.grid(row=6, column=0, padx=20, pady=5)
        
        # Scrollable frame for segments
        self.segments_frame = ctk.CTkScrollableFrame(self, label_text="Generated Segments")
        self.segments_frame.grid(row=7, column=0, padx=20, pady=20, sticky="nsew")
        self.grid_rowconfigure(7, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=8, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.grid(row=9, column=0, padx=20, pady=5)




    def update_motion_threshold(self, value):
        self.motion_threshold_label.configure(text=f"Motion Threshold: {value:.2f}")
    
    def update_audio_threshold(self, value):
        self.audio_threshold_label.configure(text=f"Audio Threshold: {value:.2f}")
    
    def drop(self, event):
        self.local_video_path = event.data
        self.video_file_label.configure(text=f"Video File: {os.path.basename(self.local_video_path)}")





    
    def start_processing(self):
        if not self.local_video_path:
            messagebox.showerror("Input Error", "Please drag and drop a video file.")
            return
        
        motion_threshold = self.motion_threshold_slider.get()
        audio_threshold = self.audio_threshold_slider.get()
        
        self.status_label.configure(text="Processing...")
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_video_thread, args=(motion_threshold, audio_threshold), daemon=True).start()






    def process_video_thread(self, motion_threshold, audio_threshold):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = self.analyze_video(self.local_video_path, motion_threshold, audio_threshold)
        
        # Extract only the most attractive segments
        total_segments = len(self.segments)
        for i, segment in enumerate(self.segments):
            temp_output_file = os.path.join(self.temp_dir, f"attractive_segment_{i+1}.mp4")
            ffmpeg_extract_subclip(self.local_video_path, segment['start'], segment['end'], targetname=temp_output_file)
            segment['file'] = temp_output_file
            
            # Update progress
            progress = (i + 1) / total_segments
            self.update_progress(progress)

        # Update UI in the main thread
        self.after(0, self.update_ui_after_processing)






    def update_ui_after_processing(self):
        if self.segments:
            for widget in self.segments_frame.winfo_children():
                widget.destroy()
            
            for i, segment in enumerate(self.segments):
                segment_frame = ctk.CTkFrame(self.segments_frame)
                segment_frame.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
                
                segment_label = ctk.CTkLabel(segment_frame, text=f"Attractive Segment {i + 1} (Score: {segment['score']:.2f})")
                segment_label.grid(row=0, column=0, padx=5, pady=5)
                
                save_button = ctk.CTkButton(segment_frame, text="Save", command=lambda s=segment['file']: self.save_segment(s))
                save_button.grid(row=0, column=1, padx=5, pady=5)
                
                preview_button = ctk.CTkButton(segment_frame, text="Preview", command=lambda s=segment['file']: self.preview_segment(s))
                preview_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.status_label.configure(text="Processing complete! Showing most attractive segments.")




    
    def save_segment(self, segment_file):
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if save_path:
            shutil.copy2(segment_file, save_path)
            messagebox.showinfo("Save Successful", f"Segment saved to {save_path}")




    
    def preview_segment(self, segment_file):
        if os.path.isfile(segment_file):
            os.startfile(segment_file)
        else:
            messagebox.showerror("Preview Error", "Segment file does not exist.")





    def analyze_motion(self, video, start_time, end_time):
        cap = cv2.VideoCapture(video)
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
        
        ret, prev_frame = cap.read()
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        motion_scores = []
        
        while cap.get(cv2.CAP_PROP_POS_MSEC) <= end_time * 1000:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion_score = np.mean(magnitude)
            motion_scores.append(motion_score)
            
            prev_gray = gray
        
        cap.release()
        return np.mean(motion_scores) if motion_scores else 0





    def analyze_audio(self, video, start_time, end_time):
        try:
            audio = video.audio.subclip(start_time, end_time)
            if audio is None:
                print(f"No audio found for segment {start_time}-{end_time}")
                return 0

            # Create a temporary file to save the audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
                temp_filename = temp_audio_file.name

            # Write audio to the temporary file
            audio.write_audiofile(temp_filename, logger=None)

            # Read the audio file using soundfile
            samples, sample_rate = sf.read(temp_filename)

            # Remove the temporary file
            os.unlink(temp_filename)

            print(f"Audio shape: {samples.shape}, Sample rate: {sample_rate}")
            
            if samples.ndim == 2:
                samples = samples.mean(axis=1)  # Convert stereo to mono
            
            return np.mean(np.abs(samples))
        except Exception as e:
            print(f"Error in analyze_audio: {str(e)}")
            print(f"Audio object type: {type(audio)}")
            if hasattr(audio, 'fps'):
                print(f"Audio FPS: {audio.fps}")
            if hasattr(audio, 'duration'):
                print(f"Audio duration: {audio.duration}")
            
            # Fallback method: use librosa to load audio directly from video file
            try:
                y, sr = librosa.load(video.filename, offset=start_time, duration=end_time-start_time)
                print(f"Librosa audio shape: {y.shape}, Sample rate: {sr}")
                return np.mean(np.abs(y))
            except Exception as e:
                print(f"Error in librosa fallback: {str(e)}")
                return 0  # Return 0 if all methods fail





    def update_progress(self, progress):
        self.after(0, lambda: self.progress_bar.set(progress))
        self.after(0, lambda: self.progress_label.configure(text=f"{int(progress * 100)}%"))





    def analyze_video(self, video_file, motion_threshold, audio_threshold):
        video = VideoFileClip(video_file)
        duration = video.duration
        segment_duration = 15  # 15-second segments
        
        segments = []
        total_segments = int(duration) // segment_duration + 1
        for i, start_time in enumerate(range(0, int(duration), segment_duration)):
            end_time = min(start_time + segment_duration, duration)
            
            motion_score = self.analyze_motion(video_file, start_time, end_time)
            audio_score = self.analyze_audio(video, start_time, end_time)
            
            attractiveness_score = motion_score + audio_score
            print(f"Segment {start_time}-{end_time}: Motion={motion_score}, Audio={audio_score}, Attractiveness={attractiveness_score}")
            
            segments.append({
                'start': start_time,
                'end': end_time,
                'score': attractiveness_score
            })
            
            # Update progress
            progress = (i + 1) / total_segments
            self.update_progress(progress)
        
        video.close()
        return self.filter_attractive_segments(segments)







    def process_video(self, local_video_path, motion_threshold, audio_threshold):
        segments = self.analyze_video(local_video_path, motion_threshold, audio_threshold)
        
        output_segments = []
        for i, (start, end) in enumerate(segments):
            output_file = f"segment_{i+1}.mp4"
            ffmpeg_extract_subclip(local_video_path, start, end, targetname=output_file)
            output_segments.append(output_file)
        
        return output_segments





    def filter_attractive_segments(self, segments, top_percentage=20):
        # Sort segments by score in descending order
        sorted_segments = sorted(segments, key=lambda x: x['score'], reverse=True)
        
        # Calculate the number of segments to keep
        num_keep = max(1, int(len(sorted_segments) * top_percentage / 100))
        
        # Return the top segments
        return sorted_segments[:num_keep]





    def __del__(self):
        # Clean up temporary directory when the application closes
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)






if __name__ == "__main__":
    app = VideoSegmentExtractor()
    app.mainloop()