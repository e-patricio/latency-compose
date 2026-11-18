import pandas as pd
import glob
import math
import matplotlib.pyplot as plt
import os

def calcular_medianas(sistema):
    ns = [1, 2, 4, 8, 16, 32]
    resultados = []
    
    for n in ns:
        arquivos = glob.glob(f"../resultados/e1/{sistema}_n{n}_run*.csv")
        vs, ps = [], []
        
        for f in arquivos:
            try:
                df = pd.read_csv(f)
                if len(df) == 0: continue
                
                t0 = df['timestamp_inicio'].iloc[0]
                val = df[df['timestamp_inicio'] >= t0 + 30.0]
                if len(val) == 0: continue
                
                dur = val['timestamp_inicio'].iloc[-1] - val['timestamp_inicio'].iloc[0]
                dur = max(dur, 0.001)
                
                ok = val[(val['sucesso'] == 1) & (val['latencia_ms'].notna())]
                vazao = len(ok) / dur
                
                if len(ok) > 0:
                    lats = sorted(ok['latencia_ms'].dropna().astype(float))
                    p99 = lats[min(len(lats)-1, math.ceil(0.99 * len(lats)) - 1)]
                    vs.append(vazao)
                    ps.append(p99)
            except Exception as e:
                print(f"Erro ao ler {f}: {e}")
                
        if vs and ps:
            v_med = sorted(vs)[len(vs)//2]
            p_med = sorted(ps)[len(ps)//2]
            resultados.append({'n': n, 'vazao': v_med, 'p99': p_med})
            
    return pd.DataFrame(resultados)

def main():
    print("Processando dados do etcd...")
    df_etcd = calcular_medianas("etcd")
    
    print("Processando dados do Cassandra...")
    df_cass = calcular_medianas("cassandra")
    
    if df_etcd.empty or df_cass.empty:
        print("Dados insuficientes para gerar o gráfico. Verifique a pasta resultados/e1/")
        return

    plt.figure(figsize=(10, 6))
    
    # Plot etcd
    plt.plot(df_etcd['vazao'], df_etcd['p99'], marker='o', color='#1f77b4', linewidth=2, label='etcd (Forte / Raft)')
    plt.annotate('N=4 (ótimo)', xy=(df_etcd['vazao'].iloc[2], df_etcd['p99'].iloc[2]), 
                 xytext=(df_etcd['vazao'].iloc[2]+15, df_etcd['p99'].iloc[2]-2),
                 fontsize=10, color='#1f77b4', weight='bold')
    plt.annotate('platô', xy=(df_etcd['vazao'].iloc[-1], df_etcd['p99'].iloc[-1]), 
                 xytext=(df_etcd['vazao'].iloc[-1]-70, df_etcd['p99'].iloc[-1]+20),
                 fontsize=10, color='#1f77b4')
                 
    # Plot cassandra
    plt.plot(df_cass['vazao'], df_cass['p99'], marker='s', color='#2ca02c', linewidth=2, label='Cassandra (Eventual / CL=ONE)')
    plt.annotate('N=2 (ótimo)', xy=(df_cass['vazao'].iloc[1], df_cass['p99'].iloc[1]), 
                 xytext=(df_cass['vazao'].iloc[1]+30, df_cass['p99'].iloc[1]-0.5),
                 fontsize=10, color='#2ca02c', weight='bold')
    plt.annotate('platô', xy=(df_cass['vazao'].iloc[-1], df_cass['p99'].iloc[-1]), 
                 xytext=(df_cass['vazao'].iloc[-1]-100, df_cass['p99'].iloc[-1]+5),
                 fontsize=10, color='#2ca02c')
                 
    plt.yscale('log')
    plt.xlabel('Vazão Efetiva (req/s com sucesso)', fontsize=12)
    plt.ylabel('Latência p99 (ms, escala log)', fontsize=12)
    plt.title('Experimento E1 - Curva de Saturação (etcd vs Cassandra)', fontsize=14, pad=15)
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(fontsize=11, loc='upper left')
    
    caminho_saida = 'saturacao_e1.png'
    plt.savefig(caminho_saida, dpi=300, bbox_inches='tight')
    print(f"\nGráfico gerado com sucesso em: {caminho_saida}")

if __name__ == "__main__":
    main()