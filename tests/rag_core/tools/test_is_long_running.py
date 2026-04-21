import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.tools.sandbox import is_long_running


# ---------------------------------------------------------------------------
# is_long_running — nhận diện code training DL
# ---------------------------------------------------------------------------

def test_is_long_running_keras_fit():
    code = "import tensorflow as tf\nmodel.fit(x_train, y_train, epochs=10)"
    assert is_long_running(code) is True


def test_is_long_running_torch_training_loop():
    code = "import torch\nfor epoch in range(100):\n    optimizer.step()"
    assert is_long_running(code) is True


def test_is_long_running_huggingface_trainer():
    code = "from transformers import Trainer\ntrainer.train()"
    assert is_long_running(code) is True


def test_is_long_running_keras_explicit():
    code = "from keras.models import Sequential\nmodel = Sequential()\nmodel.fit(X, y, epochs=20)"
    assert is_long_running(code) is True


def test_is_long_running_sklearn_fit_is_false():
    """sklearn.fit() trên toy data không phải DL — không block."""
    code = "from sklearn.linear_model import LinearRegression\nmodel = LinearRegression()\nmodel.fit(X, y)"
    assert is_long_running(code) is False


def test_is_long_running_simple_print_is_false():
    assert is_long_running("print('hello')") is False


def test_is_long_running_numpy_only_is_false():
    code = "import numpy as np\nx = np.array([1, 2, 3])\nprint(x.mean())"
    assert is_long_running(code) is False


def test_is_long_running_epoch_loop_without_dl_is_false():
    """for epoch in range(...) nhưng không có torch/tensorflow/keras → không block."""
    code = "for epoch in range(10):\n    print(epoch)"
    assert is_long_running(code) is False


def test_is_long_running_pytorch_model_train():
    code = "import torch.nn as nn\nmodel = nn.Linear(10, 1)\nmodel.train()"
    assert is_long_running(code) is True
