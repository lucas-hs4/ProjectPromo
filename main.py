from playwright.sync_api import sync_playwright
from scraper import (
    extrair_panini, extrair_vitrine_panini,
    extrair_newpop, extrair_vitrine_newpop, 
    extrair_vitrine_pipoca, extrair_jbc, extrair_vitrine_jbc,
    extrair_amazon, extrair_vitrine_amazon,
    extrair_mercadolivre, extrair_vitrine_mercadolivre
)
from database import inicializar_banco, salvar_leitura, atualizar_status_alerta, conectar, listar_urls_favoritos
from notificador import enviar_alerta_ntfy
import ctypes

DESCONTO_MINIMO_WISHLIST = 20
DESCONTO_MINIMO_PCT = 70

VITRINES_MONITORADAS = [
    #("Marvel", f"https://panini.com.br/marvel?product_list_limit=36"),
    #("Mangás", f"https://panini.com.br/planet-manga?product_list_limit=36"),
    #("DC", f"https://panini.com.br/dc-comics?product_list_limit=36"),
    #("Livros/Novels",f"https://panini.com.br/panini-books?product_list_limit=36"),
    #("Outras HQs", f"https://panini.com.br/panini-comics?product_list_limit=36"),
    #("Turma da Mônica", f"https://panini.com.br/mauricio-de-sousa-catalogo?product_list_limit=36"),
    #"https://panini.com.br/novidades/pre-vendas?product_list_limit=36", #Pré-venda
    #"https://panini.com.br/novidades/reimpressao?product_list_limit=36", #Reimpressão
    #"https://panini.com.br/desconto-saldao?product_list_limit=36", #Saldão
    #"https://panini.com.br/promos?product_list_limit=36", #Promos
    #"https://panini.com.br/desconto-manga?product_list_limit=36", #Desconto-Mangás
    #"https://panini.com.br/planet-manga/box-mangas?product_list_limit=36", #Box Mangás
    #"https://panini.com.br/catalogsearch/result/?q=tokyo+ghoul&product_list_limit=36", #Tokyo Ghoul
]

VITRINES_NEWPOP = [
    #"https://www.lojanewpop.com.br/",
    #"https://www.lojanewpop.com.br/mangas",
    #"https://www.lojanewpop.com.br/one-shots",
    #"https://www.lojanewpop.com.br/livrosnovels-",
    #"https://www.lojanewpop.com.br/nacionais",
    #"https://www.lojanewpop.com.br/pre-venda",
    #"https://www.lojanewpop.com.br/pacotes",
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
    #"https://pipocaenanquim.com.br/mangas.html",
    #"https://pipocaenanquim.com.br/quadrinhos.html",
    #"https://pipocaenanquim.com.br/livros.html",
    #"https://pipocaenanquim.com.br/colec-o.html",
    #"https://pipocaenanquim.com.br/promoc-o.html",
    #"https://pipocaenanquim.com.br/pre-vendas.html",
]

VITRINES_MPEG = [
    #"https://mpeg.com.br/mangas?product_list_limit=36",
    #"https://mpeg.com.br/novels?product_list_limit=36",
    #"https://mpeg.com.br/prevendas?product_list_limit=36",
]

VITRINES_JBC = [
    "https://www.companhiadasletras.com.br/JBC?brand=jbc&fuzzy=0&operator=and&facets=brand%2Cfuzzy%2Coperator&sort=score_desc&page=0",
]

FILTRO_AMZ = "i=stripbooks&rh=n%3A7842710011%2Cp_n_feature_nine_browse-bin%3A8529758011%2Cp_n_condition-type%3A13862762011%2Cp_n_binding_browse-bin%3A13921567011%7C13921568011"

BUSCAS_AMAZON = [
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=46&Adv-Srch-Books-Submit.y=18&unfiltered=1&ref=sr_adv_b"), #Todas : Relevância - Mais vendidos
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A7842710011&s=date-desc-rank&Adv-Srch-Books-Submit.x=46&Adv-Srch-Books-Submit.y=18&qid=1793286371&unfiltered=1&ref=sr_st_date-desc-rank&ds=v1%3AJGh5n%2BUtVzdJ37nBvSahNwYUsbNL5WamFD4Kd5XcGCM"), #Todas: Relevância - Lançamento
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A7842710011&s=popularity-rank&Adv-Srch-Books-Submit.x=55&Adv-Srch-Books-Submit.y=7&unfiltered=1&ref=sr_adv_b"), #Todas: Popularidade - Mais vendidos
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A7842710011&s=date-desc-rank&Adv-Srch-Books-Submit.x=55&Adv-Srch-Books-Submit.y=7&qid=1793286496&unfiltered=1&ref=sr_st_date-desc-rank&ds=v1%3AD0LSy%2FSe3Qcr3NGy577MLNrX5cQ22DUqq35XPgwCi1s"), #Todas: Popularidade - Lançamento
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A6740748011%2Cn%3A7842710011%2Cn%3A7842726011&s=relevancerank&dc&ds=v1%3AGIHSTbxUupX0t7Cdq5sMPvH%2FA0vN%2F%2B6wehP1aEhDdOY&Adv-Srch-Books-Submit.x=67&Adv-Srch-Books-Submit.y=0&qid=1793286857&rnid=7842710011&unfiltered=1&ref=sr_nr_n_1"), #Todas: Graphic Novels
    ("Outras", f"https://www.amazon.com.br/s?i=stripbooks&rh=n%3A6740748011%2Cn%3A7842710011%2Cn%3A7842714011&s=relevancerank&dc&ds=v1%3A%2Fa9DH9GoTOfdYKOM4Uk6nyp5p3cZQHXMVYOh%2BcyySHY&Adv-Srch-Books-Submit.x=67&Adv-Srch-Books-Submit.y=0&qid=1793286868&rnid=7842710011&unfiltered=1&ref=sr_nr_n_2"), #Todas: Mangás
    ("Panini", f"https://www.amazon.com.br/s?k=panini&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=35&Adv-Srch-Books-Submit.y=21&unfiltered=1&ref=sr_adv_b"),
    ("NewPOP", f"https://www.amazon.com.br/s?k=newpop&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=0&Adv-Srch-Books-Submit.y=0&unfiltered=1&ref=sr_adv_b"),
    ("JBC", f"https://www.amazon.com.br/s?k=jbc&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=52&Adv-Srch-Books-Submit.y=7&unfiltered=1&ref=sr_adv_b"),
    ("Pipoca & Nanquim", f"https://www.amazon.com.br/s?k=pipoca+%26+nanquim&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=51&Adv-Srch-Books-Submit.y=13&unfiltered=1&ref=sr_adv_b"),
    ("Pipoca & Nanquim", f"https://www.amazon.com.br/s?k=pipoca+e+nanquim&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=38&Adv-Srch-Books-Submit.y=13&unfiltered=1&ref=sr_adv_b"), #Pipoca e Nanquim
    ("MPEG", f"https://www.amazon.com.br/s?k=mpeg&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=50&Adv-Srch-Books-Submit.y=14&unfiltered=1&ref=sr_adv_b"),
    ("Outras", f"https://www.amazon.com.br/s?k=darkside&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=56&Adv-Srch-Books-Submit.y=4&unfiltered=1&ref=sr_adv_b"), #DarkSide
    ("Outras", f"https://www.amazon.com.br/s?k=comix+zone&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=43&Adv-Srch-Books-Submit.y=9&unfiltered=1&ref=sr_adv_b"), #Comix Zone
    ("Outras", f"https://www.amazon.com.br/s?k=outras&i=stripbooks&rh=n%3A7842710011&s=relevancerank&Adv-Srch-Books-Submit.x=55&Adv-Srch-Books-Submit.y=20&unfiltered=1&ref=sr_adv_b"),
]

BUSCAS_MERCADOLIVRE = [
    ("Outras", "https://lista.mercadolivre.com.br/_Container_lpml-hqs-e-mangas-set26"),
    ("Panini", "https://lista.mercadolivre.com.br/livros-revistas-comics/hqs-mangas/novo/panini"),
    ("JBC", "https://lista.mercadolivre.com.br/livros-revistas-comics/hqs-mangas/novo/jbc"),
    ("NewPOP", "https://lista.mercadolivre.com.br/livros-revistas-comics/hqs-mangas/novo/newpop"),
]

URLS_INDIVIDUAIS = [
    #"https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
    #"https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
    #"https://panini.com.br/marvel-boy-marvel-essenciais",
    #"https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
]

def processar_produto(dados, conexao=None):
    """Salva o quadrinho no PostgreSQL e gerencia a trava de notificação."""
    prod_id, alerta_ja_enviada, eh_favorito, preco_alvo = salvar_leitura(dados, conexao)
    estrela = "⭐ " if eh_favorito else ""
    alvo_txt = f" [🎯 Alvo: R$ {preco_alvo:.2f}]" if preco_alvo > 0 else ""
    print(f"[DB] [{dados.get('loja', 'Panini')}] | ID #{prod_id} | {estrela}{dados['nome']}{alvo_txt} | R$ {dados['preco_atual']:.2f} | ({dados['desconto_pct']}% OFF) | {dados['status']}")
    
    meta_desconto = DESCONTO_MINIMO_WISHLIST if eh_favorito else DESCONTO_MINIMO_PCT
    bateu_desconto = dados["desconto_pct"] >= meta_desconto
    bateu_alvo_reais = preco_alvo > 0 and 0 < dados["preco_atual"] <= preco_alvo
    
    em_promocao_valida = (
        dados["disponivel"] 
        and (bateu_desconto or bateu_alvo_reais)
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

import os
import scraper
from datetime import datetime

def executar_robo(modo="completo"):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Iniciando varredura ({modo})...")
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    scraper.cancelar_varredura = False
    inicializar_banco()
    conexao_db = conectar()
    
    with sync_playwright() as p:
        if modo == "login_ml":
            nav_login = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            ctx_login = nav_login.new_context(locale="pt-BR", viewport={"width": 1366, "height":768})
            pag_login = ctx_login.new_page()
            pag_login.goto("https://www.mercadolivre.com.br/gz/account-verification")
            pag_login.wait_for_timeout(60000)
            ctx_login.storage_state(path="sessao_ml.json")
            nav_login.close()
            conexao_db.close()
            print("[Login ML] ✅ Sessão salva em 'sessao_ml.json' com sucesso!")
            return
            
        navegador = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        arquivo_sessao = "sessao_ml.json" if os.path.exists("sessao_ml.json") else None
        contexto = navegador.new_context(
            locale="pt-BR",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64, x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            storage_state=arquivo_sessao
        )
        
        pagina = contexto.new_page()
        pagina.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
        
        urls_ja_varridas = set()
        
        if modo =="rapido":
            urls_diretas = listar_urls_favoritos() + URLS_INDIVIDUAIS
            for url in urls_diretas:
                if scraper.cancelar_varredura or url in urls_ja_varridas:
                    continue
                urls_ja_varridas.add(url)
                if "lojanewpop.com.br" in url:
                    dados = extrair_newpop(pagina, url)
                elif "companhiadasletras.com.br" in url:
                    dados = extrair_jbc(pagina, url)
                elif "amazon.com.br" in url:
                    dados = extrair_amazon(pagina, url)
                elif "mercadolivre.com.br" in url:
                    dados = extrair_mercadolivre(pagina, url)
                else:
                    dados = extrair_panini(pagina, url)
                if dados:
                    processar_produto(dados, conexao_db)
        
        if modo in ("completo", "Editoras", "Panini") and not scraper.cancelar_varredura:
            for item_vitrine in VITRINES_MONITORADAS:
                if scraper.cancelar_varredura: break
                url_vitrine = item_vitrine[1] if isinstance(item_vitrine, tuple) else item_vitrine
                lista_produtos = extrair_vitrine_panini(pagina, url_vitrine ,max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_produtos:
                    processar_produto(dados, conexao_db)

        if modo in ("completo", "Editoras", "NewPOP") and not scraper.cancelar_varredura:
            for url_newpop in VITRINES_NEWPOP:
                if scraper.cancelar_varredura: break
                lista_newpop = extrair_vitrine_newpop(pagina, url_newpop, max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_newpop:
                    processar_produto(dados, conexao_db)
                
        if modo in ("completo", "Editoras", "Pipoca") and not scraper.cancelar_varredura:
            for url_pipoca in VITRINES_PIPOCA:
                if scraper.cancelar_varredura: break
                lista_pipoca = extrair_vitrine_pipoca(pagina, url_pipoca, max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_pipoca:
                    processar_produto(dados,conexao_db)
                    
        if modo in ("completo", "Editoras", "MPEG") and not scraper.cancelar_varredura:
            for url_mpeg in VITRINES_MPEG:
                if scraper.cancelar_varredura: break
                lista_mpeg = extrair_vitrine_pipoca(pagina, url_mpeg, max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_mpeg:
                    processar_produto(dados, conexao_db)
                    
        if modo in ("completo", "Editoras", "JBC") and not scraper.cancelar_varredura:
            for url_jbc in VITRINES_JBC:
                if scraper.cancelar_varredura: break
                lista_jbc = extrair_vitrine_jbc(pagina, url_jbc, max_cliques=100, urls_vistas=urls_ja_varridas)
                for dados in lista_jbc:
                    processar_produto(dados, conexao_db)
                    
        if modo in ("completo", "Amazon") and not scraper.cancelar_varredura:
            for editora_nome, url_amz in BUSCAS_AMAZON:
                if scraper.cancelar_varredura: break
                lista_amz = extrair_vitrine_amazon(pagina, url_amz, editora_padrao=editora_nome, max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_amz:
                    processar_produto(dados, conexao_db)
                    
        if modo in ("completo", "Mercado Livre") and not scraper.cancelar_varredura:
            for editora_nome, url_ml in BUSCAS_MERCADOLIVRE:
                if scraper.cancelar_varredura: break
                lista_ml = extrair_vitrine_mercadolivre(pagina, url_ml, editora_padrao=editora_nome, max_paginas=100, urls_vistas=urls_ja_varridas)
                for dados in lista_ml:
                    processar_produto(dados, conexao_db)
        
        navegador.close()
        conexao_db.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Varredura concluída com sucesso!")
    
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__ == "__main__":
    executar_robo()