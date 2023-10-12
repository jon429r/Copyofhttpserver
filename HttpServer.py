import socket
from threading import Thread
import threading
from datetime import date
import time
import mimetypes
import os
import argparse

#adds command line arguements
argparser = argparse.ArgumentParser()


argparser.add_argument("-p", "--port", type=int, help="Port to run the server on")
argparser.add_argument("-d", "--directory", type=str, help="Directory to serve files from")
#Example: www/ or www backslash is not needed

args = argparser.parse_args()

if args.directory is None:
    args.directory = "www/"

print(args.port, args.directory)

#adds different mimetypes that are not included by default
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("image/jpg", ".jpg")

d = date.fromordinal(date.today().toordinal() - 1)

# Define the host and port to bind the server to
HOST = '127.0.0.1'
PORT = args.port
if PORT is None:
    PORT = 8080

# Create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the host and port
s.bind((HOST, PORT))

# Listen for incoming connections (maximum of 5 clients in the queue)
s.listen(5)

print("Server listening on", HOST, ":", PORT)


def parse_input(data) -> list[str]:
    """Parses the input from the client and returns the command in an array with 3 elements

    This function splits the inputed string on it's spaces it also adds the root directory and index.html if needed. If the format is not
    valid then it throughs an exception. Otherwise the function returns an array of three strings.

    Args:
        data (_str_): _A string of data, must be 3 elements long, including the command, the resource, and the http version_

    Returns:
        list[str]: _This is a list with 3 elements, the command, the resourse, the HTTP version_
        Index 0: The command: Get, Post, Put, Delete
        Index 1: The resource: The file to be accessed
        Index 2: The HTTP version: The HTTP version to be used. I use HTTP/1.1

    Raises:
    N/A
    """
    #Parses input and makes it usable by the server
    parsed_data = data.split()

    if parsed_data[1].endswith("/"):
        parsed_data[1] = parsed_data[1] + "index.html"

    if parsed_data[1][0:4] != args.directory:
        parsed_data[1] = str(args.directory) + parsed_data[1]
        if parsed_data[1][3] != "/":
            parsed_data[1] = parsed_data[1][0:3] + "/" + parsed_data[1][3:]
    
    return parsed_data


def get_method(resource: str, http_version: str, client_socket) -> str:
    """Handles the GET method and sends the requested file to the client.

    If the file at the end of the file path is a regular file it opens it, then sends the
    responce tag. If the file is not found it returns a FileNotFoundError execption.
    the tag should look like:
    HTTP/1.1 200 OK
    Date: Thu, 04 Feb 2010 18:50:12 GMT
    Server: ServerName/2.1
    Content-Type: text/html
    Content-Length: 1082

    <html>
    ...page data...
    </html>

    Args:
        resource (_str_): The file to be accessed.
        http_version (_str_): The HTTP version to be used.
        client_socket (_socket_): The socket that the client is connected to.

    Returns:
        str: Response message indicating success or failure.
        "404 File not found error"
        "200 OK"
    """

    try:
        if os.path.isfile(resource):
            with open(resource, "rb") as file:
                file_data = file.read()

            #gets the time and timezone
            current_time = time.strftime("%a, %d %b %Y %H:%M:%S")
            tzname_str = " ".join(time.tzname)
            tzname_str = tzname_str.split(' ')[0]

            #gets the mimetype
            content_type = mimetypes.guess_type(resource)
            content_type = str(content_type)
            content_type = content_type.split("'")[1]

            #configures the response
            response = (
                http_version.upper() + " 200 OK\n" +
                "Date: " + current_time + " " + tzname_str + "\n" +
                "Server: LocalHost/2.1\n" +
                "Content-Type: " + content_type + "\n" +
                "Content-Length: " + str(len(file_data)) + "\n\n"
            ).encode('utf-8') 


            client_socket.send(response)
            client_socket.send(file_data)

            return "200 OK"
        else:
            raise FileNotFoundError
    except FileNotFoundError:

        #gets the time and timezone
        current_time = time.strftime("%a, %d %b %Y %H:%M:%S")
        tzname_str = " ".join(time.tzname)
        tzname_str = tzname_str.split(" ")[0]

        #gets the mimetype
        content_type = mimetypes.guess_type(resource)
        content_type = str(content_type)

        #Will through an error if the file does not exist
        try:
            content_type = content_type.split("'")[1]
        except IndexError:
            content_type = "None/None"

        #configures the response
        response = (
        http_version.upper() + " 404 Not Found\n" +
        "Date: "+ current_time + " " + tzname_str + "\n" +
        "Server: LocalHost/2.1\n" +
        "Content-Type: text/plain\n" +
        "Content-Length: 0\n\n"
        ).encode('utf-8') 

        client_socket.send(response)
        return "404 Not Found"


def handle_client(client, address):
    """Handles the client connection.

    The handle client function is an infinite while loop only stopping when connection is broken
    it receives the data from the client, decodes it, finds what command type it is, and calls
    the correct command function depending on the command entered.

    Args:
        client (_type_): Client socket.
        address (_type_): Client address.

    Returns:
        No return value.
    """

    print('Connected to client at', address)
    #Main loop to handle the client
    while True:
        try:
            #Receives and parses input data
            data = client.recv(1024)
            if not data:
                print('Client disconnected')
                break


            data = parse_input(data.decode('utf-8'))
            print('Client sent:', data)

            #Sees what type of command is entered and routes the data to the correct function
            request_type = data[0].lower()
            resource = data[1]
            http_version = data[2]

            if request_type == 'get':
                print(get_method(resource, http_version, client))

        except ConnectionResetError as b:
            print('Client forcibly disconnected:', str(b))
            break

#Main loop that handles new clients and calls the handle_client function
while True:
    # Accept a client connection
    c, addr = s.accept()
    print('Accepted connection from', addr)

    try:
        Thread(target=handle_client, args=(c, addr)).start()
    except threading.ThreadError as e:
        print('Thread did not start:', str(e))

# Close the server socket
s.close()
