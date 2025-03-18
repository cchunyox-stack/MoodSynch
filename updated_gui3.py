import cv2
from deepface import DeepFace
import threading
from PIL import Image, ImageTk
import customtkinter
import tkinter as tk
import time
import pygame
import pygame.time
import random
import os
from Heart_G import init_heart_screen, show_heart_screen, init_h_loading_screen #functions for heart GUI
from GSR_G import init_GSR_screen, show_GSR_screen, init_loading_screen #functions for GSR GUI
from Final_Emotion_Process import emotion_queue, process_predictions
from raspberry_connect import connect_server

pygame.mixer.init()
pygame.init()


# Dictionary mapping moods to their respective songs
mood_songs = {
    "Positive": ["music/Happy/Smile.mp3", "music/Happy/On Repeat.mp3", "music/Happy/Hey!.mp3", "music/Happy/Ukelele.mp3", "music/Happy/Fun Day.mp3", "music/Happy/Happiness.mp3"],
    "Negative": ["music/Sad/Sad Day.mp3", "music/Sad/Better Days.mp3", "music/Sad/Misery.mp3", "music/Sad/Sad Emotional and Dramatic Piano.mp3", "music/Sad/Emotional Cinematic_34sec.mp3", "music/Sad/For When It Rains.mp3"],
    "Focused": ["music/Focused/Soft Vibes.mp3", "music/Focused/Piano Moment.mp3", "music/Focused/Melancholy Lull.mp3", "music/Focused/The Jazz Piano.mp3", "music/Focused/The Lounge.mp3", "music/Focused/Embracing the Sky.mp3"]
}


#Global variable to track whether music is paused or not
paused = False

# Load the pre-trained emotion detection model
model = DeepFace.build_model("Emotion")

# Define emotion labels
emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

# Load face cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

class CameraThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.running = False
        self.detecting = True  # Flag to control face and emotion detection
        self.detected_emotion = None
        self.detected_emotions_history = []  # List to store detected emotions during each switch
        self.emotion_counts = {"Positive": 0, "Negative": 0, "Focused": 0}

    def run(self):
        vid = cv2.VideoCapture(0)  # Initialize vid within the run method
        if not vid.isOpened():
            print("Error: Could not open webcam.")
            return

        start_time = time.time()  # Record the start time

        while not self.running:
            ret, frame = vid.read()
            if not ret:
                break

            if self.detecting:

                opencv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                captured_image = Image.fromarray(opencv_image)
                photo_image = ImageTk.PhotoImage(image=captured_image)

                # Emotion detection
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                for (x, y, w, h) in faces:
                    face_roi = gray_frame[y:y + h, x:x + w]
                    resized_face = cv2.resize(face_roi, (48, 48), interpolation=cv2.INTER_AREA)
                    normalized_face = resized_face / 255.0
                    reshaped_face = normalized_face.reshape(1, 48, 48, 1)
                    preds = model.predict(reshaped_face)[0]  # Perform emotion prediction
                    emotion_idx = preds.argmax()
                    detected_emotion = emotion_labels[emotion_idx]

                    # Append detected emotion to history
                    self.detected_emotions_history.append(detected_emotion)

                    # Count emotions
                    if detected_emotion in ["angry", "disgust", "fear", "sad"]:
                        self.emotion_counts["Negative"] += 1
                    elif detected_emotion in ["happy", "surprise"]:
                        self.emotion_counts["Positive"] += 1
                    elif detected_emotion == "neutral":
                        self.emotion_counts["Focused"] += 1

                # Check if 5 seconds have passed
                if time.time() - start_time >= 10:
                    self.detecting = False
                    break
            
                # Update GUI in the main thread
                self.parent.update_webcam_feed(photo_image)

            time.sleep(0.1)  # Adjust sleep time as needed for smoother operation

        # Calculate percentages
        total = sum(self.emotion_counts.values())
        desired_order = ['Focused', 'Negative', 'Positive']
        percentages = {emotion: count / total for emotion, count in self.emotion_counts.items()}
        emotion_percentages = [percentages[emotion] for emotion in desired_order]
        emotion_queue.put(emotion_percentages)

        print("Emotion Counts:", self.emotion_counts)
        print("Emotion Percentages:", percentages)
        print("Ordered percentages:", emotion_percentages)

        # Choose the emotion with the highest occurrence as the locked emotion
        max_emotion = max(self.emotion_counts, key=self.emotion_counts.get)
        print("Facial Emotion:", max_emotion)

        # Set the locked emotion in the parent App instance
        self.parent.lock_emotion(max_emotion)

        vid.release()  # Release the video capture object

    def stop(self):
        self.running = False

class CTkVolumeSlider(tk.Scale):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.config(
            from_=0,
            to=100,
            orient="horizontal",
            label="Volume",
            command=self.set_volume,
            showvalue=True,
            length=200,  # Adjust the length as needed
            sliderlength=20,  # Adjust the slider length as needed
        )

    def set_volume(self, volume):
        volume = float(volume) / 100.0
        pygame.mixer.music.set_volume(volume)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.gsr_emotion = None
        self.heartrate_emotion = None
        self.current_song = ""
        self.overall_emotion = None
        self.lights_active = None

        # Initialize all frames
        self.init_start_screen()
        self.init_camera_frame()
        self.init_locked_emotion_screen()
        self.init_main_frame()
        init_heart_screen(self) #heart screen initialization function comes from a seperate file
        init_GSR_screen(self) #GSR screen initialization function comes from a seperate file
        init_loading_screen(self)
        init_h_loading_screen(self)

        # Initially show the starting screen
        self.show_start_screen()
        self.hide_main_widgets()

        # Initialize the camera thread
        self.camera_thread = CameraThread(self)

        # Create a timer for updating the progress bar
        self.after(100, self.update_progress_bar)

        # Initialize the clock
        self.clock = pygame.time.Clock()

        #self.resizable(True,True)
        self.rowconfigure(0, weight=1)  # row 0 can expand vertically
        self.columnconfigure(0, weight=1)  # column 0 can expand horizontally

    def init_start_screen(self):
        # Define widgets for the start screen
        self.start_screen = customtkinter.CTkFrame(self)
        self.start_screen.grid(row=0, column=0, sticky="nsew")
        self.start_screen.grid_columnconfigure(0, weight=1)
        self.start_screen.grid_rowconfigure(0, weight=1)

        # Add a title
        title_label = customtkinter.CTkLabel(self.start_screen, text="MoodSynch", font=customtkinter.CTkFont(size=30, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=100)

        # Add a start button to transition to the camera detection screen
        start_button = customtkinter.CTkButton(self.start_screen, text="Start", command=self.show_camera_frame)
        start_button.grid(row=1, column=0, padx=20, pady=20)

        self.appearance_mode_label = customtkinter.CTkLabel(self.start_screen, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.start_screen, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(self.start_screen, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.start_screen, values=["80%", "90%", "100%", "110%", "120%", "150%", "200%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")

    def init_camera_frame(self):
        # Define widgets for the main frame
        self.camera_frame = customtkinter.CTkFrame(self)
        self.camera_frame.grid(row=0, column=0, sticky="nsew")
        self.camera_frame.grid_columnconfigure(0, weight=1)
        self.camera_frame.grid_columnconfigure(1, weight=1)
        self.camera_frame.grid_columnconfigure(2, weight=1)
        self.camera_frame.grid_rowconfigure(0, weight=1)

        # self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(1, weight=1)  # changed
        self.sidebar_frame.grid_rowconfigure(2, weight=1)
        self.sidebar_frame.grid_rowconfigure(3, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Facial Emotion Detection",
                                                font=customtkinter.CTkFont(size=25, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="Start", command=self.start_camera)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.next_button = customtkinter.CTkButton(self.sidebar_frame, text="Next", command=lambda: show_heart_screen(self))
        self.next_button.grid(row=2, column=0, padx=20, pady=10)

        # instructions
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame,
                                                text="Instructions \n 1. Press Start and the live camera will detect your emotion for 5 seconds. \n 2. The detected emotion will appear on the right, \nif you believe that the detected emotion is incorrect, you can select your intended\n emotion on the second tab and choosing the emotion from the drop down menu. \n 3. After your determined emotion is selected press Next. ",
                                                font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=1, column=2, padx=20, pady=(20, 10))


        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=170)
        self.tabview.grid(row=4, column=0, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("Detected Emotion")
        self.tabview.add("Select Emotion if detected incorrectly")
        self.tabview.tab("Detected Emotion").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Select Emotion if detected incorrectly").grid_columnconfigure(0, weight=1)

        # Add a label to the Detected Emotion tab
        self.detected_emotion_label = customtkinter.CTkLabel(self.tabview.tab("Detected Emotion"),
                                                            text="(Detected Emotion)")
        self.detected_emotion_label.grid(row=0, column=0, padx=20, pady=20)

        # Add the rest of the emotions to the option menu
        self.optionmenu_1 = customtkinter.CTkOptionMenu(self.tabview.tab("Select Emotion if detected incorrectly"),
                                                        dynamic_resizing=False, values=["Positive", "Negative", "Focused"],
                                                        command=self.lock_emotion)
        self.optionmenu_1.grid(row=1, column=0, padx=20, pady=(20, 10))

        # Initialize selected emotion
        self.selected_emotion = None

        self.label_tab_2 = customtkinter.CTkLabel(self.tabview.tab("Detected Emotion"), text="(Detected Emotion)")
        self.label_tab_2.grid(row=0, column=0, padx=20, pady=20)

        # webcam label
        self.webcam_label = customtkinter.CTkLabel(self.sidebar_frame, width=350, height=250, text="")
        self.webcam_label.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.camera_thread = None
        self.camera_running = False

        self.detected_emotion_label = customtkinter.CTkLabel(self.tabview.tab("Detected Emotion"),
                                                            text="Detected Emotion: ", font=("Arial", 25))
        self.detected_emotion_label.grid(row=0, column=0, padx=20, pady=20)

        self.locked_emotion = None  # Variable to store the locked emotion

        # set default values
        self.optionmenu_1.set("Emotions")
        self.camera_thread = None


    def init_locked_emotion_screen(self):
        # Define widgets for the locked emotion screen
        self.locked_emotion_screen = customtkinter.CTkFrame(self)
        self.locked_emotion_screen.grid(row=0, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=1, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=2, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=3, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=4, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=5, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=6, column=0, sticky="nsew")
        self.locked_emotion_screen.grid(row=7, column=0, sticky="nsew")
        # self.locked_emotion_screen.grid(row=8, column=0, sticky="nsew")
        self.locked_emotion_screen.grid_columnconfigure(0, weight=1)
        self.locked_emotion_screen.grid_rowconfigure((0,1,2,3,4,5,6,7,8), weight=1)

        # Add a title
        title_label = customtkinter.CTkLabel(self.locked_emotion_screen, text="Emotion Detected", font=customtkinter.CTkFont(size=30, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=100)

        # Label to display the emotions
        self.locked_emotion_label = customtkinter.CTkLabel(self.locked_emotion_screen, text="Facial Detection Emotion: ", font=customtkinter.CTkFont(size=20))
        self.locked_emotion_label.grid(row=1, column=0, padx=20, pady=20)
        
        self.gsr_emotion_label = customtkinter.CTkLabel(self.locked_emotion_screen, text="GSR Emotion: ", font=customtkinter.CTkFont(size=20))
        self.gsr_emotion_label.grid(row=2, column=0, padx=20, pady=20)
        self.gsr_optionmenu = customtkinter.CTkOptionMenu(self.locked_emotion_screen, dynamic_resizing=False, values=["Positive", "Negative", "Focused"], command=self.update_gsr_label)
        self.gsr_optionmenu.grid(row=3, column=0, padx=20, pady=(20, 10))

        self.heart_emotion_label = customtkinter.CTkLabel(self.locked_emotion_screen, text="Heartrate Emotion: ", font=customtkinter.CTkFont(size=20))
        self.heart_emotion_label.grid(row=4, column=0, padx=20, pady=20)
        self.heart_optionmenu = customtkinter.CTkOptionMenu(self.locked_emotion_screen, dynamic_resizing=False, values=["Positive", "Negative", "Focused"], command=self.update_heart_label)
        self.heart_optionmenu.grid(row=5, column=0, padx=20, pady=(20, 10))
        
        self.overall_emotion_label = customtkinter.CTkLabel(self.locked_emotion_screen, text="Overall Emotion: ", font=customtkinter.CTkFont(size=20))
        self.overall_emotion_label.grid(row=6, column=0, padx=20, pady=20)
        self.determine_button = customtkinter.CTkButton(self.locked_emotion_screen, text="Determine Overall Emotion", command= self.determine_and_display_overall_emotion)
        self.determine_button.grid(row=7, column=0, padx=20, pady=10) 


        self.next_button = customtkinter.CTkButton(self.locked_emotion_screen, text="Next", command=self.show_main_gui)
        self.next_button.grid(row=8, column=0, padx=20, pady=10) 



    def init_main_frame(self):
        # Define widgets for the camera detection screen
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Music player frame
        music_player_frame = customtkinter.CTkFrame(self.main_frame)
        music_player_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Add a big title for the music player section
        title_label = customtkinter.CTkLabel(music_player_frame, text="Music Player", font=customtkinter.CTkFont(size=30, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        # Slider for volume control
        self.volume_slider = CTkVolumeSlider(music_player_frame)
        self.volume_slider.set(50)
        self.volume_slider.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Button to play music
        self.play_button = customtkinter.CTkButton(music_player_frame, text="⏯", command=self.pause_resume_music, font=customtkinter.CTkFont(size=20))  
        self.play_button.grid(row=2, column=0, pady=10, padx=20, sticky="ew")

        # Button to play the next song in the current mood
        self.next_button = customtkinter.CTkButton(music_player_frame, text="NEXT", command=self.play_next_song, font=customtkinter.CTkFont(size=20))  
        self.next_button.grid(row=5, column=0, pady=10, padx=20, sticky="ew")

        # Button to play the previous song in the current mood
        self.previous_button = customtkinter.CTkButton(music_player_frame, text="PREVIOUS", command=self.play_previous_song, font=customtkinter.CTkFont(size=20))  
        self.previous_button.grid(row=6, column=0, pady=10, padx=20, sticky="ew")

        # Label to display the current song
        self.current_song_label = customtkinter.CTkLabel(music_player_frame, text="Now Playing: ", font=customtkinter.CTkFont(size=16))  
        self.current_song_label.grid(row=3, column=0, padx=20, pady=10, sticky="w")

        # Progress bar
        self.progress_bar = customtkinter.CTkProgressBar(music_player_frame, mode="determinate")
        self.progress_bar.grid(row=4, column=0, pady=10, padx=20, sticky="ew")

        # Sidebar frame
        sidebar_frame = customtkinter.CTkFrame(self.main_frame)
        sidebar_frame.grid(row=0, column=1, padx=20, pady=10, sticky="ns")

        # Lights section
        lights_label = customtkinter.CTkLabel(sidebar_frame, text="Lights", font=customtkinter.CTkFont(weight="bold", size=20))  
        lights_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Switch for turning lights on/off
        lights_switch = customtkinter.CTkSwitch(sidebar_frame, text="Lights", command=self.toggle_lights)
        lights_switch.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        # Brightness slider
        brightness_label = customtkinter.CTkLabel(sidebar_frame, text="Brightness", font=customtkinter.CTkFont(weight="bold", size=20))  
        brightness_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="w")

        # Brightness slider
        brightness_slider = customtkinter.CTkSlider(sidebar_frame, from_=0, to=100)
        brightness_slider.grid(row=3, column=0, padx=10, pady=(0, 20), sticky="w")

        # Color options
        color_label = customtkinter.CTkLabel(sidebar_frame, text="Color", font=customtkinter.CTkFont(weight="bold", size=20))  
        color_label.grid(row=4, column=0, padx=10, pady=(10, 5), sticky="w")

        color_optionmenu = customtkinter.CTkOptionMenu(sidebar_frame, values=["Red", "Green", "Blue"], command=self.change_light_color)
        color_optionmenu.grid(row=5, column=0, padx=10, pady=(0, 20), sticky="w")

        # Health Advice section
        self.health_label = customtkinter.CTkLabel(sidebar_frame, text="Emotion Tips", font=customtkinter.CTkFont(weight="bold", size=20)) 
        self.health_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        health_advice = ""
        self.health_text = customtkinter.CTkLabel(sidebar_frame, text=health_advice)
        self.health_text.grid(row=7, column=0, padx=10, pady=10, sticky="w")


    #Allows for a random song associated to the determined mood to begin playing
    def play_song_by_mood(self, mood):
        global paused, current_mood, current_song_index
        if mood in mood_songs:
            current_mood = mood
            current_song_index = random.randint(0, len(mood_songs[current_mood]) - 1)
            selected_song = mood_songs[current_mood][current_song_index]
            #print("Selected song:", selected_song) #debugging
            song_title = os.path.splitext(os.path.basename(selected_song))[0]  # Extract the song title from the file path
            #print("Song title:", song_title)  # Debugging
            self.current_song_label.configure(text=f"Now Playing: " + song_title)
            pygame.mixer.music.load(selected_song)
            pygame.mixer.music.play()
            paused = False
            
            #song_duration = pygame.mixer.Sound(selected_song).get_length()
            # Update the progress bar periodically
            #self.after(100, self.update_progress_bar)
        else:
            print("No song found for this mood.")

    #Go to next song
    def play_next_song(self):
        global paused, current_mood, current_song_index
        if current_mood and current_mood in mood_songs:
            current_song_index = (current_song_index + 1) % len(mood_songs[current_mood])
            selected_song = mood_songs[current_mood][current_song_index]
            #print("Selected song:", selected_song) #debugging
            song_title = os.path.splitext(os.path.basename(selected_song))[0]  # Extract the song title from the file path
            self.current_song_label.configure(text=f"Now Playing: " + song_title)
            pygame.mixer.music.load(selected_song)
            pygame.mixer.music.play()
            paused = False

    #Go to previous song
    def play_previous_song(self):
        global paused, current_mood, current_song_index
        if current_mood and current_mood in mood_songs:
            current_song_index = (current_song_index - 1) % len(mood_songs[current_mood])
            selected_song = mood_songs[current_mood][current_song_index]
            #print("Selected song:", selected_song) #debugging
            song_title = os.path.splitext(os.path.basename(selected_song))[0]  # Extract the song title from the file path
            self.current_song_label.configure(text=f"Now Playing: " + song_title)
            pygame.mixer.music.load(selected_song)
            pygame.mixer.music.play()
            paused = False


    def play_song(self):
        if self.overall_emotion:
            self.play_song_by_mood(self.overall_emotion)
        else:
            print("Error: No locked emotion detected.")

    def pause_resume_music(self):
        global paused
        if paused:
            pygame.mixer.music.unpause()
            paused = False
        else:
            pygame.mixer.music.pause()
            paused = True

    def set_volume(self, volume):
        volume = float(volume) / 100.0 #Convert the string value to a float and scale to the range [0, 1]
        pygame.mixer.music.set_volume(volume)

    def update_progress_bar(self):
        # Check if music is playing
        if pygame.mixer.music.get_busy():
            # Get the elapsed time in milliseconds
            elapsed_time_ms = pygame.mixer.music.get_pos()
            # Get the duration of the song in milliseconds
            song_duration_ms = self.get_song_progress()
            
            # Calculate progress as a percentage
            progress = (elapsed_time_ms / song_duration_ms) * 100
            # Update the progress bar
            self.progress_bar.set(progress)

    def get_song_progress(self):
        # Get the current position of the playback in milliseconds
        current_position_ms = pygame.mixer.music.get_pos()
        # Get the length of the currently playing music in milliseconds
        song_length_ms = pygame.mixer.Sound(self.current_song).get_length() * 1000
        # Calculate the progress as a percentage
        progress_percentage = (current_position_ms / song_length_ms) * 100
        return progress_percentage


    def hide_main_widgets(self):
        # Hide widgets in the main frame
        self.sidebar_frame.grid_remove()
        self.tabview.grid_remove()
        self.webcam_label.grid_remove()
    
    def change_light_color(self):
        print("Change Light")

    def show_start_screen(self):
        # Show the starting screen and hide others
        self.start_screen.lift()
        self.camera_frame.grid_forget()
        self.main_frame.grid_forget()
        self.tabview.grid_remove()
        self.locked_emotion_screen.grid_forget()


    def show_camera_frame(self):
        # Hide the start screen and show the camera detection screen
        self.start_screen.grid_remove()
        self.camera_frame.lift()

        self.sidebar_frame.grid(sticky="nsew")
        self.tabview.grid(sticky="nsew")
        self.webcam_label.grid(sticky="nsew")
    
    def show_locked_emotion_screen(self):
        # Show the locked emotion screen
        self.camera_frame.grid_remove()
        self.GSR_screen.grid_remove()
        self.locked_emotion_screen.lift()
        #self.determine_and_display_overall_emotion()

        self.hide_main_widgets()
        self.locked_emotion_screen.grid(sticky = "nsew")
        #self.locked_emotion_screen.grid()

        # Update the locked emotion label
        self.locked_emotion_label.configure(text=f"Locked Emotion: {self.locked_emotion}")
        #Update the GSR Emotion Label
        self.gsr_emotion_label.configure(text=f"GSR Emotion: {self.gsr_predicted_emotion}")
        #Update the Heart Rate Emotion Label
        self.heart_emotion_label.configure(text=f"Heart Emotion: {self.heart_predicted_emotion}")

    def show_main_gui(self):
        # Hide the start frame
        self.locked_emotion_screen.grid_remove()

        # Switch to the main GUI frame
        self.main_frame.lift()

        # Hide all widgets
        self.hide_main_widgets()

        # Show all widgets in the main frame
        self.main_frame.grid(sticky = "news")

        # Auto plays the song depending on the emotion
        self.play_song()

    def start_camera(self):
        # Start camera detection
        if self.camera_thread is None or not self.camera_thread.is_alive():
            self.camera_thread = CameraThread(self)
            self.camera_thread.start()
            # self.sidebar_button_1.grid_remove()

    def stop_detection(self):
        if self.camera_thread:
            self.camera_thread.detecting = False

    def connect_to_client(self):
        print("Connecting to client...")
        # Start client_connect in a separate thread
        connect_thread = threading.Thread(target=client_connect)
        connect_thread.start()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

        # Adjust the window size based on the scaling factor
        width = int(1280 * new_scaling_float)  # Adjust 1280 as per your desired initial width
        height = int(720 * new_scaling_float)  # Adjust 720 as per your desired initial height
        self.geometry(f"{width}x{height}")

    def lock_emotion(self, selected_emotion=None):
        if selected_emotion:
            self.locked_emotion = selected_emotion
        elif self.camera_thread and self.camera_thread.detected_emotion:
            self.locked_emotion = self.camera_thread.detected_emotion
        else:
            print("No emotion detected to lock.")

        # Update the label with the locked emotion
        self.detected_emotion_label.configure(text=f"Facial Emotion: {self.locked_emotion}")

    def update_gsr_label(self, selected_emotion):
        self.gsr_emotion = selected_emotion
        self.gsr_emotion_label.configure(text="GSR Emotion: " + selected_emotion)

    def update_heart_label(self, selected_emotion):
        self.heartrate_emotion = selected_emotion
        self.heart_emotion_label.configure(text="Heartrate Emotion: " + selected_emotion)

    #def determine_overall_emotion(self, locked_emotion, gsr_emotion, heartrate_emotion):
    def toggle_lights(self):
        if self.lights_active:
            # Do something else when lights are already active
            print("Turning off lights")
            # Call the function to turn off the lights
            self.turn_off_lights()
            self.lights_active = False
        else:
            # Do something when lights are not active
            print("Turning on lights")
            # Call the function to turn on the lights
            self.turn_on_lights()
            self.lights_active = True

    def turn_on_lights(self):
        # Function to turn on the lights
        client_socket = connect_server()
        client_socket.sendall(self.overall_emotion.encode())
        pass  # Replace with actual implementation

    def turn_off_lights(self):
        # Function to turn off the lights
        client_socket = connect_server()
        client_socket.sendall("off".encode())
        pass  # Replace with actual implementation
    
    def determine_overall_emotion(self,locked_emotion,gsr_emotion,heartrate_emotion):
        # Check if two or more emotions are the same
        if locked_emotion == gsr_emotion or locked_emotion == heartrate_emotion:
            overall_emotion = locked_emotion
        elif gsr_emotion == heartrate_emotion:
            overall_emotion = gsr_emotion
        else:
            # Default to the locked emotion from facial detection if no match is found
            overall_emotion = locked_emotion
        #overall_emotion = process_predictions(emotion_queue)
        return overall_emotion
    



    def determine_and_display_overall_emotion(self):
        # Health Advice
        self.health_advice = {
            "Positive": "Positive - Tips to stay Positive\n 1. Engage in Positive Self Talk\n 2. Spent Time with Positive People\n 3. Take Care of Your Physical Health\n 4. Avoid Negative Language",
            
            
            "Negative": "Negative - Tips to cope with Negativity\n 1. Exercise and Have a Healthy Diet\n 2. Practice Self Compassion\n 3. Express your Creativity and Thoughts\n 4. Stay Connected with Friends/Family",
            
            
            "Focused": "Focused - Tips to stay Focused\n 1. Set Goals\n 2. Structure your Environment for Less Distractions\n 3. Manage your Time"
        }


        locked_emotion = self.locked_emotion_label.cget("text").split(":")[1].strip()
        gsr_emotion = self.gsr_emotion_label.cget("text").split(":")[1].strip()
        heart_emotion = self.heart_emotion_label.cget("text").split(":")[1].strip()
        self.overall_emotion = self.determine_overall_emotion(locked_emotion, gsr_emotion, heart_emotion)

        self.overall_emotion_label.configure(text="Overall Emotion: " + self.overall_emotion)

        # Get the advice for the overall emotion
        advice = self.health_advice.get(self.overall_emotion, "No specific advice for this emotion.")
        # Set the text of the health advice label to the retrieved advice
        self.health_label.configure(text=advice)

    def update_webcam_feed(self, photo_image):
        self.photo_image = photo_image
        self.webcam_label.configure(image=self.photo_image)
        if self.locked_emotion:
            self.detected_emotion_label.configure(text=f"Locked Emotion: {self.locked_emotion}")
        elif self.camera_thread and self.camera_thread.detected_emotion:
            emotion = self.camera_thread.detected_emotion
            self.detected_emotion_label.configure(text=f"Detected Emotion: {emotion}")
        self.webcam_label.configure(image=self.photo_image)


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.quit)
    app.mainloop()
