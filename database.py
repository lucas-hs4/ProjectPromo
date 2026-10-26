import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def conectar():
    """Abre e retorna uma conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )
def inicializar_banco():
    """Cria as tabelas caso elas ainda não existam no banco."""
    conexao = conectar()
    cursor = conexao.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            url TEXT UNIQUE NOT NULL,
            alerta_enviado BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS alerta_enviado BOOLEAN DEFAULT FALSE;
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_precos (
            id SERIAL PRIMARY KEY,
            produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
            preco_original NUMERIC(10, 2) NOT NULL,
            preco_atual NUMERIC(10, 2) NOT NULL,
            desconto_pct INTEGER NOT NULL,
            status_estoque VARCHAR(50) NOT NULL,
            disponivel BOOLEAN NOT NULL,
            data_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );    
    """)
    
    conexao.commit()
    cursor.close()
    conexao.close()
    print("Banco de dados conectados e tabelas verificadas/criadas com sucesso.")
    
def salvar_leitura(dados):
    """
    Cadastra ou atualiza o produto na tabela 'produtos' e 
    insere um novo registro temporal em 'historico_precos'.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    
    sql_produto = """
        INSERT INTO produtos (nome, url)
        VALUES (%s, %s)
        ON CONFLICT (url) DO UPDATE
        SET nome = EXCLUDED.nome
        RETURNING id, alerta_enviado;
    """
    cursor.execute(sql_produto, (dados["nome"], dados["url"]))
    
    resultado_produto = cursor.fetchone()
    produto_id = resultado_produto[0]
    alerta_ja_enviado = resultado_produto[1]
    
    sql_historico = """
        INSERT INTO historico_precos (
            produto_id, preco_original, preco_atual,
            desconto_pct, status_estoque, disponivel
        )
        VALUES (%s, %s, %s, %s, %s, %s);    
    """
    cursor.execute(sql_historico, (
        produto_id,
        dados["preco_original"],
        dados ["preco_atual"],
        dados["desconto_pct"],
        dados["status"],
        dados["disponivel"]
    ))
    
    conexao.commit()
    cursor.close()
    conexao.close()
    
    return produto_id, alerta_ja_enviado

def atualizar_status_alerta(produto_id, status_booleano):
    """Liga (True) ou desliga (False) a trava de notificação de um produto."""
    conexao = conectar()
    cursor = conexao.cursor()
    
    cursor.execute(
        "UPDATE produtos SET alerta_enviado = %s WHERE id = %s;",
        (status_booleano, produto_id)
    )
    
    conexao.commit()
    cursor.close()
    conexao.close()