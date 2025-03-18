#lights_connection
import socket
import time
from lights_test import show_emotion
host = "169.254.142.56"  # Raspberry Pi IP address
port = 5000

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
            if command == "Focused":
                show_emotion(command)
            if command == "Positive":
                show_emotion(command)
            if command == "Negative":
                show_emotion(command)
            if command == 'off':
                show_emotion("off")

            

        # Close the client socket

except KeyboardInterrupt:
    print("Server terminated by user.")

finally:
    # Close the server socket
    client_socket.close()
    server_socket.close()
