import socket
client_socket=None #check if u need global
def connect_server():
    global client_socket

    host = "11.20.60.131"  # Replace with your Raspberry Pi's actual IP address
    port = 5000

    if client_socket and client_socket.fileno() != -1:
        print("Using existing socket.")
        return client_socket

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Looking for connection")
    
    try:
        # Connect to the server (Raspberry Pi)
        print("we're here")
        client_socket.connect((host, port))
        print(f"Connected to {host}:{port}")
        #alter it as apparentl u dont need a while true loop to keep connection alive
        return client_socket
            #return client_socket
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Stopping the client.")
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        #print("Closing the connection.")
        # Close the connection
        print("Client Socket Returned")
