import glob
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("resultados/graficos", exist_ok=True)

def processar_e1():
    arquivos = glob.glob("resultados/e1/*.csv")
    if not arquivos:
        print("Nenhum arquivo encontrado em resultados/e1/")
        return

    registros_runs = []

    for arq in arquivos:
        nome = os.path.basename(arq)
        match = re.match(r"(etcd|cassandra)_n(\d+)_run(\d+)\.csv", nome)
        if not match:
            continue
        sistema, n_threads, run = match.group(1), int(match.group(2)), int(match.group(3))

        df = pd.read_csv(arq)
        t0 = df["timestamp_inicio"].min()

        df_valido = df[df["timestamp_inicio"] >= (t0 + 30.0)].copy()
        if df_valido.empty:
            continue

        duracao_efetiva = df_valido["timestamp_inicio"].max() - df_valido["timestamp_inicio"].min()
        sucessos = df_valido[df_valido["sucesso"] == 1]

        vazao = len(sucessos) / duracao_efetiva if duracao_efetiva > 0 else 0
        p99 = np.percentile(sucessos["latencia_ms"].dropna(), 99) if len(sucessos) > 0 else np.nan
        razao = vazao / p99 if (p99 and p99 > 0) else 0

        registros_runs.append({
            "sistema": sistema,
            "N": n_threads,
            "run": run,
            "vazao": vazao,
            "p99": p99,
            "razao": razao
        })

    df_runs = pd.DataFrame(registros_runs)

    resumo = df_runs.groupby(["sistema", "N"]).agg(
        vazao_med=("vazao", "median"),
        vazao_min=("vazao", "min"),
        vazao_max=("vazao", "max"),
        p99_med=("p99", "median"),
        p99_min=("p99", "min"),
        p99_max=("p99", "max"),
        razao_med=("razao", "median")
    ).reset_index().sort_values(["sistema", "N"])

    resumo.to_csv("resultados/graficos/e1_resumo_mediana.csv", index=False)
    print("\n--- RESUMO E1 (Mediana das execuções) ---")
    print(resumo.to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    estilos = {
        "etcd": {"label": "etcd (Forte - Raft)", "color": "#1b7837", "marker": "o"},
        "cassandra": {"label": "Cassandra (Eventual - CL=ONE)", "color": "#5e3c99", "marker": "s"}
    }

    for sistema, dados in resumo.groupby("sistema"):
        est = estilos[sistema]
        ax.plot(dados["vazao_med"], dados["p99_med"], label=est["label"],
                color=est["color"], marker=est["marker"], linewidth=2)

        idx_otimo = dados["razao_med"].idxmax()
        otimo = dados.loc[idx_otimo]
        ax.annotate(
            f"N={int(otimo['N'])} (ótimo)",
            xy=(otimo["vazao_med"], otimo["p99_med"]),
            xytext=(10, 10), textcoords="offset points",
            fontsize=9, fontweight="bold", color=est["color"],
            arrowprops=dict(arrowstyle="->", color=est["color"], lw=1)
        )

        n1 = dados[dados["N"] == 1]
        if not n1.empty:
            ax.annotate("N=1", xy=(n1["vazao_med"].values[0], n1["p99_med"].values[0]),
                        xytext=(5, -12), textcoords="offset points", fontsize=8)

    ax.set_yscale("log") 
    ax.set_xlabel("Vazão efetiva (req/s com sucesso)", fontsize=11)
    ax.set_ylabel("Latência p99 (ms, escala log)", fontsize=11)
    ax.set_title("E1: Curva de Saturação — Vazão Efetiva vs. Latência p99", fontsize=12)
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig("resultados/graficos/e1_curva_saturacao.png", dpi=300)
    plt.close()

def processar_e2():
    arquivos = glob.glob("resultados/e2/*.csv")
    if not arquivos:
        print("Nenhum arquivo encontrado em resultados/e2/")
        return

    registros = []
    for arq in arquivos:
        nome = os.path.basename(arq)
        match = re.match(r"(etcd|cassandra)_otimo_run(\d+)\.csv", nome)
        if not match:
            continue
        sistema, run = match.group(1), int(match.group(2))

        df = pd.read_csv(arq)
        duracao = df["timestamp_inicio"].max() - df["timestamp_inicio"].min()
        sucessos = df[df["sucesso"] == 1]
        vazao_total = len(sucessos) / duracao if duracao > 0 else 0

        for op in ["GET", "PUT"]:
            sub = sucessos[sucessos["operacao"] == op]["latencia_ms"].dropna()
            if len(sub) == 0:
                continue
            registros.append({
                "sistema": sistema,
                "operacao": op,
                "run": run,
                "vazao_total": vazao_total,
                "p50": np.percentile(sub, 50),
                "p95": np.percentile(sub, 95),
                "p99": np.percentile(sub, 99),
            })

    df_e2 = pd.DataFrame(registros)
    resumo_e2 = df_e2.groupby(["sistema", "operacao"]).agg(
        vazao_med=("vazao_total", "median"),
        p50_med=("p50", "median"),
        p95_med=("p95", "median"),
        p99_med=("p99", "median"),
        p99_min=("p99", "min"),
        p99_max=("p99", "max"),
    ).reset_index()

    resumo_e2.to_csv("resultados/graficos/e2_baseline_percentis.csv", index=False)
    print("\n--- RESUMO E2 (Baseline - Mediana das execuções) ---")
    print(resumo_e2.to_string(index=False))

def processar_e3():
    arquivos = glob.glob("resultados/e3/*.csv")
    if not arquivos:
        print("Nenhum arquivo encontrado em resultados/e3/")
        return

    registros = []
    for arq in arquivos:
        nome = os.path.basename(arq)
        match = re.match(r"stale_(etcd|cassandra)_(base|atraso)_run(\d+)\.csv", nome)
        if not match:
            continue
        sistema, condicao, run = match.group(1), match.group(2), int(match.group(3))

        df = pd.read_csv(arq)
        confirmados = df[df["put_sucesso"] == 1]
        total_pares = len(confirmados)
        qtd_stale = confirmados["stale"].sum()
        taxa_stale_pct = (qtd_stale / total_pares * 100.0) if total_pares > 0 else 0.0

        registros.append({
            "sistema": sistema,
            "condicao": condicao,
            "run": run,
            "pares_confirmados": total_pares,
            "qtd_stale": qtd_stale,
            "taxa_stale_pct": taxa_stale_pct
        })

    df_e3 = pd.DataFrame(registros)
    resumo_e3 = df_e3.groupby(["sistema", "condicao"]).agg(
        pares_med=("pares_confirmados", "median"),
        stale_med=("qtd_stale", "median"),
        taxa_stale_pct_med=("taxa_stale_pct", "median"),
        taxa_stale_pct_min=("taxa_stale_pct", "min"),
        taxa_stale_pct_max=("taxa_stale_pct", "max"),
    ).reset_index()

    resumo_e3.to_csv("resultados/graficos/e3_stale_reads_resumo.csv", index=False)
    print("\n--- RESUMO E3 (Stale Reads - Mediana das execuções) ---")
    print(resumo_e3.to_string(index=False))


if __name__ == "__main__":
    processar_e1()
    processar_e2()
    processar_e3()