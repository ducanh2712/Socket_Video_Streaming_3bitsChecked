import socket
import sys
import threading
import cv2
import pickle
import numpy as np
import struct
import zlib
import time

import queue
from threading import Thread

q = queue.Queue(maxsize=100000) # hang doi cac frame cua video

HOST='127.0.0.1'
PORT=8485

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
print('Socket created')

s.bind((HOST,PORT))
print('Socket bind complete')
s.listen(10)
print('Socket now listening')

conn,addr=s.accept()

# Nhan so frame cua video
data = conn.recv(1024)
totalFrame = int(data.decode("utf8"))

# FPS cua video
data = conn.recv(1024)
FPS = int(data.decode("utf8"))

payload_size = struct.calcsize(">L")
print("payload_size: {}".format(payload_size))

done_flag = 0;

def frame_recv():
    data = b""
    stop_flag = 0;
    fps,st,frames_to_count,cnt = (0,0,20,0)

    while stop_flag == 0:

        while len(data) < payload_size:
            print("Recv: {}".format(len(data)))
            data += conn.recv(4096)
        
        print("Done Recv: {}".format(len(data)))
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        try:
            msg_size = struct.unpack(">L", packed_msg_size)[0]
        except:
            continue

        print("msg_size: {}".format(msg_size))
        while len(data) < msg_size:
            data += conn.recv(4096)
        
        msg_data = data[:msg_size]

        # 15 la do be gui 3bit s,r,p moi bit dang de fix length la 5
        frame_data = msg_data[15:]
        bit_seq = msg_data[:15]
        bit_seq = bit_seq.decode('utf-8')
        data = data[msg_size:]

        # ktra bit p xem loi khong
        if int(bit_seq[10:]) == 1:
            resp = 'nak'
            conn.sendall(resp.encode('utf-8'))
            continue
        else:
            resp = 'ack'
        
        frame=pickle.loads(frame_data, fix_imports=True, encoding="bytes")
        try:
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        except:
            continue
        q.put(frame)    #day frame vao queue

        cnt+=1

        conn.sendall(resp.encode('utf-8'))
        if (totalFrame == cnt): 
            stop_flag = 1
            break

    print("done thread")
    global done_flag
    done_flag = 1

def frame_show():
    fps,st,frames_to_count,cnt = (0,0,20,0)
    while (done_flag == 0):
        frame = q.get()

        frame = cv2.putText(frame,'FPS: '+str(fps),(10,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)

        cv2.imshow('Received',frame)
        cv2.waitKey(1)

        if cnt == frames_to_count:
            try:
                fps = round(frames_to_count/(time.time()-st))
                st=time.time()
                cnt=0
            except:
                pass
        cnt+=1

        time.sleep(1/(FPS+5)) # VD: 30fps -> load 1 frame sau 1/30s
    print("end thread")
    s.close()

# Chay da luong 2 ham: mot ham buffer frame, mot ham lay frame ra -> on dinh FPS
t1 = threading.Thread(target=frame_recv, name='t1')
t2 = threading.Thread(target=frame_show, name='t2')

t1.start()
t2.start()

t1.join()
t2.join()