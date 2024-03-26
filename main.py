from datetime import datetime
import math
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import av
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from threading import Thread
import time
from multiprocessing import Pool, freeze_support
import numpy as np


DEFAULT_BIB_TIMES_FILENAME = "bib_times.csv"


class BibTimes:
    def __init__(self):
        self.bib_times = []
        self.bib_results_filename = DEFAULT_BIB_TIMES_FILENAME

    def add(self, bib_time):
        self.bib_times.append(bib_time)
        self.bib_times = sorted(self.bib_times, key=lambda bib_time: bib_time[1])
        try:
            filename, extension = self.bib_results_filename.split(".")
        except Exception:
            filename = self.bib_results_filename
            extension = "csv"

        with open(f"{filename}.csv", "w") as out_file:
            for bib_time in self.bib_times:
                out_file.write(f"{bib_time[0]}, {bib_time[1]}\n")


class Result:
    def __init__(
            self, tab_control, out, direction, start_time, fps, bib_times
        ):
        self.tab = ttk.Frame(tab_control)
        self.tab_control = tab_control
        self.tab_control.add(self.tab, text=f'{start_time.strftime(".   %H:%M:%S   .")}')
        self.result_canvas = None
        self.result_canvas_frame = ttk.Frame(self.tab)
        self.result_canvas_frame.pack(expand=True, fill=tk.BOTH)
        self.fps = fps
        self.start_time = start_time
        self.direction = direction
        self.bib_times = bib_times
        if direction > 0:
            from_ = out.width
            to = 0
        else:
            from_ = 0
            to = out.width

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

        self.stats_frame = ttk.Frame(self.tab)
        self.stats_frame.pack()

        self.save_btn = ttk.Button(self.stats_frame, text="Save", command=self.save)
        self.save_btn.grid(row=3, column=0)

        self.tk_image_result = ImageTk.PhotoImage(out)
        self.out_image = out

        self.result = self.result_canvas.create_image(
            0, 0, anchor=tk.NW, image=self.tk_image_result
        )
        if direction > 0:
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
            self.stats_frame, text=f"Current Position"
        )
        self.cursor_label.grid(row=0, column=2)

        self.cursor_position =ttk.Label(
            self.stats_frame, text=f"{self.get_cursor_time()}"
        )
        self.cursor_position.grid(row=0, column=3)

        self.fps_label = ttk.Label(self.stats_frame, text="FPS: ")
        self.fps_label.grid(row=1, column=0)
        self.fps_entry = ttk.Entry(self.stats_frame)
        self.fps_entry.insert(3, f"{self.fps}")
        self.fps_entry.grid(row=1, column=1)

        self.bib_number_label = ttk.Label(self.stats_frame, text="Bib number")
        self.bib_number_label.grid(row=1, column=2)

        self.bib_number = ttk.Entry(self.stats_frame)
        self.bib_number.grid(row=1, column=3)

        self.enter_btn = ttk.Button(
            self.stats_frame, text="Enter number", command=self.enter_number
        )
        self.enter_btn.grid(row=1, column=4)

        self.update_btn = ttk.Button(
            self.stats_frame, text="Update", command=self.update_stats
        )
        self.update_btn.grid(row=2, column=1)

        self.resolution_label = ttk.Label(
            self.stats_frame,
        )
        self.resolution_label.grid(row=2, column=0)
        self.update_stats()

    def get_name(self):
        resolution = round(1 / self.fps, 6)
        duration = self.out_image.width * resolution
        end_time = self.start_time + relativedelta(seconds=duration)
        return f'{self.start_time.strftime("%H:%M:%S")} - {end_time.strftime("%H:%M:%S")}'

    def update_stats(self):
        """Updates the result tab's stats based on the inputs from the UI"""
        self.fps = int(float(self.fps_entry.get()))
        resolution = round(1 / self.fps, 6)
        self.resolution_label.config(text=f"1 px = {resolution} seconds")
        self.start_time = parse(self.start_entry.get())
        self.tab_control.tab(self.tab, text=self.get_name())
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
        if self.direction > 0:
            x = self.out_image.width - self.slider.get()
        else:
            x = self.slider.get()

        self.result_canvas.coords(self.cursor, x, 0, x, self.out_image.height)

        self.cursor_position.config(text=f"{self.get_cursor_time()}")

    def save(self):
        """Save dialog for saving the result image"""
        filename = f"Results {self.get_name().replace(':', '-')}"
        file = filedialog.asksaveasfile(
            mode="wb", defaultextension=".png", initialfile=filename
        )
        if file:
            self.out_image.save(file, "PNG")
            file.close()

    def enter_number(self):
        if not self.bib_number.get():
            return
        
        try:
            self.bib_times.add((self.bib_number.get(), self.get_cursor_time()))
        except Exception as e:
            error = f"Failed to add bib number. Most likely because the csv is open in another window. Close it, and try again. {e}"
            popup = tk.Tk()
            popup.wm_title("!")
            label = ttk.Label(popup, text=error)
            label.pack(side="top", fill="x", pady=10)
            B1 = ttk.Button(popup, text="Okay", command = popup.destroy)
            B1.pack()
            popup.mainloop()
        else:
            self.bib_number.delete(0, tk.END)
        

def sub_process(
    frame, theta, rotation, line_pos, height, direction, num_frames, frame_num,
):
    if rotation or theta:
        frame = av.VideoFrame.from_ndarray(frame[0], format=frame[1])
        image = frame.to_image()
        image = image.rotate(-theta + rotation, expand=True)

        line = image.crop(
            (line_pos, 0, line_pos + 1, height)
        )
        line = np.array(line)
    else:
        # If we don't need to rotate, we can save ourselves some effort
        line = np.ndarray((height, 1, 3))
        col = frame[0][:, line_pos]
        line[:, 0, :] = col

    if direction > 0:
        x = num_frames - frame_num - 1
    else:
        x = frame_num

    return line, x

class FinishLine:
    window = tk.Tk()
    window.title("Finish Line")
    tab_control = ttk.Notebook(window)
    tab_1 = ttk.Frame(tab_control)
    
    tab_control.add(tab_1, text="Preview")
    
    tab_control.pack(expand=1, fill="both")

    canvas = None
    line_pos = 0
    line_pos_rotate = 0
    rotation = 0

    start_time = datetime.now()
    fps = 30

    preview_canvas_frame = ttk.Frame(tab_1)
    preview_canvas_frame.pack(expand=True, fill=tk.BOTH)

    results = []

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

    # A flag that tracks if a video is being processed
    is_processing = False

    bib_times = BibTimes()
    bib_results_filename = tk.StringVar()


    def enter_key(self, event):
        # Get active tab
        active_tab_name = str(self.tab_control.nametowidget(self.tab_control.select()))

        count = 0
        for tab in self.tab_control.tabs():
            if active_tab_name == tab:
                break
            count += 1
        else:
            return

        # the first tab "preview" should not apply
        if count > 0:
            self.results[count - 1].enter_number()


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
        """Constructs the result image from the video and the finish line. 
        Fills in the results tab with the result, the finish line, and UI 
        elements."""
        start = time.time()
        self.is_processing = True
        container = av.open(self.file)
        num_frames = int(container.streams.video[0].frames)
        out = Image.new("RGB", (num_frames, self.height), (255, 255, 255))
        result_array = np.ndarray((self.height, num_frames, 3))
        results = []
        frame_num = 0
        theta = self.get_rotate_theta()
        container.streams.video[0].thread_type = "AUTO"
        with Pool() as pool:
            for frame in container.decode(video=0):
                results.append(pool.apply_async(
                    sub_process, (
                        (frame.to_ndarray(format="rgb24"), "rgb24"), 
                        theta,
                        self.rotation,
                        self.line_pos,
                        self.height,
                        self.direction.get(),
                        num_frames, 
                        frame_num, 
                    ), 
                    error_callback=lambda error: print(error)
                ))
                # When all frames have been added to the pool, the the bar will be at
                # 50%
                self.progress.set(int(50 * frame_num / num_frames))
                frame_num += 1
                if self.is_processing is False:
                    # Cancel was pressed
                    pool.close()
                    pool.terminate()
                    self.process_finished()
                    return 
            
            pool.close()
            finished_processes = set()
            num_processes = len(results)
            while len(finished_processes) != num_processes:
                if self.is_processing is False:
                    # Cancel button was pressed
                    pool.terminate()
                    self.process_finished()
                    return

                for i, result in enumerate(results):
                    if i not in finished_processes and result.ready():
                        array, x = result.get()
                        result_array[:, x, :] = array[:, 0, :]
                        finished_processes.add(i)
                        self.progress.set(
                            50 + 
                            int(50 * len(finished_processes) / num_processes)
                        )

        out = Image.fromarray(result_array.astype("uint8"), mode="RGB")
            
        self.results.append(
            Result(
                self.tab_control, 
                out, self.direction.get(), 
                self.start_time,
                self.fps,
                self.bib_times
            )
        )
        finish = time.time()
        print(f"That took {finish - start} s")
        # Move to the results tab
        self.tab_control.select(len(self.results))
        self.process_finished()

    def process_finished(self):
        # Re-enable disabled widgets
        for widget in self.ui_widgets:
            widget.config(state="normal")

        # Disable the cancel button
        self.cancel_btn.config(state="disabled")

        # Reset the progress bar
        self.progress.set(0)

        self.is_processing = False


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
        if not hasattr(self, "preview_slider"):
            self.preview_slider = tk.Scale(
                self.preview_canvas_frame,
                from_=0,
                to=preview_image.width,
                orient=tk.HORIZONTAL,
                length=preview_image.width,
                command=self.update_preview_slider,
            )
        else:
            self.preview_slider.config(
                to=preview_image.width,
                length=preview_image.width,
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
        file = filedialog.askopenfilename()
        if not file:
            return
        
        self.file = file
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
        if not hasattr(self, "file"):
            # Nothing has been loaded yet.
            return
        
        # Start the processing in its own thread so that we don't lock up the window
        # and we can draw the progress bar.
        for widget in self.ui_widgets:
            widget.config(state="disabled")

        # enable the cancel button
        self.cancel_btn.config(state="normal")

        Thread(target=self.process).start()

    def cancel_processing(self):
        self.is_processing = False

    def bib_results_filename_update(self):
        self.bib_times.bib_results_filename = self.bib_results_filename.get()
        return True

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

        bib_results_frame = ttk.Frame(self.tab_1)
        bib_results_frame.pack(fill=tk.X, side=tk.TOP)
        bib_results_label = tk.Label(bib_results_frame, text="Bib Results Filename")
        bib_results_label.pack(fill=tk.X, side=tk.LEFT)
        bib_results_filename = ttk.Entry(
            bib_results_frame, 
            textvariable=self.bib_results_filename, 
            validate="focusout", 
            validatecommand=self.bib_results_filename_update
        )
        bib_results_filename.insert(0, DEFAULT_BIB_TIMES_FILENAME)
        bib_results_filename.pack(fill=tk.X, side=tk.LEFT)

        process_frame = ttk.Frame(self.tab_1)
        process_btn = ttk.Button(
            process_frame, text="Go", width=10, command=self.process_clicked
        )
        self.ui_widgets.append(process_btn)
        process_btn.pack(fill=tk.X, side=tk.LEFT)
        progress_bar = ttk.Progressbar(process_frame, length=300, variable=self.progress, maximum=100)
        progress_bar.pack(fill=tk.X, side=tk.LEFT)
        process_frame.pack(fill=tk.X, side=tk.TOP)

        self.cancel_btn = ttk.Button(
            process_frame, text="Cancel", width=10, command=self.cancel_processing, state="disabled"
        )
        self.cancel_btn.pack(fill=tk.X, side=tk.LEFT)

        self.window.bind("<Return>", self.enter_key)
        tk.mainloop()


if __name__ == "__main__":
    freeze_support()
    finish_line = FinishLine()
    finish_line.main()
