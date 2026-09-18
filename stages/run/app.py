import gradio as gr

from stages.run.run import predict_matchup


def predict(fighter_a, fighter_b, weight_class, odds_a, odds_b):
    try:
        name_a, proba_a, name_b, proba_b = predict_matchup(
            fighter_a, fighter_b, weight_class, int(odds_a) if odds_a else None, int(odds_b) if odds_b else None
        )
    except ValueError as error:
        return str(error)
    return f"{name_a}: {proba_a:.1%}\n{name_b}: {proba_b:.1%}"


demo = gr.Interface(
    fn=predict,
    inputs=[
        gr.Textbox(label="Fighter A"),
        gr.Textbox(label="Fighter B"),
        gr.Textbox(label="Weight class", placeholder="e.g. Lightweight"),
        gr.Number(label="Fighter A moneyline", precision=0),
        gr.Number(label="Fighter B moneyline", precision=0),
    ],
    outputs=gr.Textbox(label="Prediction"),
    title="BrawlBot",
)

if __name__ == "__main__":
    demo.launch()
