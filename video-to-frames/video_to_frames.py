import customtkinter as ctk
import cv2
from tkinter import filedialog
import os
from PIL import Image
import threading
from dataclasses import dataclass
from typing import Optional, Callable, Tuple  # 添加 Tuple 导入
import logging
import subprocess

@dataclass
class VideoProcessConfig:
    video_path: str
    output_path: Optional[str]
    fps: float
    frame_format: str = 'jpg'
    
class VideoProcessor:
    def __init__(self, config: VideoProcessConfig, progress_callback: Callable[[float], None]):
        self.config = config
        self.progress_callback = progress_callback
        
    def process(self) -> Tuple[bool, str]:  # 修改这里，使用 Tuple 而不是 tuple
        try:
            cap = cv2.VideoCapture(self.config.video_path)
            if not cap.isOpened():
                return False, "无法打开视频文件"
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 添加对fps的检查和处理
            if self.config.fps <= 0:
                return False, "每秒提取帧数必须大于0"
            if self.config.fps > video_fps:
                return False, f"每秒提取帧数不能大于视频帧率({video_fps})"
                
            frame_interval = max(1, int(video_fps / self.config.fps))
            
            # 设置输出目录
            output_dir = self._get_output_directory()
            os.makedirs(output_dir, exist_ok=True)
            
            current_frame = 0
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if current_frame % frame_interval == 0:
                    self._save_frame(frame, output_dir, frame_count)
                    frame_count += 1
                    
                current_frame += 1
                self.progress_callback(current_frame / total_frames)
                
            cap.release()
            # 保存输出目录路径用于后续打开
            self.last_output_dir = output_dir
            return True, f"处理完成！共导出 {frame_count} 帧"
            
        except Exception as e:
            logging.exception("处理视频时发生错误")
            return False, f"错误: {str(e)}"
            
    def _get_output_directory(self) -> str:
        if self.config.output_path:
            return os.path.join(
                self.config.output_path, 
                os.path.splitext(os.path.basename(self.config.video_path))[0] + "_frames"
            )
        return os.path.splitext(self.config.video_path)[0] + "_frames"
        
    def _save_frame(self, frame, output_dir: str, frame_count: int):
        frame_path = os.path.join(
            output_dir, 
            f"frame_{frame_count:04d}.{self.config.frame_format}"
        )
        # 使用 imencode 和 imwrite 的组合来支持中文路径
        _, img_encoded = cv2.imencode(f'.{self.config.frame_format}', frame)
        img_encoded.tofile(frame_path)

class VideoToFramesGUI:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("视频分帧工具")
        self.app.geometry("800x600")
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self._init_ui()
        
    def _init_ui(self):
        # 主容器
        self.main_frame = ctk.CTkFrame(self.app)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # 标题区域
        self._create_title_section()
        
        # 文件选择区域
        self._create_file_section()
        
        # 设置区域
        self._create_settings_section()
        
        # 状态和控制区域
        self._create_control_section()
        
    def _create_title_section(self):
        title_frame = ctk.CTkFrame(self.main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="视频分帧工具",
            font=("Arial", 24, "bold")
        ).pack(pady=10)
        
    def _create_file_section(self):
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", pady=(0, 20))
        
        # 视频选择
        video_frame = ctk.CTkFrame(file_frame)
        video_frame.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkButton(
            video_frame,
            text="选择视频文件",
            command=self._select_video
        ).pack(side="left", padx=5)
        
        self.file_label = ctk.CTkLabel(
            video_frame,
            text="未选择文件",
            wraplength=500
        )
        self.file_label.pack(side="left", padx=5, fill="x", expand=True)
        
        # 输出目录选择
        output_frame = ctk.CTkFrame(file_frame)
        output_frame.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkButton(
            output_frame,
            text="选择输出目录",
            command=self._select_output_dir
        ).pack(side="left", padx=5)
        
        self.output_label = ctk.CTkLabel(
            output_frame,
            text="默认: 与视频相同目录",
            wraplength=500
        )
        self.output_label.pack(side="left", padx=5, fill="x", expand=True)
        
    def _create_settings_section(self):
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", pady=(0, 20))
        
        # FPS设置
        fps_frame = ctk.CTkFrame(settings_frame)
        fps_frame.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkLabel(
            fps_frame,
            text="每秒提取帧数:"
        ).pack(side="left", padx=5)
        
        self.fps_entry = ctk.CTkEntry(fps_frame, width=100)
        self.fps_entry.insert(0, "1")
        self.fps_entry.pack(side="left", padx=5)
        
        # 输出格式选择
        format_frame = ctk.CTkFrame(settings_frame)
        format_frame.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkLabel(
            format_frame,
            text="输出格式:"
        ).pack(side="left", padx=5)
        
        self.format_var = ctk.StringVar(value="jpg")
        ctk.CTkRadioButton(
            format_frame,
            text="JPG",
            variable=self.format_var,
            value="jpg"
        ).pack(side="left", padx=5)
        
        ctk.CTkRadioButton(
            format_frame,
            text="PNG",
            variable=self.format_var,
            value="png"
        ).pack(side="left", padx=5)
        
    def _create_control_section(self):
        control_frame = ctk.CTkFrame(self.main_frame)
        control_frame.pack(fill="x", pady=(0, 20))
        
        self.progress_bar = ctk.CTkProgressBar(control_frame)
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="就绪",
            font=("Arial", 12)
        )
        self.status_label.pack(pady=5)
        
        self.start_button = ctk.CTkButton(
            control_frame,
            text="开始处理",
            command=self._start_processing
        )
        self.start_button.pack(pady=10)
        
    def _select_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv")]
        )
        if path:
            self.video_path = path
            self.file_label.configure(text=path)
            
    def _select_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path = path
            self.output_label.configure(text=path)
            
    def _update_progress(self, progress: float):
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"处理中... {int(progress * 100)}%")
        
    def _start_processing(self):
        if not hasattr(self, 'video_path'):
            self.status_label.configure(text="请先选择视频文件！")
            return
            
        self.start_button.configure(state="disabled")
        self.status_label.configure(text="正在处理...")
        self.progress_bar.set(0)
        
        config = VideoProcessConfig(
            video_path=self.video_path,
            output_path=getattr(self, 'output_path', None),
            fps=float(self.fps_entry.get()),
            frame_format=self.format_var.get()
        )
        
        self.processor = VideoProcessor(config, self._update_progress)  # 修改这里，将 processor 赋值给 self.processor
        
        def process_thread():
            success, message = self.processor.process()  # 现在可以正确访问 self.processor
            self.app.after(0, self._process_complete, success, message)
            
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()
        
    def _process_complete(self, success: bool, message: str):
        self.status_label.configure(text=message)
        self.start_button.configure(state="normal")
        self.progress_bar.set(1 if success else 0)
        
        # 如果处理成功，打开输出文件夹
        if success and hasattr(self.processor, 'last_output_dir'):
            # 确保路径存在并且是绝对路径
            output_dir = os.path.abspath(self.processor.last_output_dir)
            if os.path.exists(output_dir):
                subprocess.run(['explorer', output_dir], shell=True)
        
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    app = VideoToFramesGUI()
    app.run()