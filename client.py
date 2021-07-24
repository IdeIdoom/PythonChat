from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import tkinter as tkt
from tkinter import *
#simple client that just receives and sends messages
#black box relationship, the client doesn't really know how the server works
def receive():
    while True:
        try:
            msg = client_socket.recv(BUFSIZ).decode("utf8")
            msg_list.insert(tkt.END, ""+msg+"\n")
        #if any error, just close the client
        except OSError:
            on_closing()


def send(event=None):
    msg = my_msg.get()
    my_msg.set("")
    try:
        client_socket.send(bytes(msg, "utf8"))
    except OSError:
        pass
    finally:
        if msg == "{quit}":
            client_socket.close()
            finestra.quit()

#just in case the client closes the window or types {quit}
#this is the only part that isn't a black box, we know about that command
def on_closing(event=None):
    my_msg.set("{quit}")
    send()
#tkt window for easier accessibility
#this is all GUI configuration
finestra = tkt.Tk()
finestra.title("Chat")

messages_frame = tkt.Frame(finestra)
my_msg = tkt.StringVar()
my_msg.set("")
scrollbar = tkt.Scrollbar(messages_frame)
#now with word wrap
msg_list = tkt.Text(messages_frame, height=15, width=50, yscrollcommand=scrollbar.set, wrap=WORD)
scrollbar.pack(side=tkt.RIGHT, fill=tkt.Y)
msg_list.pack(side=tkt.LEFT, fill=tkt.BOTH)
msg_list.pack()
messages_frame.pack()

entry_field = tkt.Entry(finestra, textvariable=my_msg)
entry_field.bind("<Return>", send)
entry_field.pack()

send_button = tkt.Button(finestra, text="Invio", command=send)
send_button.pack()

finestra.protocol("WM_DELETE_WINDOW", on_closing)
#preset configurations
HOST = '127.0.0.1'
PORT = 53000
BUFSIZ = 1024
ADDR = (HOST, PORT)

client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect(ADDR)

receive_thread = Thread(target=receive)
receive_thread.start()

tkt.mainloop()


