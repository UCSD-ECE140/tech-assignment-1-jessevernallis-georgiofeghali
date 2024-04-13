import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import numpy as np
import time
import random
from moveset import Moveset


# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    """
        Prints the result of the connection with a reasoncode to stdout ( used as callback for connect )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param flags: these are response flags sent by the broker
        :param rc: stands for reasonCode, which is a code for the connection result
        :param properties: can be used in MQTTv5, but is optional
    """
    print("CONNACK received with code %s." % rc)


# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    """
        Prints mid to stdout to reassure a successful publish ( used as callback for publish )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param properties: can be used in MQTTv5, but is optional
    """
    print("mid: " + str(mid))


# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """
        Prints a reassurance for successfully subscribing
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param granted_qos: this is the qos that you declare when subscribing, use the same one for publishing
        :param properties: can be used in MQTTv5, but is optional
    """
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


# print message, useful for checking if it was successful
def on_message(client, userdata, msg):
    """
        Prints a mqtt message to stdout ( used as callback for subscribe )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param msg: the message with topic and payload
    """
    global end
    if msg.topic == "games/Lobby1/lobby":
        end = str(msg.payload)

    global player_data
    for player in players:
        if msg.topic == f"games/Lobby1/{player}/game_state":
            print(f"player : {player}")
            player_data.append(json.loads(msg.payload))

    print("message: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
#find any of item that is next to a player
def find_nearby(items, player):
    item_direction = []

    for item in items:
        #direction of each item relative to the player
        item_relative = np.subtract(item,player)
        if(abs(np.sum(item_relative)) == 1 and not np.all(item_relative)):
            item_direction.append(item_relative)
    for i,direction in enumerate(item_direction):
        for move in Moveset:
            if move.value == tuple(direction):
                item_direction[i] = move.name
    return item_direction

#determines the player's next move based on gamstate data
def player_move(data):
    walls = data['walls']                                                #walls' current position
    player = data['currentPosition']                                     #player's current position
    coins = data['coin1'] + data['coin2'] + data['coin3']                #coin's current positions
    wall_direction = []                                                  #list of  direction of each wall, intailized as nothing
    coin_direction = []                                                  #list of  directions with a coin, intailized as nothing
    player_direction = []                                                #list of  directions the player can possibly move, intailized as nothing

    #for each coin in the status message give its direction to coin_direction
    coin_direction = find_nearby(coins, player)
    #if there is a coin next to the player, grab it
    if(not (len(coin_direction) == 0)):
        player_move = random.choice(coin_direction)
    else:
        #for each wall in the status message give its direction to coin_direction
        wall_direction = find_nearby(walls, player)
        #adds all moves without a wall to player direction
        for move in (member.name for member in Moveset):
            if(move not in wall_direction):
                player_direction.append(move)
        #if on an edge, remove the edge direction from player direction
        if(player[0] == 0):
            player_direction.remove("UP")
        if(player[0] == 9):
                player_direction.remove("DOWN")
        if(player[1] == 0):
                player_direction.remove("LEFT")
        if(player[1] == 9):
            player_direction.remove("RIGHT")
        player_move = random.choice(player_direction)

    return player_move
if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION1, client_id="Player1", userdata=None, protocol=paho.MQTTv5)
    
    # enable TLS for secure connection
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # set username and password
    client.username_pw_set(username, password)
    # connect to HiveMQ Cloud on port 8883 (default for MQTT)
    client.connect(broker_address, broker_port)

    # setting callbacks, use separate functions like above for better visibility
    client.on_subscribe = on_subscribe # Can comment out to not print when subscribing to new topics
    client.on_message = on_message
    client.on_publish = on_publish # Can comment out to not print when publishing to topics

    lobby_name = "Lobby1"
    players = ["Player1","Player2","Player3","Player4"]


    client.subscribe(f"games/{lobby_name}/lobby")
    client.subscribe(f'games/{lobby_name}/+/game_state')
    client.subscribe(f'games/{lobby_name}/scores')

    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'Team1',
                                            'player_name' : players[0]}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'Team1',
                                            'player_name' : players[1]}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'Team2',
                                            'player_name' : players[2]}))
    
    client.publish("new_game", json.dumps({'lobby_name':lobby_name,
                                            'team_name':'Team2',
                                            'player_name' : players[3]}))
    

    time.sleep(1) # Wait a second to resolve game start
    client.publish(f"games/{lobby_name}/start", "START")
    end = ""
    player_data = []

    client.loop_start()
    while 'Game Over: All coins have been collected' not in end:
        time.sleep(1)
        for i,data in enumerate(player_data):
            client.publish(f"games/{lobby_name}/{players[i]}/move", player_move(data))
            #reset player data each turn
        player_data = []
    client.loop_stop()