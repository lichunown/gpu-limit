import os

gpu_info = os.popen('nvidia-smi --query-gpu=index,memory.total,memory.free,memory.used --format=csv')
gpu_info.readline()

gpu_data = []
for line in gpu_info:
    index, memory_total, memory_free, memort_used = line.strip().split(', ')
    gpu_data.append((index, memory_total, memory_free, memort_used))

max_free_memory_gpu = max(gpu_data, key=lambda x:float(x[2].split()[0]))
print(max_free_memory_gpu)