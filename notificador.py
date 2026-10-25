import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def enviar_alerta_ntfy(dados, desconto_minimo):
    """Envia uma notificação Push para o celular via ntfy.sh."""
    topico = os.getenv("NTFY_TOPICO")
    
    if not topico:
        print("[Aviso] NTFY_TOPICO não configurado no arquivo .env.")
        return
    
    url_ntfy = f"https://ntfy.sh/theproject-promo-mano-no1te"
    
    mensagem = (
        f"Por: R$ {dados['preco_atual']:.2f} ({dados['desconto_pct']}% OFF)"
        f"Preço original: R$ {dados['preco_original']:.2f})\n"  
        f"Status: {dados['status']}"
    )
    
    headers = {
        "Title": f"Oferta: {dados['nome']}",
        "Priority": "high",
        "Tags": "books,money_with_wings",
        "Click": dados["url"],
        "Actions": f"view, Abrir na Panini, {dados['url']}"
    }
    
    try:
        resposta = httpx.post(url_ntfy, content=mensagem.encode("utf-8"), headers=headers)
        if resposta.status_code == 200:
            print("   [Ntfy] Notificação enviada para o celular com sucesso!")
        else:
            print("   [Ntfy] Erro ao enviar notificação. Status {resposta.status_code}")
    except Exception as erro:
        print("   [Ntfy] Falha de conexão ao enviar alerta: {erro}")