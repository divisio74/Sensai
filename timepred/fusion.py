import math

C_PROG = 3.0
P_MIN_PROG = 0.6
P_ONLY_PROG = 0.8


def progression_prior(elapsed, p):
    t_prog = elapsed / p
    if p < P_MIN_PROG:
        return t_prog, math.inf
    if p >= P_ONLY_PROG:
        return t_prog, 0.0
    sigma = C_PROG * t_prog * (1 - p) / p
    return t_prog, sigma


def bayesian_fusion(t_hist, s_hist, t_prog, s_prog):
    if s_prog == 0:
        return t_prog, 0.0, 1.0
    w_hist, w_prog = 1 / s_hist ** 2, 1 / s_prog ** 2
    t = (t_hist * w_hist + t_prog * w_prog) / (w_hist + w_prog)
    sigma = math.sqrt(1 / (w_hist + w_prog))
    cursor = w_prog / (w_hist + w_prog)
    return t, sigma, cursor
