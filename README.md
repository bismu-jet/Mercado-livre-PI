# Desafio SBPO 2025 - Solução para o Problema de Seleção de Pedidos

Este repositório contém uma solução avançada para o "Problema da Seleção de Pedidos Ótima", proposto pelo Mercado Livre como parte do Desafio de Otimização SBPO 2025.

O objetivo do problema é determinar um subconjunto de pedidos (uma "wave") e os corredores de um armazém a serem visitados para maximizar a densidade da coleta, ou seja, o número de itens coletados por corredor visitado, respeitando restrições operacionais de capacidade e estoque.

A abordagem implementada utiliza otimização matemática (Mixed-Integer Programming - MIP) para encontrar soluções de alta qualidade, empregando o **Algoritmo de Dinkelbach** para tratar a natureza fracionária da função objetivo.

## Principais Características

  * **Modelo Matemático Robusto:** Implementação de um modelo MIP que captura todas as restrições do problema, incluindo limites de tamanho da wave e suficiência de estoque.
  * **Algoritmo de Dinkelbach:** Utilização de um método iterativo e eficaz, específico para problemas de programação fracionária, garantindo a busca por uma solução ótima.
  * **Gestão de Tempo Adaptativa ("Momentum"):** O solver aloca dinamicamente o tempo de otimização a cada iteração de Dinkelbach, dedicando mais esforço computacional a subproblemas que demonstram maior potencial de melhoria.
  * **Heurística de Partida (Warm Start):** Uma heurística gulosa é executada para gerar uma solução inicial de alta qualidade, acelerando a convergência do algoritmo principal.
  * **Estrutura de Código Modular:** O projeto é organizado de forma limpa e desacoplada, separando as definições do modelo de dados (`model.py`), o parser de instâncias (`data_parser.py`) e a lógica do solver (`solver_V3.py`).

## :warning: Nota Importante sobre as Ferramentas

O regulamento oficial do desafio especifica o uso da linguagem **Java** com os solvers **CPLEX** ou **OR-Tools**.

Esta implementação foi desenvolvida em **Python** com o solver **Gurobi**. A escolha foi motivada pela agilidade no desenvolvimento, pela expressividade da API Python do Gurobi e pela robustez da ferramenta para prototipagem e resolução de problemas MIP complexos. A lógica e o modelo matemático aqui presentes são, no entanto, diretamente traduzíveis para a plataforma Java/CPLEX, se necessário.

## Estrutura do Projeto

```
.
├── docs/
│   ├── pt_challenge_rules.pdf        # Regulamento oficial do desafio
│   └── pt_problem_description.pdf    # Descrição matemática do problema
│
├── datasets/
│   ├── a/
│   │   └── instance_0001.txt         # Exemplo de instância do conjunto A
│   └── b/
│       └── instance_0001.txt         # Exemplo de instância do conjunto B
│
├── out_answers/
│   ├── a/
│   │   └── solucao_0001.txt          # Exemplo de arquivo de saída para o conjunto A
│   └── b/
│       └── solucao_0001.txt          # Exemplo de arquivo de saída para o conjunto B
│
├── main.py                           # Ponto de entrada da aplicação
├── solver_V3.py                      # Implementação principal do solver (Dinkelbach)
├── data_parser.py                    # Módulo para leitura e parsing dos arquivos de instância
├── model.py                          # Módulo com as classes de dados (Instance, Order, Aisle)
├── solver.py                         # (Versão anterior) Solver com linearização Big-M
└── README.md                         # Este arquivo
```

## Pré-requisitos

Para executar este projeto, é necessário ter o seguinte software instalado:

1.  **Python 3.8+**
2.  **Gurobi Optimizer 9.5+:** O Gurobi é um solver comercial que requer uma licença. Licenças acadêmicas gratuitas estão disponíveis no [site oficial](https://www.gurobi.com/academia/academic-program-and-licenses/).
3.  **Biblioteca Python do Gurobi (`gurobipy`):** Normalmente instalada junto com o otimizador.

## Instalação e Configuração

1.  **Clone o repositório:**

    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <NOME_DO_DIRETORIO>
    ```

2.  **Instale o Gurobi:**
    Siga as instruções no site do Gurobi para instalar o otimizador e ativar sua licença.

3.  **Crie um ambiente virtual (recomendado):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

4.  **Instale a biblioteca do Gurobi:**
    Certifique-se de que seu ambiente virtual possa encontrar a biblioteca Gurobi. Se necessário, instale-a explicitamente:

    ```
    pip install gurobipy
    ```

## Como Executar

O script `main.py` é o ponto de entrada para executar a otimização. Ele aceita argumentos de linha de comando para especificar os arquivos de entrada, saída e o limite de tempo.

### Execução de uma Única Instância

Use o seguinte comando no terminal, substituindo os placeholders:

```bash
python main.py <caminho_para_arquivo_de_entrada> <caminho_para_arquivo_de_saida> [limite_de_tempo_em_segundos]
```

  * **`<caminho_para_arquivo_de_entrada>`:** O caminho para o arquivo de texto da instância. Ex: `datasets/a/instance_0001.txt`.
  * **`<caminho_para_arquivo_de_saida>`:** O caminho onde o arquivo de solução será salvo. Ex: `out_answers/a/solucao_0001.txt`.
  * **`[limite_de_tempo_em_segundos]`:** (Opcional) O tempo máximo total para a execução do solver. Se omitido, o valor padrão definido em `main.py` será usado (atualmente 600 segundos, conforme o desafio).

**Exemplo:**

```bash
python main.py datasets/b/instance_0001.txt out_answers/b/solucao_0001.txt 300
```

### Execução em Lote (Batch)

O script `main.py` contém flags (`run_all` e `datasheet`) que podem ser modificadas para executar todas as instâncias de um determinado conjunto de dados (`a` ou `b`) de uma só vez. Esta funcionalidade foi criada para facilitar os testes em massa durante o desenvolvimento.

## Detalhes da Abordagem de Solução

### 1\. Natureza do Problema: Programação Fracionária

A função objetivo, $\\max\\frac{\\sum\_{o\\in O'}\\sum\_{i\\in I\_{o}}u\_{oi}}{|A'|}$, é um quociente entre duas funções lineares, o que caracteriza o problema como **Programação Inteira Mista Fracionária-Linear**. Modelos com essa característica não podem ser resolvidos diretamente por solvers MIP padrão.

### 2\. Algoritmo de Dinkelbach

Para contornar a complexidade da função objetivo, implementamos o **Algoritmo de Dinkelbach**. Este método iterativo transforma o problema fracionário em uma sequência de subproblemas de Programação Inteira Mista (MIP) mais fáceis de resolver.

O algoritmo funciona da seguinte maneira:

1.  **Inicialização:** Começa com uma estimativa da razão ótima, $R\_0$, obtida por meio de uma heurística gulosa.
2.  **Iteração:** Em cada iteração $k$, resolve-se o seguinte subproblema linearizado:
    $$F(R_k) = \max \left( \sum_{o \in O'} \sum_{i \in I_o} u_{oi} - R_k \cdot |A'| \right)$$
3.  **Convergência:**
      * Se o valor ótimo do subproblema, $F(R\_k)$, for muito próximo de zero, a solução atual é considerada ótima e o algoritmo para.
      * Caso contrário, a solução encontrada no subproblema (novos conjuntos $O'$ e $A'$) é usada para calcular uma nova e melhor razão, $R\_{k+1}$, que será usada na próxima iteração.

### 3\. Gestão de Tempo "Momentum"

Dado o limite de tempo fixo de 10 minutos por instância, uma gestão de tempo inteligente é crucial. A nossa implementação de Dinkelbach não divide o tempo igualmente entre as iterações. Em vez disso, ela:

  * Aloca um **orçamento de tempo base** para cada iteração.
  * Se uma iteração resulta em uma **melhora significativa** no valor da função objetivo (acima de um limiar de 10%), ela ganha "momentum".
  * A iteração seguinte recebe um **bônus de tempo**, permitindo ao Gurobi explorar mais a fundo uma região promissora do espaço de busca.

Essa estratégia adaptativa aumenta a probabilidade de encontrar soluções de alta qualidade dentro do tempo disponível.