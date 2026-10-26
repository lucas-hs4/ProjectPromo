from playwright.sync_api import sync_playwright
from scraper import extrair_panini, extrair_vitrine_panini
from database import inicializar_banco, salvar_leitura, atualizar_status_alerta
from notificador import enviar_alerta_ntfy

DESCONTO_MINIMO_PCT = 70

VITRINES_MONITORADAS = [
    "https://panini.com.br/desconto-saldao",
    "https://panini.com.br/promos",
    "https://panini.com.br/desconto-manga",
]

URLS_INDIVIDUAIS = [
    "https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
    "https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
    "https://panini.com.br/marvel-boy-marvel-essenciais",
    "https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
]
def processar_produto(dados):
    """Salva o quadrinho no PostgreSQL e gerencia a trava de notificação."""
    prod_id, alerta_ja_enviada = salvar_leitura(dados)
    print(f"[DB] ID #{prod_id} | {dados['nome']} | R$ {dados['preco_atual']:.2f} | ({dados['desconto_pct']}% OFF) | {dados['status']}")
    
    em_promocao_valida = dados["disponivel"] and dados["desconto_pct"] >= DESCONTO_MINIMO_PCT
    
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
    inicializar_banco()
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        contexto = navegador.new_context(
            locale="pt-BR",
            viewport={"width": 1366, "height": 768}
        )
        pagina = contexto.new_page()
        
        for url_vitrine in VITRINES_MONITORADAS:
            lista_produtos = extrair_vitrine_panini(pagina, url_vitrine,max_paginas=100)
            for dados in lista_produtos:
                processar_produto(dados)
                
        for url in URLS_INDIVIDUAIS:
            dados = extrair_panini(pagina, url)
            if dados:
                processar_produto(dados)
            
        navegador.close()
        print("Varredura concluída com sucesso!")

if __name__ == "__main__":
    executar_robo()