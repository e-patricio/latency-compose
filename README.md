# T2 de Sistemas Distribuídos ⚡💥

Este laboratório sobe uma rede com três nós e um contêiner gerador de carga para comparar `etcd` e `Cassandra` no GitHub Codespaces.

> **Atenção:** os laboratórios do `etcd` e do `Cassandra` devem ser iniciados individualmente. Nunca execute os dois ao mesmo tempo.

## Índice

- [0. Antes de começar](#0-antes-de-começar)
- [1. Subir o laboratório do etcd](#1-subir-o-laboratório-do-etcd)
- [2. Subir o laboratório do Cassandra](#2-subir-o-laboratório-do-cassandra)
- [3. Simular atraso de rede](#3-simular-atraso-de-rede)
- [4. Simular a perda de conexão de um nó](#4-simular-a-perda-de-conexão-de-um-nó)
- [5. Executar os experimentos](#5-executar-os-experimentos)
  - [5.1. Experimento E1: curva de saturação](#51-experimento-e1-curva-de-saturação)
  - [5.2. Experimento E2: baseline](#52-experimento-e2-baseline)
  - [5.3. Experimento E3: leituras obsoletas](#53-experimento-e3-leituras-obsoletas)
- [6. Trocar de sistema](#6-trocar-de-sistema)
- [7. Geração de gráficos](#7-geração-de-gráficos)
- [8. Encerrar tudo](#8-encerrar-tudo)

## 0. Antes de começar

1. Abra este repositório em um GitHub Codespace.
2. Aguarde o Codespace concluir a preparação do ambiente.
3. Abra o terminal integrado em **Terminal > Novo Terminal**.
4. Confirme que o Docker e o Docker Compose estão disponíveis:

   ```bash
   docker --version
   docker compose version
   ```

## 1. Subir o laboratório do etcd

Inicie o ambiente:

```bash
docker compose -f etcd.yml up -d
```

Aguarde os contêineres iniciarem e confira o estado:

```bash
docker compose -f etcd.yml ps
```

Os três nós devem aparecer com o estado `Up/Running`.

Verifique a saúde do cluster:

```bash
docker exec -e ETCDCTL_API=3 n1 etcdctl \
  --endpoints=http://172.21.0.11:2379 endpoint health
```

Aguarde o contêiner gerador instalar as dependências Python. Você pode conferir:

```bash
docker exec gerador python -c "import requests; print('gerador pronto')"
```

Para encerrar o laboratório do `etcd`:

```bash
docker compose -f etcd.yml down
```

## 2. Subir o laboratório do Cassandra

Só prossiga depois de encerrar o laboratório do `etcd`.

Inicie os três nós e o gerador:

```bash
docker compose -f cassandra.yml up -d
```

Aguarde o Cassandra ficar pronto:

```bash
./scripts/cassandra_up.sh
```

O script espera os nós ficarem disponíveis e cria o keyspace `lab` e a tabela `lab.kv`.

Confirme o estado dos contêineres:

```bash
docker compose -f cassandra.yml ps
docker exec n1 cqlsh -e "describe cluster"
```

## 3. Simular atraso de rede

Estes comandos podem ser usados com os dois laboratórios.

Adicione 50 ms de atraso em cada sentido dos nós:

```bash
./scripts/latencia_on.sh 50ms n1 n2 n3
```

Meça o RTT entre `n1` e `n2`:

```bash
./scripts/rtt.sh n1 172.20.0.12
```

Remova o atraso:

```bash
./scripts/latencia_off.sh n1 n2 n3
```

## 4. Simular a perda de conexão de um nó

Isole `n1` da rede interna entre os nós:

```bash
./scripts/particao.sh
```

O nó `n1` continua acessível pela rede dos clientes.

Execute o teste desejado durante a partição.

Reconecte `n1` à rede interna:

```bash
./scripts/cura.sh
```

## 5. Executar os experimentos

### 5.1. Experimento E1: curva de saturação

O objetivo é testar vários números de threads simultâneas (`N`) por 120 segundos (2 minutos) cada, repetindo 3 vezes para calcular a mediana.

#### Passo 1: executar o E1 no etcd

Certifique-se de que apenas o arquivo `etcd.yml` está em execução.

Execute o loop abaixo no terminal. Ele testará `N` de 1 até 512, com 3 repetições para cada valor:

```bash
for N in 1 2 4 8 16 32 64 128 256 512; do
  for run in 1 2 3; do
    docker exec gerador python /app/carga.py \
      --sistema etcd \
      --threads "$N" \
      --duracao 120 \
      --saida "/app/resultados/e1/etcd_n${N}_run${run}.csv"
  done
done
```

Opcional, mas recomendado: em um segundo terminal, execute `docker stats gerador` durante os testes com `N=256` e `N=512` para confirmar que a CPU do gerador não foi saturada, ou seja, não atingiu 400%.

Encerre o `etcd` antes de iniciar o Cassandra:

```bash
docker compose -f etcd.yml down
```

#### Passo 2: executar o E1 no Cassandra

Suba o cluster do Cassandra e crie a tabela, conforme a [seção 2](#2-subir-o-laboratório-do-cassandra).

Execute o mesmo loop trocando o sistema para `cassandra`:

```bash
for N in 1 2 4 8 16 32 64 128 256 512; do
  for run in 1 2 3; do
    docker exec gerador python /app/carga.py \
      --sistema cassandra \
      --threads "$N" \
      --duracao 120 \
      --saida "/app/resultados/e1/cassandra_n${N}_run${run}.csv"
  done
done
```

#### Passo 3: gerar o gráfico do E1 e descobrir o N ótimo

Com qualquer um dos dois contêineres geradores ativo, execute o script de análise:

```bash
docker exec gerador python /app/analisar.py
```

Na tabela **EXPERIMENTO E1**, anote o valor de `N` com a maior `razao_mediana` (vazão/p99) para o `etcd` e para o Cassandra. Esses serão os valores ótimos de `N` usados no E2.

Confira o gráfico gerado em:

```text
./gerador/resultados/graficos/e1_curva_saturacao.png
```

### 5.2. Experimento E2: baseline

Execute cada sistema com o respectivo `N` ótimo encontrado no E1, por 180 segundos (3 minutos), repetindo 3 vezes. Não utilize falhas de rede ou atraso nesta etapa.

#### Passo 1: executar o E2 no etcd

Suba apenas o arquivo `etcd.yml`, conforme a [seção 1](#1-subir-o-laboratório-do-etcd).

Substitua `16` pelo `N` ótimo encontrado para o `etcd` no E1 e execute:

```bash
N_OTIMO_ETCD=16

for run in 1 2 3; do
  docker exec gerador python /app/carga.py \
    --sistema etcd \
    --threads "$N_OTIMO_ETCD" \
    --duracao 180 \
    --saida "/app/resultados/e2/etcd_otimo_run${run}.csv"
done
```

Encerre o `etcd`:

```bash
docker compose -f etcd.yml down
```

#### Passo 2: executar o E2 no Cassandra

Suba apenas o arquivo `cassandra.yml`:

```bash
docker compose -f cassandra.yml up -d
./scripts/cassandra_up.sh
```

Substitua `32` pelo `N` ótimo encontrado para o Cassandra no E1 e execute:

```bash
N_OTIMO_CASSANDRA=32

for run in 1 2 3; do
  docker exec gerador python /app/carga.py \
    --sistema cassandra \
    --threads "$N_OTIMO_CASSANDRA" \
    --duracao 180 \
    --saida "/app/resultados/e2/cassandra_otimo_run${run}.csv"
done
```

#### Passo 3: gerar a tabela e o gráfico do E2

```bash
docker exec gerador python /app/analisar.py
```

Os percentis p50, p95 e p99, separados por GET e PUT, além da vazão, estarão em:

```text
./gerador/resultados/graficos/e2_tabela_baseline.csv
./gerador/resultados/graficos/e2_percentis_baseline.png
```

### 5.3. Experimento E3: leituras obsoletas

O coordenador envia um PUT no nó 1 (`n1`) e imediatamente faz um GET no nó 3 (`n3`) para 10.000 pares, repetindo 3 vezes na rede normal e 3 vezes com atraso de 50 ms entre os nós.

#### Passo 1: executar o E3 no etcd

Suba apenas o arquivo `etcd.yml`, conforme a [seção 1](#1-subir-o-laboratório-do-etcd), e confirme que não há atraso ativo:

```bash
./scripts/latencia_off.sh n1 n2 n3
```

Execute as 3 repetições na condição base, sem atraso:

```bash
for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema etcd \
    --pares 10000 \
    --saida "/app/resultados/e3/stale_etcd_base_run${run}.csv"
done
```

Ative o atraso de 50 ms por sentido, equivalente a 100 ms de RTT, e confirme:

```bash
./scripts/latencia_on.sh 50ms n1 n2 n3
./scripts/rtt.sh n1 172.20.0.12
```

Execute as 3 repetições na condição com atraso:

```bash
for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema etcd \
    --pares 10000 \
    --saida "/app/resultados/e3/stale_etcd_atraso_run${run}.csv"
done
```

Remova o atraso e encerre o `etcd`:

```bash
./scripts/latencia_off.sh n1 n2 n3
docker compose -f etcd.yml down
```

#### Passo 2: executar o E3 no Cassandra

Suba apenas o arquivo `cassandra.yml` e inicialize o Cassandra:

```bash
docker compose -f cassandra.yml up -d
./scripts/cassandra_up.sh
```

Execute as 3 repetições na condição base, sem atraso:

```bash
for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema cassandra \
    --pares 10000 \
    --saida "/app/resultados/e3/stale_cassandra_base_run${run}.csv"
done
```

Ative o atraso de 50 ms por sentido, equivalente a 100 ms de RTT, e confirme:

```bash
./scripts/latencia_on.sh 50ms n1 n2 n3
./scripts/rtt.sh n1 172.20.0.12
```

Execute as 3 repetições na condição com atraso:

```bash
for run in 1 2 3; do
  docker exec gerador python /app/stale_reads.py \
    --sistema cassandra \
    --pares 10000 \
    --saida "/app/resultados/e3/stale_cassandra_atraso_run${run}.csv"
done
```

Remova o atraso:

```bash
./scripts/latencia_off.sh n1 n2 n3
```

#### Passo 3: consolidar os resultados do E3

```bash
docker exec gerador python /app/analisar.py
```

A taxa percentual de leituras obsoletas, com mediana e variação mínimo-máximo, será salva em:

```text
./gerador/resultados/graficos/e3_tabela_stale_reads.csv
```

## 6. Trocar de sistema

Para parar o laboratório atual:

```bash
# Se o sistema atual for o Cassandra:
docker compose -f cassandra.yml down

# Se o sistema atual for o etcd:
docker compose -f etcd.yml down
```

Depois, execute a subida correspondente conforme a [seção 1](#1-subir-o-laboratório-do-etcd) ou a [seção 2](#2-subir-o-laboratório-do-cassandra).

## 7. Geração de gráficos

Depois de gerar os CSVs do E1 para `etcd` e Cassandra, copie-os para a pasta de entrada do script. Os comandos do E1 salvam os arquivos em `gerador/resultados/e1/`, enquanto o script lê `resultados/e1/` na raiz do repositório:

```bash
mkdir -p resultados/e1
cp gerador/resultados/e1/*.csv resultados/e1/
```

O script usa os arquivos de `N=1, 2, 4, 8, 16 e 32` e salva o gráfico em `graphs/saturacao_e1.png`.

Na raiz do repositório, acesse a pasta dos scripts:

```bash
cd graphs
```

Instale o `pip` e as dependências necessárias (`numpy`, `pandas` e `matplotlib`):

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install numpy pandas matplotlib
```

Gere o gráfico:

```bash
python3 gerar_grafico_e1.py
```

## 8. Encerrar tudo

Pare o contêiner do sistema ativo:

```bash
# Use apenas o arquivo correspondente ao sistema ativo.

# Para o etcd:
docker compose -f etcd.yml down

# Para o Cassandra:
docker compose -f cassandra.yml down
```

Para remover também os contêineres parados:

```bash
docker container prune -f
```
