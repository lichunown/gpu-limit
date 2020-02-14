# GPU limit management

机器学习领域的一些实验，由于参数较多，通常需要对不同参数跑多组实验。

本项目维护使用GPU程序的任务队列，动态调度任务。避免手动跑实验带来的繁琐感受。

## install

`setup.py`的编写似乎有些问题，现在还在调试。

```bash
git clone https://github.com/lichunown/gpu-limit.git
cd gpu-limit
python setup.py install
```

## usage

本程序使用linux socket进行交互，后台`gpulimit_server`动态调度，前台`gpulimit`发送命令，获取信息。

### 启动服务

```bash
gpulimit_server # 直接启动
nohup gpulimit_server & # 后台运行
```

### 前台命令

#### 添加任务

```bash
gpulimit add [cmds]
# for example
# gpulimit add python3 main.py --lambda=12 --alpha=1
```

#### 查看任务

```bash
gpulimit ls
```

#### 查看任务信息

```bash
gpulimit ls
```

#### 查看任务输出日志

```bash
gpulimit log [task id]
```

同样，也支持查看`gpulimit_server`的后台输出：

```bash
gpulimit log main
```

## TODO list

- [x] start
- [ ] kill all, range
- [ ] ls show use gpu & running target
- [ ] change raise type, and add `try except` for exception break.
- [ ] commit & \_\_doc\_\_