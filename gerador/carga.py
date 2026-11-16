import argparse, csv, os, random, threading, time
from adaptadores import EtcdAdapter, CassandraAdapter

def worker(tid, sistema, fim, buf, stop_event):
    rng = random.Random(42 + tid)
    adaptador = EtcdAdapter(timeout=2.0) if sistema == "etcd" else CassandraAdapter(timeout=2.0)
    val = b"x" * 256
    while not stop_event.is_set() and time.time() < fim:
        op = "GET" if rng.random() < 0.80 else "PUT"
        chave = f"k_{rng.randrange(10000):04d}"
        t0_abs, t0_mono = time.time(), time.perf_counter()
        try:
            adaptador.get(chave) if op == "GET" else adaptador.put(chave, val)
            buf.append((f"{t0_abs:.6f}", tid, op, 1, f"{(time.perf_counter() - t0_mono)*1000:.4f}"))
        except Exception:
            buf.append((f"{t0_abs:.6f}", tid, op, 0, ""))
    if hasattr(adaptador, "close"):
        adaptador.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sistema", required=True, choices=["etcd", "cassandra"])
    p.add_argument("--threads", type=int, required=True)
    p.add_argument("--duracao", type=int, required=True)
    p.add_argument("--saida", required=True)
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    fim = time.time() + args.duracao
    stop_event = threading.Event()
    bufs = [[] for _ in range(args.threads)]
    threads = [threading.Thread(target=worker, args=(i, args.sistema, fim, bufs[i], stop_event), daemon=True) for i in range(args.threads)]
    print(f"[INICIO] {args.sistema} N={args.threads} ({args.duracao}s)...")
    for t in threads: t.start()
    for t in threads: t.join()

    total = 0
    with open(args.saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_inicio", "thread_id", "operacao", "sucesso", "latencia_ms"])
        for b in bufs:
            w.writerows(b)
            total += len(b)
    print(f"[FIM] {total} amostras salvas em {args.saida}")

if __name__ == "__main__":
    main()
