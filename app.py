import time
import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import inicializar_banco, listar_ofertas, alternar_favorito, buscar_historico_produto, definir_preco_alvo
from main import executar_robo

app = Flask(__name__)

robo_em_execucao = False
intervalo_auto_min = 0

def rodar_robo_background(modo="completo"):
    global robo_em_execucao
    try:
        executar_robo(modo)
    finally:
        robo_em_execucao = False
        
        
def loop_agendador():
    """Verifica a cada minuto se está na hora de disparar a varredura automática."""
    global robo_em_execucao
    ultimo_disparo = time.time()
    while True:
        time.sleep(30)
        if intervalo_auto_min > 0 and not robo_em_execucao:
            if (time.time() - ultimo_disparo) >= (intervalo_auto_min * 60):
                robo_em_execucao = True
                ultimo_disparo = time.time()
                threading.Thread(target=rodar_robo_background, args=("rapido",), daemon=True).start()
                
threading.Thread(target=loop_agendador, daemon=True).start()               

@app.route("/")
def index():
    desconto_min = request.args.get("desconto_min", default=0, type=int)
    preco_min = request.args.get("preco_min", default=0.0, type=float)
    preco_max = request.args.get("preco_max", default=0.0, type=float)
    busca = request.args.get("busca", default="", type=str)
    loja = request.args.get("loja", default="", type=str)
    plataforma = request.args.get("plataforma", default="Editoras", type=str)
    categoria = request.args.get("categoria", default="", type=str)
    ordem = request.args.get("ordem", default="desconto", type=str)
    apenas_disp = request.args.get("disponiveis") == "1"
    apenas_fav = request.args.get("favoritos") == "1"
    pagina = request.args.get("pagina", default=1, type=int)
    por_pagina = request.args.get("por_pagina", default=100, type=int)
    if pagina < 1:
        pagina = 1
        
    ofertas = listar_ofertas(desconto_min, preco_min, preco_max, busca, loja, categoria, apenas_disp, apenas_fav, ordem, pagina, por_pagina, plataforma)
    
    total_itens = ofertas[0]["total_geral"] if ofertas else 0
    total_paginas = (total_itens + por_pagina - 1) // por_pagina if total_itens > 0 else 1
    
    return render_template(
        "index.html",
        ofertas=ofertas,
        total_itens=total_itens,
        pagina=pagina,
        total_paginas=total_paginas,
        por_pagina=por_pagina,
        desconto_min=desconto_min,
        preco_min=preco_min if preco_min > 0 else "",
        preco_max= preco_max if preco_max > 0 else "",
        busca=busca,
        loja=loja,
        plataforma=plataforma,
        categoria=categoria,
        ordem=ordem,
        apenas_disp=apenas_disp,
        apenas_fav=apenas_fav,
        robo_rodando=robo_em_execucao,
        intervalo_auto=intervalo_auto_min
    )
    
@app.route("/varrer", methods=["POST"])
def acionar_varredura():
    global robo_em_execucao
    modo = request.form.get("modo", "completo")
    if not robo_em_execucao:
        robo_em_execucao = True
        thread = threading.Thread(target=rodar_robo_background, args=(modo,))
        thread.start()
    return redirect(request.referrer or url_for("index"))

@app.route("/parar", methods=["POST"])
def parar_varredura():
    import scraper
    scraper.cancelar_varredura = True
    return redirect(request.referrer or url_for("index"))

@app.route("/favoritar/<int:produto_id>", methods=["POST"])
def favoritar(produto_id):
    novo_status = alternar_favorito(produto_id)
    return jsonify({"favorito": novo_status})

@app.route("/status_robo")
def status_robo():
    return jsonify({"rodando": robo_em_execucao})

@app.route("/historico/<int:produto_id>")
def historico_produto(produto_id):
    dados = buscar_historico_produto(produto_id)
    return jsonify (dados)

@app.route("/meta/<int:produto_id>", methods=["POST"])
def salvar_meta(produto_id):
    dados = request.get_json() or {}
    valor = float(dados.get("preco_alvo", 0.0))
    definir_preco_alvo(produto_id, valor)
    return jsonify({"preco_alvo": valor})

@app.route("/agendar", methods=["POST"])
def configurar_agendador():
    global intervalo_auto_min
    intervalo_auto_min = request.form.get("intervalo", default=0, type=int)
    return redirect(request.referrer or url_for())

if __name__ == "__main__":
    inicializar_banco()
    app.run(host="0.0.0.0", port=5000)