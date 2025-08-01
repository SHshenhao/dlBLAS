# modify form sglang
import torch
import triton

import dlblas
from dlblas.kernels.moe import biased_grouped_topk
from dlblas.utils.device_utils import infer_device


def biased_grouped_topk_org(scores, bias, num_expert_group, topk_group, topk):
    return biased_grouped_topk(scores,
                               scores,
                               bias,
                               topk=topk,
                               renormalize=True,
                               num_expert_group=num_expert_group,
                               topk_group=topk_group,
                               routed_scaling_factor=2.5)


def biased_grouped_topk_org_kernel(scores, bias, num_expert_group, topk_group, topk):
    return dlblas.moe_fused_gate(scores, bias, num_expert_group, topk_group, topk, routed_scaling_factor=2.5)


seq_length_range = [5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]
configs = [(sq, ) for sq in seq_length_range]


@triton.testing.perf_report(
    triton.testing.Benchmark(
        x_names=['seq_length'],
        x_vals=[list(_) for _ in configs],
        line_arg='provider',
        line_vals=['torch', 'kernel'],
        line_names=['torch', 'Fused Kernel'],
        styles=[('blue', '-'), ('red', '-')],
        ylabel='us',
        plot_name='moe-fused-gate-performance',
        args={},
    ))
def benchmark(seq_length, provider):
    dtype = torch.bfloat16
    device = infer_device()
    num_experts, num_expert_group, topk_group, topk = 256, 8, 4, 8

    scores = torch.randn((seq_length, num_experts), device=device, dtype=dtype)
    bias = torch.rand(num_experts, device=device, dtype=dtype)

    quantiles = [0.5, 0.2, 0.8]

    if provider == 'torch':
        ms, min_ms, max_ms = triton.testing.do_bench(
            lambda: biased_grouped_topk_org(scores.clone(), bias.clone(), num_expert_group, topk_group, topk),
            quantiles=quantiles,
        )
    elif provider == 'kernel':
        ms, min_ms, max_ms = triton.testing.do_bench(
            lambda: biased_grouped_topk_org_kernel(scores.clone(), bias.clone(), num_expert_group, topk_group, topk),
            quantiles=quantiles,
        )

    return 1000 * ms, 1000 * max_ms, 1000 * min_ms


if __name__ == '__main__':
    benchmark.run(print_data=True)
