#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Copyright (c) 2015 Dylan Stankievech
#
# Some of this code was copied from my assignment 4 submission,
# since the assignments were so similar. I didn't quite get websockets
# working, woops!
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, Response, request, redirect, url_for, render_template
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()
toSend = list()

def set_listener( entity, data ):
    # Send the update to all sockets
    for socket in toSend:
        socket.send(Json.dumps({entity:data}))

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    ''' Return index page '''
    return redirect(url_for('static', filename='index.html'))

def read_ws(ws):
    '''A greenlet function that reads from the websocket and updates the world'''
    
    # Read this socket forever
    while True:

        # Get the next message
        message = ws.receive()

        # Check that it wasn't an empty message
        if message is not None:

            # Get the data from json format
            data = json.loads(message)
            for entity in data:

                # Update the world from this data
                myWorld.space[entity] = data[entity]

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    
    # Add this socket
    toSend.append(ws)

    # Spawn a gevent to read from this websocket
    g = gevent.spawn(read_ws, ws)

    # Send the current world to this socket
    ws.send(json.dumps(myWorld.space))


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

# Note: most of the code below was copied from my
# Assignment 4 submission, since it seems we're supposed
# to provide similar functionality for HTTP responses

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    ''' Update the specified entity with the supplied data '''
    toUpdate = json.loads(request.data.decode('utf-8'))
    decoded = entity.decode('utf-8')
    myWorld.space[decoded] = toUpdate
    toReturn = json.dumps(toUpdate)
    return Response(toReturn, status=200, mimetype='application/json')

@app.route("/world", methods=['POST','GET'])    
def world():
    ''' Return a json representation of the world '''
    data = json.dumps(myWorld.space)
    response = Response(data, status=200, mimetype='application/json')
    return response

@app.route("/entity/<entity>")    
def get_entity(entity):
    ''' Handle a GET request for specified entity '''
    decoded = entity.decode('utf-8')
    toReturn = {}
    if decoded in myWorld.space:
        toReturn = myWorld.space[decoded]
    data = json.dumps(toReturn)
    response = Response(data, status=200, mimetype='application/json')
    return response


@app.route("/clear", methods=['POST','GET'])
def clear():
    ''' Clear all entities in the world '''
    myWorld.clear()
    return Response(None, status=200)



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
