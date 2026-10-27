from playwright.sync_api import sync_playwright
from scraper import extrair_panini, extrair_vitrine_panini, extrair_newpop, extrair_vitrine_newpop, extrair_vitrine_pipoca
from database import inicializar_banco, salvar_leitura, atualizar_status_alerta
from notificador import enviar_alerta_ntfy
import ctypes

DESCONTO_MINIMO_PCT = 70

VITRINES_MONITORADAS = [
    #"https://panini.com.br/desconto-saldao?product_list_limit=36",
    #"https://panini.com.br/promos?product_list_limit=36",
    #"https://panini.com.br/desconto-manga?product_list_limit=36",
    #"https://panini.com.br/marvel?binding_description=Capa+dura&product_list_limit=36",
    #"https://panini.com.br/dc-comics?binding_description=Capa+dura&product_list_limit=36",
    #"https://panini.com.br/planet-manga/box-mangas?product_list_limit=36",
    #"https://panini.com.br/catalogsearch/result/?q=tokyo+ghoul&product_list_limit=36",
]

VITRINES_NEWPOP = [
    #"https://www.lojanewpop.com.br/",
    #"https://www.lojanewpop.com.br/mangas",
    #"https://www.lojanewpop.com.br/livrosnovels-",
    #"https://www.lojanewpop.com.br/marca/aca.html",
    #"https://www.lojanewpop.com.br/marca/aventura.html"
    #"https://www.lojanewpop.com.br/marca/classicos.html",
    #"https://www.lojanewpop.com.br/marca/comedia.html",
    #"https://www.lojanewpop.com.br/marca/drama.html",
    #"https://www.lojanewpop.com.br/marca/novels.html",
    #"https://www.lojanewpop.com.br/marca/shoujo.html",
    #"https://www.lojanewpop.com.br/marca/suspense.html",
    #"https://www.lojanewpop.com.br/one-shots",
]

VITRINES_PIPOCA = [
    #https://pipocaenanquim.com.br/promoc-o.html",S
    "https://pipocaenanquim.com.br/pre-vendas.html",
    #"https://pipocaenanquim.com.br/mangas.html",
    #"https://pipocaenanquim.com.br/quadrinhos.html",
]

URLS_INDIVIDUAIS = [
    #"https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
    #"https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
    #"https://panini.com.br/marvel-boy-marvel-essenciais",
    #"https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
]
def processar_produto(dados):
    """Salva o quadrinho no PostgreSQL e gerencia a trava de notificação."""
    prod_id, alerta_ja_enviada = salvar_leitura(dados)
    print(f"[DB] [{dados.get('loja', 'Panini')}] | ID #{prod_id} | {dados['nome']} | R$ {dados['preco_atual']:.2f} | ({dados['desconto_pct']}% OFF) | {dados['status']}")
    
    em_promocao_valida = (
        dados["disponivel"] 
        and dados["desconto_pct"] >= DESCONTO_MINIMO_PCT
        and dados.get("categoria") != "Excluídos"
    )
    
    if em_promocao_valida:
        if not alerta_ja_enviada:
            print(f" >>> NOVA PROMOÇÂO ({dados['desconto_pct']}% OFF)! Disparando Alerta...")
            enviar_alerta_ntfy(dados, DESCONTO_MINIMO_PCT)
            atualizar_status_alerta(prod_id, True)
        else:
            print(" === Promoção já notificada anteriormente.")
    else:
        if alerta_ja_enviada:
            print(" --- Promoção encerrada ou esgotou. Resetando trava de alerta!")
            atualizar_status_alerta(prod_id, False)

def executar_robo():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    inicializar_banco()
    
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
        
        for url_vitrine in VITRINES_MONITORADAS:
            lista_produtos = extrair_vitrine_panini(pagina, url_vitrine,max_paginas=100)
            for dados in lista_produtos:
                processar_produto(dados)
                
        for url_vitrine in VITRINES_MONITORADAS:
            lista_produtos = extrair_vitrine_panini(pagina, url_vitrine, max_paginas=3)
            for dados in lista_produtos:
                processar_produto(dados)
                
        for url_newpop in VITRINES_NEWPOP:
            lista_newpop = extrair_vitrine_newpop(pagina, url_newpop, max_paginas=2)
            for dados in lista_newpop:
                processar_produto(dados)
                
        for url in URLS_INDIVIDUAIS:
            dados = extrair_panini(pagina, url)
            if dados:
                processar_produto(dados)
                
        for url_pipoca in VITRINES_PIPOCA:
            lista_pipoca = extrair_vitrine_pipoca(pagina, url_pipoca, max_paginas=5)
            for dados in lista_pipoca:
                processar_produto(dados)

        for url in URLS_INDIVIDUAIS:
            if "lojanewpop.com.br" in url:
                dados = extrair_newpop(pagina, url)
            else:
                dados = extrair_panini(pagina, url)

            if dados:
                processar_produto(dados)
            
        navegador.close()
        print("Varredura concluída com sucesso!")
    
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__ == "__main__":
    executar_robo()