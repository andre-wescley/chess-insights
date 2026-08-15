import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from pgn_reader import read_pgn_games
from statistics import build_games_dataframe, build_player_dataframe, build_opening_dataframe, normalize_name

st.set_page_config(page_title="Chess PGN Insights", page_icon="♟", layout="wide")
st.title("♟ Chess PGN Insights")
st.caption("Análise de partidas por PGN, Chess.com ou Lichess")


def chesscom_pgn(username, max_months):
    response = requests.get(f"https://api.chess.com/pub/player/{username.strip().lower()}/games/archives", headers={"User-Agent": "ChessPGNInsights/1.0"}, timeout=30)
    if response.status_code == 404:
        raise ValueError("Jogador não encontrado no Chess.com.")
    response.raise_for_status()
    archives = response.json().get("archives", [])[-max_months:]
    pgns = []
    for archive in archives:
        result = requests.get(f"{archive}/pgn", headers={"User-Agent": "ChessPGNInsights/1.0"}, timeout=60)
        if result.ok and result.text.strip():
            pgns.append(result.text)
    return "\n\n".join(pgns)


def lichess_pgn(username, max_games):
    result = requests.get(f"https://lichess.org/api/games/user/{username.strip()}", params={"max": max_games, "moves": "true", "tags": "true", "clocks": "true", "opening": "true", "finished": "true"}, headers={"Accept": "application/x-chess-pgn", "User-Agent": "ChessPGNInsights/1.0"}, timeout=120)
    if result.status_code == 404:
        raise ValueError("Jogador não encontrado no Lichess.")
    result.raise_for_status()
    return result.text


source = st.sidebar.radio("Fonte dos dados", ["Arquivo PGN", "Chess.com", "Lichess"])
pgn_text = ""
source_info = ""

if source == "Arquivo PGN":
    uploads = st.sidebar.file_uploader("Importe um ou mais arquivos PGN", type=["pgn"], accept_multiple_files=True)
    if not uploads:
        st.info("Selecione um ou mais arquivos PGN na barra lateral.")
        st.stop()
    pgn_text = "\n\n".join(u.getvalue().decode("utf-8-sig", errors="replace") for u in uploads)
    source_info = f"{len(uploads)} arquivo(s) local(is)"
else:
    username = st.sidebar.text_input("Nickname")
    limit = st.sidebar.number_input("Limite de partidas/meses", min_value=1, max_value=10000, value=1000 if source == "Lichess" else 12)
    button_label = "Buscar partidas no Chess.com" if source == "Chess.com" else "Buscar partidas no Lichess"
    if st.sidebar.button(button_label):
        try:
            with st.spinner("Consultando partidas..."):
                pgn_text = chesscom_pgn(username, int(limit)) if source == "Chess.com" else lichess_pgn(username, int(limit))
            st.session_state["remote_pgn"] = pgn_text
            st.session_state["source_info"] = f"{source}: {username}"
        except Exception as exc:
            st.error(str(exc))
            st.stop()
    pgn_text = st.session_state.get("remote_pgn", "")
    source_info = st.session_state.get("source_info", source)
    if not pgn_text:
        st.info(f"Informe o nickname e clique em '{button_label}'.")
        st.stop()

all_games, errors = read_pgn_games(io.StringIO(pgn_text))
if errors:
    with st.expander(f"Avisos de leitura ({len(errors)})"):
        for error in errors:
            st.warning(error)
if not all_games:
    st.error("Nenhuma partida válida foi encontrada.")
    st.stop()

games_df = build_games_dataframe(all_games)
players = pd.concat([
    games_df[["white", "white_norm"]].rename(columns={"white": "name", "white_norm": "norm"}),
    games_df[["black", "black_norm"]].rename(columns={"black": "name", "black_norm": "norm"}),
], ignore_index=True).groupby("norm", as_index=False).agg(name=("name", "first"), partidas=("name", "size"))
players = players.sort_values(["partidas", "name"], ascending=[False, True])
st.success(f"{len(all_games)} partida(s) carregada(s) — {source_info}")

selected_player = st.sidebar.selectbox("Jogador em evidência", players.name.tolist(), format_func=lambda n: f"{n} ({int(players.loc[players.name.eq(n), 'partidas'].iloc[0])} partidas)")
player_norm = normalize_name(selected_player)
player_games = games_df[(games_df.white_norm == player_norm) | (games_df.black_norm == player_norm)].copy()
opponents = sorted(set(player_games.loc[player_games.white_norm == player_norm, "black"]) | set(player_games.loc[player_games.black_norm == player_norm, "white"]))
selected_opponent = st.sidebar.selectbox("Adversário", ["Todos os adversários"] + opponents)
openings = sorted(player_games.opening_name.dropna().unique().tolist())
selected_opening = st.sidebar.selectbox("Abertura", ["Todas as aberturas"] + openings)
selected_color = st.sidebar.selectbox("Cor", ["Todas", "Brancas", "Pretas"])
selected_result = st.sidebar.selectbox("Resultado", ["Todos", "Vitória", "Derrota", "Empate"])

filtered = player_games.copy()
if selected_opponent != "Todos os adversários":
    opponent_norm = normalize_name(selected_opponent)
    filtered = filtered[((filtered.white_norm == player_norm) & (filtered.black_norm == opponent_norm)) | ((filtered.black_norm == player_norm) & (filtered.white_norm == opponent_norm))]
if selected_opening != "Todas as aberturas":
    filtered = filtered[filtered.opening_name == selected_opening]
view = build_player_dataframe(filtered, selected_player)
if selected_color != "Todas":
    view = view[view.player_color == selected_color]
if selected_result != "Todos":
    view = view[view.player_result == selected_result]

st.sidebar.caption(f"Partidas após filtros: {len(view)}")
if view.empty:
    st.warning("Nenhuma partida corresponde aos filtros selecionados.")
    st.stop()

wins, losses, draws = int(view.is_win.sum()), int(view.is_loss.sum()), int(view.is_draw.sum())
score = (wins + .5 * draws) / len(view) * 100
ratings = pd.to_numeric(view.player_rating, errors="coerce")
ratings = ratings[ratings > 0]
metrics = st.columns(7)
for col, (label, value) in zip(metrics, [("Partidas", len(view)), ("Vitórias", wins), ("Derrotas", losses), ("Empates", draws), ("Aproveitamento", f"{score:.1f}%"), ("Maior rating", int(ratings.max()) if not ratings.empty else "—"), ("Menor rating", int(ratings.min()) if not ratings.empty else "—")]):
    col.metric(label, value)

st.subheader("Desempenho por cor")
summary = view.groupby("player_color", as_index=False).agg(partidas=("game_id", "count"), vitorias=("is_win", "sum"), derrotas=("is_loss", "sum"), empates=("is_draw", "sum"), rating_medio=("player_rating", "mean"), rating_medio_adversarios=("opponent_rating", "mean"))
summary["aproveitamento"] = (summary.vitorias + .5 * summary.empates) / summary.partidas * 100
st.dataframe(summary.round(1), use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    counts = (view["player_result"].value_counts().rename_axis("resultado").reset_index(name="partidas"))

    fig_results = px.pie(counts,names="resultado",values="partidas",hole=0.48,color="resultado",
        color_discrete_map={
            "Vitória": "#16a34a",
            "Empate": "#eab308",
            "Derrota": "#dc2626",
        },
        title="Distribuição dos resultados",
    )

    fig_results.update_traces(textposition="inside",textinfo="label+percent",textfont_size=15,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Partidas: %{value}<br>"
            "Percentual: %{percent}"
            "<extra></extra>"
        ),
        marker=dict(line=dict(color="white",width=2,)),
    )

    fig_results.update_layout(height=520,
        margin=dict(
            l=20,
            r=20,
            t=70,
            b=20,
        ),
        legend=dict(orientation="v",yanchor="middle",y=0.5,xanchor="left",x=1.02,font=dict(size=14),),
        title=dict(x=0.5,xanchor="center",),
    )

    st.plotly_chart(fig_results,use_container_width=True,)
with right:
    mode = st.radio("Visualização do gráfico", ["Resultado por partida", "Pontuação acumulada"], horizontal=True)
    chart = view.copy(); chart["data"] = pd.to_datetime(chart.date, errors="coerce"); chart = chart.sort_values(["data", "game_id"]).reset_index(drop=True); chart["partida_numero"] = range(1, len(chart)+1)
    if mode == "Resultado por partida":
        fig = px.scatter(chart, x="partida_numero", y="player_result", color="player_result", symbol="player_result", hover_data=["data", "opponent", "player_color", "event", "round"], category_orders={"player_result": ["Derrota", "Empate", "Vitória"]}, color_discrete_map={"Vitória": "#16a34a", "Empate": "#eab308", "Derrota": "#dc2626"}, title="Resultado por partida")
        fig.update_traces(marker={"size": 12}); fig.update_layout(height=450, showlegend=False)
    else:
        chart["pontos"] = chart.player_result.map({"Vitória": 1, "Empate": .5, "Derrota": 0}).cumsum()
        fig = px.line(chart, x="partida_numero", y="pontos", markers=True, hover_data=["data", "opponent", "player_result"], title="Pontuação acumulada")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Aberturas por ECO e linhas")
eco_list = []
opening_df = build_opening_dataframe(view)
for eco, group in opening_df.groupby("eco", sort=True):
    name = group["opening_name"].iloc[0]
    total = int(group["partidas"].sum())
    wins_eco = int(group["vitorias"].sum())
    losses_eco = int(group["derrotas"].sum())
    draws_eco = int(group["empates"].sum())
    eco_score = (wins_eco + .5 * draws_eco) / total * 100
    title = f"{eco} — {name} | {total} partidas | {wins_eco}V {losses_eco}D {draws_eco}E | {eco_score:.1f}%"
    eco_list.append(
        {
            "eco": eco,
            "name": name,
            "total": total,
            "wins_eco": wins_eco,
            "losses_eco": losses_eco,
            "draws_eco": draws_eco,
            "eco_score": eco_score,
            "group": group.copy(),
            "title": title,
        }
    )

eco_list.sort(key=lambda item: item["total"],reverse=True,)
selected_title = st.selectbox("Selecione a abertura",[item["title"] for item in eco_list],)

selected = next(
    item
    for item in eco_list
    if item["title"] == selected_title
)

group = selected["group"]

detail = group.rename(columns={"eco": "ECO", "opening_name": "Abertura", "linha": "Linha", "first_10_moves": "Primeiros 10 lances", "partidas": "Partidas", "vitorias": "Vitórias", "derrotas": "Derrotas", "empates": "Empates", "aproveitamento": "Aproveitamento (%)"})
st.dataframe(detail[["Linha", "Primeiros 10 lances", "Partidas", "Vitórias", "Derrotas", "Empates", "Aproveitamento (%)"]].round(1), use_container_width=True, hide_index=True)

st.subheader("Partidas filtradas")
columns = ["game_id", "date", "event", "round", "opponent", "player_color", "player_result", "player_rating", "opponent_rating", "eco", "opening_name", "full_moves", "first_10_moves"]
st.dataframe(view[columns].rename(columns={"opening_name": "Abertura", "first_10_moves": "Primeiros 10 lances"}).sort_values(["date", "game_id"], ascending=[False, False]), use_container_width=True, hide_index=True)

with st.expander("Visualizar PGN"):
    selected_id = st.selectbox("ID da partida", view.game_id.tolist())
    st.code(next(g for g in all_games if g["game_id"] == selected_id)["pgn"], language="text")
