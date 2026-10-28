from playwright.sync_api import sync_playwright
from scraper import extrair_panini, extrair_vitrine_panini, extrair_newpop, extrair_vitrine_newpop, extrair_vitrine_pipoca
from database import inicializar_banco, salvar_leitura, atualizar_status_alerta, conectar, listar_urls_favoritos
from notificador import enviar_alerta_ntfy
import ctypes

DESCONTO_MINIMO_WISHLIST = 20
DESCONTO_MINIMO_PCT = 70

VITRINES_MONITORADAS = [
    "https://panini.com.br/marvel?product_list_limit=36", #Marvel
    "https://panini.com.br/planet-manga?product_list_limit=36", #Mangás
    "https://panini.com.br/dc-comics?product_list_limit=36", #DC
    "https://panini.com.br/panini-books?product_list_limit=36", #Livros/Novels
    "https://panini.com.br/panini-comics?product_list_limit=36", #Outras HQs
    "https://panini.com.br/mauricio-de-sousa-catalogo?product_list_limit=36", #Turma da Mônica
    #"https://panini.com.br/novidades/pre-vendas?product_list_limit=36", #Pré-venda
    #"https://panini.com.br/novidades/reimpressao?product_list_limit=36", #Reimpressão
    #"https://panini.com.br/desconto-saldao?product_list_limit=36", #Saldão
    #"https://panini.com.br/promos?product_list_limit=36", #Promos
    #"https://panini.com.br/desconto-manga?product_list_limit=36", #Desconto-Mangás
    #"https://panini.com.br/planet-manga/box-mangas?product_list_limit=36", #Box Mangás
    #"https://panini.com.br/catalogsearch/result/?q=tokyo+ghoul&product_list_limit=36", #Tokyo Ghoul
]

VITRINES_NEWPOP = [
    "https://www.lojanewpop.com.br/",
    "https://www.lojanewpop.com.br/mangas",
    "https://www.lojanewpop.com.br/one-shots",
    "https://www.lojanewpop.com.br/livrosnovels-",
    "https://www.lojanewpop.com.br/nacionais",
    "https://www.lojanewpop.com.br/pre-venda",
    "https://www.lojanewpop.com.br/pacotes",
    #"https://www.lojanewpop.com.br/marca/aca.html",
    #"https://www.lojanewpop.com.br/marca/aventura.html",
    #"https://www.lojanewpop.com.br/marca/classicos.html",
    #"https://www.lojanewpop.com.br/marca/comedia.html",
    #"https://www.lojanewpop.com.br/marca/drama.html",
    #"https://www.lojanewpop.com.br/marca/novels.html",
    #"https://www.lojanewpop.com.br/marca/shoujo.html",
    #"https://www.lojanewpop.com.br/marca/suspense.html",
]

VITRINES_PIPOCA = [
    "https://pipocaenanquim.com.br/mangas.html",
    "https://pipocaenanquim.com.br/quadrinhos.html",
    "https://pipocaenanquim.com.br/livros.html,",
    "https://pipocaenanquim.com.br/colec-o.html",
    #"https://pipocaenanquim.com.br/promoc-o.html",
    #"https://pipocaenanquim.com.br/pre-vendas.html",
]

URLS_INDIVIDUAIS = [
    #"https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
    #"https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
    #"https://panini.com.br/marvel-boy-marvel-essenciais",
    #"https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
]

def processar_produto(dados, conexao=None):
    """Salva o quadrinho no PostgreSQL e gerencia a trava de notificação."""
    prod_id, alerta_ja_enviada, eh_favorito = salvar_leitura(dados,conexao)
    estrela = "⭐ " if eh_favorito else ""
    print(f"[DB] [{dados.get('loja', 'Panini')}] | ID #{prod_id} | {estrela}{dados['nome']} | R$ {dados['preco_atual']:.2f} | ({dados['desconto_pct']}% OFF) | {dados['status']}")
    
    meta_desconto = DESCONTO_MINIMO_WISHLIST if eh_favorito else DESCONTO_MINIMO_PCT
    
    em_promocao_valida = (
        dados["disponivel"] 
        and dados["desconto_pct"] >= meta_desconto
        and dados.get("categoria") != "Excluídos"
    )
    
    if em_promocao_valida:
        if not alerta_ja_enviada:
            print(f" >>> NOVA PROMOÇÂO ({dados['desconto_pct']}% OFF)! Disparando Alerta...")
            enviar_alerta_ntfy(dados, meta_desconto, eh_favorito)
            atualizar_status_alerta(prod_id, True)
        else:
            print(" === Promoção já notificada anteriormente.")
    else:
        if alerta_ja_enviada:
            print(" --- Promoção encerrada ou esgotou. Resetando trava de alerta!")
            atualizar_status_alerta(prod_id, False)

import scraper
from datetime import datetime

def executar_robo(modo="completo"):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Iniciando varredura ({modo})...")
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    scraper.cancelar_varredura = False
    inicializar_banco()
    conexao_db = conectar()
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        contexto = navegador.new_context(
            locale="pt-BR",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64, x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        
        pagina = contexto.new_page()
        pagina.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
        
        urls_ja_varridas = set()
        
        urls_diretas = listar_urls_favoritos() + URLS_INDIVIDUAIS
        for url in urls_diretas:
            if scraper.cancelar_varredura or url in urls_ja_varridas:
                continue
            urls_ja_varridas.add(url)
            if "lojanewpop.com.br" in url:
                dados = extrair_newpop(pagina, url)
            else:
                dados = extrair_panini(pagina, url)
            if dados:
                processar_produto(dados, conexao_db)
        
        if modo == "completo" and not scraper.cancelar_varredura:
            for url_vitrine in VITRINES_MONITORADAS:
                if scraper.cancelar_varredura: break
                lista_produtos = extrair_vitrine_panini(pagina, url_vitrine,max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_produtos:
                    processar_produto(dados, conexao_db)
                #if dados["url"] in urls_ja_varridas:
                    #continue
                #urls_ja_varridas.add(dados["url"])
                

            for url_newpop in VITRINES_NEWPOP:
                if scraper.cancelar_varredura: break
                lista_newpop = extrair_vitrine_newpop(pagina, url_newpop, max_paginas=50, urls_vistas=urls_ja_varridas)
                for dados in lista_newpop:
                    processar_produto(dados, conexao_db)
                
            for url_pipoca in VITRINES_PIPOCA:
                if scraper.cancelar_varredura: break
                lista_pipoca = extrair_vitrine_pipoca(pagina, url_pipoca, max_paginas=50, urls_vistas=urls_ja_varridas)
                for dados in lista_pipoca:
                    processar_produto(dados,conexao_db)

        #for url in URLS_INDIVIDUAIS:
            #if "lojanewpop.com.br" in url:
                #dados = extrair_newpop(pagina, url)
            #else:
                #dados = extrair_panini(pagina, url)

            #if dados:
                #processar_produto(dados)
        
        navegador.close()
        conexao_db.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Varredura concluída com sucesso!")
    
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__ == "__main__":
    executar_robo()