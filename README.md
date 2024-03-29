FinishLine takes any video, and transforms it into a time-vs-vertical plot, like what
a photo-finish camera would capture. This of course doesn't give you any more information
than what the original video contains, but it does make it easier to see the order of
finishers across a finish line without needing to step through a video frame by frame.
Additionally, FinishLine makes it easy to see the time at which finishers crossed the 
line.

Dependencies are managed with poetry. Once installed, run main.py to start the program. Alternatively, download an executable from the most recent release and run that.

To use:
1. Load a video file using the "load video" button. The first frame of the video will appear. If the video needs to be rotated, press the "rotate video" buttons to align things.
2. A white line representing the finish line is drawn over the preview. Drag the slider to adjust the position of this line until it covers the finish line in the video. If you need to rotate the line, press the "rotate line" buttons until it is aligned.
3. Select which direction the racers are traveling with the radio buttons.
4. Optionally enter the UTC offset of the timezone that the video was recorded in.
5. Press "Go" to create the photo-finish image.
6. Check the results in the new tab. 
7. FinishLine will do its best to determine the start time of the video, and the frame rate. If either of these values are incorrect, you can enter corrected numbers for each of them, then press update. 
8. A white line appears at either the far left or right of the result image (depending on which direction of travel was selected). Drag the slider control to adjust the position of the line. Click the slider bar to move the line 1 pixel at a time.
9. The current position of the line will be given as a time. This makes it possible to measure the time at which different finishers cross the line. 
10. Press "save" to save a png of the result image.
11. Enter a bib number into the text field, then press enter. A CSV file will be created. An entry for the current time and bib number will be added to the csv file. It is sorted and saved with each number entered. This makes it quick to scroll the finish line through each finisher in the image and tabulate everyone's finish time. You can change the file that results are saved to by updating the `
12. Return to the preview tab and process another video. Bib times from subsequent videos in the same session will be added to the csv file.

![Example](example.png)
