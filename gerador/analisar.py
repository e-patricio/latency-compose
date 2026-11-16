import argparse, csv, statistics

def percentil(dados, p):
    if not dados:
        return 0.0
    dados_ord = sorted(dados)
    k = (len(dados_ord) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(dados_ord) else f
    return dados_ord[f] + (dados_ord[c] - dados_ord[f]) * (k - f)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("arquivo", help="Caminho do CSV")
    p.add_argument("--descartar", type=float, default=30.0, help="Segundos iniciais p descartar")
    args = p.parse_args()

    linhas = []
    with open(args.arquivo, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            linhas.append((float(row["timestamp_inicio"]), row["operacao"], int(row["sucesso"]), row["latencia_ms"]))

    if not linhas:
        print("Arquivo vazio.")
        return

    t_inicio = min(x[0] for x in linhas)
    t_corte = t_inicio + args.descartar
    validas = [x for x in linhas if x[0] >= t_corte]

    if not validas:
        print(f"Nenhuma amostra apos descartar {args.descartar}s (rode com --descartar 0 para testes curtos).")
        return

    t_fim = max(x[0] for x in validas)
    duracao_efetiva = max(t_fim - t_corte, 0.001)

    sucessos = [x for x in validas if x[2] == 1 and x[3] != ""]
    erros = len(validas) - len(sucessos)

    lats_all = [float(x[3]) for x in sucessos]
    lats_get = [float(x[3]) for x in sucessos if x[1] == "GET"]
    lats_put = [float(x[3]) for x in sucessos if x[1] == "PUT"]

    vazao = len(sucessos) / duracao_efetiva
    p99_all = percentil(lats_all, 99)
    razao = (vazao / p99_all) if p99_all > 0 else 0.0

    print(f"=== Analise: {args.arquivo} (descarte={args.descartar}s) ===")
    print(f"Duracao util: {duracao_efetiva:.1f}s | Sucessos: {len(sucessos)} | Erros: {erros}")
    print(f"Vazao efetiva: {vazao:.2f} req/s")
    print(f"Geral -> p50: {percentil(lats_all, 50):.2f} ms | p95: {percentil(lats_all, 95):.2f} ms | p99: {p99_all:.2f} ms")
    print(f"GET   -> p50: {percentil(lats_get, 50):.2f} ms | p95: {percentil(lats_get, 95):.2f} ms | p99: {percentil(lats_get, 99):.2f} ms")
    print(f"PUT   -> p50: {percentil(lats_put, 50):.2f} ms | p95: {percentil(lats_put, 95):.2f} ms | p99: {percentil(lats_put, 99):.2f} ms")
    print(f"Razao (Vazao / p99): {razao:.2f} (req/s por ms)\n")

if __name__ == "__main__":
    main()
