from playwright.sync_api import sync_playwright
from scraper import extrair_panini
from database import inicializar_banco, salvar_leitura

MONITORAMENTO = [
    {
        "url": "https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
        "alvo": 60.00
    },
    {
        "url": "https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
        "alvo": 95.00
    },
    {
        "url": "https://panini.com.br/marvel-boy-marvel-essenciais",
        "alvo": 70.00
    },
    {
        "url": "https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
        "alvo": 60.00
    },
]

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
        
        for item in MONITORAMENTO:
            dados = extrair_panini(pagina, item["url"])
            
            if dados:
                prod_id, preco_alvo = salvar_leitura(dados, item["alvo"])
                print(f"[DB] Salvo ID #{prod_id} | {dados['nome']} | R$ {dados['preco_atual']} {dados['desconto_pct']}% OFF | {dados['status']}")
                
                if dados["disponivel"] and dados ["preco_atual"] <= preco_alvo:
                    print(f" >>> ALERTA DE COMPRA! Preço atual (R$ {dados['preco_atual']}) atingiu o alvo de R$ {preco_alvo}!")
                elif not dados["disponivel"]:
                    print(" --- Ignorado no alerta: Produto fora de estoque.")
            
        navegador.close()

if __name__ == "__main__":
    executar_robo()