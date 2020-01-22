import os, sys, random, time

allow = random.randint(0, 16) if len(sys.argv)<=1 else float(sys.argv[1])
sleep = random.randint(1, 60) if len(sys.argv)<=2 else float(sys.argv[2])

if os.environ.get('CUDA_VISIBLE_DEVICES'):
    GPU_ID = int(os.environ['CUDA_VISIBLE_DEVICES'])
else:
    GPU_ID = 0

print(f'use gpu: {GPU_ID}, allow: {allow}')

data = []
with open('./Resources', 'r') as f:
    for line in f:
        id, free = line.strip().split(':')
        free = float(free)
        if int(id) == GPU_ID:
            if free < allow:
                print(f'GPU {GPU_ID} need {allow} memory, but only {free} free.')
                exit(1)
            free = free - allow
        data.append((id, free))


with open('./Resources', 'w') as f:
    f.write('\n'.join([f'{id}:{free}' for id, free in data]))

time.sleep(sleep)

data[GPU_ID] = (GPU_ID, float(data[GPU_ID][1]) + float(allow))


with open('./Resources', 'w') as f:
    f.write('\n'.join([f'{id}:{free}' for id, free in data]))

exit(0)
