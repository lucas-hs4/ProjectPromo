from playwright.sync_api import sync_playwright

TERMOS_IGNORADOS = [
    "figurinha", "álbum", "album","cromo", "envelope",
    "adrenalyn", "fifa", "libertadores", "brasileirão",
    "brasileirao", "copa do mundo", "seleção da copa", "starter pack",
    "chaveiro", "pn toys"
]

def extrair_panini(pagina, url_produto):
    print(f"Consultando:: {url_produto}...")
    
    try:
        resposta = pagina.goto(url_produto, wait_until="domcontentloaded")
        
        if resposta.status != 200:
            print(f"Erro ao acessar a página. Status: {resposta.status}")
            return None
            
        titulo = pagina.locator("h1.page-title").inner_text().strip()
        
        loc_img = pagina.locator('meta[property="og:image"]')
        imagem_url = loc_img.get_attribute("content") if loc_img.count() > 0 else ""
            
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
            
        loja_nome = "Pipoca & Nanquim" if "pipocaenanquim.com.br" in url_produto else "Panini"
            
        return {
            "loja": loja_nome,
            "categoria": identificar_categoria(titulo, url_produto, preco_atual),
            "nome": titulo,
            "url": url_produto,
            "imagem_url": imagem_url,
            "preco_original": preco_original,
            "preco_atual": preco_atual,
            "desconto_pct": desconto_pct,
            "status": status_estoque,
            "disponivel": disponivel
        }
    except Exception as erro:
        print(f"   [Erro] Falha ao ler produto {url_produto}: {erro}")
        return None

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
            try:
                card = cards.nth(i)
            
                link_elemento = card.locator("a.product-item-link").first
                if link_elemento.count() == 0:
                    continue
        
                nome = link_elemento.inner_text().strip()
                url_produto = link_elemento.get_attribute("href")
                
                img_elemento = card.locator("img.product-image-photo").first
                imagem_url = img_elemento.get_attribute("src") if img_elemento.count() > 0 else ""

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
                    "loja": "Panini",
                    "categoria": identificar_categoria(nome, url_atual, preco_atual),
                    "nome": nome,
                    "url": url_produto,
                    "imagem_url": imagem_url,
                    "preco_original": preco_original,
                    "preco_atual": preco_atual,
                    "desconto_pct": desconto_pct,
                    "status": status_estoque,
                    "disponivel": disponivel
                })
            except Exception as erro_card:
                print(f"   [Aviso] Pulando card #{i+1} por erro de leitura {erro_card}")
                continue
            
        botao_proxima = pagina.locator("li.pages-item-next a.action.next").first
        if botao_proxima.count() > 0 and pagina_num < max_paginas:
            url_atual = botao_proxima.get_attribute("href")
            pagina_num += 1
        else:
            url_atual = None
            
    return produtos_extraidos

def identificar_categoria(nome, url_contexto="", preco_atual=10.0):
    """Classifica automaticamente a HQ/Mangá por Universo ou Categoria."""
    texto = f"{nome} {url_contexto}".lower()
    
    if preco_atual < 1.0 or any(termo in texto for termo in TERMOS_IGNORADOS):
        return "Excluídos"
    
    if "tartarugas ninja" in texto or "ultimo ronin" in texto or "último ronin" in texto:
        return "As Tartarugas Ninja"
    if "/disney" in texto or "disney" in texto or any(d in texto for d in ["mickey", "pato donald", "donald", "ducktales", "duck tales", "mickey e pateta", "tio patinhas", "minnie", "pateta"]):
        return "Disney"
    if "/invencivel" in texto or "invencível" in texto or "invencivel" in texto:
        return "Invencível"
    elif "/spawn" in texto or "spawn" in texto:
        return "Spawn"
    elif "/conan" in texto or "conan" in texto or "espada selvagem" in texto or "kull" in texto:
        return "Conan"
    elif "/star-wars" in texto or "star wars" in texto or "mandalorian" in texto or "darth vader" in texto:
        return "Star Wars"
    elif "/the-walking-dead" in texto or "walking dead" in texto:
        return "The Walking Dead"
    elif "/panini-books" in texto or "novel" in texto or "livro" in texto or "livros.html" in texto or "livrosnovels" in texto:
        return "Novels & Livros"
    elif "/marvel" in texto or any(h in texto for h in ["homem-aranha","homem de ferro", "viúva negra", "viuva negra", "viúva-negra", "aranha", "vingadores", "x-men", "wolverine", "demolidor", "thor", "capitão américa", "capitao américa", "hulk", "deadpool", "quarteto fantástico", "surfista prateado"]):
        return "Marvel"
    elif "/dc-comics" in texto or "dc+comics" in texto or any(h in texto for h in ["batman", "superman", "mulher-maravilha", "liga da justiça", "flash", "lanterna verde", "asa noturna", "coringa", "sandman", "arlequina", "watchmen", "juízo final", "heróis em crise", "herois em crise", "robin", "shazam"]):
        return "DC Comics"
    elif "/planet-manga" in texto or "planet+manga" in texto or "lojanewpop" in texto or "mangas.html" in texto or any(m in texto for m in ["junji ito", "shigurui", "city hunter", "cat's eye", "cats eye", "chushingura", "battle royale", "one piece", "berserk", "naruto", "dragon ball", "demon slayer", "jujutsu", "tokyo ghoul", "chainsaw man"]):
        return "Mangás"
    elif "/mauricio-de-sousa-catalogo" in texto or "mauricio" in texto or "mônica" in texto or "monica" in texto or "cebolinha" in texto or "cascão" in texto or "magali" in texto or "chico bento" in texto or "xaveco" in texto or "tina" in texto or "saiba mais" in texto:
        return "Turma da Mônica"
    else:
        return "Outros"

def limpar_preco_br(texto):
    """Converte 'R$ 84,90' para o float 84.90."""
    if not texto:
        return 0.0
    limpo = texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def extrair_vitrine_newpop(pagina, url_inicial, max_paginas=2):
    """
    Crawler para a NewPOP (Loja Integrada) com captura de capa e categoria.
    """
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []

    while url_atual and pagina_num <= max_paginas:
        print(f"\n[NewPOP] Varrendo Página {pagina_num}: {url_atual}...")

        try:
            resposta = pagina.goto(url_atual, wait_until="domcontentloaded")
            if resposta.status != 200:
                print(f"Erro ao acessar NewPOP. Status: {resposta.status}")
                break
        except Exception as erro:
            print(f"   [Erro de Rede] Falha na NewPOP: {erro}")
            break

        cards = pagina.locator("#listagemProdutos div.listagem-item")
        total_cards = cards.count()
        print(f"Encontrados {total_cards} produtos nesta página.")

        for i in range(total_cards):
            try:
                card = cards.nth(i)

                link_el = card.locator("a.nome-produto").first
                if link_el.count() == 0:
                    continue

                nome = link_el.inner_text().strip()
                url_produto = link_el.get_attribute("href")

                # Captura a capa na NewPOP
                img_el = card.locator("img.imagem-principal").first
                imagem_url = img_el.get_attribute("src") if img_el.count() > 0 else ""

                # Preço Atual
                loc_promo = card.locator("strong.preco-promocional").first
                loc_normal = card.locator("strong.preco-venda").first

                if loc_promo.count() > 0:
                    attr_preco = loc_promo.get_attribute("data-sell-price")
                    preco_atual = float(attr_preco) if attr_preco else limpar_preco_br(loc_promo.inner_text())
                elif loc_normal.count() > 0:
                    attr_preco = loc_normal.get_attribute("data-sell-price")
                    preco_atual = float(attr_preco) if attr_preco else limpar_preco_br(loc_normal.inner_text())
                else:
                    preco_atual = 0.0

                # Preço Original (Riscado)
                loc_antigo = card.locator("s.preco-venda").first
                if loc_antigo.count() > 0:
                    preco_original = limpar_preco_br(loc_antigo.inner_text())
                else:
                    preco_original = preco_atual

                desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0

                # Estoque e Categoria pelas classes do card na NewPOP
                classes_card = card.get_attribute("class") or ""
                indisponivel_tag = card.locator(".bandeira-indisponivel, .indisponivel").count() > 0

                if indisponivel_tag or "indisponivel" in classes_card or preco_atual == 0.0:
                    status_estoque = "Indisponível"
                    disponivel = False
                elif "prod-cat-589867" in classes_card:
                    status_estoque = "Pré-venda"
                    disponivel = True
                else:
                    status_estoque = "Em estoque"
                    disponivel = True

                categoria = "Novels & Livros" if "prod-cat-500119" in classes_card else "Mangás"

                produtos_extraidos.append({
                    "loja": "NewPOP",
                    "categoria": categoria,
                    "nome": nome,
                    "url": url_produto,
                    "imagem_url": imagem_url,
                    "preco_original": preco_original,
                    "preco_atual": preco_atual,
                    "desconto_pct": desconto_pct,
                    "status": status_estoque,
                    "disponivel": disponivel
                })
            except Exception as erro_card:
                print(f"   [Aviso] Pulando card #{i+1} na NewPOP: {erro_card}")
                continue

        botao_prox = pagina.locator(".pagination li:not(.disabled) a[rel='next'], .pagination li a:has-text('›')").first
        if botao_prox.count() > 0 and pagina_num < max_paginas:
            prox_href = botao_prox.get_attribute("href")
            if prox_href and prox_href != "#" and not prox_href.startswith("javascript"):
                url_atual = prox_href if prox_href.startswith("http") else f"https://www.lojanewpop.com.br{prox_href}"
                pagina_num += 1
            else:
                url_atual = None
        else:
            url_atual = None

    return produtos_extraidos

def extrair_newpop (pagina, url_produto):
    """Extrai os dados de uma página individual de produto da NewPOP."""
    print(f"Consultando NewPOP: {url_produto}...")
    
    try:
        resposta = pagina.goto(url_produto, wait_until="domcontentloaded")
        if resposta.status != 200:
            print(f"Erro ao acessar produto NewPOP. Status: {resposta.status}")
            return None
        
        titulo = pagina.locator("h1.nome-produto").first.inner_text().strip()
        
        loc_img = pagina.locator('meta[property="og:image"]')
        imagem_url = loc_img.get_attribute("content") if loc_img.count() > 0 else ""
        
        bloco = pagina.locator("div.principal div.acoes-produto").first
        
        loc_promo = bloco.locator("strong.preco-promocional").first
        loc_normal = bloco.locator("strong.preco-venda").first
        
        if loc_promo.count() > 0:
            attr_preco = loc_promo.get_attribute("data-sell-price")
            preco_atual = float(attr_preco) if attr_preco else limpar_preco_br(loc_promo.inner_text())
        elif loc_normal.count() > 0:
            attr_preco = loc_normal.get_attribute("data-sell-price")
            preco_atual = float(attr_preco) if attr_preco else limpar_preco_br(loc_normal.inner_text())
        else:
            preco_atual = 0.0
        
        loc_antigo = bloco.locator("s.preco-venda").first
        if loc_antigo.count() > 0:
            preco_original = limpar_preco_br(loc_antigo.inner_text())
        else:
            preco_original = preco_atual
            
        desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0
        
        classes_bloco = bloco.get_attribute("class") or ""
        tem_botao = bloco.locator("a.botao-comprar").count() > 0
        texto_migalhas = pagina.locator("div.breadcrumbs").inner_text() if pagina.locator("div.breadcrumbs").count() > 0 else ""
        
        if "indisponivel" in classes_bloco or not tem_botao or preco_atual == 0.0:
            status_estoque = "Indisponível"
            disponivel = False
        elif "Pré-venda" in texto_migalhas or "Pré-venda" in titulo:
            status_estoque = "Pré-venda"
            disponivel = True
        else:
            status_estoque = "Em estoque"
            disponivel = True
            
        categoria = "Novels & Livros" if "Novels" in texto_migalhas or "Livros" in titulo else "Mangás"
        
        return {
            "loja": "NewPOP",
            "categoria": categoria,
            "nome": titulo,
            "url": url_produto,
            "imagem_url": imagem_url,
            "preco_original": preco_original,
            "preco_atual": preco_atual,
            "desconto_pct": desconto_pct,
            "status": status_estoque,
            "disponivel": disponivel
        }
    except Exception as erro:
        print(f"   [Erro] Falha ao ler produto NewPOP {url_produto}: {erro}")
        return None
    
def extrair_vitrine_pipoca(pagina, url_inicial, max_paginas=100):
    """
    Crawler para Pipoca & Nanquim (Magento 2).
    Funciona tanto na Home (carrosséis) quanto nas páginas de categorias (.html).
    """
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []
    urls_vistas = set()
    
    while url_atual and pagina_num <= max_paginas:
        print(f"\n[Pipoca & Nanquim] Varrendo Página {pagina_num}: {url_atual}...")
        
        try:
            resposta = pagina.goto(url_atual, wait_until="commit", timeout=60000)
            if resposta.status != 200:
                print(f"Erro ao acessar Pipoca & Nanquim. Status: {resposta.status}")
                break
            pagina.wait_for_selector("div.products-grid, ol.widget-product-carousel", timeout=30000)
        except Exception as erro:
            print(f"   [Erro de Rede] Falha em Pipoca & Nanquim: {erro}")
            break
        
        cards = pagina.locator("div.products-grid div.product-item-info, ol.widget-product-carousel div.product-item-info")
        total_cards = cards.count()
        print(f"Encontrados {total_cards} cards nessa página.")
        
        for i in range(total_cards):
            try:
                card = cards.nth(i)
                
                link_el = card.locator("a.product-item-link").first
                if link_el.count() == 0:
                    continue
                
                nome = link_el.inner_text().strip()
                url_produto = link_el.get_attribute("href")
                
                if url_produto in urls_vistas:
                    continue
                urls_vistas.add(url_produto)
                
                texto_analise = f"{nome} {url_produto}".lower()
                
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

                img_el = card.locator("img.product-image-photo").first
                imagem_url = img_el.get_attribute("src") if img_el.count() > 0 else ""

                tem_botao = card.locator("button.tocart").count() > 0
                fora_estoque = card.locator(".stock.unavailable").count() > 0
                texto_card = card.inner_text()

                if fora_estoque or not tem_botao:
                    status_estoque = "Indisponível"
                    disponivel = False
                elif "Pré-venda" in texto_card or "Pré-Venda" in texto_card:
                    status_estoque = "Pré-venda"
                    disponivel = True
                else:
                    status_estoque = "Em estoque"
                    disponivel = True

                produtos_extraidos.append({
                    "loja": "Pipoca & Nanquim",
                    "categoria": identificar_categoria(nome, url_atual, preco_atual),
                    "nome": nome,
                    "url": url_produto,
                    "imagem_url": imagem_url,
                    "preco_original": preco_original,
                    "preco_atual": preco_atual,
                    "desconto_pct": desconto_pct,
                    "status": status_estoque,
                    "disponivel": disponivel
                })
            except Exception as erro_card:
                print(f"   [Aviso] Pulando card #{i+1} na P&N: {erro_card}")
                continue

        botao_proxima = pagina.locator("li.pages-item-next a.action.next").first
        if botao_proxima.count() > 0 and pagina_num < max_paginas:
            url_atual = botao_proxima.get_attribute("href")
            pagina_num += 1
        else:
            url_atual = None

    return produtos_extraidos