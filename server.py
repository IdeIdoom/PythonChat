import threading
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import json
import time as time_functions
import random


class Question:
#Question class, data from the json file
    textQuestion = ""
    answer = ""
    answers = []

    def __init__(self, textQuestion, answer, answers):
        self.textQuestion = textQuestion
        self.answer = answer
        self.answers = answers

    def verify_answer(self, answer):
        return self.answer == answer


class Timer:
#Countdown timer class
    def __init__(self, time):
        self.time = time
        self.started = False

    def countdown(self):
        while ( self.time > 0 ) and ( self.started is True ):
            self.time -= 1
            time_functions.sleep(1)
        self.started = False

    def start(self):
        self.started = True
        Thread(target=self.countdown).start()

    def stop(self):
        self.started = False


class Player:
    name = ""
    points = 0
    #if trap question is selected then they get defeated
    is_defeated = False

    def __init__(self):
        pass

    def set_name(self, name):
        self.name = name

    def change_score(self, points):
        self.points += points


def accept_connections():
    global game_mode
    #we can't allow people in if the game has ended
    while game_mode != "ENDING":
        #Accept clients on a thread, tell them to input name
        client, client_address = SERVER.accept()
        print("%s:%s si e' collegato." % client_address)
        client.send(bytes("Salve! Digita il tuo Nome seguito dal tasto Invio!", "utf8"))
        #lists used for control
        addresses[client] = client_address
        client_sockets.append(client)
        #start thread handling every client
        Thread(target=handle_client, args=(client,)).start()


def close_clients():
    #Close all clients and remove them from their respective lists
    for client in client_sockets:
        client.close()
        del addresses[client]
        del player_list[client]
        del clients[client]


def hand_out_question_list(client):
    #this will hand out a series of questions from the json file
    #it will have an 1/3 chance to put the trap question in the 1st or 2nd question
    #if not, fall back to third question
    #otherwise put in different questions inside our list (different between eachother)
    questions = []
    trap_selected = False
    for i in range(3):
        random.seed()
        chance = random.randint(1, 3)
        if (chance == 3) and (trap_selected is False):
            question_number = random.randint(0,len(trap_question_list)-1)
            questions.append(trap_question_list[question_number])
            trap_selected = True
        else:
            if(i == 2) and (trap_selected is False):
                question_number = random.randint(0, len(trap_question_list) - 1)
                questions.append(trap_question_list[question_number])
                trap_selected = True
            else:
                question_number = random.randint(0, len(question_list) - 1)
                while question_list[question_number] in questions:
                    question_number = random.randint(0, len(question_list) - 1)
                questions.append(question_list[question_number])
    #then send out these questions to the player
    counter = 1
    for question in questions:
        client.send(bytes("%s" % counter + ". " + question.textQuestion, "utf8"))
        counter += 1
    #and return the list so that it can be handled by client basis
    return questions



def handle_client(client):
    #first check the name or if they just want to quit
    msg = client.recv(BUFSIZ).decode("utf8")
    if msg != "{quit}":
        #then welcome them and add them to the player list
        question = -1
        answer_mode = False
        name = msg
        welcome = 'Benvenuto %s! Se vuoi lasciare la Chat, scrivi {quit} per uscire.' % name
        client.send(bytes(welcome, "utf8"))
        msg = "%s si e' unito al chat!" % name
        print(msg)
        broadcast(bytes(msg, "utf8"))
        player_list[client] = Player()
        player_list[client].set_name(name)
        clients[client] = name
        while game_mode != "ENDING":
            #for error checking in case sockets get shutdown pre-emptively from the client side
            try:
                msg = client.recv(BUFSIZ).decode("utf8")
            except Exception:
                continue
            #in the case client wants to quit
            if msg == "{quit}":
                client.close()
                del player_list[client]
                del clients[client]
                del addresses[client]
                leave_message = "%s abbandona la Chat." % name
                broadcast(bytes(leave_message, "utf8"))
                print(leave_message)
                break
            #clients can talk to eachother normally during lobby
            if game_mode == "LOBBY":
                broadcast(bytes(msg, "utf8"), name + ": ")
                print("" + name + ": " + msg)
            #if the client is not defeated yet and they're playing then they can only send the messages to the server
            elif game_mode == "GAME" and player_list[client].is_defeated is False:
                #the client-server relationship is on a black-box relationship, this is to send back the client the message they wrote
                client.send(bytes("" + name + ": " + msg, "utf8"))
                print("" + name + ": " + msg)
                if(answer_mode is False):
                    #this is for checking if they have chosen a question already or not
                    #check the range and if it's an actual number
                    try:
                        answer = int(msg)
                        if (answer < 1) or (answer > 3):
                            continue
                        else:
                            answer -= 1
                    except ValueError:
                        continue
                    #trap question selected, the player has been defeated
                    if (per_player_question_list[client][answer].answer == "Trappola"):
                        player_list[client].is_defeated = True
                        msg = "Hai appena scelto una domanda trappola! Sei stato sconfito!"
                        client.send(bytes(msg, "utf8"))
                    else:
                    #if the question wasn't a trap then we let them answer the question
                        question = answer
                        client.send(bytes(per_player_question_list[client][question].textQuestion, "utf8"))
                        counter = 1
                        for question_answer in per_player_question_list[client][question].answers:
                            client.send(bytes("%s" % counter + ". %s" % question_answer,"utf8"))
                            counter += 1
                        answer_mode = True
                else:
                    #the player can now answer the question, we just make the answer match the positions in lists
                    try:
                        answer = int(msg)
                        answer -= 1
                    except ValueError:
                        continue
                    #check if the answer is right then deduct or increase the point value accordingly
                    if (answer in range(len(per_player_question_list[client][question].answers))):
                        if (per_player_question_list[client][question].verify_answer(per_player_question_list[client][question].answers[answer])):
                            player_list[client].change_score((+1))
                            msg = "Corretto!"
                            client.send(bytes(msg, "utf8"))
                        else:
                            player_list[client].change_score((-1))
                            msg = "Sbagliato!"
                            client.send(bytes(msg, "utf8"))
                    #once that's all done, it's back to selecting a question
                    #we also send the client a new set of questions
                        answer_mode = False
                        per_player_question_list[client] = hand_out_question_list(client)
            elif game_mode == "END OF GAME":
                #the game is over and the clients got the score
                #if they want to play again, they can send {rematch} to get added back
                broadcast(bytes(msg, "utf8"), name + ": ")
                print("" + name + ": " + msg)
                if msg == "{rematch}":
                    rematch_votes[client] = "Yes"
    else:
        #we don't know who left without inputting a name
        client.close()
        del addresses[client]
        del player_list[client]
        leave_message = "Qualcuno ha abbandonato la Chat."
        broadcast(bytes(leave_message))
        print(leave_message)

def game_manager():
    #main game thread
    #manages each game state
    #Lobby is the default mode; during lobby mode players can talk to each other until enough players connect (at least 2)
    #Game is the game mode, during which players cannot talk to each and answer questions
    global game_mode
    while game_mode != "ENDING":
        if game_mode == "LOBBY":
            if (len(player_list) >= 2) and (new_Timer.started is False):
                #if the timer hasn't started and there are enough players
                time_functions.sleep(3)
                new_Timer.time = 20
                #send to all players and print for logging
                msg = "Il gioco comincia in 20 secondi! \nAvete 3 minuti per rispondere alle domande! \nAlcune domande sono trappole che vi fa perdere! \nOgni domanda vale un +1 o -1!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                #start timer
                new_Timer.start()
            elif (len(player_list) < 2) and (new_Timer.started is True):
                #if the person is by themselves
                new_Timer.stop()
            elif (new_Timer.time == 0) and (len(player_list) >=2):
                #the game has started
                #we now hand out the questions
                #we switch the game mode to GAME
                #we start our timer for 30 minutes
                new_Timer.stop()
                msg = "Il gioco comincia!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                for client in client_sockets:
                    per_player_question_list[client] = hand_out_question_list(client)
                game_mode = "GAME"
                new_Timer.time = 180
                new_Timer.start()
                time_functions.sleep(1)
        elif game_mode == "GAME":
            if (len(player_list) < 2):
                new_Timer.stop()
                #oops, just one player remaining, back to the lobby!
                game_mode = "LOBBY"
                msg = "Il gioco e' finito all'improvviso! Si e' scollegato qualcuno! \nSi ritorna al Lobby!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                time_functions.sleep(3)
            if (new_Timer.time == 0):
                #the game has stopped and we have the results
                #there are some pauses for more dramatic effect
                #we now set the game mode to "END OF GAME" and let players talk to eachother
                game_mode = "END OF GAME"
                msg = "Stop!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                time_functions.sleep(3)
                msg = "Vediamo i risultati!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                time_functions.sleep(3)
                #we check by player basis if they have lost because of a trap question
                #otherwise just print out their score
                for client in client_sockets:
                    if player_list[client].is_defeated is False:
                        msg = "%s ha %d punti!" % (player_list[client].name, player_list[client].points)
                        broadcast(bytes(msg, "utf8"))
                        print(msg)
                    else:
                        msg = "%s ha perso per colpa di una domanda trappola!" % player_list[client].name
                        broadcast(bytes(msg, "utf8"))
                        print(msg)
                time_functions.sleep(3)
                msg = "Se si vuole fare una rivincita, scrivi {rematch}! \nDecidete in 3 minuti! \nSi vogliono almeno 2 giocatori!"
                broadcast(bytes(msg, "utf8"))
                print(msg)
                #end of game lobby timer
                new_Timer.time = 180
                new_Timer.start()
        elif (game_mode == "END OF GAME"):
            #we just keep checking the rematch list
            #once the timer is done, the players that don't want to rematch will get removed
            #others will continue playing by going back to the lobby
            if (new_Timer.time == 0) and (len(rematch_votes)>=2):
                for client in client_sockets:
                    if client not in rematch_votes:
                        client.close()
                        del addresses[client]
                        del player_list[client]
                        del clients[client]
                    if client in rematch_votes:
                        player_list[client].points = 0
                        player_list[client].is_defeated = False
                    del rematch_votes[client]
                game_mode = "LOBBY"
                #not enough players, time to end the game
            elif (new_Timer.time == 0) and (len(rematch_votes)<2):
                game_mode = "ENDING"
    msg = "Il gioco ha finito! Arrivederci"
    broadcast(bytes(msg, "utf8"))
    print(msg)
    time_functions.sleep(5)
    close_clients()

#msg is a series of bytes, remember to do conversion before hand
#this is to match the socket.send
def broadcast(msg, prefix=""):
    for user in clients:
        user.send(bytes(prefix, "utf8") + msg)

#various lists to keep track of the player
clients = {}
addresses = {}
client_sockets = []
player_list = {}
rematch_votes = {}
#lists to keep track of the questions
question_list = []
trap_question_list = []
per_player_question_list = {}
#initialized the important variables
game_mode = "LOBBY"
new_Timer = Timer(60)
#load in the questions from data.json
f = open('data.json', "r")
data = json.load(f)

for question in data['domande']:
    if question['risposta'] != "Trappola":
        question_list.append(Question(question['testoDomanda'], question['risposta'], question['risposte']))
    else:
        trap_question_list.append(Question(question['testoDomanda'], question['risposta'], question['risposte']))
#server variables
HOST = ''
PORT = 53000
BUFSIZ = 1024
ADDR = (HOST, PORT)
#bind the inbound socket
SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)

if __name__ == "__main__":
    #we now listen to max 4 players and start our threads
    SERVER.listen(4)
    print("In attesa di connessioni...")
    ACCEPT_THREAD = Thread(target=accept_connections)
    GAME_THREAD = Thread(target=game_manager)
    ACCEPT_THREAD.start()
    GAME_THREAD.start()
    #after everything is done, we join the threads and close them then close the server
    GAME_THREAD.join()
    ACCEPT_THREAD.join()
    SERVER.close()
