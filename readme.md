# gpulimit: 使用GPU（机器学习算法）的任务队列管理

这是一个任务队列自动调度的程序。

研究机器学习算法，针对不同参数，常常需要跑多组实验。而机器学习的算法通常占用大量的内存、显存。通常无法同时运行多组程序。

**本调度程序可以自动安排不同GPU上的任务数量，自动调度，同时提供前端管理界面，供手动管理。**



## install

### 源码安装

```bash
git clone https://github.com/lichunown/gpu-limit.git
cd gpu-limit
python setup.py install
```

### pip 安装

本项目已上传pypi，可直接通过pip安装

```bash
pip3 install gpulimit
```

## usage

本程序使用linux socket进行交互，后台`gpulimit_server`动态调度，前台`gpulimit`发送命令，获取信息。

### 启动后台服务

```bash
gpulimit_server # 直接启动
nohup gpulimit_server & # 后台运行
```

### 前台命令

```bash
$ gpulimitc help

GPU Task Manage:
    usage:

        client.py -h                  show help
        gpulimit add [cmds]           add task [cmds] to gpulimit queue.


    other commands:

        help [cmd]                    show help
        add [cmds]                    ls GPU task queue status
        ls                            ls GPU task queue status
        show [id]                     show task [id] details.
        rm [id]                       remove task [id] from manage, 
        							  	if task is running, kill it.
        							  
        kill [id]                     kill task [id]
        move [id] [index(default=0)]  move [id] to [index]
        set [name] [value]            set some property.
        start [id defalut=None]       Force start task(s).
        log [id]                      show [id] output.
        status                        show System status.
        debug [id]                    if task [id] is `CMD_ERROR`, 
                                      	use this show error traceback.
```

#### 添加任务

```bash
gpulimit add [cmds]
# for example
# gpulimit add python3 main.py --lambda=12 --alpha=1
gpulimit add --priority=1 [cmds] # 改变添加任务优先级
gpulimit add --logpath="./" [cmds] # 重定向任务输出（默认在/tmp/gpulimit下）
```

#### 查看任务

```bash
gpulimit ls
```

#### 查看任务信息

```bash
gpulimit show [id]
```

#### 查看任务输出日志

```bash
gpulimit log [task id]
```

同样，也支持查看`gpulimit_server`的后台输出：

```bash
gpulimit log main
```
#### 更改调度算法参数

```bash
gpulimit set # 查看现有参数
gpulimit set [param name] [value]# 设置新参数
```
现有调度算法下，共有参数如下：
- TIMER_POLLING_TIME：轮询时间
- MAX_ERR_TIMES：最大运行次数（大于1的话，任务出错可重启）
- SAFETY_KEEP_MEMORY：保留内存百分比（默认0.2），当内存超出80%时不再新添加任务
- SAFETY_KEEP_GPU_MEMORY：针对单个显卡，保留显存的百分比（默认0.5），当显存超出50%时不再新添加任务

## scheduling

整个系统调度抽为以下4种：

- timer_call定时器：按照一定时间间隔运行
- callback_process_end：单个任务结束回调函数
- callback_add_process：用户添加任务时的回调函数
- user_start_scheduling：用户强制运行任务调用


目前调度算法为：
- 仅仅进行轮询，有符合条件的任务的话，每次添加1个任务（**条件**参考**[更改调度算法参数]**部分）

task信息：

- priority：default=5， 越小越优先
- status
  - 'CMD_ERROR'：命令本身有问题，python报错，可用`gpulimit debug [id]`查看报错信息
  -  'complete'：任务完成
  - 'waiting'：等待调用
  -  'running'：正在运行
  - 'runtime_error'：任务在运行过程中出错，可能是显存爆了，也有可能是程序有问题
  -  'killed'：被用户kill的正在运行的进程，用户可以通过start命令重启
  - 'paused'：暂停的进程（暂停状态仍然占用GPU显存）
- run_times：任务出错

## V0.2.0

- 重写status状态
- 调整task调度
- 简化调度算法

## TODO list


- [x] change raise type, and add `try except` for exception break.
- [x] \_\_doc\_\_
- [ ] kill all, range
- [x] add commits
- [x] use priority queue as task_manage.queue
- [x] Improve scheduling aligorithm
- [ ] catch memory error in cmds， when cmds is `python ...` and use`tf` or `pytorch`.