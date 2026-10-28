import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import inicializar_banco, listar_ofertas, alternar_favorito
from main import executar_robo

app = Flask(__name__)

robo_em_execucao = False

def rodar_robo_background(modo="completo"):
    global robo_em_execucao
    try:
        executar_robo(modo)
    finally:
        robo_em_execucao = False
        
@app.route("/")
def index():
    desconto_min = request.args.get("desconto_min", default=0, type=int)
    preco_min = request.args.get("preco_min", default=0.0, type=float)
    preco_max = request.args.get("preco_max", default=0.0, type=float)
    busca = request.args.get("busca", default="", type=str)
    loja = request.args.get("loja", default="", type=str)
    categoria = request.args.get("categoria", default="", type=str)
    ordem = request.args.get("ordem", default="desconto", type=str)
    apenas_disp = request.args.get("disponiveis") == "1"
    apenas_fav = request.args.get("favoritos") == "1"
    pagina = request.args.get("pagina", default=1, type=int)
    por_pagina = request.args.get("por_pagina", default=100, type=int)
    if pagina < 1:
        pagina = 1
        
    ofertas = listar_ofertas(desconto_min, preco_min, preco_max, busca, loja, categoria, apenas_disp, apenas_fav, ordem, pagina, por_pagina)
    
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
        categoria=categoria,
        ordem=ordem,
        apenas_disp=apenas_disp,
        apenas_fav=apenas_fav,
        robo_rodando=robo_em_execucao
    )
    
@app.route("/varrer", methods=["POST"])
def acionar_varredura():
    global robo_em_execucao
    modo = request.form.get("modo", "completo")
    if not robo_em_execucao:
        robo_em_execucao = True
        thread = threading.Thread(target=rodar_robo_background, args=(modo,))
        thread.start()
    return redirect(url_for("index"))

@app.route("/parar", methods=["POST"])
def parar_varredura():
    import scraper
    scraper.cancelar_varredura = True
    return redirect(url_for("index"))

@app.route("/favoritar/<int:produto_id>", methods=["POST"])
def favoritar(produto_id):
    novo_status = alternar_favorito(produto_id)
    return jsonify({"favorito": novo_status})

@app.route("/status_robo")
def status_robo():
    return jsonify({"rodando": robo_em_execucao})

if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True, port=5000)