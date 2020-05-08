import base64
import sys
import threading
import time
import telepot
import os
import sklearn
from telepot.loop import MessageLoop
import pickle
import numpy as np
import requests
import queue
from io import BytesIO
import json
import socket
from PIL import Image
from threading import Thread

client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('127.0.0.1',5555))

def handle(msg):
    """
    A function that will be invoked when a message is
    recevied by the bot
    """
    content_type, chat_type, chat_id = telepot.glance(msg)


    if content_type=='text':
        image_url=msg["text"]
        image_data = requests.get(image_url).content
        with open('image.png', 'wb') as outfile:
            outfile.write(image_data)
        with lock1:
            image_obj=open('image.png', 'rb')
            q1.put(image_obj)
            q1.put(chat_id)

    if content_type == 'photo':
        bot.download_file(msg['photo'][-1]['file_id'], 'image.png')
        with lock1:
            image_obj=open('image.png','rb')
            q1.put(image_obj)
            q1.put(chat_id)
        # reply="hhaha"
        # bot.sendMessage(chat_id, reply)
        print("run into handle")

def client_handle(client_socket):
    while True:

        while not q1.empty():
            try:
                print("run into client_socket")
            except:
                print("connect error")
            data={}
            with lock1:
                data_image_obj=q1.get()
                data_chat_id = q1.get()
                q1.queue.clear()

            image = Image.open('image.png')
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            encoded_image = base64.b64encode(buffered.getvalue()).decode()#这里需要注意，bug改了好久才发现

            str_encoded_image=str(encoded_image)

            data_image_obj.close()

            data = {'image_content': str_encoded_image, 'chat_id': data_chat_id}
            image_data_send = json.dumps(data).encode()

            image_data_send_size=len(image_data_send)
            print("size send to server: ",image_data_send_size)

            client_socket.send(str(image_data_send_size).encode())
            sig=client_socket.recv(1024)#阻塞确保收到size

            print(sig.decode())
            client_socket.sendall(image_data_send)

            # try:
            #     load_data=json.loads(image_data_send)
            #     print(load_data)
            # except:
            #     print("load error")
            print("now receiving answer from server")

            size=client_socket.recv(1024).decode()

            if not size:
                print("no size from server")
                continue
            else:
                client_socket.send("already know size of what you sent, go on".encode())
                print("already know size of what you sent, go on",size)
                length=0
                data_from_server=b''
                while length<int(size):
                    data_from_server+=client_socket.recv(1024)
                    length+=len(data_from_server)
                data_from_server=json.loads(data_from_server.decode())

                with lock2:
                    q2.put(data_from_server)


def client_sendingto_user(client_socket):
    while True:
        if not q2.empty():
            with lock2:
                data_to_bot=q2.get()
                q2.queue.clear()
            #bot.sendMessage(data_to_bot['chat_id'], data_to_bot['predictions'])
            list_result=""
            for key,value in data_to_bot['predictions'].items():
                list_result+=key+' '+'('+value+')'+'\n'
            bot.sendMessage(data_to_bot['chat_id'],list_result)
        time.sleep(3)


if __name__=='__main__':
    q1=queue.Queue()
    q2=queue.Queue()
    lock1=threading.Lock()#创建一个同步锁解决thread1和2在queue1之间datarace的问题

    lock2=threading.Lock()#创建一个同步锁解决t2和3的问题

    token="685459005:AAFr6YriPp3b_vCIvxsaQQA5maZmMtvJ-io"
    bot = telepot.Bot(token)

    MessageLoop(bot, handle).run_as_thread()
    t2=threading.Thread(target=client_handle,args=(client_socket,))
    #t3=threading.Thread(target=client_sendingto_user,args=(client_socket,))
    t2.start()
    client_sendingto_user(client_socket)#由于只能三个线程，所以我把t3注释了，以主线程的函数运行
    #t3.start()


    t2.join()
    #t3.join()
    while True:
        time.sleep(5)