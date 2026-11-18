latency-compose

– T2 de Sistemas Distribuídos⚡💥

Este laboratório sobe uma rede de três nós e um contêiner gerador de carga para comparar etcd e Cassandra no GitHub Codespaces.

0. Antes de começar >.<

Abra este repositório em um GitHub Codespace.

Aguarde o Codespace terminar de preparar o ambiente.

Abra o terminal integrado com Terminal > Novo Terminal.

Confirme que Docker e Docker Compose estão disponíveis:

docker --version
docker compose version


Atenção: Deve-se subir individualmente ambos os laboratórios. Nunca suba os dois juntos!

1. Subir o laboratório do etcd

Execute:

docker compose -f etcd.yml up -d


Aguarde os contêineres iniciarem e confira o estado:

docker compose -f etcd.yml ps


Os três nós devem aparecer com o estado Up/Running.

Verifique a saúde do cluster:

docker exec -e ETCDCTL_API=3 n1 etcdctl --endpoints=http://172.21.0.11:2379 endpoint health


Aguarde o contêiner gerador instalar as dependências Python. Você pode conferir:

docker exec gerador python -c "import requests; print('gerador pronto')"


Para encerrar o laboratório do etcd:

docker compose -f etcd.yml down


2. Subir o laboratório do Cassandra

Só prossiga depois de encerrar o laboratório do etcd.

Inicie os três nós e o gerador:

docker compose -f cassandra.yml up -d


Aguarde o Cassandra ficar pronto:

./scripts/cassandra_up.sh


O script espera os nós ficarem disponíveis e cria o keyspace lab e a tabela lab.kv.

Confirme o estado dos contêineres:

docker compose -f cassandra.yml ps
docker exec n1 cqlsh -e "describe cluster"


3. Simular atraso de rede

Estes comandos podem ser usados com os dois laboratórios.

Adicione 50 ms de atraso em cada sentido dos nós:

./scripts/latencia_on.sh 50ms n1 n2 n3


Meça o RTT entre n1 e n2:

./scripts/rtt.sh n1 172.20.0.12


Remova o atraso:

./scripts/latencia_off.sh n1 n2 n3


4. Simular a perda de conexão de um nó

Isole n1 da rede interna entre os nós:

./scripts/particao.sh


n1 continua acessível pela rede dos clientes.

Execute o teste que quiser durante a partição.

Reconecte n1 à rede interna:

./scripts/cura.sh


5. Executar os Experimentos (E1, E2 e E3)

5.1. Experimento E1 — Curva de Saturação

O objetivo é testar vários números de threads simultâneas (N) por 120 segundos (2 minutos) cada, repetindo 3 vezes para calcular a mediana.

Passo 1: Rodar E1 no etcd

Certifique-se de que apenas o etcd.yml está rodando (Seção 1).

Execute o loop abaixo no terminal (vai testar N de 1 até 512, 3 vezes cada):

for N in 1 2 4 8 16 32 64 128 256 512; do
  for run in 1 2 3; do
    docker exec gerador python /app/carga.py \
      --sistema etcd \
      --threads $N \
      --duracao 120 \
      --saida /app/resultados/e1/etcd_n${N}_run${run}.csv
  done
done


(Opcional, mas recomendado) Abra um segundo terminal e rode docker stats gerador durante os testes de N=256 e N=512 para confirmar que a CPU do gerador não saturou (não bateu 400%).

Encerre o etcd antes de ir para o Cassandra:

docker compose -f etcd.yml down


Passo 2: Rodar E1 no Cassandra

Suba o cluster do Cassandra e crie a tabela (Seção 2).

Execute o mesmo loop trocando para cassandra:

for N in 1 2 4 8 16 32 64 128 256 512; do
  for run in 1 2 3; do
    docker exec gerador python /app/carga.py \
      --sistema cassandra \
      --threads $N \
      --duracao 120 \
      --saida /app/resultados/e1/cassandra_n${N}_run${run}.csv
  done
done


Passo 3: Gerar o gráfico do E1 e descobrir o N ótimo

Com qualquer um dos dois contêineres gerador ativo, rode o script de análise:

docker exec gerador python /app/analisar.py


Olhe no terminal a tabela EXPERIMENTO E1 e anote qual valor de N teve a maior razao_mediana ($\text{vazão} / \text{p99}$) para o etcd e para o Cassandra. Esses são os seus valores de N ótimo para o E2.

Confira o gráfico gerado em ./gerador/resultados/graficos/e1_curva_saturacao.png.

5.2. Experimento E2 — Baseline (Desempenho no N Ótimo)

Aqui rodamos cada sistema no seu respectivo N ótimo encontrado no E1, por 180 segundos (3 minutos), repetindo 3 vezes sem falhas e sem atraso de rede.

Passo 1: Rodar E2 no etcd

Suba apenas o etcd.yml (Seção 1).

Substitua 16 abaixo pelo N ótimo do etcd encontrado no E1 e execute:

N_OTIMO_ETCD=16

for run in 1 2 3; do
  docker exec gerador python /app/carga.py \
    --sistema etcd \
    --threads $N_OTIMO_ETCD \
    --duracao 180 \
    --saida /app/resultados/e2/etcd_otimo_run${run}.csv
done


Derrube o etcd:

docker compose -f etcd.yml down


Passo 2: Rodar E2 no Cassandra

Suba apenas o cassandra.yml e rode ./scripts/cassandra_up.sh (Seção 2).

Substitua 32 abaixo pelo N ótimo do Cassandra encontrado no E1 e execute:

N_OTIMO_CASSANDRA=32

for run in 1 2 3; do
  docker exec gerador python /app/carga.py \
    --sistema cassandra \
    --threads $N_OTIMO_CASSANDRA \
    --duracao 180 \
    --saida /app/resultados/e2/cassandra_otimo_run${run}.csv
done


Passo 3: Gerar a tabela e o gráfico do E2

docker exec gerador python /app/analisar.py


Os resultados de p50, p95, p99 (separados por GET e PUT) e vazão estarão em ./gerador/resultados/graficos/e2_tabela_baseline.csv e ./gerador/resultados/graficos/e2_percentis_baseline.png.

5.3. Experimento E3 — Leituras Obsoletas (Stale Reads)

O coordenador envia PUT no Nó 1 (n1) e imediatamente faz GET no Nó 3 (n3) por 10.000 pares, repetindo 3 vezes na rede normal e 3 vezes com atraso de 50 ms entre os nós.

Passo 1: Rodar E3 no etcd (Rede Normal + Rede com Atraso)

Suba apenas o etcd.yml (Seção 1) e garanta que não há atraso ativo (./scripts/latencia_off.sh n1 n2 n3).

Rode as 3 repetições na condição base (sem atraso):

for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema etcd \
    --pares 10000 \
    --saida /app/resultados/e3/stale_etcd_base_run${run}.csv
done


Ative o atraso de 50 ms por sentido (RTT = 100 ms) e confirme com rtt.sh:

./scripts/latencia_on.sh 50ms n1 n2 n3
./scripts/rtt.sh n1 172.20.0.12


Rode as 3 repetições na condição atraso:

for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema etcd \
    --pares 10000 \
    --saida /app/resultados/e3/stale_etcd_atraso_run${run}.csv
done


Remova o atraso de rede e derrube o etcd:

./scripts/latencia_off.sh n1 n2 n3
docker compose -f etcd.yml down


Passo 2: Rodar E3 no Cassandra (Rede Normal + Rede com Atraso)

Suba apenas o cassandra.yml e execute ./scripts/cassandra_up.sh (Seção 2).

Rode as 3 repetições na condição base (sem atraso):

for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema cassandra \
    --pares 10000 \
    --saida /app/resultados/e3/stale_cassandra_base_run${run}.csv
done


Ative o atraso de 50 ms por sentido (RTT = 100 ms) e confirme com rtt.sh:

./scripts/latencia_on.sh 50ms n1 n2 n3
./scripts/rtt.sh n1 172.20.0.12


Rode as 3 repetições na condição atraso:

for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema cassandra \
    --pares 10000 \
    --saida /app/resultados/e3/stale_cassandra_atraso_run${run}.csv
done


Remova o atraso de rede:

./scripts/latencia_off.sh n1 n2 n3


Passo 3: Consolidar os resultados do E3

docker exec gerador python /app/analisar.py


A taxa percentual de stale reads (mediana e variação min-max) será salva em ./gerador/resultados/graficos/e3_tabela_stale_reads.csv.

6. Trocar de sistema

Para parar o laboratório atual:

# se o sistema atual for o Cassandra:
docker compose -f cassandra.yml down

# se o sistema atual for o etcd:
docker compose -f etcd.yml down


Depois, execute a subida correspondente da seção 1 ou 2.

7. Encerrar tudo

Quando terminar os testes, pare o contêiner do sistema ativo:

# Use apenas o arquivo correspondente ao sistema ativo.
docker compose -f etcd.yml down
# ou
docker compose -f cassandra.yml down


Para remover também os contêineres parados, use o comando manualmente conforme necessário:

docker container prune -f