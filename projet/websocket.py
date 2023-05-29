# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:00:17 2020

@author: julien
"""


async def websocket_application(scope, receive, send):
    while True:
        event = await receive()

        if event['type'] == 'websocket.connect':
            await send({
                'type': 'websocket.accept'
            })

        if event['type'] == 'websocket.disconnect':
            break

        if event['type'] == 'websocket.receive':
            if event['text'] == 'ping':
                await send({
                    'type': 'websocket.send',
                    'text': 'pong!'
                })
        await send({
            'type': 'websocket.send',
            'text': 'toto!'
        })