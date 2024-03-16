from datetime import datetime
import math
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import av
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from threading import Thread


class FinishLine:

    window = tk.Tk()
    window.title("Finish Line")
    tab_control = ttk.Notebook(window)
    tab_1 = ttk.Frame(tab_control)
    tab_2 = ttk.Frame(tab_control)

    tab_control.add(tab_1, text="Preview")
    tab_control.add(tab_2, text="Results")
    tab_control.pack(expand=1, fill="both")

    canvas = None
    line_pos = 0
    line_pos_rotate = 0
    rotation = 0

    start_time = datetime.now()
    fps = 30

    preview_canvas_frame = ttk.Frame(tab_1)
    preview_canvas_frame.pack(expand=True, fill=tk.BOTH)

    result_canvas = None
    result_canvas_frame = ttk.Frame(tab_2)
    result_canvas_frame.pack(expand=True, fill=tk.BOTH)

    out_image = None

    # For tracking which radio button is selected
    direction = tk.IntVar(value=1)

    # For the progress bar
    progress = tk.IntVar(value=0)

    # An array for holding all UI widgets that will need to be disabled
    # during processing
    ui_widgets = []

    # For setting the users preferred timezone. Default to -7 cause that's
    # where I live.
    utc_offset = tk.IntVar(value=-7)

    def rotate_ccw(self):
        """Rotates the finish line counter clockwise"""
        self.line_pos_rotate += 5
        self.canvas.coords(
            self.line,
            self.line_pos - self.line_pos_rotate,
            0,
            self.line_pos + self.line_pos_rotate,
            self.height,
        )

    def rotate_cw(self):
        """Rotates the finish line clockwise"""
        self.line_pos_rotate -= 5
        self.canvas.coords(
            self.line,
            self.line_pos - self.line_pos_rotate,
            0,
            self.line_pos + self.line_pos_rotate,
            self.height,
        )

    def rotate_image_cw(self):
        """Rotates the preview image 90 degress clockwise"""
        self.rotation -= 90
        self.preview_image = self.preview_image.rotate(-90, expand=True)
        self.redraw()

    def rotate_image_ccw(self):
        """Rotates the preview image 90 degress counter clockwise"""
        self.rotation += 90
        self.preview_image = self.preview_image.rotate(90, expand=True)
        self.redraw()

    def redraw(self):
        """Redraws the preview image and finish line after rotating the preview image"""
        height = self.height
        self.height = self.width
        self.width = height
        self.line_pos = int(self.width / 2)
        self.tk_image = ImageTk.PhotoImage(self.preview_image)
        self.canvas.itemconfig(self.preview, image=self.tk_image)
        self.canvas.coords(
            self.line,
            self.line_pos - self.line_pos_rotate,
            0,
            self.line_pos + self.line_pos_rotate,
            self.height,
        )
        self.preview_slider.config(to=self.width, length=self.width)
        self.preview_slider.set(self.line_pos)
        self.update_preview_slider()
        self.canvas.config(scrollregion=(0, 0, self.width, self.height))
        self.canvas.pack()
        
    def get_rotate_theta(self):
        """Returns the current rotation angle of the finish line in degrees"""
        return math.atan2(self.line_pos_rotate, self.height / 2) * 180 / math.pi

    def process(self):
        """Constructs the result image from the video and the finish line. Fills in the 
        results tab with the result, the finish line, and UI elements."""
        container = av.open(self.file)
        num_frames = container.streams.video[0].frames
        out = Image.new("RGB", (num_frames, self.height), (255, 255, 255))
        frame_num = 0
        theta = self.get_rotate_theta()
        container.streams.video[0].thread_type = "AUTO"
        for frame in container.decode(video=0):
            image = frame.to_image()
            if theta or self.rotation:
                image = image.rotate(-theta + self.rotation, expand=True)
            line = image.crop((self.line_pos, 0, self.line_pos + 1, self.height))
            if self.direction.get() > 0:
                x = num_frames - frame_num - 1
            else:
                x = frame_num

            out.paste(line, (x, 0, x + 1, self.height))
            self.progress.set(int(100 * frame_num / num_frames))
            frame_num += 1

        if self.direction.get() > 0:
            from_ = out.width
            to = 0
        else:
            from_ = 0
            to = out.width

        if not self.result_canvas:
            self.result_canvas = tk.Canvas(
                self.result_canvas_frame, scrollregion=(0, 0, out.width, out.height)
            )
            self.result_hbar = ttk.Scrollbar(
                self.result_canvas_frame, orient=tk.HORIZONTAL
            )
            self.result_hbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.result_hbar.config(command=self.result_canvas.xview)

            self.result_vbar = ttk.Scrollbar(
                self.result_canvas_frame, orient=tk.VERTICAL
            )
            self.result_vbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.result_vbar.config(command=self.result_canvas.yview)

            self.result_canvas.config(
                xscrollcommand=self.result_hbar.set, yscrollcommand=self.result_vbar.set
            )

            self.slider = tk.Scale(
                self.result_canvas_frame,
                from_=from_,
                to=to,
                orient=tk.HORIZONTAL,
                length=out.width,
                command=self.update_cursor,
            )
            self.slider.pack(side=tk.TOP, anchor=tk.NW)

            self.stats_frame = ttk.Frame(self.tab_2)
            self.stats_frame.pack()

            self.save_btn = ttk.Button(self.stats_frame, text="Save", command=self.save)
            self.save_btn.grid(row=3, column=0)

        else:
            self.result_canvas.delete("all")
            self.result_canvas.config(scrollregion=(0, 0, out.width, out.height))
            self.slider.config(from_=from_, to=to, length=out.width)

        self.tk_image_result = ImageTk.PhotoImage(out)
        self.out_image = out

        self.result = self.result_canvas.create_image(
            0, 0, anchor=tk.NW, image=self.tk_image_result
        )
        if self.direction.get() > 0:
            x = out.width - self.slider.get()
        else:
            x = self.slider.get()

        self.cursor = self.result_canvas.create_line(x, 0, x, out.height, width=1, fill="#ffffff")
        self.result_canvas.pack(expand=True, fill=tk.BOTH)

        self.start_label = ttk.Label(
            self.stats_frame, text=f"Start Time: "
        )
        self.start_label.grid(row=0, column=0)

        self.start_entry = ttk.Entry(self.stats_frame)
        self.start_entry.insert(3, f"{self.start_time.strftime('%H:%M:%S')}")
        self.start_entry.grid(row=0, column=1)

        self.cursor_label = ttk.Label(
            self.stats_frame, text=f"Current Position: {self.get_cursor_time()}"
        )
        self.cursor_label.grid(row=0, column=2)

        self.fps_label = ttk.Label(self.stats_frame, text="FPS: ")
        self.fps_label.grid(row=1, column=0)
        self.fps_entry = ttk.Entry(self.stats_frame)
        self.fps_entry.insert(3, f"{self.fps}")
        self.fps_entry.grid(row=1, column=1)

        self.update_btn = ttk.Button(
            self.stats_frame, text="Update", command=self.update_stats
        )
        self.update_btn.grid(row=1, column=2)

        self.resolution_label = ttk.Label(
            self.stats_frame,
        )
        self.resolution_label.grid(row=2, column=0)
        self.update_stats()
        self.process_finished()

    def process_finished(self):
        # Move to the results tab
        self.tab_control.select(1)

        # Re-enable disabled widgets
        for widget in self.ui_widgets:
            widget.config(state="normal")

    def update_stats(self):
        """Updates the result tab's stats based on the inputs from the UI"""
        self.fps = int(float(self.fps_entry.get()))
        self.resolution_label.config(text=f"1 px = {round(1 / self.fps, 6)} seconds")
        self.start_time = parse(self.start_entry.get())
        self.update_cursor()

    def get_cursor_time(self):
        """returns the time at which the result cursor is located in the result image"""
        if self.out_image:
            seconds_from_start = self.slider.get() / self.fps
            return (
                self.start_time + relativedelta(seconds=seconds_from_start)
            ).strftime("%H:%M:%S.%f")

    def update_cursor(self, *args, **kwargs):
        """Updates the location of the cursor on the result tab"""
        if self.direction.get() > 0:
            x = self.out_image.width - self.slider.get()
        else:
            x = self.slider.get()

        self.result_canvas.coords(self.cursor, x, 0, x, self.out_image.height)

        self.cursor_label.config(text=f"Current Position: {self.get_cursor_time()}")

    def save(self):
        """Save dialog for saving the result image"""
        filename = f"Results"
        file = filedialog.asksaveasfile(
            mode="w", defaultextension=".jpg", initialfile=filename
        )
        if file:
            self.out_image.save(file)
            file.close()

    def get_first_frame_from_video(self):
        """Opens the video's first frame and extracts some metadata for later use.
        Returns the first frame as an image."""
        container = av.open(self.file)
        self.metadata = container.metadata
        self.length_seconds = container.duration / 10**6
        self.playback_framerate = int(str(container.streams.video[0].base_rate))

        start_time_str = self.metadata.get("creation_time", "")
        if start_time_str:
            self.start_time = parse(start_time_str)
            self.start_time += relativedelta(hours=self.utc_offset.get())

            if fps := self.metadata.get("com.android.capture.fps"):
                self.fps = int(float(fps))
                self.finish_time = self.start_time + relativedelta(
                    seconds=self.length_seconds / (self.fps / self.playback_framerate)
                )
            else:
                self.fps = 30

        for frame in container.decode(video=0):
            return frame.to_image()

    def load_preview(self, preview_image):
        """Given the preview image, draws it onto the canvas. Draws the finish line. Creates the
        slider control for the finish line."""
        self.tk_image = ImageTk.PhotoImage(preview_image)
        self.preview = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.line = self.canvas.create_line(
            self.line_pos, 0, self.line_pos, self.height, width=1, tags="line", fill="#ffffff"
        )
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.preview_slider = tk.Scale(
            self.preview_canvas_frame,
            from_=0,
            to=preview_image.width,
            orient=tk.HORIZONTAL,
            length=preview_image.width,
            command=self.update_preview_slider,
        )
        self.preview_slider.set(round(preview_image.width / 2))
        self.preview_slider.pack(side=tk.TOP, anchor=tk.NW)
        self.ui_widgets.append(self.preview_slider)

    def update_preview_slider(self, *args, **kwargs):
        self.line_pos = self.preview_slider.get()
        self.canvas.coords(
            self.line,
            self.line_pos - self.line_pos_rotate,
            0,
            self.line_pos + self.line_pos_rotate,
            self.height,
        )

    def load_video(self):
        """Opens a file select dialog for the user to select a video. Loads a preview image
        into the canvas. Draws the finish line and slider controls."""
        self.rotation = 0
        self.file = filedialog.askopenfilename()
        if not self.file:
            return
        
        self.preview_image = self.get_first_frame_from_video()
        self.width, self.height = self.preview_image.size
        self.line_pos = self.width / 2
        if self.canvas:
            self.canvas.delete("all")
            self.canvas.config(scrollregion=(0, 0, self.width, self.height))

        else:
            self.canvas = tk.Canvas(
                self.preview_canvas_frame, scrollregion=(0, 0, self.width, self.height)
            )
            self.preview_hbar = ttk.Scrollbar(
                self.preview_canvas_frame, orient=tk.HORIZONTAL,
            )
            self.preview_hbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.preview_hbar.config(command=self.canvas.xview)

            self.preview_vbar = ttk.Scrollbar(
                self.preview_canvas_frame, orient=tk.VERTICAL
            )
            self.preview_vbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.preview_vbar.config(command=self.canvas.yview)

            self.canvas.config(
                xscrollcommand=self.preview_hbar.set,
                yscrollcommand=self.preview_vbar.set,
            )

        self.load_preview(self.preview_image)

    def process_clicked(self):
        # Start the processing in its own thread so that we don't lock up the window
        # and we can draw the progress bar.
        for widget in self.ui_widgets:
            widget.config(state="disabled")

        Thread(target=self.process).start()

    def main(self):
        """Draws the UI and starts the main tkinter loop"""
        rotate_frame = ttk.Frame(self.tab_1)
        load_video_btn = ttk.Button(
            rotate_frame, text="Load Video", width=30, command=self.load_video
        )
        self.ui_widgets.append(load_video_btn)
        load_video_btn.pack(fill=tk.Y, side=tk.LEFT)
        rotate_image_ccw_btn = ttk.Button(
            rotate_frame,
            text="Rotate Video 90 deg CCW",
            width=30,
            command=self.rotate_image_ccw,
        )
        self.ui_widgets.append(rotate_image_ccw_btn)
        rotate_image_ccw_btn.pack(fill=tk.Y, side=tk.LEFT)

        rotate_image_cw_btn = ttk.Button(
            rotate_frame,
            text="Rotate Video 90 deg CW",
            width=30,
            command=self.rotate_image_cw,
        )
        self.ui_widgets.append(rotate_image_cw_btn)
        rotate_image_cw_btn.pack(fill=tk.Y, side=tk.LEFT)

        rotate_frame.pack(fill=tk.X, side=tk.TOP)

        line_frame = ttk.Frame(self.tab_1)
        rotate_ccw_btn = ttk.Button(
            line_frame,
            text="Rotate Line CCW",
            width=20,
            command=self.rotate_ccw,
        )
        self.ui_widgets.append(rotate_ccw_btn)
        rotate_ccw_btn.pack(fill=tk.Y, side=tk.LEFT)

        rotate_cw_btn = ttk.Button(
            line_frame,
            text="Rotate Line CW",
            width=20,
            command=self.rotate_cw,
        )
        self.ui_widgets.append(rotate_cw_btn)
        rotate_cw_btn.pack(fill=tk.Y, side=tk.LEFT)

        line_frame.pack(fill=tk.X, side=tk.TOP)

        radio_frame = ttk.Frame(self.tab_1)
        radio_frame.pack(fill=tk.X, side=tk.TOP)
        radio_label = tk.Label(radio_frame, text="Direction of travel")
        radio_label.pack(fill=tk.X, side=tk.LEFT)
        radio_1 = tk.Radiobutton(
            radio_frame, text="Left to Right", variable=self.direction, value=1
        )
        self.ui_widgets.append(radio_1)
        radio_1.pack(fill=tk.X, side=tk.LEFT)
        radio_2 = tk.Radiobutton(
            radio_frame, text="Right to Left", variable=self.direction, value=-1
        )
        self.ui_widgets.append(radio_2)
        radio_2.pack(fill=tk.X, side=tk.LEFT)

        utc_offset_frame = ttk.Frame(self.tab_1)
        utc_offset_frame.pack(fill=tk.X, side=tk.TOP)
        utc_label = tk.Label(utc_offset_frame, text="UTC Offset")
        utc_label.pack(fill=tk.X, side=tk.LEFT)
        
        utc_offset = ttk.Spinbox(utc_offset_frame, from_=-24, to=24, wrap=True, textvariable=self.utc_offset)
        utc_offset.pack(fill=tk.X, side=tk.LEFT)

        process_frame = ttk.Frame(self.tab_1)
        process_btn = ttk.Button(
            process_frame, text="GO!", width=10, command=self.process_clicked
        )
        self.ui_widgets.append(process_btn)
        process_btn.pack(fill=tk.X, side=tk.LEFT)
        progress_bar = ttk.Progressbar(process_frame, length=300, variable=self.progress, maximum=100)
        progress_bar.pack(fill=tk.X, side=tk.LEFT)
        process_frame.pack(fill=tk.X, side=tk.TOP)

        tk.mainloop()


if __name__ == "__main__":
    finish_line = FinishLine()
    finish_line.main()
