import json
from playwright.sync_api import sync_playwright

cancelar_varredura = False

TERMOS_IGNORADOS = [
    "figurinha", "álbum", "album","cromo", "envelope",
    "adrenalyn", "fifa", "libertadores", "brasileirão",
    "brasileirao", "copa do mundo", "seleção da copa", "starter pack",
    "chaveiro", "pn toys", "assinatura", "figure"
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
            
        if "pipocaenanquim.com.br" in url_produto:
            loja_nome = "Pipoca & Nanquim"
        elif "mpeg.com.br" in url_produto:
            loja_nome = "MPEG"
        else:
            loja_nome = "Panini"
            
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
    
def ler_cards_magento(cards):
    """Lê todos os cards da página de uma só vez no navegador (Panini e Pipoca & Nanquim)."""
    return cards.evaluate_all("""els => els.map(el => {
        const link = el.querySelector('a.product-item-link');
        const img = el.querySelector('img.product-image-photo');
        const pFinal = el.querySelector('[data-price-type="finalPrice"]');
        const pOld = el.querySelector('[data-price-type="oldPrice"]');
        const texto = el.innerText || '';
        return {
            nome: link ? link.innerText.trim() : '',
            url: link ? link.href : '',
            img: img ? img.src : '',
            preco_atual: pFinal ? parseFloat(pFinal.getAttribute('data-price-amount') || 0) : 0,
            preco_antigo: pOld ? parseFloat(pOld.getAttribute('data-price-amount') || 0) : 0,
            disponivel: !!el.querySelector('button.tocart') && !el.querySelector('.stock.unavailable'),
            prevenda: !!el.querySelector('.infobase-label-presale') || texto.includes('Pré-venda') || texto.includes('Pré-Venda')
        };
    })""")

def extrair_vitrine_panini(pagina, url_inicial, max_paginas=100, urls_vistas=None):
    """
    Crawler de Categoria: entra na vitrine, extrai todos o cards da grade
    e avança para as próximas páginas sozinho até atingir 'max_paginas'.
    """
    
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []
    if urls_vistas is None:
        urls_vistas = set()
    
    while url_atual and pagina_num <= max_paginas:
        if cancelar_varredura:
            print("   [Parada] Varredura interrompida pelo usuário.")
            break
        print(f"[Crawler] Varrendo Página {pagina_num}: {url_atual}...")
    
        try:
            resposta = pagina.goto(url_atual, wait_until="commit", timeout=60000)
            if resposta.status != 200:
                print(f"Erro ao acessar a vitrine. Status: {resposta.status}")
                break
            pagina.wait_for_selector("div.products-grid", timeout=30000)
        except Exception as erro:
            print(f"   [Erro de Rede] Pulo na Página {pagina_num} da Panini: {erro}")
            break
    
        cards = pagina.locator("div.products-grid div.product-item-info")
        lista_bruta = ler_cards_magento(cards)
        print(f"Encontrados {len (lista_bruta)} produtos nesta página.")
    
        for item in lista_bruta:
            if not item["url"] or item["url"] in urls_vistas:
                continue
            urls_vistas.add(item["url"])
            
            preco_atual = item["preco_atual"]
            preco_original = item["preco_antigo"] if item["preco_antigo"] > 0 else preco_atual
            desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0
            
            if not item["disponivel"]:
                status_estoque = "Indisponível"
            elif item["prevenda"]:
                status_estoque = "Pré-venda"
            else:
                status_estoque = "Em estoque"

            produtos_extraidos.append({
                "loja": "Panini",
                "categoria": identificar_categoria(item["nome"], url_atual, preco_atual),
                "nome": item["nome"],
                "url": item["url"],
                "imagem_url": item["img"],
                "preco_original": preco_original,
                "preco_atual": preco_atual,
                "desconto_pct": desconto_pct,
                "status": status_estoque,
                "disponivel": item["disponivel"]
            })
            
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
    
    if 0 < preco_atual < 1.0 or any(termo in texto for termo in TERMOS_IGNORADOS):
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
    elif "/panini-books" in texto or "/novels" in texto or "novel" in texto or "livro" in texto or "livros.html" in texto or "livrosnovels" in texto:
        return "Novels & Livros"
    elif "/marvel" in texto or any(h in texto for h in ["homem-aranha","homem de ferro", "viúva negra", "viuva negra", "viúva-negra", "aranha", "vingadores", "x-men", "wolverine", "demolidor", "thor", "capitão américa", "capitao américa", "hulk", "deadpool", "quarteto fantástico", "surfista prateado"]):
        return "Marvel"
    elif "/dc-comics" in texto or "dc+comics" in texto or any(h in texto for h in ["batman", "superman", "mulher-maravilha", "liga da justiça", "flash", "lanterna verde", "asa noturna", "coringa", "sandman", "arlequina", "watchmen", "juízo final", "heróis em crise", "herois em crise", "robin", "shazam"]):
        return "DC Comics"
    elif "/planet-manga" in texto or "planet+manga" in texto or "lojanewpop" in texto or "mpeg.com.br" in texto or "mangas.html" in texto or any(m in texto for m in ["junji ito", "shigurui", "city hunter", "cat's eye", "cats eye", "chushingura", "battle royale", "one piece", "berserk", "naruto", "dragon ball", "demon slayer", "jujutsu", "tokyo ghoul", "chainsaw man"]):
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

def extrair_vitrine_newpop(pagina, url_inicial, max_paginas=2,urls_vistas=None):
    """
    Crawler para a NewPOP (Loja Integrada) com captura de capa e categoria.
    """
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []
    if urls_vistas is None:
        urls_vistas = set()
        
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
        lista_bruta = cards.evaluate_all("""els => els.map(el => {
            const link = el.querySelector('a.nome-produto');
            const img = el.querySelector('img.imagem-principal');
            const pPromo = el.querySelector('strong.preco-promocional');
            const pNormal = el.querySelector('strong.preco-venda');
            const pAntigo = el.querySelector('s.preco-venda');
            const classes = el.className || '';
            return {
                nome: link ? link.innerText.trim() : '',
                url: link ? link.href : '',
                img: img ? img.src : '',
                preco_attr: pPromo ? pPromo.getAttribute('data-sell-price') : (pNormal ? pNormal.getAttribute('data-sell-price') : ''),
                preco_txt: pPromo ? pPromo.innerText : (pNormal ? pNormal.innerText : ''),
                antigo_txt: pAntigo ? pAntigo.innerText : '',
                classes: classes,
                esgotado: !! el.querySelector('.bandeira-indisponivel, .indisponivel') || classes.includes('indisponivel')
            };
        })""")
        print(f"Encontrados {len(lista_bruta)} produtos nesta página.")

        for item in lista_bruta:
            if not item["url"] or item["url"] in urls_vistas:
                continue
            urls_vistas.add(item["url"])
            
            preco_atual = float(item["preco_attr"]) if item["preco_attr"] else limpar_preco_br(item["preco_txt"])
            preco_original = limpar_preco_br(item["antigo_txt"]) if item["antigo_txt"] else preco_atual
            desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0

            if item["esgotado"] or preco_atual == 0.0:
                status_estoque = "Indisponível"
                disponivel = False
            elif "prod-cat-589867" in item["classes"]:
                status_estoque = "Pré-venda"
                disponivel = True
            else:
                status_estoque = "Em estoque"
                disponivel = True

            categoria = "Novels & Livros" if "prod-cat-500119" in item["classes"] else "Mangás"

            produtos_extraidos.append({
                "loja": "NewPOP",
                "categoria": categoria,
                "nome": item["nome"],
                "url": item["url"],
                "imagem_url": item["img"],
                "preco_original": preco_original,
                "preco_atual": preco_atual,
                "desconto_pct": desconto_pct,
                "status": status_estoque,
                "disponivel": disponivel
            })

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
    
def extrair_vitrine_pipoca(pagina, url_inicial, max_paginas=100, urls_vistas=None):
    """
    Crawler para Pipoca & Nanquim (Magento 2).
    Funciona tanto na Home (carrosséis) quanto nas páginas de categorias (.html).
    """
    url_atual = url_inicial
    pagina_num = 1
    produtos_extraidos = []
    if urls_vistas is None:
        urls_vistas = set()
        
    loja_nome = "MPEG" if "mpeg.com.br" in url_inicial else "Pipoca & Nanquim"
    
    while url_atual and pagina_num <= max_paginas:
        if cancelar_varredura:
            print("   [Parada] Varredura interrompida pelo usuário.")
            break
        print(f"\n[{loja_nome}] Varrendo Página {pagina_num}: {url_atual}...")
        
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
        lista_bruta = ler_cards_magento(cards)
        print(f"Encontrados {len(lista_bruta)} cards nessa página.")
        
        for item in lista_bruta:
            if not item["url"] or item["url"] in urls_vistas:
                continue
            urls_vistas.add(item["url"])

            preco_atual = item["preco_atual"]
            preco_original = item["preco_antigo"] if item["preco_antigo"] > 0 else preco_atual
            desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0

            if not item["disponivel"]:
                status_estoque = "Indisponível"
            elif item["prevenda"]:
                status_estoque = "Pré-venda"
            else:
                status_estoque = "Em estoque"

            produtos_extraidos.append({
                "loja": loja_nome,
                "categoria": identificar_categoria(item["nome"], url_atual, preco_atual),
                "nome": item["nome"],
                "url": item["url"],
                "imagem_url": item["img"],
                "preco_original": preco_original,
                "preco_atual": preco_atual,
                "desconto_pct": desconto_pct,
                "status": status_estoque,
                "disponivel": item["disponivel"]
            })

        botao_proxima = pagina.locator("li.pages-item-next a.action.next").first
        if botao_proxima.count() > 0 and pagina_num < max_paginas:
            url_atual = botao_proxima.get_attribute("href")
            pagina_num += 1
        else:
            url_atual = None

    return produtos_extraidos

def converter_no_jbc(no):
    """Converse o bloco JSON de um produto da JBC/Companhia das Letras para o formato do banco."""
    nome = no.get("name", "").strip()
    slug = no.get("slug") or no.get("seo", {}).get("canonical", "").strip("/")
    if not nome or not slug:
        return None
    
    url_produto = f"https://www.companhiadasletras.com.br/{slug}/p" if not slug.endswith("/p") else f"https://www.companhiadasletras.com.br/{slug}"
    
    imagens = no.get("image", [])
    imagem_url = imagens[0].get("url", "") if imagens else ""
    
    ofertas = no.get("offers", {}).get("offers", [])
    if ofertas:
        preco_atual = float(ofertas[0].get("price", 0.0))
        preco_original = float(ofertas[0].get("listPrice", preco_atual))
        em_estoque_vtex = "InStock" in ofertas[0].get("availability", "")
    else:
        preco_atual = 0.0
        preco_original = 0.0
        em_estoque_vtex = False
        
    desconto_pct = round(((preco_original - preco_atual) / preco_original) * 100) if preco_original > preco_atual else 0
    
    specs = {s.get("name"): s.get("value", "") for s in no.get("specifications", [])}
    status_disp = specs.get("Status de disponibilidade", "").lower()
    
    if not em_estoque_vtex or preco_atual == 0.0:
        status_estoque = "Indisponível"
        disponivel = False
    elif "pré-venda" in status_disp or "pre-venda" in status_disp:
        status_estoque = "Pré-venda"
        disponivel = True
    else:
        status_estoque = "Em estoque"
        disponivel = True
        
    categoria = "Novels & Livros" if ("novel" in nome.lower() or "livro" in nome.lower()) else "Mangás"
    
    return {
        "loja": "JBC",
        "categoria": categoria,
        "nome": nome,
        "url": url_produto,
        "imagem_url": imagem_url,
        "preco_original": preco_original,
        "preco_atual": preco_atual,
        "desconto_pct": desconto_pct,
        "status": status_estoque,
        "disponivel": disponivel
    }
    
def extrair_jbc(pagina, url_produto):
    """Extrai dados de um mangá individual da JBC (usado na Wishlist)."""
    print(f"Consultando JBC: {url_produto}...")
    try:
        resposta = pagina.goto(url_produto, wait_until="domcontentloaded", timeout=60000)
        if resposta.status != 200:
            return None
        texto_json = pagina.locator("script#__NEXT_DATA__").inner_text()
        dados_next = json.loads(texto_json)
        no_produto = dados_next.get("props", {}).get("pageProps", {}).get("data", {}).get("product", {})
        return converter_no_jbc(no_produto)
    except Exception as erro:
        print(f"   [Erro] Falhar ao ler produto JBC {url_produto}: {erro}")
        return None
    
def extrair_vitrine_jbc(pagina, url_inicial, max_cliques=90, urls_vistas=None):
    """
    Crawler para a vitrine da JBC na Companhia das Letras.
    Clica em 'Ver mais' e para sozinho assim que os títulos começarem a repetir.
    """
    produtos_extraidos = []
    if urls_vistas is None:
        urls_vistas = set()
        
    nos_fila = []

    def capturar_graphql(resposta):
        if "graphql" in resposta.url and resposta.status == 200:
            try:
                d = resposta.json()
                edges = d.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                for e in edges:
                    if "node" in e:
                        nos_fila.append(e["node"])
            except Exception:
                pass
            
    pagina.on("response", capturar_graphql)
    
    try:
        print(f"\n[JBC] Abrindo vitrine: {url_inicial}...")
        pagina.goto(url_inicial, wait_until="domcontentloaded", timeout=60000)
        
        loc_next = pagina.locator("script#__NEXT_DATA__")
        if loc_next.count() > 0:
            dados_iniciais = json.loads(loc_next.inner_text())
            edges_ini = dados_iniciais.get("props", {}).get("pageProps", {}).get("data", {}).get("search", {}).get("products", {}).get("edges", [])
            for e in edges_ini:
                if "node" in e:
                    nos_fila.append(e["node"])
                    
        clique_num = 0
        while clique_num <= max_cliques:
            if cancelar_varredura:
                print("   [Parada] Varredura interrompida pelo usuário.")
                break
            
            novos_neste_lote = 0
            while nos_fila:
                no = nos_fila.pop(0)
                prod = converter_no_jbc(no)
                if prod and prod["url"] not in urls_vistas:
                    urls_vistas.add(prod["url"])
                    produtos_extraidos.append(prod)
                    novos_neste_lote += 1
                    
            print(f"[JBC] Lote {clique_num + 1}: +{novos_neste_lote}  mangás inéditos (Total JBC: {len(produtos_extraidos)}).")
            
            if clique_num > 0 and novos_neste_lote == 0:
                print("[JBC] Fim do catálogo atingido (títulos repetidos detectados). Encerrando JBC!")
                break
            
            botao_mais = pagina.locator("button:has-text('Ver mais'), a:has-text('Ver mais')").first
            if botao_mais.count() == 0 or clique_num >= max_cliques:
                break
            
            clique_num += 1
            botao_mais.evaluate("el => el.click()")
            pagina.wait_for_timeout(1800)
            
    except Exception as erro:
        print(f"   [Erro de Rede] Falha na vitrine JBC: {erro}")
    finally:
        pagina.remove_listener("response", capturar_graphql)    
    
    return produtos_extraidos