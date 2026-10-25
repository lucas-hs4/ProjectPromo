from playwright.sync_api import sync_playwright
from scraper import extrair_panini
from database import inicializar_banco, salvar_leitura, atualizar_status_alerta
from notificador import enviar_alerta_ntfy

DESCONTO_MINIMO_PCT = 15

URLS_MONITORADAS = [
    "https://panini.com.br/surfista-prateado-escuridao-marvel-essenciais",
    "https://panini.com.br/demolidor-a-queda-de-murdock-adequ001r2",
    "https://panini.com.br/marvel-boy-marvel-essenciais",
    "https://panini.com.br/a-essencia-do-medo-marvel-essenciais",
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
        
        for url in URLS_MONITORADAS:
            dados = extrair_panini(pagina, url)
            
            if dados:
                prod_id, alerta_ja_enviado = salvar_leitura(dados)
                print(f"[DB] Salvo ID #{prod_id} | {dados['nome']} | R$ {dados['preco_atual']} {dados['desconto_pct']}% OFF | {dados['status']}")
                
                em_promocao_valida = dados["disponivel"] and dados["desconto_pct"] >= DESCONTO_MINIMO_PCT
                
                if em_promocao_valida:
                    if not alerta_ja_enviado:
                        print(f" >>> ALERTA DE COMPRA! OFERTA: R$ {dados['preco_atual']}({dados['desconto_pct']}% OFF)")
                        enviar_alerta_ntfy(dados, DESCONTO_MINIMO_PCT)
                        atualizar_status_alerta(prod_id, True)
                    else:
                        print(" === Promoção continua ativa, mas o alerta já foi enviado anteriormente.")
                else:
                    if alerta_ja_enviado:
                        print(" --- A promoção acabou ou o item esgotou. Resetando trava de alerta para o futuro!")
                        atualizar_status_alerta(prod_id, False)
                    elif not dados["disponivel"]:
                        print(" --- Ignorado no alerta: Produto fora de estoque.")
            
        navegador.close()

if __name__ == "__main__":
    executar_robo()