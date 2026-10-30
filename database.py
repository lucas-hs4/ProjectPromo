import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from scraper import identificar_categoria

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
    
    cursor.execute("""
        UPDATE produtos SET categoria = 'Outros'
        WHERE categoria IN ('Panini Comics / Outros', 'Geral');
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS favorito BOOLEAN DEFAULT FALSE;
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS ultimo_alerta TIMESTAMP;
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS plataforma VARCHAR(50) DEFAULT 'Editoras';
    """)
    
    cursor.execute("""
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS preco_alvo NUMERIC(10, 2) DEFAULT 0.0;
    """)
    
    cursor.execute("UPDATE produtos SET categoria = 'Mangás' WHERE loja = 'NewPOP' AND categoria = 'Excluídos';")
    #cursor.execute("DELETE FROM produtos WHERE plataforma = 'Amazon' AND favorito = FALSE;")
    cursor.execute("""
        DELETE FROM produtos
        WHERE plataforma = 'Amazon'
            AND favorito = FALSE
            AND (
                categoria = 'Excluídos'
                OR nome ILIKE ANY (ARRAY['%Portuguese Edition%', '%Chinese Edition%', '%para colorir%', '%MPEG-7%', '%MPEG-2%', '%DivX%', '%Supremo Tribunal%', 'Supremo Tibunal'])
                OR (loja = 'Outras' AND nome ILIKE ANY (ARRAY['%outra%', '%outro%']))
            );
    """)
    
    cursor.execute("SELECT id, nome, loja FROM produtos WHERE plataforma = 'Amazon' AND loja LIKE 'Todas%';")
    from scraper import identificar_editora
    for pid, pnome, ploja in cursor.fetchall():
        nova_ed = identificar_editora(pnome, ploja)
        nova_cat = identificar_categoria(pnome, nova_ed.lower(), 10.0)
        cursor.execute("UPDATE produtos SET loja = %s, categoria = %s WHERE id = %s;", (nova_ed, nova_cat, pid))
    
    conexao.commit()
    cursor.close()
    conexao.close()
    print("Banco de dados conectados e tabelas verificadas/criadas com sucesso.")
    
def salvar_leitura(dados, conexao=None):
    """
    Cadastra ou atualiza o produto na tabela 'produtos' e 
    insere um novo registro temporal em 'historico_precos'.
    """
    fechar_ao_final = conexao is None
    if fechar_ao_final:
        conexao = conectar()
    cursor = conexao.cursor()
    
    loja = dados.get("loja", "Panini")
    plataforma = dados.get("plataforma", "Editoras")
    imagem_url = dados.get("imagem_url", "")
    categoria = dados.get("categoria", "Outros")
    
    sql_produto = """
        INSERT INTO produtos (nome, url, loja, plataforma, imagem_url, categoria)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE
        SET nome = EXCLUDED.nome,
            loja = EXCLUDED.loja,
            plataforma = EXCLUDED.plataforma,
            imagem_url = CASE
                WHEN EXCLUDED.imagem_url != '' THEN EXCLUDED.imagem_url
                ELSE produtos.imagem_url
            END,
            categoria = CASE
                WHEN EXCLUDED.categoria IN ('Geral', 'Outros')
                    AND produtos.categoria NOT IN ('Geral', 'Outros', 'Excluídos')
                THEN produtos.categoria
                ELSE EXCLUDED.categoria
            END
        RETURNING id, (alerta_enviado AND ultimo_alerta IS NOT NULL AND ultimo_alerta > NOW() - INTERVAL '3 days'), favorito, COALESCE(preco_alvo, 0.0);
    """
    cursor.execute(sql_produto, (dados["nome"], dados["url"], loja, plataforma, imagem_url, categoria))
    
    resultado_produto = cursor.fetchone()
    produto_id = resultado_produto[0]
    alerta_ja_enviado = resultado_produto[1]
    eh_favorito = resultado_produto[2]
    preco_alvo = float(resultado_produto[3])
    
    cursor.execute("""
        SELECT preco_atual, disponivel, status_estoque
        FROM historico_precos
        WHERE produto_id = %s
        ORDER BY data_consulta DESC
        LIMIT 1;
    """, (produto_id,))
    
    ultima_leitura = cursor.fetchone()
    
    mudou_estado = (
        ultima_leitura is None
        or float(ultima_leitura[0]) != float(dados["preco_atual"])
        or ultima_leitura[1] != dados["disponivel"]
        or ultima_leitura[2] != dados["status"]
    )
    
    if mudou_estado:
    
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
    if fechar_ao_final:
        conexao.close()
    
    return produto_id, alerta_ja_enviado, eh_favorito, preco_alvo

def atualizar_status_alerta(produto_id, status_booleano):
    """Liga (True) ou desliga (False) a trava de notificação de um produto."""
    conexao = conectar()
    cursor = conexao.cursor()
    
    cursor.execute("""
        UPDATE produtos
        SET alerta_enviado = %s,
            ultimo_alerta = CASE WHEN %s = TRUE THEN CURRENT_TIMESTAMP ELSE ultimo_alerta END
        WHERE id = %s;
    """, (status_booleano, status_booleano, produto_id))
    
    
    conexao.commit()
    cursor.close()
    conexao.close()
    
def listar_ofertas(desconto_min=0, preco_min=0.0, preco_max=0.0, busca="", loja="", categoria="", apenas_disponiveis=False, apenas_favoritos=False, ordem="desconto", pagina=1, por_pagina=48, plataforma="Editoras"):
    """
    Busca todos os produtos com sua leitura mais recente,
    aplicando filtros de desconto, nome e estoque.
    """
    conexao = conectar()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    sql = """
        SELECT COUNT(*) OVER() AS total_geral, * FROM (
            SELECT DISTINCT ON (p.id)
                p.id, p.nome, p.url, p.loja, p.plataforma, p.imagem_url, p.categoria, p.favorito,
                COALESCE(p.preco_alvo, 0.0) AS preco_alvo,
                h.preco_original, h.preco_atual, h.desconto_pct,
                h.status_estoque, h.disponivel, h.data_consulta,
                MIN(h.preco_atual) OVER (PARTITION BY p.id) AS menor_preco
            FROM produtos p
            JOIN historico_precos h ON p.id = h.produto_id
            ORDER BY p.id, h.data_consulta DESC
        ) AS ultimas_leituras
        WHERE desconto_pct >= %s
          AND unaccent(nome) ILIKE unaccent(%s)
    """
    parametros = [desconto_min, f"%{busca}%"]
    
    if preco_min > 0:
        sql += " AND preco_atual >= %s"
        parametros.append(preco_min)
    
    if preco_max > 0:
        sql += " AND preco_atual <= %s"
        parametros.append(preco_max)
    
    if loja:
        sql += " AND loja = %s"
        parametros.append(loja)
    
    if plataforma == "Wishlist":
        sql += " AND favorito = TRUE"
    elif plataforma and plataforma != "Todas":
        sql += " AND plataforma = %s"
        parametros.append(plataforma)
    
    if categoria:
        sql += " AND categoria = %s"
        parametros.append(categoria)
    else:
        sql += " AND categoria != 'Excluídos'"
        
    if apenas_disponiveis:
        sql += " AND disponivel = TRUE"
        
    if apenas_favoritos:sql += " AND favorito = TRUE"
        
        #adicionar "LIMIT 200" depois de DESC e ASC para agilizar o site
    if ordem == "preco_menor":
        sql += " ORDER BY preco_atual ASC, desconto_pct DESC"
    elif ordem == "nome":
        sql += " ORDER BY nome ASC"
    elif ordem == "recentes":
        sql += " ORDER BY data_consulta DESC, desconto_pct DESC"
    else:
        sql += " ORDER BY desconto_pct DESC, preco_atual ASC"
        
    offset = (pagina - 1) * por_pagina
    sql += " LIMIT %s OFFSET %s;"
    parametros.extend([por_pagina, offset])

    cursor.execute(sql,tuple(parametros))
    produtos = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    return produtos

def alternar_favorito(produto_id):
    """Inverte o status de favorito (True <-> False) de um produto."""
    conexao = conectar()
    cursor = conexao.cursor()
    
    cursor.execute("""
        UPDATE produtos
        SET favorito = NOT COALESCE(favorito, FALSE)
        WHERE id = %s
        RETURNING favorito;
    """, (produto_id,))
    
    novo_status = cursor.fetchone()[0]
    conexao.commit()
    cursor.close()
    conexao.close()
    return novo_status

def listar_urls_favoritos():
    """Retorna a lista de URLs de todos os produtos marcados na Wishlist."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT url FROM produtos WHERE favorito = TRUE;")
    urls = [linha[0] for linha in cursor.fetchall()]
    cursor.close()
    conexao.close()
    return urls

def buscar_historico_produto(produto_id):
    """Retorna todas as leituras de preço de um produto em ordem cronológica."""
    conexao = conectar()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT
            TO_CHAR(data_consulta, 'DD/MM/YYYY HH24:MI') AS data_formatada,
            FLOAT8(preco_original) AS preco_original,
            FLOAT8(preco_atual) AS preco_atual,
            desconto_pct,
            status_estoque,
            disponivel
        FROM historico_precos
        WHERE produto_id = %s
        ORDER BY data_consulta ASC;
    """, (produto_id,))
    historico = cursor.fetchall()
    cursor.close()
    conexao.close()
    return historico

def definir_preco_alvo(produto_id, valor_alvo):
    """Define uma meta de preço (R$) para o produto e já o coloca na Wishlist."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        UPDATE produtos
        SET preco_alvo = %s,
            favorito = CASE WHEN %s > 0 THEN TRUE ELSE favorito END
        WHERE id = %s;
    """, (valor_alvo, valor_alvo, produto_id))
    conexao.commit()
    cursor.close()
    conexao.close()