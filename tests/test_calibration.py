import numpy as np
from sklearn.metrics import brier_score_loss


def test_brier_score_is_zero_for_perfectly_confident_correct_predictions():
    y_true = np.array([1, 0, 1, 0])
    y_proba = np.array([1.0, 0.0, 1.0, 0.0])
    assert brier_score_loss(y_true, y_proba) == 0.0


def test_brier_score_is_quarter_for_always_predicting_the_coin_flip():
    y_true = np.array([1, 0, 1, 0])
    y_proba = np.array([0.5, 0.5, 0.5, 0.5])
    assert brier_score_loss(y_true, y_proba) == 0.25


def test_brier_score_is_worse_for_confidently_wrong_than_for_uncertain():
    y_true = np.array([1, 0, 1, 0])
    confidently_wrong = brier_score_loss(y_true, np.array([0.0, 1.0, 0.0, 1.0]))
    uncertain = brier_score_loss(y_true, np.array([0.5, 0.5, 0.5, 0.5]))
    assert confidently_wrong > uncertain
