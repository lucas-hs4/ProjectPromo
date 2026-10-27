import threading
from flask import Flask, render_template, request, redirect, url_for
from database import inicializar_banco, listar_ofertas
from main import executar_robo

app = Flask(__name__)

robo_em_execucao = False

def rodar_robo_background():
    global robo_em_execucao
    try:
        executar_robo()
    finally:
        robo_em_execucao = False
        
@app.route("/")
def index():
    desconto_min = request.args.get("desconto_min", default=0, type=int)
    preco_max = request.args.get("preco_max", default=0.0, type=float)
    busca = request.args.get("busca", default="", type=str)
    loja = request.args.get("loja", default="", type=str)
    categoria = request.args.get("categoria", default="", type=str)
    ordem = request.args.get("ordem", default="desconto", type=str)
    apenas_disp = request.args.get("disponiveis") == "1"
    
    ofertas = listar_ofertas(desconto_min, preco_max, busca, loja, categoria, apenas_disp, ordem)
    
    return render_template(
        "index.html",
        ofertas=ofertas,
        desconto_min=desconto_min,
        preco_max= preco_max if preco_max > 0 else "",
        busca=busca,
        loja=loja,
        categoria=categoria,
        ordem=ordem,
        apenas_disp=apenas_disp,
        robo_rodando=robo_em_execucao
    )
    
@app.route("/varrer", methods=["POST"])
def acionar_varredura():
    global robo_em_execucao
    if not robo_em_execucao:
        robo_em_execucao = True
        thread = threading.Thread(target=rodar_robo_background)
        thread.start()
    return redirect(url_for("index"))

if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True, port=5000)