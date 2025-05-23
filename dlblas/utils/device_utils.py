# Copyright (c) 2025, DeepLink.
import functools
import subprocess

import torch
import triton

DEVICE_COUNT = torch.cuda.device_count()


def is_gpu_idle(gpu_id):
    try:
        # 调用 nvidia-smi 命令
        result = subprocess.check_output([
            'nvidia-smi',
            '--query-compute-apps=gpu_uuid',
            '--format=csv,noheader,nounits',
            f"--id={gpu_id}",
        ])
        # 解析输出
        processes = result.decode('utf-8').strip().split('\n')
        # import pdb; pdb.set_trace()
        # 检查是否有进程正在运行
        if len(processes) == 1 and processes[0] == '':
            return True  # GPU is idle
        else:
            return False  # GPU is not idle
    except Exception as e:
        print('Failed to check GPU status')
        return False


def get_idle_device():
    for gpu_id in range(DEVICE_COUNT):
        if is_gpu_idle(gpu_id) == True:
            print(f"GPU {gpu_id} is idle, we will use cuda:{gpu_id}")
            return f"cuda:{gpu_id}"
    print('[WARN] All GPU device is busy, will use cuda:0 as default, performance data maybe inaccurate.')
    return 'cuda:0'


WARPS_PER_SM = {
    (8, 0): 64,
    (8, 6): 48,
    (8, 7): 48,
    (8, 9): 48,
    (9, 0): 64,
    (10, 0): 64,
    (10, 1): 48,
    (12, 0): 48,
}


@functools.lru_cache
def get_device_props(device=None):
    if device is None:
        device = torch.cuda.current_device()

    props = torch.cuda.get_device_properties(device)

    warps_per_sm = WARPS_PER_SM.get((props.major, props.minor), 32)
    out = dict(
        multi_processor_count=props.multi_processor_count,
        warps_per_sm=warps_per_sm,
    )
    return out


def is_cuda():
    return triton.runtime.driver.active.get_current_target().backend == 'cuda'


def is_mlu_592():
    target = triton.runtime.driver.active.get_current_target()
    return target.backend == 'mlu' and target.arch == 592


def is_muxi():
    target = triton.runtime.driver.active.get_current_target()
    return target.backend == 'maca'
