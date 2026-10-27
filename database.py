import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS loja VARCHAR(50) DEFAULT 'Panini';
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS imagem_url TEXT;
    """)
    
    cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS categoria VARCHAR(50) DEFAULT 'Geral';
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
    
    loja = dados.get("loja", "Panini")
    imagem_url = dados.get("imagem_url", "")
    categoria = dados.get("categoria", "Geral")
    
    sql_produto = """
        INSERT INTO produtos (nome, url, loja, imagem_url, categoria)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE
        SET nome = EXCLUDED.nome,
            loja = EXCLUDED.loja,
            imagem_url = EXCLUDED.imagem_url,
            categoria = EXCLUDED.categoria
        RETURNING id, alerta_enviado;
    """
    cursor.execute(sql_produto, (dados["nome"], dados["url"], loja, imagem_url, categoria))
    
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
    
def listar_ofertas(desconto_min=0, preco_max=0.0, busca="", loja="", categoria="", apenas_disponiveis=False, ordem="desconto"):
    """
    Busca todos os produtos com sua leitura mais recente,
    aplicando filtros de desconto, nome e estoque.
    """
    conexao = conectar()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    sql = """
        SELECT * FROM (
            SELECT DISTINCT ON (p.id)
                p.id, p.nome, p.url, p.loja, p.imagem_url, p.categoria,
                h.preco_original, h.preco_atual, h.desconto_pct,
                h.status_estoque, h.disponivel, h.data_consulta
            FROM produtos p
            JOIN historico_precos h ON p.id = h.produto_id
            ORDER BY p.id, h.data_consulta DESC
        ) AS ultimas_leituras
        WHERE desconto_pct >= %s
          AND unaccent(nome) ILIKE unaccent(%s)
    """
    parametros = [desconto_min, f"%{busca}%"]
    
    if preco_max > 0:
        sql += " AND preco_atual <= %s"
        parametros.append(preco_max)
    
    if loja:
        sql += " AND loja = %s"
        parametros.append(loja)
    
    if categoria:
        sql += " AND categoria = %s"
        parametros.append(categoria)
    else:
        sql += " AND categoria != 'Excluídos'"
        
    if apenas_disponiveis:
        sql += " AND disponivel = TRUE"
        
    if ordem == "preco_menor":
        sql += " ORDER BY preco_atual ASC, desconto_pct DESC;"
    elif ordem == "nome":
        sql += " ORDER BY nome ASC;"
    else:
        sql += " ORDER BY desconto_pct DESC, preco_atual ASC;"

    cursor.execute(sql,tuple(parametros))
    produtos = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    return produtos