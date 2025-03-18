#TCP Server Check
import socket
import time
from gsr_sensor import GroveGSRSensor
#from Pulse_Data import read_heart_rate
from hrv_readings import read_pulse
import preprocess_ibi
from preprocess_ibi import preprocess_IBI_intervals
#from lights_test import show_emotion
print("here")
host = "192.168.1.105"  # Raspberry Pi IP address
port = 5000

print("here")
# Create a server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#server_socket.close()
# Bind socket properties

server_socket.bind((host, port))
command = ''
server_socket.listen(5)

print("Waiting for connections...")

try:
    while True:
        # Accept a connection
        client_socket, client_address = server_socket.accept()
        print(f"Connection established with {client_address}")
        while True:
            command = client_socket.recv(1024).decode()
            #code block to send GSR data
            if command == "send_gsr":
                gsr_data = []                                   # List to collect GSR data
                GSR_sensor = GroveGSRSensor(channel = 0)        #Initialize GSR object

                sampling_rate = 0.125                           # Collecting Data at 8 Hz
                start_time = time.time()                        #Set Start Time
                while time.time() - start_time < 39:
                    gsr_reading = GSR_sensor.GSR
                    print(gsr_reading)
                    #gsr data from sensor
                    gsr_data.append(gsr_reading)                #append every reading to overall list
                    time.sleep(0.125)                           #0.125 allows for 8 Hz sampling_rate
                #convert to string?
                gsr_data_str = ','.join(map(str, gsr_data))     #convert list to a string to be able to send
                client_socket.sendall(gsr_data_str.encode())    #send info to client
                print('GSR Data Sent to the Client')
                print(gsr_data_str)
                client_socket.close()
            #code block to send Heart Rate Data    
            if command == "send_heart":
                heart_data = []                                 #List to collect heart data
                start_time = time.time()                        #Set start time
                  #read for 30 seconds
                heart_rate = read_pulse()
                extracted_features = preprocess_IBI_intervals(heart_rate)
                # Convert extracted features to string
                extracted_str = extracted_features.to_csv(index=False)

                # Send extracted features back to the client
                client_socket.sendall(extracted_str.encode())
                print('Extracted Features sent to the client')
                print(extracted_str)
            # if command == "Focused":
            #     show_emotion(command)
            # if command == "Positive":
            #     show_emotion(command)
            # if command == "Negative":
            #     show_emotion(command)

            

        # Close the client socket

except KeyboardInterrupt:
    print("Server terminated by user.")

finally:
    # Close the server socket
    server_socket.close()

