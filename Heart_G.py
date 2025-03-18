#Heart GUI
import threading
import queue
from PIL import Image, ImageTk
import customtkinter
import tkinter
import time
import pandas as pd
import numpy as np
from statistics import mode
from GSR_G import show_GSR_screen
import joblib
from raspberry_connect import connect_server
from Final_Emotion_Process import emotion_queue
from io import StringIO
#import hrvanalysis
#from hrvanalysis import get_time_domain_features, get_frequency_domain_features

heart_command_queue = queue.Queue()

heart_result_queue = queue.Queue()

pi_queue = queue.Queue()
heart_processing_event = threading.Event()
heart_calculating_event = threading.Event()

#Function to remove heart loading screen when required to do so
def hide_heart_loading_screen(Parent):
      Parent.h_loading_screen.grid_remove()

def start_heart_loading_thread(Parent):
    loading_thread = threading.Thread(target=loading_process, args=(Parent,))
    loading_thread.start()
def loading_process(Parent,step=1):
        if step <= 30:
                Parent.h_progress_bar.step() 


        elif heart_processing_event.is_set():
                Parent.h_loading_label.configure(text = "Preprocessing...\n You can remove finger from sensor")
                Parent.h_progress_bar.start()
                heart_processing_event.clear()
        elif step >= 75:
                Parent.progress_bar.stop()

        elif heart_calculating_event.is_set():
                Parent.h_progress_bar.start()
                heart_calculating_event.clear()
                Parent.h_loading_label.configure(text = "Calculating Heart Rate Emotion..")
        elif step >=90:
                Parent.progress_bar.stop()

        Parent.after(1000, loading_process, Parent, step+1)
    
#Intialize heart loading screen
def init_h_loading_screen(Parent):
    Parent.h_loading_screen = customtkinter.CTkFrame(Parent)
    Parent.h_loading_screen.grid_columnconfigure(0, weight=1)
    Parent.h_loading_screen.grid_rowconfigure(0, weight=1)

    Parent.h_loading_label = customtkinter.CTkLabel(Parent.h_loading_screen, text="Analyzing Heart Rate..", font=customtkinter.CTkFont(size=20, weight="bold"))
    Parent.h_loading_label.grid(row=0, column=0)

    #Progress Bar
    #instead of speed think of step size
    Parent.h_progress_bar = customtkinter.CTkProgressBar(Parent.h_loading_screen, width=300,height = 50, border_width = 1,  mode="determinate", determinate_speed = .5)
    Parent.h_progress_bar.set(0)
    Parent.h_progress_bar.grid(row=1, column=0, pady=20)

def show_heart_loading_screen(Parent):
    Parent.heart_screen.grid_remove() # hide heart screen 
    Parent.h_loading_screen.lift() # lift heart loading screen
    Parent.h_loading_screen.grid(sticky="nsew")
    start_heart_loading_thread(Parent)

def init_heart_screen(Parent):
        Parent.heart_screen = customtkinter.CTkFrame(Parent)
        #Define grid for heart screen
        #Column Configuration (2 Columns, equally split)
        Parent.heart_screen.grid_columnconfigure((0,1), weight = 1, uniform = 'col_weight')
        #Row Configuration (4 rows, Instructions to take up two rows, Title to take up first row, but first row is smaller than the other rows)
        Parent.heart_screen.grid_rowconfigure(0, weight = 1 )
        Parent.heart_screen.grid_rowconfigure((1,2,3), weight = 2, uniform = 'row_weight')

        #Variable for Emotion associated with heart 

        heart_image = customtkinter.CTkImage(dark_image = Image.open("C:\\Users\\crist\\Downloads\\MoodSynch\\heartimage.jpg"), size = (200, 300))
        heart_label = customtkinter.CTkLabel(Parent.heart_screen, text = "", image = heart_image)

        Parent.heart_label_image = customtkinter.CTkLabel(Parent.heart_screen, text = "", image = heart_image)
        Parent.heart_label_image.grid(row = 1, column = 0)
        #Add Title
        Parent.title_label = customtkinter.CTkLabel(Parent.heart_screen, text = "Heart Rate Analysis", font = customtkinter.CTkFont(size = 30, weight = "bold"))
        Parent.title_label.grid(row = 0, column = 0, columnspan = 2) # no sticky so its centered across both columns with columnspan = 2

        Parent.instructionh= customtkinter.CTkLabel(Parent.heart_screen, text = '''1. Place finger in sensor as shown\n 2. Click Start to begin Analysis\n 3. Wait for analysis to end (around 30 seconds)\n 4. Click Next to end Analysis ''',
                                                     font = customtkinter.CTkFont(size = 24, weight = "bold"))
        Parent.instructionh.grid(row = 1, column = 1, rowspan = 2)

        Parent.text2= customtkinter.CTkLabel(Parent.heart_screen, text = "Monitor", font = customtkinter.CTkFont(size = 20, weight = "bold"))
        Parent.text2.grid(row = 2, column = 0)


        #Add two buttons one to start heart rate analysis and one to move on to GSR analysis ("Next")
        #Start Heart Analysis Button Starts a thread which runs in the background analysis the heart rate data, allows for GUI to continue being active
        Parent.heart_button = customtkinter.CTkButton(Parent.heart_screen, text = "Start Heart Analysis", command = lambda: start_heart_thread(Parent)) 
        Parent.heart_button.grid(row = 3, column = 0) # center in the middle of the last row and first columnd, adjust padding levels to make bigger if needed

        Parent.next_button = customtkinter.CTkButton(Parent.heart_screen, text = "Next", command = lambda: show_GSR_screen(Parent)) # replace command with function to move on to GSR screen
        Parent.next_button.grid(row = 3, column = 1) # center in the middle of the last row and second column, adjust padding levels to make bigger if needed

        #Test for now
        #Solution ?

def show_heart_screen(Parent):
        # Hide the camera screen and show the heart rate screen
    global client_socket
    
    client_socket = connect_server()
    print(client_socket)

    Parent.camera_frame.grid_remove() # hide camera frame 
    Parent.heart_screen.lift() # lift heart screen
    Parent.hide_main_widgets()
    Parent.heart_screen.grid(sticky = "nsew")

def start_heart_thread(Parent):
        #daemon is not set to true as we want the thread to end once we get our emotion associated with heart rate
        show_heart_loading_screen(Parent)
        heart_analysis_thread = threading.Thread(target=predict_heart_emotion, args=(Parent,))
        heart_analysis_thread.start()

def request_heart_data():
        client_socket = connect_server()
        command = heart_command_queue.get()
        client_socket.sendall(command.encode())
        heart_data = client_socket.recv(1024).decode()
        #print(f"GSR Reading: {gsr_data}")
        heart_result_queue.put(heart_data)
        #return gsr_data
                             #return heart rate data to be used by other functions

def predict_heart_emotion(Parent): #function used to predict emotion based of readings
    #load in gsr model
    heart_command_queue.put("send_heart")
    request_heart_data()
    reordered_df = pd.read_csv("C:\\Users\\crist\\Downloads\\MoodSynch\\reorder.csv")
    try:
         heart_readings = heart_result_queue.get(timeout=10)
         extracted_features = pd.read_csv(StringIO(heart_readings))
         extracted_features.drop(['sdnn', 'cvnni','vlf'], axis=1, inplace=True)
         extracted_features = extracted_features[reordered_df.columns]
         #raspberry pi is sending us the extracted features
    except queue.Empty:
         print("Timeout error: No Heart Rate Data Received")
         return "Unknown"
    print("Preprocessing Data")
    heart_processing_event.set()
    #preprocessed_heart_readings = preprocess_heart_rate(heart_readings)
    #preprocessing happens in pi

    #Get preprocessed heart rate data
    #Load heart rate model
    heart_calculating_event.set()
    print(heart_readings)
    forest_model = joblib.load("c:\\Users\\crist\\Downloads\\MoodSynch\\hrv_model.joblib")
    # Use the loaded model to make emotion prediction based off GSR readings
    emotion_prediction = forest_model.predict(extracted_features)
    print(emotion_prediction) # load model and pass throught the data frame we made with the readings
    emotion_prediction = emotion_prediction[0]
    
    #Get probabilities according to heart rate
    heart_probabilities = forest_model.predict_proba(extracted_features)
    # Combine class labels with their respective probabilities
    predicted_classes = forest_model.classes_
    class_probabilities_with_labels = zip(predicted_classes, heart_probabilities)

# Print the probabilities with their respective class labels
    for class_label, probability in class_probabilities_with_labels:
        print(f"Probability of {class_label}: {probability}")
        
    heart_probabilities = np.array(heart_probabilities).flatten()
    print(heart_probabilities)
    emotion_queue.put(heart_probabilities)


    #most_common_emotion = mode(emotion_prediction)
    #emotion_mapping = {
    #       0:"Negative", 
    #       1:"Focused",
    #       2:"Positive"
    #}

    #mapped_emotion = emotion_mapping.get(most_common_emotion)
    
    Parent.heart_predicted_emotion = emotion_prediction # Have to initialize **** REVIEW
    Parent.h_loading_screen.grid_remove() # hide camera frame 
    Parent.heart_screen.lift() # lift heart screen
    Parent.heart_screen.grid(sticky = "nsew")
    print(emotion_prediction)
    return emotion_prediction

# def preprocess_heart_rate(heart_readings): #function used to preprocess the heart rate data we collected
#         #heart readings come in a string so we have to take into account of that
#         #we have to get the ibi intervals to pass down
#       #convert to list so we pass down as paramaters to hrvanalysis functions
#       #get time domain_features

#       #heart readings should be the IBI intervals communicated by the Pi
#       time_domain_features = get_time_domain_features(heart_readings)
#       frequency_domain_features = get_frequency_domain_features(heart_readings)#dont forget about sampling frequency

#       extracted_features =[]

#       user_features = pd.DataFrame({
#             **time_domain_features,
#             **frequency_domain_features
#         }, index=[0])
#       extracted_features.append(user_features)

#       return extracted_features