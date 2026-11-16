import argparse, csv, os, time
from adaptadores import EtcdAdapter, CassandraAdapter

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sistema", required=True, choices=["etcd", "cassandra"])
    p.add_argument("--pares", type=int, default=10000)
    p.add_argument("--saida", required=True)
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    if args.sistema == "etcd":
        w_node = EtcdAdapter(endpoints=["http://172.21.0.11:2379"], timeout=2.0)
        r_node = EtcdAdapter(endpoints=["http://172.21.0.13:2379"], timeout=2.0)
    else:
        w_node = CassandraAdapter(hosts=["172.21.0.11"], timeout=2.0)
        r_node = CassandraAdapter(hosts=["172.21.0.13"], timeout=2.0)

    stale, validos, ultimo, regs = 0, 0, 0, []
    print(f"[E3] Iniciando {args.pares} pares PUT(n1) -> GET(n3) no {args.sistema}")
    for v in range(1, args.pares + 1):
        t0 = time.time()
        try:
            w_node.put("chave_stale_e3", f"{v:016d}".encode("ascii"))
            ultimo = v
        except Exception:
            continue
        try:
            resp = r_node.get("chave_stale_e3")
            lido = int(resp.decode("ascii")) if resp is not None else 0
            eh_stale = 1 if lido < ultimo else 0
            stale += eh_stale
            validos += 1
            regs.append((f"{t0:.6f}", ultimo, lido, eh_stale))
        except Exception:
            continue

    with open(args.saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "escrito_n1", "lido_n3", "stale"])
        w.writerows(regs)

    if hasattr(w_node, "close"): w_node.close()
    if hasattr(r_node, "close"): r_node.close()
    print(f"[E3 FIM] Validos: {validos} | Stale reads: {stale} ({(stale/validos*100 if validos else 0):.3f}%)")

if __name__ == "__main__":
    main()
