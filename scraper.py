from playwright.sync_api import sync_playwright

def extrair_panini(pagina, url_produto):
    print(f"Consultando:: {url_produto}...")
    
    resposta = pagina.goto(url_produto, wait_until="domcontentloaded")
    
    
    if resposta.status != 200:
        print(f"Erro ao acessar a página. Status: {resposta.status}")
        return None
        
    titulo = pagina.locator("h1.page-title").inner_text().strip()
        
    bloco_principal = pagina.locator("div.product-info-main")
        
    loc_preco_final = bloco_principal.locator('[data-price-type="finalPrice"]')
    if loc_preco_final.count() > 0:
        preco_texto = loc_preco_final.get_attribute("data-price-amount")
        preco_atual = float(preco_texto)
    else:
        preco_atual = 0.0  
        
    loc_preco_antigo = bloco_principal.locator('[data-price-type="oldPrice"]')
    if loc_preco_antigo.count() > 0:
        preco_antigo_texto = loc_preco_antigo.get_attribute("data-price-amount")
        preco_original = float(preco_antigo_texto)
    else:
        preco_original = preco_atual
        
    desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0
        
    tem_botao_compra = bloco_principal.locator("#product-addtocart-button").count() > 0
    fora_de_estoque = bloco_principal.locator("div.stock.unavailable").count() > 0
    texto_bloco = bloco_principal.inner_text()
        
    if fora_de_estoque or not tem_botao_compra:
        status_estoque = "Indisponível"
        disponivel = False
    elif "Pré-venda" in texto_bloco or "previsão de envio" in texto_bloco:
        status_estoque = "Pré-venda"
        disponivel = True
    else:
        status_estoque = "Em estoque"
        disponivel = True
        
    return {
        "nome": titulo,
        "url": url_produto,
        "preco_original": preco_original,
        "preco_atual": preco_atual,
        "desconto_pct": desconto_pct,
        "status": status_estoque,
        "disponivel": disponivel
        
    }

def extrair_vitrine_panini(pagina, url_inicial, max_paginas=100):
    """
    Crawler de Categoria: entra na vitrine, extrai todos o cards da grade
    e avança para as próximas páginas sozinho até atingir 'max_paginas'.
    """
    
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []
    
    while url_atual and pagina_num <= max_paginas:
        print(f"[Crawler] Varrendo Página {pagina_num}: {url_atual}...")
    
        resposta = pagina.goto(url_atual, wait_until="domcontentloaded")
    
        if resposta.status != 200:
            print(f"Erro ao acessar a vitrine. Status: {resposta.status}")
            break
    
        cards = pagina.locator("div.products-grid div.product-item-info")
        total_cards = cards.count()
        print(f"Encontrados {total_cards} produtos nesta página.")
    
        for i in range(total_cards):
            card = cards.nth(i)
        
            link_elemento = card.locator("a.product-item-link").first
            if link_elemento.count() == 0:
                continue
    
            nome = link_elemento.inner_text().strip()
            url_produto = link_elemento.get_attribute("href")

            loc_preco_final = card.locator('[data-price-type="finalPrice"]').first
            if loc_preco_final.count() > 0:
                preco_atual = float(loc_preco_final.get_attribute("data-price-amount"))
            else:
                preco_atual = 0.0
        
            loc_preco_antigo = card.locator('[data-price-type="oldPrice"]').first
            if loc_preco_antigo.count() > 0:
                preco_original = float(loc_preco_antigo.get_attribute("data-price-amount"))
            else:
                preco_original = preco_atual
                
            desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0

            tem_botao_compra = card.locator("button.tocart").count() > 0
            fora_de_estoque = card.locator(".stock.unavailable").count() > 0
            texto_card = card.inner_text()
            
            if fora_de_estoque or not tem_botao_compra:
                status_estoque = "Indisponível"
                disponivel = False
            elif "Pré-venda" in texto_card or card.locator(".infobase-label-presale").count() > 0:
                status_estoque = "Pré-venda"
                disponivel = True
            else: 
                status_estoque = "Em estoque"
                disponivel = True
                
            produtos_extraidos.append({
                "nome": nome,
                "url": url_produto,
                "preco_original": preco_original,
                "preco_atual": preco_atual,
                "desconto_pct": desconto_pct,
                "status": status_estoque,
                "disponivel": disponivel
            })
        botao_proxima = pagina.locator("li.pages-item-next a.action.next").first
        if botao_proxima.count() > 0 and pagina_num < max_paginas:
            url_atual = botao_proxima.get_attribute("href")
            pagina_num += 1
        else:
            url_atual = None
    return produtos_extraidos