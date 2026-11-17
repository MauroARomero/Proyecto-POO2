#!/usr/bin/env python3
"""Genera archivos .jtl SINTÉTICOS con el mismo formato de JMeter.

Sirve únicamente para probar el notebook antes de tener mediciones reales.
NO son resultados de tu aplicación: no los uses en el informe final.

Modelo (simplificado): sistema cerrado con N usuarios y tiempo de espera Z.
  X = min_suave(N / (Z + R0), capacidad)   y   R = N / X - Z
La capacidad depende del escenario y de las réplicas (ver `capacity`).

Uso:  python scripts/generate_demo_results.py --out results_demo [--seed 7]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

USERS = [10, 50, 100, 200]
THINK_S = 0.1
BASE_LATENCY_S = 0.030
DURATION_S = 60
RAMP_S = 10
PER_POD_RPS = 110.0

SCENARIOS = {
    "compose": [1],
    "k8s-1nodo": [1, 2, 3],
    "k8s-2nodos": [1, 2, 3],
    "k8s-3nodos": [1, 2, 3],
}
MIX = [  # etiqueta, peso %, multiplicador de latencia
    ("GET /products/{id}", 40, 0.8),
    ("GET /products", 20, 1.1),
    ("GET /products?category", 10, 1.0),
    ("GET /products/search", 15, 1.8),
    ("POST /orders", 10, 1.5),
    ("GET /reports/top-products", 5, 4.0),
]


def soft_min(a, b, k=6.0):
    return (a ** -k + b ** -k) ** (-1.0 / k)


def capacity(scenario, replicas):
    if scenario == "compose":
        return soft_min(PER_POD_RPS * 0.95, 400.0)
    if scenario == "k8s-1nodo":      # un nodo compartido con PostgreSQL
        raw, db_cap = PER_POD_RPS * min(replicas, 2.0) * (0.95 if replicas > 1 else 1.0), 330.0
    elif scenario == "k8s-2nodos":
        raw, db_cap = PER_POD_RPS * min(replicas, 4) * (0.93 if replicas > 1 else 1.0), 430.0
    else:
        raw, db_cap = PER_POD_RPS * replicas * (0.92 if replicas > 1 else 1.0), 430.0
    return soft_min(raw, db_cap)


def make_run(rng, scenario, replicas, users, t0_ms):
    cap = capacity(scenario, replicas)
    t = np.arange(DURATION_S)
    n_t = users * np.minimum(1.0, (t + 1) / RAMP_S)
    x_open = n_t / (THINK_S + BASE_LATENCY_S)
    x = soft_min(x_open, cap)
    r = np.maximum(BASE_LATENCY_S, n_t / x - THINK_S)
    overload = (x_open / cap).max()
    err_p = 0.0 if overload <= 1.2 else min(0.03, 0.003 * (overload - 1.2))

    counts = rng.poisson(x)
    sec = np.repeat(t, counts)
    n = sec.size
    stamps = t0_ms + (sec + rng.random(n)) * 1000.0

    names = [m[0] for m in MIX]
    weights = np.array([m[1] for m in MIX], dtype=float) / 100.0
    mult = np.array([m[2] for m in MIX]) / float(np.dot(weights, [m[2] for m in MIX]))
    idx = rng.choice(len(MIX), size=n, p=weights)
    sigma = 0.4
    mean_s = r[sec] * mult[idx]
    elapsed = rng.lognormal(np.log(mean_s) - sigma ** 2 / 2, sigma) * 1000.0
    failed = rng.random(n) < err_p

    return pd.DataFrame({
        "timeStamp": stamps.astype("int64"),
        "elapsed": np.maximum(1, elapsed.round()).astype("int64"),
        "label": np.array(names)[idx],
        "responseCode": np.where(failed, "500", "200"),
        "success": np.where(failed, "false", "true"),
        "allThreads": np.minimum(users, (n_t[sec]).round().astype(int)),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results_demo")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    t0 = 1_760_000_000_000
    total = 0
    for scenario, reps in SCENARIOS.items():
        for r in reps:
            for u in USERS:
                df = make_run(rng, scenario, r, u, t0)
                df.to_csv(out / f"{scenario}__r{r}__u{u}.jtl", index=False)
                total += len(df)
                t0 += (DURATION_S + 30) * 1000
    (out / "LEEME.txt").write_text(
        "DATOS SINTETICOS DE DEMOSTRACION generados por scripts/generate_demo_results.py.\n"
        "No provienen de ninguna medicion real.\n", encoding="utf-8")
    print(f"[demo] {total} muestras sintéticas escritas en {out}/")


if __name__ == "__main__":
    main()
