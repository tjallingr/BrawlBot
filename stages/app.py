
import json

import gradio as gr

from stages.run.run import predict_matchup
from stages.train.eval import load_metrics, load_predictions, simulate_betting
from stages.weekly import PREDICTIONS_PATH, predict_upcoming_card


def predict(fighter_a, fighter_b, weight_class, odds_a, odds_b):
    try:
        name_a, proba_a, name_b, proba_b = predict_matchup(
            fighter_a, fighter_b, weight_class, int(odds_a) if odds_a else None, int(odds_b) if odds_b else None
        )
    except ValueError as error:
        return str(error)
    return f"{name_a}: {proba_a:.1%}\n{name_b}: {proba_b:.1%}"


def _as_rows(results: list[dict]) -> list[list[str]]:
    return [
        [r["fighter_a"], r["fighter_b"], "?" if "error" in r else f"{r['proba_a']:.1%}",
         "?" if "error" in r else f"{r['proba_b']:.1%}", r.get("error", "")]
        for r in results
    ]


def load_saved_card():
    if not PREDICTIONS_PATH.exists():
        return _as_rows([])
    return _as_rows(json.loads(PREDICTIONS_PATH.read_text()))


def refresh_card():
    return _as_rows(predict_upcoming_card())


CARD_COLUMNS = ["Fighter A", "Fighter B", "Win % A", "Win % B", "Note"]
PREDICTION_COLUMNS = ["Date", "Fighter A", "Fighter B", "Predicted A win %", "Actual winner"]


def _metrics_summary(metrics: dict, betting: dict) -> str:
    return (
        f"AUC {metrics['auc']:.3f}   "
        f"Accuracy {metrics['accuracy']:.3f}   "
        f"Recall {metrics['recall']:.3f}   "
        f"Precision {metrics['precision']:.3f}   "
        f"Brier {metrics['brier']:.3f}\n"
        f"Betting ({betting['n_fights_with_odds']} fights had odds) -- "
        f"flat €{betting['flat_stake']:.0f}/fight on the model's pick: €{betting['flat_profit']:+.2f}   "
        f"stake-by-edge over the market ({betting['edge_bets_placed']} bets placed): €{betting['edge_profit']:+.2f}"
    )


def _calibration_rows(metrics: dict) -> list[list[float]]:
    return [[round(predicted * 100, 1), round(observed * 100, 1)] for predicted, observed in metrics["calibration"]]


def load_eval():
    metrics = load_metrics()
    predictions = load_predictions()
    betting = simulate_betting(predictions)
    display = predictions.drop(columns=["r_odds_prob", "b_odds_prob"]).assign(date=predictions["date"].astype(str))
    return _metrics_summary(metrics, betting), _calibration_rows(metrics), display.values.tolist()


with gr.Blocks(title="BrawlBot") as demo:
    with gr.Tab("Predict a matchup"):
        gr.Interface(
            fn=predict,
            inputs=[
                gr.Textbox(label="Fighter A"),
                gr.Textbox(label="Fighter B"),
                gr.Textbox(label="Weight class", placeholder="e.g. Lightweight"),
                gr.Number(label="Fighter A moneyline", precision=0),
                gr.Number(label="Fighter B moneyline", precision=0),
            ],
            outputs=gr.Textbox(label="Prediction"),
        )

    with gr.Tab("This week's card"):
        table = gr.Dataframe(headers=CARD_COLUMNS, value=load_saved_card)
        refresh = gr.Button("Refresh now (re-scrapes odds, takes ~20s)")
        refresh.click(fn=refresh_card, outputs=table)

    with gr.Tab("Eval (holdout fights)"):
        gr.Markdown("Retrained weekly on everything; this is the last honest holdout evaluation (~15% of data) from before that final retrain.")
        metrics_box = gr.Textbox(label="Metrics", interactive=False, lines=2)
        calibration_table = gr.Dataframe(headers=["Predicted win %", "Observed win %"], label="Calibration")
        predictions_table = gr.Dataframe(headers=PREDICTION_COLUMNS, label="Predictions vs outcomes")
        refresh_eval = gr.Button("Refresh")
        eval_outputs = [metrics_box, calibration_table, predictions_table]
        refresh_eval.click(fn=load_eval, outputs=eval_outputs)
        demo.load(fn=load_eval, outputs=eval_outputs)

if __name__ == "__main__":
    demo.launch()
