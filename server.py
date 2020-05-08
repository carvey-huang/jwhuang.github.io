import os
import socket
import threading
import queue
import sys
import requests
import json
import base64
import matplotlib.pyplot as plt
from torch.autograd import Variable
import torchvision.transforms as transforms
import torch
import time
import torchvision.models as models
from PIL import Image


def model_handle():
    model = models.inception_v3(pretrained=True)
    model.transform_input = True
    content = requests.get("https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json").text
    labels = json.loads(content)
    with lock2:
        conn_socket=q3.get()
    while True:
        received_size = 0
        print("waiting for client sending size")
        from_client_datasize=conn_socket.recv(1024).decode()
        from_client_datasize=int(from_client_datasize)
        conn_socket.send(b'server already know the size that client send, plz go on')
        print("size well received: ",from_client_datasize)
        final_data = b''

        while received_size<from_client_datasize:

            temp_data=conn_socket.recv(1024)
            if len(temp_data)==0:
                print("conn lost")
            final_data+=temp_data
            received_size+=len(temp_data)


        #print(final_data)
        print(len(final_data))
        print(received_size)
        jsonDict = json.loads(final_data.decode())

        #print(jsonDict)
            # data = base64.b64decode(jsonDict["image_content"])
            #
            # image_file=open('image_file','wb')
            # image_file.write(data)

        print("now model working ")
        data_from_client_image = base64.b64decode(jsonDict["image_content"])
        #print(jsonDict["image_content"])
        image_file=open('image_file.png','wb')
        image_file.write(data_from_client_image)
        im=Image.open('image_file.png')
        #plt.show(im)

        normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(299),
            transforms.ToTensor(),
            normalize
        ])

        img_tensor = preprocess(im)
        img_tensor.unsqueeze_(0)
        img_variable = Variable(img_tensor)

        model.eval()
        preds = model(img_variable)

        # Convert the prediction into text labels
        # Get the top 5 predictions
        percentage = torch.nn.functional.softmax(preds, dim=1)[0]
        predictions = []
        predictions_dic={}
        predictions_to_send={}
        for i, score in enumerate(percentage.data.numpy()):
            predictions.append((score, labels[str(i)][1]))

        predictions.sort(reverse=True)

        predictions_format=[]
        for score,label in predictions[:5]:
            #label = '{:16s}'.format(label)
            score='{:.4f}'.format(score)
            predictions_format.append((label,str(score)))

        predictions_to_send['predictions']=dict(predictions_format[:5])
        predictions_to_send['chat_id']=jsonDict['chat_id']
        predictions_to_send=json.dumps(predictions_to_send)
        predictions_to_send_size=str(len(predictions_to_send))
        print("now feedback predictions to client")
        print(len(predictions_to_send))
        conn_socket.send(predictions_to_send_size.encode())
        conn_socket.recv(1024)#阻塞，确保client收到大小

        conn.send(predictions_to_send.encode())

if __name__ == '__main__':


    q3=queue.Queue()
    lock2=threading.Lock()
    IP = "127.0.0.1"
    port = 5555
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((IP, port))
    server_socket.listen(3)
    conn,addr=server_socket.accept()
    with lock2:
        q3.put(conn)
    t1=threading.Thread(target=model_handle).start()

    while True:
        time.sleep(3)
    #final_data = b''

    # while True:
    #     received_size=0
    #     from_client_datasize=conn.recv(1024).decode()
    #     from_client_datasize=int(from_client_datasize)
    #     conn.send(b'already know the size')
    #     print(from_client_datasize)
    #     while received_size<from_client_datasize:
    #         temp_data=conn.recv(min(from_client_datasize-received_size, 1024))
    #         if len(temp_data)==0:
    #             print("conn lost")
    #         final_data+=temp_data
    #         received_size+=sys.getsizeof(temp_data)
    #
    #     print(final_data.decode())
    #     jsonDict = json.loads(final_data.decode())
    #     with lock2:
    #         q3.put(jsonDict)
    #     print(jsonDict)
    #     # data = base64.b64decode(jsonDict["image_content"])
    #     #
    #     # image_file=open('image_file','wb')
    #     # image_file.write(data)

    t1.join()
    conn.close()