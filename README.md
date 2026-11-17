# latency-compose
– T2 de Sistemas Distribuídos⚡💥

Este laboratório sobe uma rede de três nós e um contêiner gerador de carga para comparar **etcd** e **Cassandra** no GitHub Codespaces.

## 0. Antes de começar >.<

1. Abra este repositório em um **GitHub Codespace**.
2. Aguarde o Codespace terminar de preparar o ambiente.
3. Abra o terminal integrado com **Terminal > Novo Terminal**.
4. Confirme que Docker e Docker Compose estão disponíveis:

   ```bash
   docker --version
   docker compose version
   ```

Deve se subir individualmente ambos os laboratorios, não suba junto! 
## 1. Subir o laboratório do etcd

1. Execute:

   ```bash
   docker compose -f etcd.yml up -d
   ```

2. Aguarde os contêineres iniciarem e confira o estado:

   ```bash
   docker compose -f etcd.yml ps
   ```

   Os três nós devem aparecer com o estado `Up`/`Running`.

3. Verifique a saúde do cluster:

   ```bash
   docker exec n1 sh -c 'ETCDCTL_API=3 etcdctl --endpoints=http://172.21.0.11:2379 endpoint health'
   ```

4. Aguarde o contêiner `gerador` instalar as dependências Python. Você pode conferir:

   ```bash
   docker exec gerador python -c "import requests; print('gerador pronto')"
   ```

Para encerrar o laboratório do etcd:

```bash
docker compose -f etcd.yml down
```

## 2. Subir o laboratório do Cassandra

Só prossiga depois de encerrar o laboratório do etcd.

1. Inicie os três nós e o gerador:

   ```bash
   docker compose -f cassandra.yml up -d
   ```

2. Aguarde o Cassandra ficar pronto:

   ```bash
   ./scripts/cassandra_up.sh
   ```

   O script espera os nós ficarem disponíveis e cria a chave `lab` e a tabela `lab.kv`.

3. Confirme o estado dos contêineres:

   ```bash
   docker compose -f cassandra.yml ps
   docker exec n1 cqlsh -e "describe cluster"
   ```

## 3. Simular atraso de rede

Estes comandos podem ser usados com os dois laboratórios.

1. Adicione 50 ms de atraso em cada sentido dos nós:

   ```bash
   ./scripts/latencia_on.sh 50ms n1 n2 n3
   ```

2. Meça o RTT entre `n1` e `n2`:

   ```bash
   ./scripts/rtt.sh n1 172.20.0.12
   ```

3. Remova o atraso:

   ```bash
   ./scripts/latencia_off.sh n1 n2 n3
   ```

## 4. Simular a perda de conexão de um nó

1. Isole `n1` da rede interna entre os nós:

   ```bash
   ./scripts/particao.sh
   ```

   `n1` continua acessível pela rede dos clientes.

2. Execute o teste que quiser durante a partição.

3. Reconecte `n1` à rede interna:

   ```bash
   ./scripts/cura.sh
   ```

## 5. Medir leituras obsoletas

Com o sistema desejado já iniciado, execute o teste no contêiner `gerador`:

```bash
docker exec gerador python /app/stale_reads.py \
  --sistema cassandra \
  --pares 10000 \
  --saida /app/stale_cassandra.csv
```

Para testar o etcd, troque `--sistema cassandra` por `--sistema etcd` e altere o nome do arquivo de saída.

Copie o CSV gerado para a máquina do Codespace:

```bash
docker cp gerador:/app/stale_cassandra.csv ./resultados/stale_cassandra.csv
```

## 6. Trocar de sistema

Para parar o laboratório atual:

```bash
# se o sistema atual for o Cassandra:
docker compose -f cassandra.yml down

# se o sistema atual for o etcd:
docker compose -f etcd.yml down
```

Depois, execute a subida correspondente da seção 1 ou 3.

## 9. Encerrar tudo

Quando terminar os testes, pare o contêiner do sistema ativo:

```bash
# Use apenas o arquivo correspondente ao sistema ativo.
docker compose -f etcd.yml down
# ou
docker compose -f cassandra.yml down
```

Para remover também os contêineres parados e os resultados, use os comandos manualmente conforme necessário:

```bash
docker container prune -f
```