#GSR_G
import threading
import queue
import customtkinter
import tkinter
import time
from PIL import Image
import pandas as pd
import numpy as np
from raspberry_connect import connect_server
from Final_Emotion_Process import emotion_queue
import joblib
from scipy import signal, stats



gsr_lock = threading.Lock()

#Queues to Send message to Pi and For result
gsr_command_queue = queue.Queue()

gsr_result_queue = queue.Queue()

processing_event = threading.Event()
calculating_event = threading.Event()

def start_loading_thread(Parent):
    loading_thread = threading.Thread(target=loading_process, args=(Parent,))
    loading_thread.start()

def loading_process(Parent, step=1):

    if step <= 40:
        Parent.progress_bar.step() 


    elif processing_event.is_set():
        Parent.loading_label.configure(text = "Preprocessing...\n You can remove fingers from sensor")
        Parent.progress_bar.start()
        processing_event.clear()
    elif step >= 75:
        Parent.progress_bar.stop()

    elif calculating_event.is_set():
        Parent.progress_bar.start()
        calculating_event.clear()
        Parent.loading_label.configure(text = "Calculating GSR Emotion..")
    elif step >=90:
         Parent.progress_bar.stop()

    Parent.after(1000, loading_process, Parent, step+1)
    
    

def init_loading_screen(Parent):
    Parent.loading_screen = customtkinter.CTkFrame(Parent)
    Parent.loading_screen.grid_columnconfigure(0, weight=1)
    Parent.loading_screen.grid_rowconfigure(0, weight=1)

    Parent.loading_label = customtkinter.CTkLabel(Parent.loading_screen, text="Analyzing Galvanic Skin Response..", font=customtkinter.CTkFont(size=20, weight="bold"))
    Parent.loading_label.grid(row=0, column=0)
    
    #instead of speed think of step size
    Parent.progress_bar = customtkinter.CTkProgressBar(Parent.loading_screen, width=300,height = 50, border_width = 1,  mode="determinate", determinate_speed = .5)
    Parent.progress_bar.set(0)
    Parent.progress_bar.grid(row=1, column=0, pady=20)

    #Parent.loading_screen.withdraw()

def hide_loading_screen(Parent):
    Parent.loading_screen.grid_remove()

def show_loading_screen(Parent):
      
    Parent.GSR_screen.grid_remove() # hide camera frame 
    Parent.loading_screen.lift() # lift heart screen
    Parent.loading_screen.grid(sticky="nsew")
    start_loading_thread(Parent)

def init_GSR_screen(Parent):
        Parent.GSR_screen = customtkinter.CTkFrame(Parent)
        #Define grid for heart screen
        #Column Configuration (2 Columns, equally split)
        # Parent.GSR_screen.grid_columnconfigure((0,1), weight = 1, uniform = 'a')
        # #Row Configuration (4 rows, Instructions to take up two rows, Title to take up first row, but first row is smaller than the other rows)
        # #Parent.GSR_screen.grid_rowconfigure(0, weight = 1 )
        # Parent.GSR_screen.grid_rowconfigure(0, weight = 0 )
        # Parent.GSR_screen.grid_rowconfigure((1,2,3), weight = 1, uniform = 'a')
        Parent.GSR_screen.grid_columnconfigure(0, weight=1)  # Make the first column expandable
        Parent.GSR_screen.grid_columnconfigure(1, weight=1)  # Make the second column expandable
        Parent.GSR_screen.grid_rowconfigure(0, weight=1)  # Make the first row expandable
        Parent.GSR_screen.grid_rowconfigure(1, weight=1)  # Make the second row expandable
        Parent.GSR_screen.grid_rowconfigure(2, weight=1)  # Make the third row expandable
        Parent.GSR_screen.grid_rowconfigure(3, weight=1) 


        gsr_image = customtkinter.CTkImage(dark_image = Image.open("C:\\Users\\crist\\Downloads\\gsr_image.jpg"), size = (300, 300))
        gsr_label = customtkinter.CTkLabel(Parent.GSR_screen, text = "", image = gsr_image)
        #Add Title
        Parent.title_label = customtkinter.CTkLabel(Parent.GSR_screen, text = "Galvanic Skin Response Analysis", font = customtkinter.CTkFont(size = 30, weight = "bold"))
        Parent.title_label.grid(row = 0, column = 0, columnspan = 2) # no sticky so its centered across both columns with columnspan = 2

        Parent.instruction1= customtkinter.CTkLabel(Parent.GSR_screen, text = '''1. Place Fingers in Sensors\n 2. Click Start to begin Analysis\n 3. Wait for analysis to end (around 39 seconds)\n 4. Click Next to end Analysis ''',
                                                     font = customtkinter.CTkFont(size = 24, weight = "bold"))
        Parent.instruction1.grid(row = 1, column = 1, rowspan = 2)


        Parent.gsr_label_image = customtkinter.CTkLabel(Parent.GSR_screen, text = "", image = gsr_image)
        Parent.gsr_label_image.grid(row = 1, column = 0)

        Parent.text2= customtkinter.CTkLabel(Parent.GSR_screen, text = "GSR Readings", font = customtkinter.CTkFont(size = 20, weight = "bold"))
        Parent.text2.grid(row = 2, column = 0)


        #Add two buttons one to start heart rate analysis and one to move on to GSR analysis ("Next")
        Parent.gsr_button = customtkinter.CTkButton(Parent.GSR_screen, text = "Start Analysis", command = lambda: start_GSR_thread(Parent),fg_color= '#1d544d') # replace command with call to sensor
        Parent.gsr_button.grid(row = 3, column = 0, columnspan = 2) # center in the middle of the last row and first columnd, adjust padding levels to make bigger if needed

        #Parent.next_button = customtkinter.CTkButton(Parent.GSR_screen, text = "Next", command = Parent.show_locked_emotion_screen) # replace command with function to move on to GSR screen
        #Parent.next_button.grid(row = 3, column = 1) # center in the middle of the last row and second column, adjust padding levels to make bigger if needed
def show_GSR_screen(Parent):
    Parent.heart_screen.grid_remove() # hide camera frame 
    Parent.GSR_screen.lift() # lift heart screen
    Parent.GSR_screen.grid(sticky="nsew")

def start_GSR_thread(Parent):
        #daemon is not set to true as we want the thread to end once we get our emotion associated with heart rate
        #show_loading_screen(Parent)
        show_loading_screen(Parent)
        GSR_analysis_thread = threading.Thread(target=predict_GSR_emotion, args=(Parent,))
        GSR_analysis_thread.start()

def request_gsr_data(Parent):
        client_socket = connect_server()
        command = gsr_command_queue.get() #command should be "send_gsr"
        client_socket.sendall(command.encode())
        gsr_data = client_socket.recv(1024).decode()
        #print(f"GSR Reading: {gsr_data}")
        gsr_result_queue.put(gsr_data)
        client_socket.close()
        #return gsr_data

def predict_GSR_emotion(Parent): #function used to predict emotion based of readings
    gsr_command_queue.put("send_gsr")
    request_gsr_data(Parent)
    try:
         gsr_data = gsr_result_queue.get(timeout=10)
    except queue.Empty:
         print("Timeout error: No GSR Data Received")
         return "Unknown"

    print(gsr_data)
    #update global variable with message
    processing_event.set()
    time.sleep(2)
    preprocessed_gsr_data = preprocess_GSR_readings(gsr_data)
    calculating_event.set()
    time.sleep(2)
    svm_model = joblib.load("C:\\Users\\crist\\Downloads\\MoodSynch\\gsr_svm_model.joblib")
    # Use the loaded model to make emotion prediction based off GSR readings

    #Predict emotion for GSR alone
    emotion_prediction = svm_model.predict(preprocessed_gsr_data)
    
    #Place probabilities in a queue to be retrieved
    gsr_probabilities = svm_model.predict_proba(preprocessed_gsr_data)
    gsr_probabilities = np.array(gsr_probabilities).flatten()
    emotion_queue.put(gsr_probabilities)


    emotion_mapping = {
        "Happy":"Positive",
        "Neutral" : "Focused",
        "Sad":"Negative"
    }
    
    print(emotion_prediction[0])
    final_emotion = emotion_mapping.get(emotion_prediction[0], "unknown") 
    Parent.text2.configure(text=f"GSR Emotion: {final_emotion}")
    Parent.gsr_predicted_emotion = final_emotion
    print(final_emotion)
    hide_loading_screen(Parent)
    show_GSR_screen(Parent)
    Parent.gsr_button.grid_configure(row=3, column=0, columnspan = 1)
    Parent.next_button = customtkinter.CTkButton(Parent.GSR_screen, text = "Next", command = Parent.show_locked_emotion_screen) # replace command with function to move on to GSR screen
    Parent.next_button.grid(row = 3, column = 1) # center in the middle of the last row and second column, adjust padding levels to make bigger if needed
    return final_emotion


def preprocess_GSR_readings(gsr_readings): #function used to preprocess the gsr data we collected
    #preprocess GSR readings that come in from the Raspberry Pi
    features = []
    print("Test preprocess")
    #indicate we are done after preprocessing GSR readings
    #gsr_readings = gsr_readings.split(',')
    gsr_readings = list(map(int, filter(lambda x: x != '', gsr_readings.split(','))))
    df = pd.DataFrame({"GSR_Data": gsr_readings})
    individual_data = df.iloc[:]

    raw_gsr = individual_data['GSR_Data'].values

    #filter GSR readings through a butterworth filter
    filter_gsr = butter(raw_gsr, cutoff_freq=5, sample_rate = 8)
    max_value, min_value, std_dev, kurtosis = gsr_features(filter_gsr)

    avg_diff_raw_gsr = np.mean(np.diff(raw_gsr))

    features.append([
        avg_diff_raw_gsr,
        np.mean(filter_gsr),
        max_value,
        min_value,
        std_dev,
        kurtosis,
        #write in features
    ])

    # Display the DataFrame
    gsr_data = pd.DataFrame(features, columns =[
    "AverageDiffGSRRaw",
    "Average of Filtered GSR",
    "Max",
    "Min",
    "Standard Deviation",
    "Kurtosis"
    ])

    return gsr_data

def gsr_features(signal):
    max_value = np.max(signal)
    min_value = np.min(signal)
    std_dev = np.std(signal)
    kurt = stats.kurtosis(signal)

    return max_value, min_value, std_dev, kurt
def butter(data, cutoff_freq, sample_rate):
    cutoff_freq = cutoff_freq/sample_rate
    b, a = signal.butter(4, cutoff_freq, btype='low')
    filtered_data = signal.filtfilt(b, a, data)
    return filtered_data