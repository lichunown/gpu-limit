import torch
import sys,time

sleep_time = float(sys.argv[1])
memory = float(sys.argv[2])

a = torch.ones([int(memory * 1024*1024*1024)//4], dtype=torch.float32).cuda()
time.sleep(sleep_time)